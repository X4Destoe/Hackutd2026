from app.shared import ids
from app.shared.enums import WorkOrderStatus
from app.shared.schemas import WorkOrder
from app.shared.store import Repo, store


def wo(i, status="sent", b="BLD-1"):
    return WorkOrder(id=f"WO-{i}", plan_id="PLAN-1", building_id=b, action_code="X", party_id="T", text="t",
                     status=status, created_at_hour=-12)


def test_crud_and_filters():
    r = Repo("workorders")
    r.put(wo(1)); r.put(wo(2, "done")); r.put(wo(3, "sent", "BLD-2"))
    assert r.count() == 3 and r.get("WO-1").id == "WO-1" and r.get("nope") is None
    assert [w.id for w in r.list(status="sent")] == ["WO-1", "WO-3"]
    assert [w.id for w in r.list(status=WorkOrderStatus.sent, building_id="BLD-2")] == ["WO-3"]  # enum or value
    r.put(wo(1, "done")); assert r.require("WO-1").status == WorkOrderStatus.done  # put replaces by id
    r.delete("WO-1"); assert r.count() == 2


def test_require_raises_keyerror():
    try:
        Repo("plans").require("PLAN-9"); assert False
    except KeyError as e:
        assert "PLAN-9" in str(e)


def test_reset_clears_repos_state_and_ids():
    store.workorders.put(wo(1)); store.state["x"] = 1; ids.new_id("WO")
    store.reset()
    assert store.workorders.count() == 0 and store.state == {} and ids.new_id("WO") == "WO-001"
