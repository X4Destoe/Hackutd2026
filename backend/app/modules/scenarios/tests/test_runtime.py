import copy

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import scenarios
from app.shared.store import store


def test_custom_effects_drive_existing_engine_metadata_and_reset():
    with TestClient(create_app()) as client:
        before = scenarios.scenario().model_dump(mode="json")
        low = client.post("/api/simulation/start", json={"city": "houston", "disaster": "flood", "water_ft": 2, "outage_hours": 0})
        assert low.status_code == 200
        low_damage = sum(row["money"]["property_damage_cents"] for row in client.get("/api/impact").json())
        high = client.post("/api/simulation/start", json={"city": "houston", "disaster": "flood", "water_ft": 12, "outage_hours": 72})
        assert high.status_code == 200
        sid = high.json()["scenario_id"]
        assert sum(row["money"]["property_damage_cents"] for row in client.get("/api/impact").json()) > low_damage
        assert any(row["id"] == sid and row["city"] == "Houston" for row in client.get("/api/scenarios").json())
        plan = client.get("/api/fix-first").json()[0]
        assert client.post(f"/api/plans/{plan['plan_id']}/approve", json={"by": "MGR-01"}).status_code == 200
        assert client.get("/api/workorders").json()
        reset = client.post("/api/demo/reset")
        assert reset.status_code == 200 and reset.json()["scenario_id"] == sid
        assert client.get("/api/workorders").json() == []
        assert client.post("/api/scenarios/harvey_houston/load").status_code == 200
        assert scenarios.scenario().model_dump(mode="json") == before


def test_winter_controls_drive_hazard_and_city_specific_impact():
    with TestClient(create_app()) as client:
        result = client.post("/api/simulation/start", json={"city": "dallas", "disaster": "winter", "temperature_f": -10, "ice_in": 1.3, "outage_hours": 48})
        assert result.status_code == 200
        center = scenarios.scenario().center
        reading = scenarios.hazard_at(center.lat, center.lon)
        assert reading["temp_f"] == -10 and reading["ice_in"] == 1.3
        buildings = {b.id: b for b in store.buildings.list()}
        impacts = client.get("/api/impact").json()
        assert any(row["money"]["net_exposure_cents"] > 0 for row in impacts if buildings[row["building_id"]].city == "Dallas")
        assert all(row["money"]["net_exposure_cents"] == 0 for row in impacts if buildings[row["building_id"]].city != "Dallas")


def test_runtime_registry_is_bounded_and_current_definition_remains_resettable():
    with TestClient(create_app()) as client:
        ids = []
        for hours in range(20):
            result = client.post("/api/simulation/start", json={"city": "houston", "disaster": "windstorm", "outage_hours": hours})
            assert result.status_code == 200
            ids.append(result.json()["scenario_id"])
        metas = client.get("/api/scenarios").json()
        assert len([s for s in metas if s["id"].startswith("custom_")]) <= scenarios.RUNTIME_LIMIT
        assert ids[-1] in {s["id"] for s in metas}
        assert client.post("/api/demo/reset").json()["scenario_id"] == ids[-1]
        assert client.post(f"/api/scenarios/{ids[0]}/load").status_code == 404


def test_runtime_inputs_are_copied_and_validation_does_not_reset_active_state():
    with TestClient(create_app()) as client:
        client.post("/api/simulation/start", json={"city": "houston", "disaster": "flood"})
        source = scenarios.scenario().model_copy(deep=True)
        anchors = copy.deepcopy(scenarios._anchors(source.id))
        source.id = "custom_copy_test"
        anchors["id"] = source.id
        scenarios.load_definition(source, anchors)
        source.name = "Changed caller object"
        anchors["pools"][0]["peak_ft"] = 999
        assert scenarios.scenario().name != source.name
        assert scenarios.hazard_at(29.75, -95.47)["flood_depth_ft"] == 6
        state = scenarios.current().model_dump()
        invalid = scenarios.scenario().model_copy(update={"id": "harvey_houston"}, deep=True)
        with pytest.raises(ValueError, match="custom_"):
            scenarios.load_definition(invalid, anchors)
        assert scenarios.current().model_dump() == state
        with pytest.raises(ValueError, match="finite"):
            scenarios.load_definition(scenarios.scenario(), {**anchors, "bad": float("nan")})
        assert scenarios.current().model_dump() == state
