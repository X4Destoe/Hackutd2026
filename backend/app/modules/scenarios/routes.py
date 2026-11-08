"""HTTP routes for scenarios (docs/prd/02-contracts.md §3). Mounted under /api by app.main."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.shared import schemas
from app.shared.store import store

import app.modules.scenarios as sc

router = APIRouter(tags=["scenarios"])


class ResetBody(BaseModel):
    scenario_id: Optional[str] = None


class TimelineBody(BaseModel):
    hour: int


class UtilityStatus(schemas.UtilityNode):
    down: bool


@router.get("/scenarios", response_model=list[schemas.ScenarioMeta])
def list_scenarios():
    return sc.scenarios_meta()


@router.post("/scenarios/{scenario_id}/load", response_model=schemas.DemoState)
def load_scenario(scenario_id: str):
    return sc.load(scenario_id)


@router.post("/demo/reset", response_model=schemas.DemoState)
def reset(body: Optional[ResetBody] = None):
    return sc.load((body.scenario_id if body else None) or sc.current().scenario_id)


@router.get("/demo/state", response_model=schemas.DemoState)
def state():
    return sc.current()


@router.post("/timeline", response_model=schemas.DemoState)
def timeline(body: TimelineBody):
    try:
        return sc.set_hour(body.hour)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/overlays")
def overlays(hour: Optional[int] = None) -> dict:
    return sc.overlays(hour)


@router.get("/buildings", response_model=list[schemas.Building])
def buildings():
    sc.current()
    return store.buildings.list()


@router.get("/utilities", response_model=list[UtilityStatus])
def utilities():
    sc.current()
    return [UtilityStatus(**u.model_dump(), down=sc.utility_down(u.id)) for u in store.utilities.list()]
