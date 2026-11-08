from __future__ import annotations

import hashlib
import json
import math
import secrets
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared import schemas

CITIES = {
    "houston": {"name": "Houston", "lat": 29.75, "lon": -95.47, "zoom": 10.0},
    "dallas": {"name": "Dallas", "lat": 32.84, "lon": -96.82, "zoom": 10.0},
    "fort_myers": {"name": "Fort Myers", "lat": 26.56, "lon": -81.84, "zoom": 10.0},
}
DISASTERS = {"flood": "Flood", "hurricane": "Hurricane", "windstorm": "Windstorm", "winter": "Winter storm", "surge": "Storm surge"}
HOURS = [-48, -24, -12, 0, 12, 48, 168]
PRESENT = {"-48": 0, "-24": 0, "-12": 0, "0": 1, "12": 0.85, "48": 0.35, "168": 0}


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    city: Literal["houston", "dallas", "fort_myers", "random"]
    disaster: Literal["flood", "hurricane", "windstorm", "winter", "surge"]
    water_ft: float = Field(default=6, ge=0, le=20)
    wind_mph: float = Field(default=100, ge=0, le=180)
    outage_hours: int = Field(default=24, ge=0, le=168)
    temperature_f: float = Field(default=10, ge=-30, le=32)
    ice_in: float = Field(default=0.5, ge=0, le=2)


def options() -> dict:
    return {"cities": [{"id": key, **city} for key, city in CITIES.items()],
            "disasters": [{"id": key, "name": name, "cities": ["fort_myers"] if key == "surge" else list(CITIES)} for key, name in DISASTERS.items()],
            "disclaimer": "Synthetic planning exercise. Hazard footprints and effects are hypothetical, not forecasts or verified local conditions."}


def _ring(lon: float, lat: float, radius_mi: float) -> list[list[float]]:
    points = [[lon + math.cos(i * math.tau / 64) * radius_mi / (69 * math.cos(math.radians(lat))),
               lat + math.sin(i * math.tau / 64) * radius_mi / 69] for i in range(64)]
    return points + [points[0]]


def build(request: SimulationRequest, utilities: list[schemas.UtilityNode]) -> tuple[schemas.Scenario, dict, SimulationRequest]:
    # Restrict random surge selection to the supported coastal city.
    if request.city == "random":
        request = request.model_copy(update={"city": "fort_myers" if request.disaster == "surge" else secrets.choice(list(CITIES))})
    if request.disaster == "surge" and request.city != "fort_myers":
        raise ValueError("Storm surge is available only for the supported coastal city, Fort Myers")
    city = CITIES[request.city]
    lon, lat = city["lon"], city["lat"]
    digest = hashlib.sha256(json.dumps(request.model_dump(), sort_keys=True).encode()).hexdigest()[:12]
    sid = f"custom_{request.city}_{request.disaster}_{digest}"
    wet = request.disaster in ("flood", "hurricane", "surge")
    windy = request.disaster in ("hurricane", "windstorm")
    winter = request.disaster == "winter"
    water_kind = "surge" if request.disaster == "surge" else "flood"
    hazards = ([water_kind] if wet else []) + (["wind"] if windy else []) + (["winter"] if winter else [])
    anchors = {"id": sid, "kind": "winter" if winter else water_kind if wet else "wind", "present": PRESENT.copy(),
               "_comment": "Synthetic exercise anchors; not observed or forecast hazard geography."}
    if wet:
        anchors["pools"] = [{"center": [lon, lat], "radius_mi": 12, "peak_ft": request.water_ft}]
    if windy:
        anchors["wind"] = {"track": [[lon - 0.2, lat - 0.2], [lon + 0.2, lat + 0.2]], "peak_mph": request.wind_mph}
    if winter:
        anchors.update(area={"center": [lon, lat], "rx": 12 / (69 * math.cos(math.radians(lat))), "ry": 12 / 69},
                       ice_in=request.ice_in, temps={str(h): t for h, t in zip(HOURS, [40, max(32, request.temperature_f + 10), request.temperature_f + 5, request.temperature_f, min(32, request.temperature_f + 3), 40, 50])})
    steps = []
    for hour in HOURS:
        phase = "forecast" if hour < 0 else "impact" if hour <= 12 else "recovery"
        factor = 1 if hour < 0 else PRESENT[str(hour)]
        overlays = []
        def add(style, hazard, radius, intensity):
            overlays.append(schemas.Overlay(id=f"{sid}-{hour}-{style}-{radius}", style=style, hazard=hazard,
                geojson={"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
                    "forecast": hour < 0, "intensity": intensity, "source": "Synthetic exercise geometry"},
                    "geometry": {"type": "Polygon", "coordinates": [_ring(lon, lat, radius)]}}]}))
        if wet and request.water_ft > 0 and factor:
            for radius in (12, 9, 6, 3):
                add("surge_water" if water_kind == "surge" else "flood_water", water_kind, radius,
                    round(request.water_ft * (1 - 0.6 * radius / 12) * factor, 2))
        if windy and request.wind_mph > 0 and factor:
            add("wind_swirl", "wind", 30, round(request.wind_mph * factor, 1))
        if winter and (hour < 0 or hour <= 48):
            add("snow_ice", "winter", 12, request.ice_in)
        outages = [schemas.UtilityOutage(node_id=node.id, hours=request.outage_hours) for node in utilities
                   if node.city == city["name"] and request.outage_hours > 0]
        effects = []
        if wet: effects.append(f"peak water {request.water_ft:g} ft at the exercise center")
        if windy: effects.append(f"peak wind {request.wind_mph:g} mph")
        if winter: effects.append(f"minimum {request.temperature_f:g}°F and {request.ice_in:g} in ice")
        effects.append(f"{request.outage_hours}h utility outage")
        steps.append(schemas.TimelineStep(hour=hour, phase=phase, label=f"{hour:+d}h · {phase.title()}", overlays=overlays,
                     utility_outages=outages, narrative=f"Custom {DISASTERS[request.disaster].lower()} exercise in {city['name']}: " + "; ".join(effects) + ". Hypothetical effects, not a forecast."))
    scenario = schemas.Scenario(id=sid, name=f"Custom {DISASTERS[request.disaster]}", real_event="Synthetic planning exercise",
        date_label="User-configured effects", city=city["name"], center={"lat": lat, "lon": lon}, zoom=city["zoom"],
        hazards=hazards, steps=steps, sources=["User-selected synthetic inputs; existing fictional portfolio and analytic impact model"],
        disclaimer=options()["disclaimer"])
    return scenario, anchors, request
