"""Analytic hazard model over a scenario's anchors (data/anchors/<id>.json). Pure functions, no state.

Same formulas as demo/model.js and data/make_overlays.py (the drawn overlay bands are a coarser picture of this):
  water depth (ft)  = peak * (1 - d / half_width)        within half_width miles of a river/coast line
                    = peak * (1 - 0.6 * d / radius)       within radius miles of a pool (low spot)
  wind (mph)        = peak * max(0.35, 1 - max(0, d - 8) / 80)   d = miles to the storm track
  winter            = temperature and ice inside the winter ellipse

Two readings of the same model:
  damage  (default): what has hit, or is forecast to hit, the site. Forecast steps give the predicted peak; impact and
                     recovery steps give the worst seen so far (damage doesn't un-happen). Used for money.
  present (present=True): conditions physically at the site at that step. Used for "is this help site safe right now".
"""
from __future__ import annotations

import math

MI_PER_DEG = 69.0


def _xy(lon: float, lat: float, lat0: float) -> tuple[float, float]:
    return lon * math.cos(math.radians(lat0)) * MI_PER_DEG, lat * MI_PER_DEG


def dist_mi(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Miles between two (lon, lat) points."""
    lat0 = (a[1] + b[1]) / 2
    (ax, ay), (bx, by) = _xy(*a, lat0), _xy(*b, lat0)
    return math.hypot(ax - bx, ay - by)


def dist_to_line_mi(p: tuple[float, float], line: list[list[float]]) -> float:
    """Miles from (lon, lat) to the nearest point of a polyline of [lon, lat]."""
    px, py = _xy(*p, p[1])
    best = math.inf
    for (lon_a, lat_a), (lon_b, lat_b) in zip(line, line[1:]):
        (ax, ay), (bx, by) = _xy(lon_a, lat_a, p[1]), _xy(lon_b, lat_b, p[1])
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ((dx * dx + dy * dy) or 1)))
        best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def factor(anchors: dict, hour: int, present: bool) -> float:
    """Share of the peak hazard at this step."""
    shares = {int(h): v for h, v in anchors["present"].items()}
    if present:
        return shares.get(hour, 0.0)
    if hour < 0:
        return 1.0  # forecast: the predicted peak
    return max((v for h, v in shares.items() if 0 <= h <= hour), default=0.0)


def _winter(anchors: dict, lon: float, lat: float, hour: int, present: bool) -> tuple[float | None, float]:
    area = anchors.get("area")
    if anchors.get("kind") != "winter" or not area:
        return None, 0.0
    (cx, cy), rx, ry = area["center"], area["rx"], area["ry"]
    if ((lon - cx) / rx) ** 2 + ((lat - cy) / ry) ** 2 > 1:
        return None, 0.0
    temps = {int(h): t for h, t in anchors["temps"].items()}
    ice = anchors.get("ice_in", 0.0)
    if present:
        return temps.get(hour), ice if 0 <= hour <= 48 else 0.0
    # forecast: the predicted coldest; impact: that step; recovery: the coldest seen so far (PRD 03 §3 peak rule)
    if hour < 0:
        return min(temps.values()), ice
    if hour <= 12:
        return temps[hour], ice
    return min(t for h, t in temps.items() if 0 <= h <= hour), ice


def hazard_at(anchors: dict, lat: float, lon: float, hour: int, present: bool = False) -> dict:
    f = factor(anchors, hour, present)
    p = (lon, lat)
    water = 0.0
    for r in anchors.get("rivers", []):
        d = dist_to_line_mi(p, r["coords"])
        if d < r["half_width_mi"]:
            water = max(water, r["peak_ft"] * (1 - d / r["half_width_mi"]) * f)
    for pool in anchors.get("pools", []):
        d = dist_mi(p, tuple(pool["center"]))
        if d < pool["radius_mi"]:
            water = max(water, pool["peak_ft"] * (1 - 0.6 * d / pool["radius_mi"]) * f)
    wind = 0.0
    if anchors.get("wind"):
        w = anchors["wind"]
        d = dist_to_line_mi(p, w["track"])
        wind = w["peak_mph"] * max(0.35, 1 - max(0.0, d - 8) / 80) * f
    temp, ice = _winter(anchors, lon, lat, hour, present)
    return {"flood_depth_ft": round(water, 2), "wind_mph": round(wind, 1), "ice_in": ice, "temp_f": temp,
            "in_burn_zone": False}
