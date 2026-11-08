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
RETRY_SECONDS = 60           # after a failed refresh, wait this long before trying again (no retry storm)
GAUGE_RADIUS_MI = 5.0
LIVE_DIR = DATA_DIR / "live"
CACHE_FILE = LIVE_DIR / "cache" / "last.json"   # git-ignored
SEED_FILE = LIVE_DIR / "seed.json"               # committed: a real recorded snapshot for offline demos
NOTES = ["No free real-time power-outage feed exists, so live mode shows no utility outages.",
         "NWS alerts give areas and severity, not depths: hazard intensities in live mode are labeled proxies."]

_lock = threading.Lock()
_state: dict = {"snapshot": None, "loaded_at": 0.0, "last_attempt": 0.0, "refreshing": False, "errors": [], "hourly_urls": {}}


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


def build_snapshot(c, buildings: list[dict], hourly_urls: dict[str, str] | None = None,
                   previous: dict | None = None) -> tuple[dict, list[str]]:
    """Fetch every feed once. Feeds fail independently: a failed feed keeps its last good value and as-of time from
    `previous` and records the error, so a partial outage never wipes good data or looks fresh."""
    errors: list[str] = []
    hourly_urls = hourly_urls if hourly_urls is not None else {}
    prev = previous or {}
    prev_feeds, now = prev.get("feeds", {}), feeds.now_iso()
    feed_state: dict[str, dict] = {}

    def run(key: str, label: str, fetch, keep):
        try:
            value = fetch()
            feed_state[key] = {"as_of": now, "error": None}
            return value
        except Exception as e:  # noqa: BLE001 - one feed failing must not stop the others
            errors.append(f"{label}: {type(e).__name__}")
            feed_state[key] = {"as_of": (prev_feeds.get(key) or {}).get("as_of"), "error": type(e).__name__}
            return keep

    alerts = run("alerts", "NWS alerts", lambda: feeds.fetch_alerts(c, states()), prev.get("alerts"))
    conditions: dict[str, dict] = {}
    gauges_by_city: dict[str, list] = {}
    for city, spec in _cities(buildings).items():
        def forecast(city=city, spec=spec):
            summary, hourly_urls[city] = feeds.fetch_forecast(c, spec["lat"], spec["lon"], hourly_urls.get(city))
            return summary
        value = run(f"forecast:{city}", f"NWS forecast {city}", forecast, (prev.get("conditions") or {}).get(city))
        if value is not None:
            conditions[city] = value
        value = run(f"gauges:{city}", f"USGS gauges {city}", lambda spec=spec: feeds.fetch_gauges(c, spec["bbox"]),
                    (prev.get("gauges_by_city") or {}).get(city))
        if value is not None:
            gauges_by_city[city] = value
    gauges = [g for city in sorted(gauges_by_city) for g in gauges_by_city[city]]
    nearest = {}
    for b in buildings:
        best = min(gauges, key=lambda g: feeds.miles((b["lat"], b["lon"]), (g["lat"], g["lon"])), default=None)
        if best and (d := feeds.miles((b["lat"], b["lon"]), (best["lat"], best["lon"]))) <= GAUGE_RADIUS_MI:
            nearest[b["id"]] = {**best, "distance_mi": round(d, 1)}
    snap = {"fetched_at": now, "states": states(), "alerts": alerts, "conditions": conditions, "gauges": gauges,
            "gauges_by_city": gauges_by_city, "building_gauges": nearest, "feeds": feed_state,
            "sources": ["NWS api.weather.gov (alerts, hourly forecast)", "USGS Water Services (gage height)"]}
    return snap, errors


def _usable(snap: dict | None) -> bool:
    return bool(snap and (snap.get("alerts") is not None or snap.get("conditions") or snap.get("gauges")))


def _refresh_worker() -> None:
    try:
        with feeds.client() as c:
            snap, errors = build_snapshot(c, _portfolio(), dict(_state["hourly_urls"]), previous=_state["snapshot"])
        with _lock:
            _state["errors"] = errors
            if _usable(snap):
                _state["snapshot"] = snap
                if not errors:
                    _state["loaded_at"] = time.time()
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
        _state["last_attempt"] = time.time()
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
        t = time.time()
        ok_due = t - _state["loaded_at"] > CACHE_SECONDS            # last full success is old
        retry_ok = t - _state.get("last_attempt", 0.0) > (CACHE_SECONDS if not _state["errors"] else RETRY_SECONDS)
        due = ok_due and retry_ok
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
    """Overall and per-feed freshness. A feed with no data or older than 15 minutes is stale: consumers treat it as
    UNKNOWN, never as 'no hazard'."""
    snap = _state["snapshot"] or {}
    per_feed = {}
    for key, f in (snap.get("feeds") or {}).items():
        age = _age_seconds(f.get("as_of"))
        per_feed[key] = {"as_of": f.get("as_of"), "age_seconds": None if age is None else round(age),
                         "stale": age is None or age > STALE_SECONDS, "error": f.get("error")}
    age = _age_seconds(snap.get("fetched_at"))
    alerts = (snap.get("alerts") or {}).get("features", [])
    return {"fetched_at": snap.get("fetched_at"), "age_seconds": None if age is None else round(age),
            "stale": not per_feed or any(f["stale"] for f in per_feed.values()), "refreshing": _state["refreshing"],
            "states": snap.get("states", states()), "feeds": per_feed, "alert_count": len(alerts),
            "alerts_without_area": (snap.get("alerts") or {}).get("without_area", 0), "gauge_count": len(snap.get("gauges", [])),
            "cities": sorted(snap.get("conditions", {})), "sources": snap.get("sources", []), "errors": list(_state["errors"]),
            "notes": NOTES}


def register() -> None:
    """Nothing to subscribe to; the first snapshot() call starts fetching."""


from .routes import router  # noqa: E402

__all__ = ["snapshot", "status", "refresh", "build_snapshot", "register", "router", "NOTES"]
