"""impact: for every building, what this disaster costs the business, and why. Public interface: INTERFACE.md."""
from __future__ import annotations

import json
import logging
from typing import Iterable

from app.modules import scenarios
from app.shared import schemas
from app.shared.config import DATA_DIR
from app.shared.events import bus
from app.shared.store import store

from . import constants
from .model import Site, compute, risk_for

log = logging.getLogger(__name__)
_latest: dict[str, schemas.Impact] = {}


# ---------- links to the actions module (built later; impact must work without it) ----------

def _catalog() -> dict[str, schemas.ActionTemplate]:
    try:
        from app.modules.actions import catalog
        return catalog
    except ImportError:
        return _file_catalog()


_file_cache: dict[str, schemas.ActionTemplate] = {}


def _file_catalog() -> dict[str, schemas.ActionTemplate]:
    if not _file_cache:
        for a in json.loads((DATA_DIR / "actions.json").read_text()):
            t = schemas.ActionTemplate.model_validate(a)
            _file_cache[t.code] = t
    return _file_cache


def _approved(building_id: str) -> list[str]:
    try:
        from app.modules.actions import approved_codes
    except ImportError:
        return []
    return list(approved_codes(building_id))


# ---------- core ----------

def _site(b: schemas.Building, hour: int, codes: Iterable[str]) -> Site:
    sc = scenarios.scenario()
    catalog = _catalog()
    node = store.utilities.get(b.utility_node_id)
    return Site(hazard=scenarios.hazard_at(b.lat, b.lon, hour), water_kind="surge" if "surge" in sc.hazards else "flood",
                power_out_hours=scenarios.outage_hours(b.utility_node_id, hour),
                grid_down=scenarios.utility_down(b.utility_node_id, hour), hour=hour,
                utility_name=node.name if node else b.utility_node_id, in_scenario=b.city == sc.city,
                actions=[catalog[c] for c in dict.fromkeys(codes) if c in catalog])


def _hour(hour: int | None) -> int:
    return scenarios.step(hour).hour


def impact_for(building_id: str, hour: int | None = None, extra_actions: list[str] | None = None) -> schemas.Impact:
    """Impact with approved actions (+ what-if extra_actions). Pure function of its inputs."""
    b = store.buildings.require(building_id)
    unknown = [c for c in extra_actions or [] if c not in _catalog()]
    if unknown:
        raise KeyError(f"unknown action codes {unknown}")
    approved = _approved(building_id)
    codes = (["FLOOD_BARRIERS"] if b.systems.flood_barriers_installed else []) + approved + list(extra_actions or [])
    return compute(b, _site(b, _hour(hour), codes), with_approved_actions=bool(approved))


def baseline_for(building_id: str, hour: int | None = None) -> schemas.Impact:
    """Impact with NO plan actions (permanent installed systems still count). For 'avoided' math."""
    b = store.buildings.require(building_id)
    codes = ["FLOOD_BARRIERS"] if b.systems.flood_barriers_installed else []
    return compute(b, _site(b, _hour(hour), codes))


def recompute(hour: int | None = None) -> list[schemas.Impact]:
    """All buildings at that step (default current); caches and emits impact.updated."""
    h = _hour(hour)
    out = [impact_for(b.id, h) for b in store.buildings.list()]
    if h == scenarios.current().step_hour:
        _latest.clear()
        _latest.update({i.building_id: i for i in out})
        bus.emit("impact.updated", {"step_hour": h, "summary": summary(out).model_dump(mode="json")})
    return out


def latest() -> list[schemas.Impact]:
    """Cached impacts at the current step (recomputed on timeline.changed / plan.changed)."""
    cur = scenarios.current().step_hour
    if not _latest or next(iter(_latest.values())).step_hour != cur:
        return recompute()
    return list(_latest.values())


def summary(impacts: list[schemas.Impact] | None = None) -> schemas.PortfolioSummary:
    impacts = impacts if impacts is not None else latest()
    h = impacts[0].step_hour if impacts else scenarios.current().step_hour
    avoided = approved_count = 0
    for i in impacts:
        codes = _approved(i.building_id)
        if codes:
            approved_count += len(codes)
            avoided += baseline_for(i.building_id, h).money.net_exposure_cents - i.money.net_exposure_cents
    m = [i.money for i in impacts]
    worst = sorted((i for i in impacts if i.money.net_exposure_cents > 0), key=lambda i: -i.money.net_exposure_cents)
    return schemas.PortfolioSummary(
        scenario_id=scenarios.current().scenario_id, step_hour=h,
        buildings_at_risk=sum(1 for i in impacts if i.risk != "none"),
        gross_loss_cents=sum(x.property_damage_cents + x.rent_abatement_cents + x.sla_penalty_cents + x.operations_cents for x in m),
        net_exposure_cents=sum(x.net_exposure_cents for x in m), avoided_cents=avoided, actions_approved=approved_count,
        worst_building_ids=[i.building_id for i in worst[:5]],
        insurance_recovery_cents=sum(x.insurance_recovery_cents for x in m))


def site_safe(lat: float, lon: float, utility_node_id: str | None = None, hour: int | None = None) -> bool:
    """Is a help site usable right now? Uses the PRESENT hazard (water recedes, power returns)."""
    hz = scenarios.hazard_at(lat, lon, hour, present=True)
    if hz["flood_depth_ft"] > constants.SAFE_MAX_WATER_FT or hz["wind_mph"] > constants.SAFE_MAX_WIND_MPH or hz["in_burn_zone"]:
        return False
    return not (utility_node_id and scenarios.utility_down(utility_node_id, hour))


def register() -> None:
    for event in ("scenario.loaded", "timeline.changed", "plan.changed"):
        bus.on(event, lambda _payload: recompute())


from .routes import router  # noqa: E402

__all__ = ["register", "recompute", "impact_for", "baseline_for", "summary", "site_safe", "latest", "risk_for", "router"]
