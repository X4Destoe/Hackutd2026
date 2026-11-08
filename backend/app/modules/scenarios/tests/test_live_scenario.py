import copy

import pytest
from fastapi.testclient import TestClient

import app.modules.live as live
from app.main import create_app
from app.modules import impact
from app.modules import scenarios as sc
from app.modules.scenarios import live_scenario
from app.shared.events import bus
from app.shared.store import store


def square(lon, lat, d=0.03):
    return {"type": "Polygon", "coordinates": [[[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]]}


def alert(event, severity, geometry, headline="h"):
    return {"type": "Feature", "geometry": geometry, "properties": {"event": event, "severity": severity, "headline": headline,
                                                                  "ends": "2026-11-09T00:00:00Z"}}


BAYOU = (-95.3625, 29.7567)
SNAP = {
    "fetched_at": "2026-11-08T06:00:00+00:00", "states": ["TX", "FL"],
    "alerts": {"type": "FeatureCollection", "features": [
        alert("Flood Warning", "Severe", square(*BAYOU), "Flood Warning for Buffalo Bayou"),
        alert("Rip Current Statement", "Moderate", square(-95.0, 29.3)),          # not modeled -> ignored
        alert("Flood Warning", "Severe", square(-99.0, 29.7)),                     # far from Houston -> ignored
    ]},
    "conditions": {"Houston": {"hours": 48, "min_temp_f": 61, "max_wind_mph": 12, "max_precip_pct": 80, "now_temp_f": 66,
                               "now_wind_mph": 5, "now": "Rain", "worst": "Heavy rain"}},
    "gauges": [], "gauges_by_city": {}, "building_gauges": {},
    "feeds": {"alerts": {"as_of": "x", "error": None}, "forecast:Houston": {"as_of": "x", "error": None}},
}
FRESH = {"feeds": {"alerts": {"stale": False}, "forecast:Houston": {"stale": False}, "gauges:Houston": {"stale": False}}}


@pytest.fixture
def c(monkeypatch):
    state = {"snap": copy.deepcopy(SNAP), "status": copy.deepcopy(FRESH)}
    monkeypatch.setattr(live, "snapshot", lambda: state["snap"])
    monkeypatch.setattr(live, "status", lambda: state["status"])
    sc._live_built.clear()
    with TestClient(create_app()) as client:
        client.state = state
        yield client


def test_live_scenarios_are_listed_per_city(c):
    metas = {m["id"]: m for m in c.get("/api/scenarios").json()}
    for sid in ("live_houston", "live_dallas", "live_fort_myers"):
        assert metas[sid]["step_hours"] == [-24, 0] and metas[sid]["name"].startswith("Live · ")


def test_real_alert_polygons_become_labeled_proxy_overlays(c):
    assert c.post("/api/scenarios/live_houston/load").json()["step_hour"] == -24
    feats = c.get("/api/overlays").json()["features"]
    assert len(feats) == 1  # unmodeled and far-away alerts are left out
    p = feats[0]["properties"]
    assert p["style"] == "flood_water" and p["event"] == "Flood Warning" and p["proxy"] is True and p["forecast"] is True
    assert p["headline"] == "Flood Warning for Buffalo Bayou" and p["intensity"] == 2.0
    assert "proxies" in sc.scenario().disclaimer


def test_hazard_inside_a_flood_warning_is_the_documented_proxy(c):
    c.post("/api/scenarios/live_houston/load")
    hz = sc.hazard_at(BAYOU[1], BAYOU[0])
    assert hz["flood_depth_ft"] == 2.0 and hz["sources"]["water"] == "NWS Flood Warning (proxy)"
    outside = sc.hazard_at(29.70, -95.60)
    assert outside["flood_depth_ft"] == 0 and outside["wind_mph"] == 12  # forecast wind still applies


def test_impact_and_fix_first_run_unchanged_and_say_where_numbers_come_from(c):
    c.post("/api/scenarios/live_houston/load")
    i = impact.impact_for("BLD-HOU-01")
    assert i.risk != "none"
    assert any("NWS Flood Warning (proxy)" in d for d in i.drivers)
    assert "BLD-HOU-01" in [x["building_id"] for x in c.get("/api/fix-first").json()]


def test_stale_or_missing_data_is_reported_as_unknown(c):
    c.state["status"] = {"feeds": {"alerts": {"stale": True}}}
    c.post("/api/scenarios/live_houston/load")
    assert "unknown, not safe" in sc.step(-24).narrative


def test_new_live_data_rebuilds_the_scenario_and_recomputes(c):
    c.post("/api/scenarios/live_houston/load")
    seen = []
    bus.on("timeline.changed", lambda p: seen.append(p["scenario_id"]))
    c.state["snap"] = {**copy.deepcopy(SNAP), "fetched_at": "2026-11-08T06:05:00+00:00",
                       "alerts": {"type": "FeatureCollection", "features": []}}
    bus.emit("live.updated", {})
    assert seen == ["live_houston"]
    assert c.get("/api/overlays").json()["features"] == [] and impact.impact_for("BLD-HOU-01").risk == "none"


def test_proxy_table():
    assert live_scenario.proxy("Flash Flood Warning", "Extreme") == ("flood_water", "flood", 4.5)
    assert live_scenario.proxy("Storm Surge Warning", "Severe")[0] == "surge_water"
    assert live_scenario.proxy("Hurricane Warning", "Extreme") == ("wind_swirl", "wind", 90.0)
    assert live_scenario.proxy("Rip Current Statement", "Moderate") is None
