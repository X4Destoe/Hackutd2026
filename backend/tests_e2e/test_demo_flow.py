"""Cross-module demo gate: public HTTP interfaces only, with all outbound delivery simulated."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.shared.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LIVE_FETCH", "0")
    monkeypatch.setattr(settings, "messaging_mode", "sim")
    with TestClient(create_app()) as client:
        yield client


def get(client, path):
    response = client.get("/api" + path)
    assert response.status_code == 200, (path, response.text)
    return response.json()


def post(client, path, body=None):
    response = client.post("/api" + path, json=body)
    assert response.status_code == 200, (path, response.text)
    return response.json()


def assert_waterfall(impact):
    assert impact["data_quality"] == "modeled"
    money = impact["money"]
    gross = sum(money[field] for field in ("property_damage_cents", "rent_abatement_cents", "sla_penalty_cents", "operations_cents"))
    assert gross - money["insurance_recovery_cents"] == money["net_exposure_cents"]
    assert all(money[field] >= 0 for field in money)


@pytest.mark.parametrize("scenario,resident_request", [
    ("harvey_houston", "Our apartment in Memorial flooded. 2 adults need shelter and a dry place."),
    ("uri_dallas", "We are in Oak Lawn. 2 adults need a warm place, our apartment is freezing."),
    ("ian_fort_myers", "Our home in Fort Myers Beach flooded. 2 adults need shelter and a dry place."),
])
def test_full_historical_demo_from_reset_through_execution_help_and_reports(client, scenario, resident_request):
    state = post(client, "/demo/reset", {"scenario_id": scenario})
    assert state["messaging_mode"] == "sim"
    first = get(client, "/fix-first?limit=1")[0]
    plan = post(client, f"/plans/{first['plan_id']}/approve", {"by": "MGR-01"})
    assert plan["status"] == "executing"
    orders = get(client, "/workorders")
    assert orders and all(order["status"] == "sent" for order in orders)
    for order in orders:
        post(client, "/demo/simulate-message", {"party_id": order["party_id"], "text": "DONE " + order["id"]})
    assert all(order["status"] == "done" for order in get(client, "/workorders"))
    assert next(p for p in get(client, "/plans") if p["id"] == plan["id"])["status"] == "done"
    post(client, "/demo/simulate-message", {"phone": "+12145550123", "text": resident_request})
    referral = get(client, "/referrals")[0]
    assert referral["status"] == "routed"
    destination = next(site for site in get(client, "/resources") if site["id"] == referral["resource_id"])
    assert destination["status"] in ("open", "full") and destination["used"] >= referral["people"]
    for step in get(client, "/timeline"):
        post(client, "/timeline", {"hour": step["hour"]})
        for impact in get(client, "/impact"):
            assert_waterfall(impact)
        sites = {site["id"]: site for site in get(client, "/resources")}
        for current in get(client, "/referrals"):
            if current["status"] in ("routed", "rerouted"):
                assert sites[current["resource_id"]]["status"] not in ("unsafe", "closed")
        assert all(0 <= site["used"] <= site["capacity"] for site in sites.values())
    for kind in ("executive_summary", "tenant_notice"):
        report = post(client, "/reports", {"kind": kind, "building_id": plan["building_id"]})
        printable = client.get(f"/api/reports/{report['id']}/html")
        assert printable.status_code == 200 and "@media print" in printable.text
    assert all(message["channel"] == "sim" for message in get(client, "/messages"))


def test_custom_exercise_enters_same_demo_pipeline_and_reset_is_repeatable(client):
    for _ in range(2):
        state = post(client, "/simulation/start", {"city": "dallas", "disaster": "winter", "temperature_f": -5, "ice_in": 1, "outage_hours": 72})
        assert state["scenario_id"].startswith("custom_dallas_winter_")
        for impact in get(client, "/impact"):
            assert_waterfall(impact)
        candidate = get(client, "/fix-first?limit=1")[0]
        post(client, f"/plans/{candidate['plan_id']}/approve", {"by": "MGR-01"})
        assert get(client, "/workorders")
        reset = post(client, "/demo/reset")
        assert reset["scenario_id"] == state["scenario_id"]
        assert get(client, "/workorders") == [] and get(client, "/messages") == []


def test_missing_live_data_cannot_offer_sites_or_generate_false_financial_reports(client, monkeypatch):
    from app.modules import live
    monkeypatch.setattr(live, "snapshot", lambda: {"fetched_at": None, "alerts": None, "conditions": {}, "gauges": []})
    monkeypatch.setattr(live, "status", lambda: {"feeds": {}})
    post(client, "/scenarios/live_houston/load")
    assert get(client, "/portfolio/summary")["data_quality"] == "unknown"
    assert get(client, "/fix-first?community=1") == []
    assert all(site["status"] == "unsafe" for site in get(client, "/resources?city=Houston"))
    response = client.post("/api/reports", json={"kind": "executive_summary"})
    assert response.status_code == 422
    assert get(client, "/reports") == []
