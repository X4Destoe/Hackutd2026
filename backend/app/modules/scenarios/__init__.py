"""scenarios: the world - disaster presets, timeline, portfolio seed, demo state and the hazard lookup.

Public interface: see INTERFACE.md. Other modules import only `from app.modules import scenarios`.
"""
from __future__ import annotations

import json
import logging
import threading
from functools import lru_cache

from app.shared import schemas
from app.shared.config import DATA_DIR, settings
from app.shared.events import bus
from app.shared.store import store

from . import hazard

log = logging.getLogger(__name__)
_lock = threading.RLock()
STATE_KEY = "demo"


# ---------- data files ----------

@lru_cache(maxsize=None)
def _scenario(scenario_id: str) -> schemas.Scenario:
    path = DATA_DIR / "scenarios" / f"{scenario_id}.json"
    if not path.exists():
        raise KeyError(f"scenario {scenario_id} not found")
    return schemas.Scenario.model_validate_json(path.read_text())


@lru_cache(maxsize=None)
def _anchors(scenario_id: str) -> dict:
    return json.loads((DATA_DIR / "anchors" / f"{scenario_id}.json").read_text())


def _seed(name: str, model):
    return [model.model_validate(x) for x in json.loads((DATA_DIR / f"{name}.json").read_text())]


def scenario_ids() -> list[str]:
    return sorted(p.stem for p in (DATA_DIR / "scenarios").glob("*.json"))


def scenarios_meta() -> list[schemas.ScenarioMeta]:
    out = []
    for sid in scenario_ids():
        s = _scenario(sid)
        out.append(schemas.ScenarioMeta(id=s.id, name=s.name, real_event=s.real_event, date_label=s.date_label,
                                        city=s.city, hazards=s.hazards, step_hours=[st.hour for st in s.steps]))
    return out


# ---------- state ----------

def _llm_provider() -> str:
    try:
        from app.modules import ai
        return ai.provider_name()
    except Exception:  # ai is optional for this module
        return "templates"


def load(scenario_id: str) -> schemas.DemoState:
    """Reset the store, seed the portfolio, start the timeline at the first step, emit scenario.loaded."""
    s = _scenario(scenario_id)
    _anchors(scenario_id)  # fail now, not mid-demo, if the hazard anchors are missing
    phones = settings.demo_phone_map()
    with _lock:
        store.reset()
        store.buildings.put_all(_seed("portfolio", schemas.Building))
        store.utilities.put_all(_seed("utilities", schemas.UtilityNode))
        parties = _seed("parties", schemas.Party)
        for p in parties:
            if p.id in phones:
                p.phone = phones[p.id]
        store.parties.put_all(parties)
        first = s.steps[0]
        state = schemas.DemoState(scenario_id=s.id, step_hour=first.hour, phase=first.phase,
                                  messaging_mode=settings.messaging_mode if settings.messaging_mode in ("sim", "photon") else "sim",
                                  llm_provider=_llm_provider())
        store.state[STATE_KEY] = state
    bus.emit("scenario.loaded", state.model_dump(mode="json"))
    return state


def current() -> schemas.DemoState:
    state = store.state.get(STATE_KEY)
    if state is None:
        return load(settings.default_scenario)
    return state


def scenario() -> schemas.Scenario:
    return _scenario(current().scenario_id)


def _hour(hour: int | None) -> int:
    """None -> current step. A non-step hour snaps to the latest step at or before it."""
    if hour is None:
        return current().step_hour
    hours = [st.hour for st in scenario().steps]
    return max((h for h in hours if h <= hour), default=hours[0])


def step(hour: int | None = None) -> schemas.TimelineStep:
    h = _hour(hour)
    return next(st for st in scenario().steps if st.hour == h)


def set_hour(hour: int) -> schemas.DemoState:
    """Move the timeline to one of the scenario's step hours and emit timeline.changed."""
    hours = [st.hour for st in scenario().steps]
    if hour not in hours:
        raise ValueError(f"hour must be one of {hours}")
    with _lock:
        state = current().model_copy(update={"step_hour": hour, "phase": step(hour).phase})
        store.state[STATE_KEY] = state
    bus.emit("timeline.changed", state.model_dump(mode="json"))
    return state


# ---------- hazard and utilities ----------

def hazard_at(lat: float, lon: float, hour: int | None = None, present: bool = False) -> dict:
    """{"flood_depth_ft","wind_mph","ice_in","temp_f","in_burn_zone"} at a point.

    Default (damage reading): forecast steps give the predicted peak; impact/recovery steps give the worst so far.
    present=True: conditions physically there at that step (water receding, power back) - use for help-site safety.
    flood_depth_ft is storm surge when "surge" is in scenario().hazards. temp_f is None outside the winter area.
    """
    return hazard.hazard_at(_anchors(current().scenario_id), lat, lon, _hour(hour), present)


def outage_hours(node_id: str, hour: int | None = None) -> float:
    """Total predicted (forecast) or actual outage duration for the node known at that step; 0 if none."""
    return next((o.hours for o in step(hour).utility_outages if o.node_id == node_id), 0.0)


def utility_down(node_id: str, hour: int | None = None) -> bool:
    """True while the node is actually out: from landfall (hour 0) until its outage duration has passed."""
    h = _hour(hour)
    return 0 <= h < outage_hours(node_id, h)


def _v(x) -> str:
    return getattr(x, "value", x)


def overlays(hour: int | None = None) -> dict:
    """All overlays at that step as one FeatureCollection; each feature carries properties.style and .hazard."""
    feats = []
    for ov in step(hour).overlays:
        for f in ov.geojson.get("features", []):
            feats.append({**f, "properties": {**f.get("properties", {}), "style": _v(ov.style), "hazard": _v(ov.hazard),
                                              "overlay_id": ov.id}})
    return {"type": "FeatureCollection", "features": feats}


def register() -> None:
    """Nothing to subscribe to: scenarios is the source of scenario.loaded and timeline.changed."""


from .routes import router  # noqa: E402  (routes use the functions above)

__all__ = ["load", "current", "scenario", "step", "set_hour", "hazard_at", "utility_down", "outage_hours", "overlays",
           "scenarios_meta", "scenario_ids", "register", "router"]
