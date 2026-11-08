"""scenarios: the world - disaster presets, timeline, portfolio seed, demo state and the hazard lookup.

Public interface: see INTERFACE.md. Other modules import only `from app.modules import scenarios`.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from collections import OrderedDict
from functools import lru_cache

from app.shared import schemas
from app.shared.config import DATA_DIR, settings
from app.shared.events import bus
from app.shared.store import store

from . import hazard, live_scenario

log = logging.getLogger(__name__)
_lock = threading.RLock()
STATE_KEY = "demo"
RUNTIME_LIMIT = 16
_runtime: OrderedDict[str, tuple[schemas.Scenario, dict]] = OrderedDict()


# ---------- data files ----------

_live_built: dict[str, tuple[tuple, schemas.Scenario]] = {}


def _live_snapshot() -> dict:
    from app.modules import live
    return live.snapshot()


def _live_scenario(scenario_id: str) -> schemas.Scenario:
    """Built from the live snapshot; rebuilt only when new data arrives."""
    from app.modules import live
    snap = live.snapshot()
    freshness = live.status()
    city = live_scenario.CITIES[scenario_id]
    feeds = freshness.get("feeds") or {}
    fingerprint = tuple((key, (feeds.get(key) or {}).get("as_of"), (feeds.get(key) or {}).get("stale", True),
                         (feeds.get(key) or {}).get("error")) for key in ("alerts", f"forecast:{city}", f"gauges:{city}"))
    key = (snap.get("fetched_at"), id(snap), fingerprint)
    cached = _live_built.get(scenario_id)
    if cached and cached[0] == key:
        return cached[1]
    built = live_scenario.build(scenario_id, snap, freshness)
    _live_built[scenario_id] = (key, built)
    return built


@lru_cache(maxsize=None)
def _file_scenario(scenario_id: str) -> schemas.Scenario:
    path = DATA_DIR / "scenarios" / f"{scenario_id}.json"
    if not path.exists():
        raise KeyError(f"scenario {scenario_id} not found")
    return schemas.Scenario.model_validate_json(path.read_text())


@lru_cache(maxsize=None)
def _file_anchors(scenario_id: str) -> dict:
    return json.loads((DATA_DIR / "anchors" / f"{scenario_id}.json").read_text())


def _scenario(scenario_id: str) -> schemas.Scenario:
    with _lock:
        if scenario_id in live_scenario.CITIES:
            return _live_scenario(scenario_id)
        return _runtime[scenario_id][0] if scenario_id in _runtime else _file_scenario(scenario_id)


def _anchors(scenario_id: str) -> dict:
    with _lock:
        return _runtime[scenario_id][1] if scenario_id in _runtime else _file_anchors(scenario_id)


def _seed(name: str, model):
    return [model.model_validate(x) for x in json.loads((DATA_DIR / f"{name}.json").read_text())]


def scenario_ids() -> list[str]:
    with _lock:
        return sorted({p.stem for p in (DATA_DIR / "scenarios").glob("*.json")} | set(_runtime) | set(live_scenario.CITIES))


def scenarios_meta() -> list[schemas.ScenarioMeta]:
    out = []
    with _lock:
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


def _seed_state(s: schemas.Scenario) -> schemas.DemoState:
    """Called under _lock by both loaders; publish events only after the lock is released."""
    phones = settings.demo_phone_map()
    buildings = _seed("portfolio", schemas.Building)
    utilities = _seed("utilities", schemas.UtilityNode)
    parties = _seed("parties", schemas.Party)
    for p in parties:
        if p.id in phones:
            p.phone = phones[p.id]
    store.reset()
    store.buildings.put_all(buildings)
    store.utilities.put_all(utilities)
    store.parties.put_all(parties)
    first = s.steps[0]
    state = schemas.DemoState(scenario_id=s.id, step_hour=first.hour, phase=first.phase,
                              messaging_mode=settings.messaging_mode if settings.messaging_mode in ("sim", "photon") else "sim",
                              llm_provider=_llm_provider())
    store.state[STATE_KEY] = state
    return state


def load(scenario_id: str) -> schemas.DemoState:
    """Reset/reseed a historical or registered custom scenario; emit the normal scenario.loaded event."""
    with _lock:
        s = _scenario(scenario_id)
        if scenario_id not in live_scenario.CITIES:
            _anchors(scenario_id)  # fail before resetting if data is missing
        state = _seed_state(s)
    bus.emit("scenario.loaded", state.model_dump(mode="json"))
    return state


def load_definition(definition: schemas.Scenario, anchors: dict) -> schemas.DemoState:
    """Register/activate a bounded in-memory synthetic definition; never overwrite historical JSON."""
    s = schemas.Scenario.model_validate(definition.model_dump())
    if not re.fullmatch(r"custom_[a-z0-9_]{1,120}", s.id):
        raise ValueError("Runtime scenario IDs must use the custom_ namespace")
    hours = [step.hour for step in s.steps]
    if not hours or hours != sorted(set(hours)):
        raise ValueError("A runtime scenario needs unique chronological steps")
    if not isinstance(anchors, dict):
        raise ValueError("Runtime hazard anchors must be an object")
    try:
        anchors = json.loads(json.dumps(anchors, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError("Runtime hazard anchors must contain finite JSON values") from exc
    if anchors.get("id") != s.id or anchors.get("kind") not in ("flood", "surge", "winter", "wind"):
        raise ValueError("Runtime anchor identity or hazard kind is invalid")
    shares = anchors.get("present")
    if not isinstance(shares, dict) or any(str(hour) not in shares for hour in hours):
        raise ValueError("Runtime anchors must describe present conditions at every step")
    if any(not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in shares.values()):
        raise ValueError("Present hazard fractions must be between zero and one")
    if anchors["kind"] == "winter" and (not anchors.get("area") or any(str(hour) not in anchors.get("temps", {}) for hour in hours)):
        raise ValueError("Winter runtime anchors need an area and temperatures for every step")
    if s.city not in {building.city for building in _seed("portfolio", schemas.Building)}:
        raise ValueError("No seeded portfolio exists for this runtime city")
    with _lock:
        _runtime[s.id] = (s, anchors)
        _runtime.move_to_end(s.id)
        state = _seed_state(s)
        while len(_runtime) > RUNTIME_LIMIT:
            _runtime.popitem(last=False)
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

def data_quality() -> str:
    sid = current().scenario_id
    if sid not in live_scenario.CITIES:
        return "modeled"
    from app.modules import live
    return live_scenario.data_quality(live.snapshot(), live.status(), live_scenario.CITIES[sid])

def hazard_at(lat: float, lon: float, hour: int | None = None, present: bool = False) -> dict:
    """{"flood_depth_ft","wind_mph","ice_in","temp_f","in_burn_zone"} at a point.

    Default (damage reading): forecast steps give the predicted peak; impact/recovery steps give the worst so far.
    present=True: conditions physically there at that step (water receding, power back) - use for help-site safety.
    flood_depth_ft is storm surge when "surge" is in scenario().hazards. temp_f is None outside the winter area.
    """
    sid = current().scenario_id
    if sid in live_scenario.CITIES:  # labeled proxies from real NWS alerts + forecast (same reading now and in the window)
        from app.modules import live
        snapshot = _live_snapshot()
        return {**live_scenario.hazard_at(snapshot, sid, lat, lon),
                "data_quality": live_scenario.data_quality(snapshot, live.status(), live_scenario.CITIES[sid])}
    return hazard.hazard_at(_anchors(sid), lat, lon, _hour(hour), present)


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


def _on_live_updated(_payload: dict) -> None:
    """New real-time data while a live scenario is shown: rebuild it and let everyone recompute."""
    state = store.state.get(STATE_KEY)
    if state is not None and state.scenario_id in live_scenario.CITIES:
        _live_built.pop(state.scenario_id, None)
        bus.emit("timeline.changed", state.model_dump(mode="json"))


def register() -> None:
    bus.on("live.updated", _on_live_updated)


from .routes import router  # noqa: E402  (routes use the functions above)

__all__ = ["load", "load_definition", "current", "scenario", "step", "set_hour", "hazard_at", "utility_down", "outage_hours", "overlays",
           "scenarios_meta", "scenario_ids", "data_quality", "register", "router"]
