"""actions: turn dollars into decisions - plans with ROI and act-by, Fix-First, approve/reject. Interface: INTERFACE.md.

Work orders, texts and technician replies on approval live in execute.py (TASK-021); approve() calls it when present.
"""
from __future__ import annotations

import logging

from app.modules import scenarios
from app.shared import schemas
from app.shared.events import bus
from app.shared.store import store

from .catalog import catalog, is_community
from .plans import ACTIVE, LOCK, fix_first, plan_is_community, refresh as _refresh

log = logging.getLogger(__name__)


class PlanConflict(ValueError):
    """The plan is not in a state that allows this change (HTTP 409)."""


def refresh() -> list[schemas.Plan]:
    """Rebuild proposed plans for the current step, mark missed ones, emit plans.updated."""
    plans = _refresh()
    top = [i.model_dump(mode="json") for i in fix_first(5)]
    bus.emit("plans.updated", {"count": len(plans), "fix_first_top": top})
    return plans


def approved_codes(building_id: str) -> list[str]:
    """Action codes of this building's approved / executing / done plans (read by impact)."""
    codes: list[str] = []
    for p in store.plans.list(building_id=building_id):
        if str(getattr(p.status, "value", p.status)) in ACTIVE:
            codes += [a.code for a in p.actions]
    return list(dict.fromkeys(codes))


def _decide(plan_id: str, by: str, status: str) -> schemas.Plan:
    with LOCK:  # check + write + execute as one step: concurrent approvals cannot both win
        plan = store.plans.require(plan_id)
        if str(getattr(plan.status, "value", plan.status)) != "proposed":
            raise PlanConflict(f"{plan_id} is {getattr(plan.status, 'value', plan.status)}, only proposed plans can be {status}")
        update = {"status": status}
        if status == "approved":
            update |= {"approved_by": by, "approved_at_hour": scenarios.current().step_hour}
        plan = store.plans.put(plan.model_copy(update=update))
        if status == "approved":
            try:
                from . import execute  # TASK-021: work orders, task texts, tenant notices, help-site registration
            except ImportError:
                execute = None
            if execute is not None and hasattr(execute, "on_approved"):
                plan = execute.on_approved(plan) or store.plans.require(plan_id)
    # impact recomputes on plan.changed -> impact.updated -> refresh(): the building drops out of Fix-First
    bus.emit("plan.changed", {"plan_id": plan.id, "building_id": plan.building_id, "status": str(getattr(plan.status, "value", plan.status))})
    return plan


def approve(plan_id: str, by: str) -> schemas.Plan:
    return _decide(plan_id, by, "approved")


def reject(plan_id: str, by: str) -> schemas.Plan:
    return _decide(plan_id, by, "rejected")


def register() -> None:
    # impact.updated follows scenario.loaded, timeline.changed and plan.changed, so plans always see fresh impact
    bus.on("impact.updated", lambda _payload: refresh())


from .routes import router  # noqa: E402

__all__ = ["catalog", "is_community", "register", "refresh", "approve", "reject", "approved_codes", "fix_first",
           "plan_is_community", "PlanConflict", "router"]
