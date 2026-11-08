from fastapi import APIRouter, HTTPException

from app.modules import scenarios
from app.shared import schemas
from app.shared.store import store
from .model import SimulationRequest, build, options

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/options")
def list_options():
    return options()


@router.post("/preview")
def preview(request: SimulationRequest):
    scenarios.current()
    try:
        scenario, _anchors, resolved = build(request, store.utilities.list())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"scenario": scenario.model_dump(mode="json"), "configuration": resolved.model_dump()}


@router.post("/start", response_model=schemas.DemoState)
def start(request: SimulationRequest):
    loader = getattr(scenarios, "load_definition", None)
    if not callable(loader):
        raise HTTPException(503, "Custom simulation loading is not available in this backend version")
    scenarios.current()
    try:
        scenario, anchors, _resolved = build(request, store.utilities.list())
        return loader(scenario, anchors)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
