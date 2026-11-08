"""Approval -> owned work orders -> task/tenant messages -> technician acknowledgement.

The simulator delivers inline. Real-channel dispatch runs off the request path; approval
records intent, never proof that a phone received a message or mitigation was completed.
"""
from __future__ import annotations
import re
import threading
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.shared import schemas, ids, config
from app.shared.enums import PlanStatus, WorkOrderStatus, ResourceType, ResourceStatus, NeedType
from app.shared.events import bus
from app.shared.store import store
from .catalog import catalog
from .plans import LOCK

_runs: dict[str, object] = {}
_dispatch_slots = threading.BoundedSemaphore(4)
router = APIRouter(tags=['workorders'])


def _event(order):
    bus.emit('workorder.changed', {'work_order_id': order.id, 'building_id': order.building_id, 'status': str(order.status)})


def _plan_progress(plan_id):
    plan = store.plans.require(plan_id)
    orders = store.workorders.list(plan_id=plan_id)
    status = PlanStatus.done if orders and all(o.status == WorkOrderStatus.done for o in orders) else PlanStatus.executing
    updated = store.plans.put(plan.model_copy(update={'status': status}))
    bus.emit('plan.changed', {'plan_id': plan.id, 'building_id': plan.building_id, 'status': str(status)})
    return updated


def _update(order, status, note=None, media_urls=None):
    photos = list(order.photo_urls)
    for url in media_urls or []:
        if isinstance(url, str) and urlparse(url).scheme in ('http', 'https') and url not in photos:
            photos.append(url)
    updates = list(order.updates)
    if note and note not in updates:
        updates.append(note)
    updated = store.workorders.put(order.model_copy(update={'status': status, 'updates': updates, 'photo_urls': photos[-20:]}))
    _event(updated)
    return updated


def _valid(plan_id, token):
    return _runs.get(plan_id) is token and store.plans.get(plan_id) is not None


def _deliver(plan_id, token, order_ids):
    from app.modules import messaging
    from app.modules import scenarios
    for order_id in order_ids:
        with LOCK:
            if not _valid(plan_id, token): return
            order = store.workorders.require(order_id)
            building = store.buildings.require(order.building_id)
            template = catalog[order.action_code]
        try:
            message = messaging.send(order.party_id, order.text, 'task', work_order_id=order.id)
            sent = message.status == 'sent'
        except (KeyError, ValueError):
            sent = False
        with LOCK:
            if not _valid(plan_id, token): return
            current = store.workorders.require(order_id)
            # A fast inbound reply may have already accepted/completed the task.
            if current.status == WorkOrderStatus.created:
                _update(current, WorkOrderStatus.sent if sent else WorkOrderStatus.blocked,
                        'Task message sent via ' + message.channel if sent else 'Task message failed. Coordinator follow-up required.')
        if template.tenant_notice_text:
            body = template.tenant_notice_text.format(building=building.name, deadline=f'{template.act_by_hour:+d}h relative to impact')
            for tenant in building.tenants:
                with LOCK:
                    if not _valid(plan_id, token): return
                try:
                    notice = messaging.send(tenant.contact_party_id or tenant.id, body, 'tenant_notice', work_order_id=order.id)
                    if notice.status != 'sent':
                        with LOCK:
                            if _valid(plan_id, token): _update(store.workorders.require(order.id), store.workorders.require(order.id).status, 'A tenant notice failed. Coordinator follow-up required.')
                except (KeyError, ValueError):
                    with LOCK:
                        if _valid(plan_id, token): _update(store.workorders.require(order.id), store.workorders.require(order.id).status, 'Tenant contact unavailable. Coordinator follow-up required.')
        if template.creates_help_site:
            with LOCK:
                if not _valid(plan_id, token): return
            try:
                from app.modules import resources
                resource = schemas.Resource(id=f'RES-{building.id}-HELP', type=ResourceType.cbre_help_site,
                    name=building.name, address=building.address, city=building.city, lat=building.lat, lon=building.lon,
                    capacity=building.host_capacity, status=ResourceStatus.open,
                    needs_served=[NeedType.shelter, NeedType.warmth, NeedType.food_water], building_id=building.id,
                    utility_node_id=building.utility_node_id, hours='24 hours', source='cbre')
                resources.register_site(resource)
            except (ImportError, AttributeError, ValueError, KeyError):
                with LOCK:
                    if _valid(plan_id, token): _update(store.workorders.require(order.id), WorkOrderStatus.blocked, 'Help-site registration unavailable. Do not route residents here yet.')


