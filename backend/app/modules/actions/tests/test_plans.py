import sys
import threading
import time
import types

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import actions as ac
from app.modules import impact as im
from app.shared.events import bus
from app.shared.store import store


@pytest.fixture
def c():
    with TestClient(create_app()) as client:
        yield client


def step(c, hour):
    assert c.post("/api/timeline", json={"hour": hour}).status_code == 200


def plan_for(building_id, status="proposed", community=False):
    found = [p for p in store.plans.list(building_id=building_id, status=status) if ac.plan_is_community(p) == community]
    return found[0] if found else None


def test_bayou_plan_has_barriers_with_roi_above_10_in_top_3(c):
    step(c, -24)
    p = plan_for("BLD-HOU-01")
    assert "FLOOD_BARRIERS" in [a.code for a in p.actions]
    assert p.roi > 10 and p.avoided_cents > 10 * p.cost_cents and p.act_by_hour <= -12
    assert "BLD-HOU-01" in [i.building_id for i in ac.fix_first(3)]


def test_after_the_contractor_deadline_a_barrier_plan_due_at_minus_12_remains(c):
    step(c, -24)
    first = plan_for("BLD-HOU-01").id
    step(c, -12)
    assert store.plans.require(first).status == "missed"
    live = plan_for("BLD-HOU-01")
    assert live.id != first and live.act_by_hour == -12 and "FLOOD_BARRIERS" in [a.code for a in live.actions]


def test_unapproved_plan_is_missed_at_impact_and_keeps_would_have_saved(c):
    step(c, -24)
    pid = plan_for("BLD-HOU-05").id
    step(c, 0)
    missed = c.get("/api/plans?status=missed&building_id=BLD-HOU-05").json()
    assert [p["id"] for p in missed][0] == pid and missed[0]["avoided_cents"] > 0


def test_plan_ids_are_stable_and_rewinding_revives_the_missed_plan(c):
    step(c, -48)
    pid = plan_for("BLD-HOU-01").id
    step(c, -24)
    assert plan_for("BLD-HOU-01").id == pid
    step(c, 0)
    step(c, -24)
    assert plan_for("BLD-HOU-01").id == pid and not plan_for("BLD-HOU-01", "missed")


def test_fix_first_countdown_changes_with_the_timeline(c):
    step(c, -48)
    left_48 = {i.building_id: i.hours_left for i in ac.fix_first()}
    step(c, -24)
    left_24 = {i.building_id: i.hours_left for i in ac.fix_first()}
    assert left_48["BLD-HOU-01"] - left_24["BLD-HOU-01"] == 24
    items = ac.fix_first()
    urgent = [i.hours_left <= 12 for i in items]
    assert urgent == sorted(urgent, reverse=True)  # deadlines within 12h first


def test_approve_lowers_net_counts_avoided_and_leaves_fix_first(c):
    step(c, -24)
    pid = plan_for("BLD-HOU-01").id
    before = im.impact_for("BLD-HOU-01").money.net_exposure_cents
    seen = []
    bus.on("plan.changed", lambda p: seen.append(p))
    r = c.post(f"/api/plans/{pid}/approve", json={"by": "MGR-01"})
    assert r.status_code == 200 and r.json()["status"] in ("approved", "executing") and r.json()["approved_by"] == "MGR-01"
    assert seen and seen[-1]["plan_id"] == pid
    assert im.impact_for("BLD-HOU-01").money.net_exposure_cents < before
    s = c.get("/api/portfolio/summary").json()
    assert s["avoided_cents"] > 0 and s["actions_approved"] >= 1
    assert "BLD-HOU-01" not in [i["building_id"] for i in c.get("/api/fix-first").json()]
    assert c.post(f"/api/plans/{pid}/approve", json={"by": "MGR-01"}).status_code == 409
    step(c, 0)
    assert store.plans.require(pid).status != "missed"  # approved plans never go missed


def test_reject_removes_the_building_from_fix_first(c):
    step(c, -24)
    pid = plan_for("BLD-HOU-02").id
    assert c.post(f"/api/plans/{pid}/reject", json={"by": "MGR-01"}).json()["status"] == "rejected"
    assert "BLD-HOU-02" not in [i.building_id for i in ac.fix_first()]


def test_community_help_site_is_listed_separately(c):
    step(c, -24)
    community = c.get("/api/fix-first?community=1").json()
    assert [i["building_id"] for i in community] == ["BLD-HOU-04"]  # Galleria: dry, powered, can host
    assert "BLD-HOU-04" not in [i["building_id"] for i in c.get("/api/fix-first").json()]


def test_generator_actions_follow_the_building(c):
    c.post("/api/scenarios/uri_dallas/load")
    step(c, -24)
    lone_star = [a.code for a in plan_for("BLD-DAL-02").actions]
    lakewood = [a.code for a in plan_for("BLD-DAL-03").actions]
    assert "GENERATOR_FUEL" in lone_star and "RENTAL_GENERATOR" not in lone_star  # has a generator
    assert "RENTAL_GENERATOR" in lakewood and "GENERATOR_FUEL" not in lakewood  # has none


def test_response_plans_after_landfall_have_no_pre_storm_actions(c):
    step(c, 0)
    for p in store.plans.list(status="proposed"):
        assert all(a.act_by_hour >= 0 for a in p.actions)


def test_catalog_route(c):
    codes = [t["code"] for t in c.get("/api/actions/catalog").json()]
    assert "FLOOD_BARRIERS" in codes and len(codes) == len(ac.catalog)


def test_a_slow_ai_provider_never_blocks_the_timeline(c, monkeypatch):
    from app.modules import ai
    monkeypatch.setattr(ai, "provider_name", lambda: "fake:slow")
    monkeypatch.setattr(ai, "rationale", lambda facts: (time.sleep(0.4), "Slow but thoughtful rationale.")[1])
    t = time.perf_counter()
    step(c, -24)
    assert time.perf_counter() - t < 0.3  # plans use the instant local text first
    assert plan_for("BLD-HOU-01").rationale.startswith("Cost $")
    deadline = time.time() + 3
    while time.time() < deadline and plan_for("BLD-HOU-01").rationale != "Slow but thoughtful rationale.":
        time.sleep(0.05)
    assert plan_for("BLD-HOU-01").rationale == "Slow but thoughtful rationale."  # upgraded in the background


def test_concurrent_approvals_decide_a_plan_exactly_once(c, monkeypatch):
    calls = []
    fake = types.ModuleType("app.modules.actions.execute")
    fake.on_approved = lambda plan: (calls.append(plan.id), time.sleep(0.05))[0] and None
    monkeypatch.setitem(sys.modules, "app.modules.actions.execute", fake)
    step(c, -24)
    pid = plan_for("BLD-HOU-01").id
    barrier, results = threading.Barrier(2), []

    def go():
        barrier.wait()
        try:
            ac.approve(pid, "MGR-01")
            results.append("ok")
        except ac.PlanConflict:
            results.append("409")

    threads = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == ["409", "ok"] and calls == [pid]
