"""HTTP routes for actions (docs/prd/02-contracts.md §4). Mounted under /api by app.main."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.shared import schemas
from app.shared.enums import WorkOrderStatus

import app.modules.actions as actions

router = APIRouter(tags=["actions"])


class ByBody(BaseModel):
    by: str


class WorkOrderUpdate(BaseModel):
    status: WorkOrderStatus
    note: Optional[str] = None


@router.get("/actions/catalog", response_model=list[schemas.ActionTemplate])
def action_catalog():
    return list(actions.catalog.values())


@router.get("/plans", response_model=list[schemas.Plan])
def plans(building_id: Optional[str] = None, status: Optional[str] = None):
    from app.modules import scenarios
    from app.shared.store import store

    scenario_id = scenarios.current().scenario_id
    found = [plan for plan in store.plans.list() if plan.scenario_id == scenario_id]
    if building_id:
        found = [plan for plan in found if plan.building_id == building_id]
    if status:
        found = [plan for plan in found if plan.status.value == status or plan.status == status]
    return found


@router.post("/plans/{plan_id}/approve", response_model=schemas.Plan)
def approve_plan(plan_id: str, body: ByBody):
    try:
        return actions.approve(plan_id, body.by)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/reject", response_model=schemas.Plan)
def reject_plan(plan_id: str, body: ByBody):
    try:
        return actions.reject(plan_id, body.by)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/fix-first", response_model=list[schemas.FixFirstItem])
def fix_first(limit: int = 10, community: int = 0):
    return actions.fix_first(limit, community=bool(community))


@router.get("/workorders", response_model=list[schemas.WorkOrder])
def work_orders(building_id: Optional[str] = None):
    from app.shared.store import store
    return store.workorders.list(building_id=building_id) if building_id else store.workorders.list()


@router.post("/workorders/{work_order_id}/update", response_model=schemas.WorkOrder)
def update_work_order(work_order_id: str, body: WorkOrderUpdate):
    return actions.update_work_order(work_order_id, body.status, body.note)
