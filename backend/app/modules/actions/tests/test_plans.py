"""Acceptance from docs/prd/modules/actions.md (plan building and the approve loop)."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import actions, scenarios as sc
from app.modules import impact
from app.shared.events import bus
from app.shared.store import store


def _plan(building_id: str):
    plans = [plan for plan in store.plans.list(building_id=building_id) if not _community(plan)]
    assert plans, building_id
    return plans[0]


def _community(plan) -> bool:
    return bool(plan.actions) and all(actions.catalog[action.code].community for action in plan.actions)


def test_catalog_matches_the_contract_file():
    assert "FLOOD_BARRIERS" in actions.catalog
    assert actions.catalog["FLOOD_BARRIERS"].act_by_hour == -12
    assert actions.catalog["FLOOD_BARRIERS"].cost_cents == 1_800_000


def test_bayou_plaza_fix_first_includes_flood_barriers_with_roi_above_10():
    sc.load("harvey_houston")
    sc.set_hour(-24)
    actions.refresh()
    plan = _plan("BLD-HOU-01")
    codes = [action.code for action in plan.actions]
    assert "FLOOD_BARRIERS" in codes
    barriers = next(action for action in plan.actions if action.code == "FLOOD_BARRIERS")
    assert barriers.act_by_hour == -12
    assert plan.roi > 10
    top = actions.fix_first(10)
    assert plan.id in [item.plan_id for item in top[:3]]
    assert top[0].rank == 1


def test_energy_corridor_is_missed_once_its_deadline_passes():
    sc.load("harvey_houston")
    sc.set_hour(-24)
    actions.refresh()
    proposed = _plan("BLD-HOU-05")
    assert proposed.status == "proposed" and proposed.avoided_cents > 0
    saved = proposed.avoided_cents
    sc.set_hour(0)
    actions.refresh()
    missed = _plan("BLD-HOU-05")
    assert missed.id == proposed.id
    assert missed.status == "missed"
    assert missed.avoided_cents == saved
    assert missed.rationale.startswith("would have saved")


def test_approve_sends_work_orders_and_lowers_net_exposure():
    sc.load("harvey_houston")
    sc.set_hour(-24)
    actions.refresh()
    plan = _plan("BLD-HOU-01")
    before = impact.impact_for("BLD-HOU-01", -24).money.net_exposure_cents
    seen = []
    bus.on("workorder.changed", seen.append)
    approved = actions.approve(plan.id, "casey")
    after = impact.impact_for("BLD-HOU-01", -24).money.net_exposure_cents
    assert after < before
    assert "FLOOD_BARRIERS" in actions.approved_codes("BLD-HOU-01")
    orders = store.workorders.list(plan_id=plan.id)
    assert orders and all(order.status == "sent" for order in orders)
    assert approved.status == "executing"
    reply = actions.apply_task_reply(orders[0].party_id, "DONE")
    assert reply is not None and reply.status == "done"
    assert seen and seen[-1]["work_order_id"] == reply.id and seen[-1]["status"] == "done"


def test_routes_list_catalog_plans_and_fix_first():
    with TestClient(create_app()) as client:
        client.post("/api/scenarios/harvey_houston/load")
        client.post("/api/timeline", json={"hour": -24})
        catalog = client.get("/api/actions/catalog")
        assert catalog.status_code == 200 and any(row["code"] == "FLOOD_BARRIERS" for row in catalog.json())
        listed = client.get("/api/plans", params={"building_id": "BLD-HOU-01"})
        assert listed.status_code == 200 and listed.json()
        top = client.get("/api/fix-first", params={"limit": 3})
        assert top.status_code == 200 and len(top.json()) <= 3
        plan_id = listed.json()[0]["id"]
        approved = client.post(f"/api/plans/{plan_id}/approve", json={"by": "casey"})
        assert approved.status_code == 200
        assert client.get("/api/workorders", params={"building_id": "BLD-HOU-01"}).json()
        assert client.post(f"/api/plans/{plan_id}/approve", json={"by": "casey"}).status_code == 409
