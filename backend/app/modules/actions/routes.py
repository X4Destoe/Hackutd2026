"""HTTP routes for actions (docs/prd/02-contracts.md §3). Work-order routes come with TASK-021."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.shared import schemas
from app.shared.store import store

import app.modules.actions as ac

router = APIRouter(tags=["actions"])


class DecisionBody(BaseModel):
    by: str = "portfolio manager"


@router.get("/actions/catalog", response_model=list[schemas.ActionTemplate])
def get_catalog():
    return list(ac.catalog.values())


@router.get("/plans", response_model=list[schemas.Plan])
def plans(building_id: Optional[str] = None, status: Optional[schemas.PlanStatus] = None):
    filters = {k: v for k, v in {"building_id": building_id, "status": status}.items() if v is not None}
    return sorted(store.plans.list(**filters), key=lambda p: p.id)


def _decide(fn, plan_id: str, body: Optional[DecisionBody]):
    try:
        return fn(plan_id, (body or DecisionBody()).by)
    except ac.PlanConflict as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/plans/{plan_id}/approve", response_model=schemas.Plan)
def approve(plan_id: str, body: Optional[DecisionBody] = None):
    return _decide(ac.approve, plan_id, body)


@router.post("/plans/{plan_id}/reject", response_model=schemas.Plan)
def reject(plan_id: str, body: Optional[DecisionBody] = None):
    return _decide(ac.reject, plan_id, body)


@router.get("/fix-first", response_model=list[schemas.FixFirstItem])
def fix_first(limit: int = 10, community: int = 0):
    return ac.fix_first(limit, bool(community))
