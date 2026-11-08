"""Live scenarios ('live_houston', 'live_dallas', 'live_fort_myers') built from today's real NWS/USGS data (app.modules.live).

A live scenario has two steps: −24 'Now' (forecast phase: act before the window) and 0 'Next 48 h' (the forecast window).
NWS alerts give areas and severity, not depths, so hazard intensities are LABELED PROXIES (table below), never measurements.
Missing or stale feeds are UNKNOWN: the narrative says so instead of implying 'no hazard'.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from shapely.geometry import Point, shape

from app.shared import schemas
from app.shared.config import DATA_DIR

CITIES = {"live_houston": "Houston", "live_dallas": "Dallas", "live_fort_myers": "Fort Myers"}
STEPS = [(-24, "forecast", "Now · act before the window"), (0, "impact", "Next 48 h · forecast window")]
PAD_DEG = 0.6  # alerts within this many degrees of the city's buildings belong to its live scenario

# NWS event -> (style, hazard, proxy intensity by severity). Depth in ft, wind in mph, ice in inches.
WATER = {"Flash Flood Warning": 3.0, "Flood Warning": 2.0, "Flood Advisory": 0.5, "Areal Flood Advisory": 0.5,
         "Flash Flood Statement": 1.0, "Flood Statement": 0.5}
SURGE = {"Storm Surge Warning": 4.0, "Coastal Flood Warning": 2.5, "Coastal Flood Advisory": 1.0, "Coastal Flood Statement": 0.5}
WIND = {"Hurricane Warning": 90, "Extreme Wind Warning": 115, "Tropical Storm Warning": 50, "High Wind Warning": 58}
WINTER = {"Ice Storm Warning": 0.5, "Winter Storm Warning": 0.25, "Winter Weather Advisory": 0.1, "Extreme Cold Warning": 0.0,
          "Hard Freeze Warning": 0.0, "Freeze Warning": 0.0}
SEVERITY = {"Extreme": 1.5, "Severe": 1.0, "Moderate": 0.75, "Minor": 0.5}


def proxy(event: str, severity: str | None) -> tuple[str, str, float] | None:
    """(overlay style, hazard kind, proxy intensity) for an NWS event, or None if the app does not model it."""
    k = SEVERITY.get(severity or "", 0.75)
    if event in WATER:
        return "flood_water", "flood", round(WATER[event] * k, 2)
    if event in SURGE:
        return "surge_water", "surge", round(SURGE[event] * k, 2)
    if event in WIND:
        return "wind_swirl", "wind", float(WIND[event])
    if event in WINTER:
        return "snow_ice", "winter", WINTER[event]
    return None


def _city_box(city: str) -> tuple[float, float, float, float]:
    pts = [(b["lon"], b["lat"]) for b in json.loads((DATA_DIR / "portfolio.json").read_text()) if b["city"] == city]
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    return min(lons) - PAD_DEG, min(lats) - PAD_DEG, max(lons) + PAD_DEG, max(lats) + PAD_DEG


_parsed: dict[tuple, list] = {}


def _alerts_for(snapshot: dict, city: str) -> list[tuple[dict, object, tuple[str, str, float]]]:
    """Modeled alerts near the city, with parsed shapes (cached per snapshot: plans call hazard_at hundreds of times)."""
    key = (snapshot.get("fetched_at"), id(snapshot), city)
    if key not in _parsed:
        if len(_parsed) > 16:
            _parsed.clear()
        _parsed[key] = _parse(snapshot, city)
    return _parsed[key]


def _parse(snapshot: dict, city: str) -> list[tuple[dict, object, tuple[str, str, float]]]:
    west, south, east, north = _city_box(city)
    out = []
    for f in (snapshot.get("alerts") or {}).get("features", []):
        p = f.get("properties", {})
        kind = proxy(p.get("event", ""), p.get("severity"))
        if not kind or not f.get("geometry"):
            continue
        geom = shape(f["geometry"])
        bx0, by0, bx1, by1 = geom.bounds
        if bx1 < west or bx0 > east or by1 < south or by0 > north:
            continue
        out.append((f, geom, kind))
    return out


def build(scenario_id: str, snapshot: dict, freshness: dict) -> schemas.Scenario:
    city = CITIES[scenario_id]
    alerts = _alerts_for(snapshot, city)
    cond = (snapshot.get("conditions") or {}).get(city)
    feeds = (freshness or {}).get("feeds", {})
    unknown = [k for k in ("alerts", f"forecast:{city}", f"gauges:{city}") if (feeds.get(k) or {}).get("stale", True)]
    hazards = sorted({k[1] for _, _, k in alerts}) or ["flood"]
    fetched = snapshot.get("fetched_at") or "never"
    events = sorted({f["properties"]["event"] for f, _, _ in alerts})
    now_text = (f"{len(alerts)} active NWS alert(s) near {city}: {', '.join(events)}." if alerts
                else f"No modeled NWS alerts near {city} right now.")
    if cond:
        now_text += f" Next 48 h: low {cond['min_temp_f']:g}°F, wind up to {cond['max_wind_mph']:g} mph, rain chance up to {cond['max_precip_pct']:g}%."
    if unknown:
        now_text += f" Data unavailable or stale: {', '.join(unknown)} (unknown, not safe)."
    steps = []
    for hour, phase, label in STEPS:
        feats = []
        for f, _geom, (style, hazard, value) in alerts:
            p = f["properties"]
            feats.append({"style": style, "hazard": hazard, "feature": {"type": "Feature", "geometry": f["geometry"], "properties": {
                "intensity": value, "proxy": True, "forecast": phase == "forecast", "event": p.get("event"),
                "severity": p.get("severity"), "headline": p.get("headline"), "ends": p.get("ends") or p.get("expires")}}})
        overlays = []
        for style in sorted({x["style"] for x in feats}):
            group = [x for x in feats if x["style"] == style]
            overlays.append({"id": f"{scenario_id}-{hour}-{style}", "style": style, "hazard": group[0]["hazard"],
                             "geojson": {"type": "FeatureCollection", "features": [x["feature"] for x in group]}})
        narrative = now_text if hour < 0 else (f"Forecast window: {cond['worst']}." if cond else "Forecast unavailable (unknown).")
        steps.append({"hour": hour, "phase": phase, "label": label, "overlays": overlays, "utility_outages": [], "narrative": narrative})
    pts = json.loads((DATA_DIR / "portfolio.json").read_text())
    city_pts = [b for b in pts if b["city"] == city]
    center = {"lat": sum(b["lat"] for b in city_pts) / len(city_pts), "lon": sum(b["lon"] for b in city_pts) / len(city_pts)}
    today = datetime.now(timezone.utc).strftime("%b %d, %Y")
    return schemas.Scenario.model_validate({
        "id": scenario_id, "name": f"Live · {city}", "real_event": "Active NWS alerts and forecasts (real time)",
        "date_label": f"{today} · data {fetched[11:16] if len(fetched) > 15 else fetched} UTC", "city": city, "center": center,
        "zoom": 10, "hazards": hazards, "steps": steps,
        "sources": ["NOAA National Weather Service: active alerts and hourly forecast (api.weather.gov)",
                    "USGS Water Services: instantaneous gage height"],
        "disclaimer": "Live screening view: NWS alerts carry areas and severity, not depths, so hazard intensities and dollar figures "
                      "are labeled proxies. No real-time utility outage data. Missing or stale feeds mean unknown, not safe."})


def hazard_at(snapshot: dict, scenario_id: str, lat: float, lon: float) -> dict:
    """Proxy hazard at a point: the strongest modeled alert containing it, plus the city's forecast temperature."""
    city = CITIES[scenario_id]
    pt = Point(lon, lat)
    water = wind = ice = 0.0
    winter = False
    label = {}
    for f, geom, (style, hazard, value) in _alerts_for(snapshot, city):
        if not geom.contains(pt):
            continue
        event = f["properties"].get("event")
        if hazard in ("flood", "surge") and value > water:
            water, label["water"] = value, event
        elif hazard == "wind" and value > wind:
            wind, label["wind"] = value, event
        elif hazard == "winter":
            winter, ice = True, max(ice, value)
            label["winter"] = event
    cond = (snapshot.get("conditions") or {}).get(city) or {}
    wind = max(wind, float(cond.get("max_wind_mph") or 0))
    temp = cond.get("min_temp_f") if (winter or (cond.get("min_temp_f") is not None and cond["min_temp_f"] <= 32)) else None
    sources = {k: f"NWS {v} (proxy)" for k, v in label.items()}
    if "wind" not in sources and wind:
        sources["wind"] = "NWS hourly forecast"
    return {"flood_depth_ft": round(water, 2), "wind_mph": round(wind, 1), "ice_in": ice, "temp_f": temp, "in_burn_zone": False,
            "sources": sources}
