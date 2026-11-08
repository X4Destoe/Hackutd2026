"""HTTP routes for messaging (docs/prd/02-contracts.md §4). Mounted under /api by app.main."""
from __future__ import annotations

import json

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.shared import schemas

import app.modules.messaging as messaging

router = APIRouter(tags=["messaging"])


class SimulateBody(BaseModel):
    phone: Optional[str] = None
    party_id: Optional[str] = None
    text: str = Field(min_length=1, max_length=2000)
    media_url: Optional[str] = None


@router.get("/messages", response_model=list[schemas.Message])
def messages(party_id: Optional[str] = None):
    from app.shared.store import store

    found = store.messages.list(party_id=party_id) if party_id else store.messages.list()
    return sorted(found, key=lambda message: message.id)


@router.get("/messaging/status", response_model=schemas.MessagingStatus)
def messaging_status():
    return messaging.status()


@router.post("/demo/simulate-message", response_model=schemas.Message)
def simulate_message(body: SimulateBody):
    if body.phone:
        party = messaging.party_for_phone(body.phone)
    elif body.party_id:
        from app.shared.store import store
        party = store.parties.require(body.party_id)
    else:
        raise HTTPException(status_code=422, detail="phone or party_id is required")
    media = [body.media_url] if body.media_url else []
    return messaging.receive(party, body.text, media)


@router.post("/webhooks/photon")
async def photon_webhook(request: Request):
    headers = {key.lower(): value for key, value in request.headers.items()}
    raw = await request.body()
    if messaging._mode() == "photon":
        try:
            return messaging.accept_photon_webhook(raw, headers)
        except PermissionError:
            raise HTTPException(status_code=401, detail="invalid signature")
        except ValueError:
            raise HTTPException(status_code=400, detail="malformed webhook")
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return messaging.accept_webhook(payload, headers)
