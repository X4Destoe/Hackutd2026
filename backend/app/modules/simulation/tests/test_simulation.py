import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.modules import scenarios
from app.modules.simulation.model import CITIES, SimulationRequest, build
from app.shared import schemas
from app.shared.store import store


@pytest.fixture
def utilities():
    scenarios.load("harvey_houston")
    return store.utilities.list()


@pytest.mark.parametrize("city", CITIES)
@pytest.mark.parametrize("disaster", ["flood", "hurricane", "windstorm", "winter"])
def test_supported_combinations_have_valid_closed_geometry_and_city_outages(city, disaster, utilities):
    scenario, anchors, resolved = build(SimulationRequest(city=city, disaster=disaster), utilities)
    assert scenario.id.startswith("custom_")
    assert scenario.real_event == "Synthetic planning exercise"
    assert scenario.city == CITIES[city]["name"]
    assert anchors["id"] == scenario.id
    assert resolved.city == city
    for step in scenario.steps:
        assert all(store.utilities.require(outage.node_id).city == scenario.city for outage in step.utility_outages)
        for overlay in step.overlays:
            for feature in overlay.geojson["features"]:
                ring = feature["geometry"]["coordinates"][0]
                assert ring[0] == ring[-1] and len(ring) >= 4
                assert all(-180 <= lon <= 180 and -90 <= lat <= 90 for lon, lat in ring)


def test_controls_drive_model_anchors_and_rendered_intensities(utilities):
    a, aa, _ = build(SimulationRequest(city="houston", disaster="hurricane", water_ft=2, wind_mph=60, outage_hours=6), utilities)
    b, ab, _ = build(SimulationRequest(city="houston", disaster="hurricane", water_ft=12, wind_mph=150, outage_hours=72), utilities)
    assert a.id != b.id
    assert aa["pools"][0]["peak_ft"] == 2 and ab["pools"][0]["peak_ft"] == 12
    assert aa["wind"]["peak_mph"] == 60 and ab["wind"]["peak_mph"] == 150
    assert {outage.hours for outage in b.steps[3].utility_outages} == {72}
    assert max(o.geojson["features"][0]["properties"]["intensity"] for o in b.steps[3].overlays) == 150


def test_winter_minimum_is_the_selected_temperature(utilities):
    for temperature in (-30, 10, 32):
        _, anchors, _ = build(SimulationRequest(city="dallas", disaster="winter", temperature_f=temperature, ice_in=1.2), utilities)
        assert min(anchors["temps"].values()) == temperature
        assert anchors["ice_in"] == 1.2


def test_zero_effects_do_not_create_water_or_wind_geometry_or_outages(utilities):
    scenario, anchors, _ = build(SimulationRequest(city="houston", disaster="hurricane", water_ft=0, wind_mph=0, outage_hours=0), utilities)
    assert all(not step.overlays and not step.utility_outages for step in scenario.steps)
    assert anchors["pools"][0]["peak_ft"] == 0


def test_surge_restricted_to_coastal_city_and_random_is_resolved(utilities):
    with pytest.raises(ValueError, match="coastal"):
        build(SimulationRequest(city="dallas", disaster="surge"), utilities)
    scenario, _, resolved = build(SimulationRequest(city="random", disaster="surge"), utilities)
    assert scenario.city == "Fort Myers" and resolved.city == "fort_myers"
    for _ in range(10):
        _, _, resolved = build(SimulationRequest(city="random", disaster="flood"), utilities)
        assert resolved.city in CITIES


@pytest.mark.parametrize("field,value", [("water_ft", -1), ("water_ft", float("nan")), ("wind_mph", 181), ("outage_hours", 169), ("temperature_f", -31), ("ice_in", 3), ("city", "anywhere"), ("disaster", "unknown")])
def test_invalid_inputs_are_rejected(field, value):
    body = {"city": "houston", "disaster": "flood", field: value}
    with pytest.raises(ValidationError):
        SimulationRequest(**body)


def test_preview_is_read_only_and_missing_loader_is_explicit(monkeypatch):
    with TestClient(create_app()) as client:
        before = scenarios.current().model_dump()
        response = client.post("/api/simulation/preview", json={"city": "dallas", "disaster": "winter"})
        assert response.status_code == 200
        assert response.json()["scenario"]["city"] == "Dallas"
        assert scenarios.current().model_dump() == before
        monkeypatch.delattr(scenarios, "load_definition", raising=False)
        assert client.post("/api/simulation/start", json={"city": "houston", "disaster": "flood"}).status_code == 503


def test_start_uses_public_loader(monkeypatch):
    called = []
    def load_definition(scenario, anchors):
        called.append((scenario, anchors))
        return schemas.DemoState(scenario_id=scenario.id, step_hour=-48, phase="forecast", messaging_mode="sim", llm_provider="templates")
    monkeypatch.setattr(scenarios, "load_definition", load_definition, raising=False)
    with TestClient(create_app()) as client:
        response = client.post("/api/simulation/start", json={"city": "houston", "disaster": "flood", "water_ft": 8})
        assert response.status_code == 200
        assert response.json()["scenario_id"].startswith("custom_houston_flood_")
        assert called[0][1]["pools"][0]["peak_ft"] == 8
