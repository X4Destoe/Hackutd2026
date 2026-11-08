"""Build a scenario's 7 timeline steps and hazard overlays from its hand-placed anchors.

    python -m data.make_overlays harvey_houston        # writes data/scenarios/harvey_houston.json

Anchors (data/anchors/<id>.json) describe the hazard analytically (river lines with peak depth and half-width,
pools, a snow/ice area, a storm track). This script turns them into nested GeoJSON intensity bands per step
(docs/prd/03-data-and-scenarios.md §1) and validates the result against the Scenario contract.
Footprints are approximate and illustrative.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Point, mapping

from app.shared.schemas import Scenario

DATA = Path(__file__).resolve().parent
STEPS = [(-48, "forecast"), (-24, "forecast"), (-12, "forecast"), (0, "impact"), (12, "impact"), (48, "recovery"), (168, "recovery")]
BANDS = [1.0, 0.66, 0.33]  # outer → inner share of the half-width; inner bands are deeper
MI_PER_DEG = 69.0


def _proj(lat0: float):
    """Local equirectangular projection to miles (accurate enough at city scale), and its inverse."""
    scale = np.array([math.cos(math.radians(lat0)) * MI_PER_DEG, MI_PER_DEG])
    return (lambda xy: xy * scale), (lambda xy: xy / scale)


def transform(fn, geom):
    return shapely.transform(geom, fn)


def _feature(geom, **props) -> dict:
    return {"type": "Feature", "properties": props, "geometry": mapping(geom)}


def _water_bands(anchor: dict, lat0: float, factor: float, forecast: bool) -> list[dict]:
    fwd, inv = _proj(lat0)
    feats = []
    for r in anchor.get("rivers", []):
        line = transform(fwd, LineString(r["coords"]))
        for frac in BANDS:
            width = r["half_width_mi"] * frac * (1 if forecast else factor)
            if width <= 0.01:
                continue
            depth = round(r["peak_ft"] * (1 - frac) * (1 if forecast else factor) + 0.5 * (1 if forecast else factor), 1)
            feats.append(_feature(transform(inv, line.buffer(width, quad_segs=8)), intensity=depth, source=r["name"], forecast=forecast))
    for p in anchor.get("pools", []):
        c = transform(fwd, Point(p["center"]))
        for frac in BANDS:
            radius = p["radius_mi"] * frac * (1 if forecast else max(factor, 0.4))
            depth = round(p["peak_ft"] * (1 - 0.6 * frac) * (1 if forecast else factor), 1)
            feats.append(_feature(transform(inv, c.buffer(radius, quad_segs=16)), intensity=depth, source=p["name"], forecast=forecast))
    return feats


def _wind_rings(anchor: dict, lat0: float, factor: float) -> list[dict]:
    w = anchor.get("wind")
    if not w or factor <= 0:
        return []
    fwd, inv = _proj(lat0)
    eye = transform(fwd, Point(w["eye"]))
    rings = []
    for radius, share in [(60, 0.4), (35, 0.6), (18, 0.8), (8, 1.0)]:
        rings.append(_feature(transform(inv, eye.buffer(radius, quad_segs=24)), intensity=round(w["peak_mph"] * share * factor)))
    return rings


def _track(anchor: dict) -> list[dict]:
    w = anchor.get("wind")
    return [_feature(LineString(w["track"]), intensity=w["peak_mph"])] if w else []


def _snow(anchor: dict, hour: int, forecast: bool) -> list[dict]:
    a = anchor.get("area")
    if not a:
        return []
    temp = anchor["temps"][str(hour)]
    pts = [(a["center"][0] + math.cos(t / 90 * 2 * math.pi) * a["rx"], a["center"][1] + math.sin(t / 90 * 2 * math.pi) * a["ry"]) for t in range(91)]
    from shapely.geometry import Polygon
    ice = anchor.get("ice_in", 0) if (forecast or hour <= 48) else 0
    return [_feature(Polygon(pts), intensity=ice, temp_f=temp, forecast=forecast)]


def build(scenario_id: str) -> dict:
    a = json.loads((DATA / "anchors" / f"{scenario_id}.json").read_text())
    lat0 = a["center"]["lat"]
    steps = []
    for hour, phase in STEPS:
        forecast = phase == "forecast"
        factor = a["present"][str(hour)]
        overlays = []
        water_style = "surge_water" if a["kind"] == "surge" else "flood_water"
        water_hazard = "surge" if a["kind"] == "surge" else "flood"
        if a.get("rivers") or a.get("pools"):
            feats = _water_bands(a, lat0, factor, forecast)
            if feats:
                overlays.append({"id": f"{scenario_id}-{hour}-water", "style": water_style, "hazard": water_hazard, "geojson": {"type": "FeatureCollection", "features": feats}})
        if a["kind"] == "winter":
            overlays.append({"id": f"{scenario_id}-{hour}-snow", "style": "snow_ice", "hazard": "winter",
                             "geojson": {"type": "FeatureCollection", "features": _snow(a, hour, forecast)}})
        if a.get("wind"):
            if forecast:
                overlays.append({"id": f"{scenario_id}-{hour}-track", "style": "forecast_cone", "hazard": "wind", "geojson": {"type": "FeatureCollection", "features": _track(a)}})
            rings = _wind_rings(a, lat0, 1.0 if forecast else factor)
            if rings and phase == "impact":
                overlays.append({"id": f"{scenario_id}-{hour}-wind", "style": "wind_swirl", "hazard": "wind", "geojson": {"type": "FeatureCollection", "features": rings}})
        steps.append({"hour": hour, "phase": phase, "label": f"{'+7d' if hour == 168 else ('+' if hour > 0 else ('−' if hour < 0 else '')) + str(abs(hour)) + 'h'} · {phase.title()}",
                      "overlays": overlays, "narrative": a["narrative"][str(hour)],
                      "utility_outages": [{"node_id": k, "hours": v} for k, v in a.get("outages", {}).items()]})
    scenario = {"id": a["id"], "name": a["name"], "real_event": a["real_event"], "date_label": a["date_label"], "city": a["city"],
                "center": a["center"], "zoom": a["zoom"], "hazards": a["hazards"], "steps": steps, "sources": a["sources"],
                "disclaimer": a["disclaimer"]}
    Scenario.model_validate(scenario)  # contract check
    return scenario


def main(ids: list[str]) -> None:
    for sid in ids:
        out = DATA / "scenarios" / f"{sid}.json"
        out.write_text(json.dumps(build(sid), ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"wrote {out.relative_to(DATA.parent)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1:] or [p.stem for p in (DATA / "anchors").glob("*.json")])
