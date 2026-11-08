"""HTTP routes for reports (docs/prd/02-contracts.md §3). Mounted under /api by app.main."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.shared import schemas
from app.shared.store import store

import app.modules.reports as rp

router = APIRouter(tags=["reports"])


class ReportBody(BaseModel):
    kind: schemas.ReportKind
    building_id: Optional[str] = None
    send: bool = False  # tenant_notice only: also text a short version to each tenant contact


@router.post("/reports", response_model=schemas.Report)
def create(body: ReportBody):
    try:
        return rp.generate(body.kind, body.building_id, body.send)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/reports", response_model=list[schemas.Report])
def list_reports():
    return sorted(store.reports.list(), key=lambda r: r.id, reverse=True)


@router.get("/reports/{report_id}/html", response_class=HTMLResponse)
def printable(report_id: str):
    return rp.html(report_id)