def on_approved(plan: schemas.Plan):
    """Called under the actions decision lock. Idempotent for an already materialized plan."""
    with LOCK:
        if store.workorders.list(plan_id=plan.id): return store.plans.require(plan.id)
        building = store.buildings.require(plan.building_id)
        orders = []
        for action in plan.actions:
            template = catalog[action.code]
            order_id = ids.new_id('WO')
            text = 'Operation Storm task {id}: {task}. Reply DONE {id}, BLOCKED {id} <reason>, or send a photo.'.format(
                id=order_id, task=template.task_text.format(building=building.name, deadline=f'{action.act_by_hour:+d}h relative to impact').rstrip('.'))
            order = schemas.WorkOrder(id=order_id, plan_id=plan.id, building_id=building.id, action_code=action.code,
                party_id=building.onsite_party_id, text=text, status=WorkOrderStatus.created,
                created_at_hour=plan.approved_at_hour if plan.approved_at_hour is not None else 0)
            store.workorders.put(order); orders.append(order.id); _event(order)
        updated = store.plans.put(plan.model_copy(update={'status': PlanStatus.executing}))
        token = object(); _runs[plan.id] = token
    if config.settings.messaging_mode == 'sim':
        _deliver(plan.id, token, orders)
    elif _dispatch_slots.acquire(blocking=False):
        def run():
            try: _deliver(plan.id, token, orders)
            finally: _dispatch_slots.release()
        threading.Thread(target=run, name='response-dispatch', daemon=True).start()
    else:
        with LOCK:
            for order_id in orders: _update(store.workorders.require(order_id), WorkOrderStatus.blocked, 'Dispatch busy. Coordinator follow-up required; no automatic retry.')
    return store.plans.require(plan.id)


def apply_task_reply(party_id: str, text: str, media_urls: list[str] | None = None):
    from app.modules import messaging
    match = re.match(r'^\s*(DONE|BLOCKED|ACCEPTED|ACCEPT)\b(?:\s+(?:WO-)?(\d+))?', text, re.IGNORECASE)
    command = match.group(1).upper() if match else ('DONE' if text.strip() in ('\u2705', '\u2713') else None)
    explicit = match.group(2) if match else None
    with LOCK:
        owned = store.workorders.list(party_id=party_id)
        if explicit:
            order = next((o for o in owned if int(o.id.rsplit('-',1)[-1]) == int(explicit)), None)
        else:
            candidates = [o for o in owned if o.status != WorkOrderStatus.done]
            order = max(candidates, key=lambda o: int(o.id.rsplit('-',1)[-1]), default=None)
        if order is None: return None
        if order.status == WorkOrderStatus.done: return order
        status = (WorkOrderStatus.done if command == 'DONE' else WorkOrderStatus.blocked if command == 'BLOCKED'
                  else WorkOrderStatus.accepted if command in ('ACCEPT','ACCEPTED') or media_urls and order.status in (WorkOrderStatus.sent,WorkOrderStatus.created)
                  else order.status)
        order = _update(order, status, text.strip() or 'Photo received', media_urls)
        _plan_progress(order.plan_id)
    messaging.send(party_id, f'Recorded {order.id}: {order.status}.', 'task_update', work_order_id=order.id)
    return order


def register_execution():
    # Messaging already routes technician messages to actions.apply_task_reply; do not register twice.
    def clear(_payload):
        with LOCK: _runs.clear()
    bus.on('scenario.loaded', clear)


class WorkOrderUpdate(BaseModel):
    status: WorkOrderStatus
    note: str | None = None


@router.get('/workorders', response_model=list[schemas.WorkOrder])
def workorders(building_id: str | None = None):
    return store.workorders.list(**({'building_id': building_id} if building_id else {}))


@router.post('/workorders/{order_id}/update', response_model=schemas.WorkOrder)
def update_workorder(order_id: str, body: WorkOrderUpdate):
    with LOCK:
        order = store.workorders.require(order_id)
        if order.status == WorkOrderStatus.done and body.status != WorkOrderStatus.done:
            raise HTTPException(409, 'Completed work orders cannot be reopened through this endpoint')
        updated = _update(order, body.status, body.note)
        _plan_progress(order.plan_id)
        return updated
