"""live: real-time hazard feeds (NWS alerts + hourly forecasts, USGS gauges) for the portfolio's cities. Interface: INTERFACE.md.

Never blocks a request on the network: snapshot() returns what is cached and refreshes in a background thread when it is
older than CACHE_SECONDS. With no network it falls back to the last good snapshot on disk, then to the committed seed.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

from app.shared.config import DATA_DIR
from app.shared.events import bus

from . import feeds

log = logging.getLogger(__name__)
CACHE_SECONDS = 300          # refresh at most every 5 minutes (NWS asks clients not to hammer)
STALE_SECONDS = 900          # older than 15 minutes = stale (shown in the UI)
GAUGE_RADIUS_MI = 5.0
LIVE_DIR = DATA_DIR / "live"
CACHE_FILE = LIVE_DIR / "cache" / "last.json"   # git-ignored
SEED_FILE = LIVE_DIR / "seed.json"               # committed: a real recorded snapshot for offline demos
NOTES = ["No free real-time power-outage feed exists, so live mode shows no utility outages.",
         "NWS alerts give areas and severity, not depths: hazard intensities in live mode are labeled proxies."]

_lock = threading.Lock()
_state: dict = {"snapshot": None, "loaded_at": 0.0, "refreshing": False, "errors": [], "hourly_urls": {}}


def states() -> list[str]:
    return [s.strip().upper() for s in os.environ.get("LIVE_STATES", "TX,FL").split(",") if s.strip()]


def _portfolio() -> list[dict]:
    from app.shared.store import store
    buildings = [b.model_dump(mode="json") for b in store.buildings.list()]
    return buildings or json.loads((DATA_DIR / "portfolio.json").read_text())


def _cities(buildings: list[dict]) -> dict[str, dict]:
    """One forecast point (centroid) and one gauge search box per portfolio city."""
    out: dict[str, dict] = {}
    for city in sorted({b["city"] for b in buildings}):
        pts = [(b["lat"], b["lon"]) for b in buildings if b["city"] == city]
        lats, lons = [p[0] for p in pts], [p[1] for p in pts]
        out[city] = {"lat": sum(lats) / len(lats), "lon": sum(lons) / len(lons),
                     "bbox": (min(lons) - 0.08, min(lats) - 0.08, max(lons) + 0.08, max(lats) + 0.08)}
    return out


def build_snapshot(c, buildings: list[dict], hourly_urls: dict[str, str] | None = None) -> tuple[dict, list[str]]:
    """Fetch everything once. Each source fails independently; errors are returned, never raised."""
    errors: list[str] = []
    hourly_urls = hourly_urls if hourly_urls is not None else {}
    try:
        alerts = feeds.fetch_alerts(c, states())
    except Exception as e:  # noqa: BLE001 - one feed failing must not stop the others
        errors.append(f"NWS alerts: {type(e).__name__}")
        alerts = None
    conditions, gauges = {}, []
    for city, spec in _cities(buildings).items():
        try:
            conditions[city], hourly_urls[city] = feeds.fetch_forecast(c, spec["lat"], spec["lon"], hourly_urls.get(city))
        except Exception as e:  # noqa: BLE001
            errors.append(f"NWS forecast {city}: {type(e).__name__}")
        try:
            gauges += feeds.fetch_gauges(c, spec["bbox"])
        except Exception as e:  # noqa: BLE001
            errors.append(f"USGS gauges {city}: {type(e).__name__}")
    nearest = {}
    for b in buildings:
        best = min(gauges, key=lambda g: feeds.miles((b["lat"], b["lon"]), (g["lat"], g["lon"])), default=None)
        if best and (d := feeds.miles((b["lat"], b["lon"]), (best["lat"], best["lon"]))) <= GAUGE_RADIUS_MI:
            nearest[b["id"]] = {**best, "distance_mi": round(d, 1)}
    snap = {"fetched_at": feeds.now_iso(), "states": states(), "alerts": alerts, "conditions": conditions,
            "gauges": gauges, "building_gauges": nearest,
            "sources": ["NWS api.weather.gov (alerts, hourly forecast)", "USGS Water Services (gage height)"]}
    return snap, errors


def _usable(snap: dict | None) -> bool:
    return bool(snap and snap.get("alerts") is not None and snap.get("conditions"))


def _refresh_worker() -> None:
    try:
        with feeds.client() as c:
            snap, errors = build_snapshot(c, _portfolio(), dict(_state["hourly_urls"]))
        with _lock:
            _state["errors"] = errors
            if _usable(snap):
                _state["snapshot"], _state["loaded_at"] = snap, time.time()
                CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                CACHE_FILE.write_text(json.dumps(snap))
        if _usable(snap):
            bus.emit("live.updated", status())
    except Exception:  # noqa: BLE001
        log.exception("live refresh failed")
        with _lock:
            _state["errors"] = ["live refresh failed"]
    finally:
        with _lock:
            _state["refreshing"] = False


def refresh(block: bool = False) -> None:
    """Start a background refresh (or run it inline with block=True, for scripts)."""
    with _lock:
        if _state["refreshing"]:
            return
        _state["refreshing"] = True
    if block:
        _refresh_worker()
    else:
        threading.Thread(target=_refresh_worker, name="live-refresh", daemon=True).start()


def _load_from_disk() -> None:
    for path in (CACHE_FILE, SEED_FILE):
        if path.exists():
            try:
                _state["snapshot"] = json.loads(path.read_text())
                _state["loaded_at"] = 0.0  # disk data is old by definition: refresh soon
                return
            except ValueError:
                continue


def snapshot() -> dict:
    """Latest snapshot (possibly stale or the recorded seed). Kicks off a refresh when due. Never waits for the network."""
    with _lock:
        if _state["snapshot"] is None:
            _load_from_disk()
        due = time.time() - _state["loaded_at"] > CACHE_SECONDS
        snap = _state["snapshot"]
    if due and os.environ.get("LIVE_FETCH", "1") != "0":
        refresh()
    return snap or {"fetched_at": None, "alerts": {"type": "FeatureCollection", "features": []}, "conditions": {}, "gauges": [],
                    "building_gauges": {}, "sources": [], "states": states()}


def _age_seconds(fetched_at: str | None) -> float | None:
    if not fetched_at:
        return None
    from datetime import datetime, timezone
    return (datetime.now(timezone.utc) - datetime.fromisoformat(fetched_at)).total_seconds()


def status() -> dict:
    snap = _state["snapshot"] or {}
    age = _age_seconds(snap.get("fetched_at"))
    alerts = (snap.get("alerts") or {}).get("features", [])
    return {"fetched_at": snap.get("fetched_at"), "age_seconds": None if age is None else round(age),
            "stale": age is None or age > STALE_SECONDS, "refreshing": _state["refreshing"], "states": snap.get("states", states()),
            "alert_count": len(alerts), "alerts_without_area": (snap.get("alerts") or {}).get("without_area", 0),
            "gauge_count": len(snap.get("gauges", [])), "cities": sorted(snap.get("conditions", {})),
            "sources": snap.get("sources", []), "errors": list(_state["errors"]), "notes": NOTES}


def register() -> None:
    """Nothing to subscribe to; the first snapshot() call starts fetching."""


from .routes import router  # noqa: E402

__all__ = ["snapshot", "status", "refresh", "build_snapshot", "register", "router", "NOTES"]
