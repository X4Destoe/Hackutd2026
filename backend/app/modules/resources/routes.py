"""HTTP routes for resources (docs/prd/02-contracts.md §3). Mounted under /api by app.main."""
from typing import Optional

from fastapi import APIRouter

from app.shared import schemas
from app.shared.store import store

router = APIRouter(tags=["resources"])


@router.get("/resources", response_model=list[schemas.Resource])
def resources(city: Optional[str] = None):
    filters = {"city": city} if city else {}
    return sorted(store.resources.list(**filters), key=lambda r: r.id)


@router.get("/referrals", response_model=list[schemas.Referral])
def referrals():
    return sorted(store.referrals.list(), key=lambda r: r.id, reverse=True)
