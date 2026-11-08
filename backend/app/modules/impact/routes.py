"""HTTP routes for impact (docs/prd/02-contracts.md §3). Mounted under /api by app.main."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from app.shared import schemas

import app.modules.impact as im

router = APIRouter(tags=["impact"])


@router.get("/impact", response_model=list[schemas.Impact])
def all_impacts(hour: Optional[int] = None):
    return im.latest() if hour is None else im.recompute(hour)


@router.get("/impact/{building_id}", response_model=schemas.Impact)
def one_impact(building_id: str, hour: Optional[int] = None):
    return im.impact_for(building_id, hour)


@router.get("/portfolio/summary", response_model=schemas.PortfolioSummary)
def portfolio_summary():
    return im.summary()
