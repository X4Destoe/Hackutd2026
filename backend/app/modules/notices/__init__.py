"""Explicit customer emergency notices; delivery remains owned by messaging."""
from __future__ import annotations

import threading
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules import messaging, scenarios
from app.shared.store import store

router = APIRouter(tags=['customer notices'])
_lock = threading.RLock()


class NoticeRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=100)
    scenario_id: str = Field(min_length=1)
    step_hour: int
    building_id: str
    tenant_ids: list[str] = Field(min_length=1, max_length=30)
    text: str = Field(min_length=1, max_length=1600)
    mode: Literal['sim', 'photon']


@router.post('/customer-notices')
def dispatch(body: NoticeRequest):
    """Validate the whole audience before sending; request IDs prevent accidental resends."""
    with _lock:
        state = scenarios.current()
        if body.scenario_id != state.scenario_id or body.step_hour != state.step_hour:
            raise HTTPException(409, 'Scenario or timeline changed. Review the notice before sending.')
        if body.mode != messaging.status().mode:
            raise HTTPException(409, 'Messaging mode changed. Review delivery mode before sending.')
        building = store.buildings.require(body.building_id)
        audience = {t.id: t for t in building.tenants}
        tenant_ids = list(dict.fromkeys(body.tenant_ids))
        if any(t not in audience for t in tenant_ids):
            raise HTTPException(422, 'Every recipient must be a tenant of the selected building.')
        contacts = []
        for tid in tenant_ids:
            party_id = audience[tid].contact_party_id
            if not party_id or not store.parties.get(party_id):
                raise HTTPException(422, 'A selected tenant has no messaging contact.')
            if party_id not in contacts:
                contacts.append(party_id)
        text = body.text.strip()
        if not text:
            raise HTTPException(422, 'Notice text cannot be blank.')
        fingerprint = [body.scenario_id, body.step_hour, body.building_id, sorted(tenant_ids), text, body.mode]
        history = store.state.setdefault('customer_notice_requests', {})
        previous = history.get(body.request_id)
        if previous:
            if previous['fingerprint'] != fingerprint:
                raise HTTPException(409, 'Request ID already used for another notice.')
            return {'messages': [store.messages.require(mid) for mid in previous['ids']], 'duplicate': True}
        if len(history) >= 500:
            raise HTTPException(409, 'Notice limit reached for this demo. Reset before sending more.')
        # Record each attempt before continuing. A failed/unknown send is never retried automatically.
        record = {'fingerprint': fingerprint, 'ids': []}
        history[body.request_id] = record
        for party_id in contacts:
            message = messaging.send(party_id, f'Operation Storm | {building.name}\n{text}', 'tenant_notice')
            record['ids'].append(message.id)
        return {'messages': [store.messages.require(mid) for mid in record['ids']], 'duplicate': False}
