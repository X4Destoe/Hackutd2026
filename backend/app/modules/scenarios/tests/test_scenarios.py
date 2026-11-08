import time

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import scenarios as sc
from app.modules.scenarios import hazard
from app.shared.events import bus
from app.shared.store import store

HOURS = [-48, -24, -12, 0, 12, 48, 168]


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def above_floor(building_id: str, hour: int, **kw) -> float:
    b = store.buildings.require(building_id)
    return sc.hazard_at(b.lat, b.lon, hour, **kw)["flood_depth_ft"] - b.first_floor_elev_ft


def test_uri_load_gives_snow_overlay_and_12_buildings(client):
    state = client.post("/api/scenarios/uri_dallas/load").json()
    assert state["scenario_id"] == "uri_dallas" and state["step_hour"] == -48 and state["phase"] == "forecast"
    styles = {f["properties"]["style"] for f in client.get("/api/overlays?hour=0").json()["features"]}
    assert "snow_ice" in styles
    assert len(client.get("/api/buildings").json()) == 12


def test_three_scenarios_have_three_different_hazard_looks(client):
    looks = {}
    for meta in client.get("/api/scenarios").json():
        assert meta["step_hours"] == HOURS
        client.post(f"/api/scenarios/{meta['id']}/load")
        looks[meta["id"]] = {f["properties"]["style"] for f in client.get("/api/overlays?hour=0").json()["features"]}
    assert "flood_water" in looks["harvey_houston"] and "surge_water" in looks["ian_fort_myers"] and "snow_ice" in looks["uri_dallas"]


def test_bayou_plaza_about_3ft_at_impact_and_peak_kept_in_recovery():
    sc.load("harvey_houston")
    assert 2.5 <= above_floor("BLD-HOU-01", 0) <= 3.5
    assert above_floor("BLD-HOU-01", 168) == pytest.approx(above_floor("BLD-HOU-01", 12))  # damage doesn't un-happen
    assert above_floor("BLD-HOU-01", 168, present=True) < 0  # but the water is gone (help-site safety)
    assert above_floor("BLD-HOU-03", 0) > 3  # Meyerland: barriers useless
    assert above_floor("BLD-HOU-04", 0) <= 0  # Galleria stays dry


def test_forecast_shows_predicted_peak_but_nothing_is_physically_there_yet():
    sc.load("harvey_houston")
    assert above_floor("BLD-HOU-01", -24) == pytest.approx(above_floor("BLD-HOU-01", 0))
    b = store.buildings.require("BLD-HOU-01")
    assert sc.hazard_at(b.lat, b.lon, -24, present=True)["flood_depth_ft"] == 0


def test_stepping_the_timeline_emits_each_time_and_is_fast(client):
    client.post("/api/scenarios/harvey_houston/load")
    bus.clear_handlers()  # the 50 ms budget excludes subscribers (impact, actions recompute on this event)
    seen = []
    bus.on("timeline.changed", lambda p: seen.append(p["step_hour"]))
    for h in HOURS:
        t = time.perf_counter()
        r = client.post("/api/timeline", json={"hour": h})
        assert r.status_code == 200 and r.json()["step_hour"] == h
        assert (time.perf_counter() - t) < 0.05
    assert seen == HOURS
    assert client.get("/api/demo/state").json()["phase"] == "recovery"


def test_bad_hour_and_unknown_scenario_are_rejected(client):
    assert client.post("/api/timeline", json={"hour": 5}).status_code == 422
    assert client.post("/api/scenarios/atlantis/load").status_code == 404


def test_reset_reloads_and_clears_state(client):
    client.post("/api/scenarios/ian_fort_myers/load")
    client.post("/api/timeline", json={"hour": 12})
    state = client.post("/api/demo/reset", json={}).json()
    assert state["scenario_id"] == "ian_fort_myers" and state["step_hour"] == -48
    assert client.post("/api/demo/reset", json={"scenario_id": "uri_dallas"}).json()["scenario_id"] == "uri_dallas"


def test_utility_outages_start_at_landfall_and_end_after_their_duration(client):
    sc.load("harvey_houston")
    assert sc.outage_hours("UTL-HOU-SUB1", -24) == 96  # predicted at forecast
    assert not sc.utility_down("UTL-HOU-SUB1", -24)
    assert sc.utility_down("UTL-HOU-SUB1", 0) and sc.utility_down("UTL-HOU-SUB1", 48)
    assert not sc.utility_down("UTL-HOU-SUB1", 168)
    assert sc.outage_hours("UTL-HOU-SUB2", 0) == 0
    client.post("/api/timeline", json={"hour": 0})
    down = {u["id"]: u["down"] for u in client.get("/api/utilities").json()}
    assert down["UTL-HOU-SUB1"] and not down["UTL-HOU-SUB2"]


def test_winter_reading_inside_and_outside_the_storm():
    sc.load("uri_dallas")
    lone_star = store.buildings.require("BLD-DAL-02")
    hz = sc.hazard_at(lone_star.lat, lone_star.lon, 0)
    assert hz["temp_f"] <= 20 and hz["ice_in"] > 0
    temps = [sc.hazard_at(lone_star.lat, lone_star.lon, h)["temp_f"] for h in (-24, 0, 12, 48, 168)]
    assert temps == [2, 5, 2, 2, 2]  # forecast: predicted coldest; impact: that step; recovery: coldest seen
    assert sc.hazard_at(lone_star.lat, lone_star.lon, 168, present=True)["temp_f"] == 40
    houston = store.buildings.require("BLD-HOU-01")
    assert sc.hazard_at(houston.lat, houston.lon, 0)["temp_f"] is None


def test_demo_phones_override_party_phones(monkeypatch):
    monkeypatch.setattr(sc.settings, "demo_phones", "+12145550199:TECH-HOU-01")
    sc.load("harvey_houston")
    assert store.parties.require("TECH-HOU-01").phone == "+12145550199"


def test_hazard_formulas():
    a = {"kind": "flood", "present": {"-24": 0, "0": 1, "12": 1, "48": 0.5},
         "rivers": [{"name": "r", "peak_ft": 6, "half_width_mi": 1.0, "coords": [[-95.0, 29.0], [-95.0, 30.0]]}]}
    on_line = hazard.hazard_at(a, 29.5, -95.0, 0)["flood_depth_ft"]
    half_way = hazard.hazard_at(a, 29.5, -95.0 + 0.5 / (69 * 0.8704), 0)["flood_depth_ft"]
    assert on_line == 6 and half_way == pytest.approx(3, abs=0.05)
    assert hazard.hazard_at(a, 29.5, -94.9, 0)["flood_depth_ft"] == 0  # beyond the half-width
    assert hazard.hazard_at(a, 29.5, -95.0, 48, present=True)["flood_depth_ft"] == 3
    assert hazard.hazard_at(a, 29.5, -95.0, 48)["flood_depth_ft"] == 6


def test_timeline_steps_without_geometry(client):
    client.post("/api/scenarios/harvey_houston/load")
    steps = client.get("/api/timeline").json()
    assert [s["hour"] for s in steps] == HOURS
    assert all(s["narrative"] and s["label"] and "overlays" not in s for s in steps)
    assert steps[3]["phase"] == "impact" and steps[3]["label"].startswith("0h")
