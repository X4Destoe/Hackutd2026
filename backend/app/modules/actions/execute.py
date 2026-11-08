"""Approve, reject, and technician replies.

Messaging and help-site registration are optional until those modules land: work orders are still
stored and marked sent so the impact loop can run on the simulator.
"""

from __future__ import annotations

import re

from app.shared import ids, schemas
from app.shared.enums import MessageKind, NeedType, PlanStatus, ResourceStatus, ResourceType, WorkOrderStatus
from app.shared.events import bus
from app.shared.store import store

from . import planning


def _fill(template: str, building: str, deadline: str) -> str:
    class _Map(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    return template.format_map(_Map(building=building, deadline=deadline))


def _send(party_id: str, body: str, kind: MessageKind, work_order_id: str | None = None) -> None:
    try:
        from app.modules import messaging
    except ImportError:
        return
    messaging.send(party_id, body, kind, work_order_id=work_order_id)


def _help_site(building: schemas.Building) -> None:
    try:
        from app.modules import resources
    except ImportError:
        return
    resources.register_site(schemas.Resource(
        id=ids.new_id("RES"),
        type=ResourceType.cbre_help_site,
        name=f"{building.name} help site",
        address=building.address,
        city=building.city,
        lat=building.lat,
        lon=building.lon,
        capacity=building.host_capacity,
        status=ResourceStatus.open,
        needs_served=[NeedType.shelter],
        building_id=building.id,
        utility_node_id=building.utility_node_id,
        hours="For the duration of the emergency",
        source="cbre",
    ))


def _work_orders(plan: schemas.Plan, building: schemas.Building, hour: int) -> list[schemas.WorkOrder]:
    from . import catalog

    orders = []
    for action in plan.actions:
        template = catalog[action.code]
        deadline = f"hour {action.act_by_hour:+d}"
        order = schemas.WorkOrder(
            id=ids.new_id("WO"),
            plan_id=plan.id,
            building_id=building.id,
            action_code=action.code,
            party_id=building.onsite_party_id,
            text=_fill(template.task_text, building.name, deadline),
            status=WorkOrderStatus.sent,
            created_at_hour=hour,
        )
        store.workorders.put(order)
        if template.creates_help_site:
            _help_site(building)
        _send(order.party_id, order.text, MessageKind.task, order.id)
        if template.tenant_notice_text:
            notice = _fill(template.tenant_notice_text, building.name, deadline)
            for tenant in building.tenants:
                if tenant.contact_party_id:
                    _send(tenant.contact_party_id, notice, MessageKind.tenant_notice, order.id)
        orders.append(order)
    return orders


def _emit_plan(plan: schemas.Plan) -> None:
    bus.emit("plan.changed", {"plan_id": plan.id, "building_id": plan.building_id, "status": plan.status.value})


def _emit_order(order: schemas.WorkOrder) -> None:
    bus.emit("workorder.changed", {
        "work_order_id": order.id, "building_id": order.building_id, "status": order.status.value,
    })


def _finish_plan_if_done(plan_id: str) -> None:
    plan = store.plans.require(plan_id)
    orders = store.workorders.list(plan_id=plan_id)
    if orders and all(order.status == WorkOrderStatus.done for order in orders):
        done = plan.model_copy(update={"status": PlanStatus.done})
        store.plans.put(done)
        _emit_plan(done)


def approve(plan_id: str, by: str) -> schemas.Plan:
    from app.modules import scenarios

    plan = store.plans.require(plan_id)
    if plan.status != PlanStatus.proposed:
        raise ValueError(f"plan {plan_id} is {plan.status.value}, not proposed")
    building = store.buildings.require(plan.building_id)
    hour = scenarios.current().step_hour
    approved = plan.model_copy(update={"status": PlanStatus.approved, "approved_by": by, "approved_at_hour": hour})
    store.plans.put(approved)
    orders = _work_orders(approved, building, hour)
    executing = approved.model_copy(update={"status": PlanStatus.executing if orders else PlanStatus.approved})
    store.plans.put(executing)
    planning.invalidate()
    _emit_plan(executing)
    for order in orders:
        _emit_order(order)
    return executing


def reject(plan_id: str, by: str) -> schemas.Plan:
    plan = store.plans.require(plan_id)
    if plan.status != PlanStatus.proposed:
        raise ValueError(f"plan {plan_id} is {plan.status.value}, not proposed")
    rejected = plan.model_copy(update={"status": PlanStatus.rejected, "approved_by": by})
    store.plans.put(rejected)
    planning.invalidate()
    _emit_plan(rejected)
    return rejected


def _target_order(party_id: str, number: int | None) -> schemas.WorkOrder | None:
    orders = [order for order in store.workorders.list(party_id=party_id) if order.status != WorkOrderStatus.done]
    if number is not None:
        wanted = f"WO-{number:03d}"
        return next((order for order in orders if order.id == wanted), None)
    if not orders:
        return None
    return sorted(orders, key=lambda order: order.id)[-1]


def apply_task_reply(party_id: str, text: str, media_urls: list[str] | None = None) -> schemas.WorkOrder | None:
    """DONE / ✅ closes a work order. BLOCKED records the reason. A photo moves a sent order to accepted."""
    media = list(media_urls or [])
    raw = text.strip()
    lowered = raw.lower()
    number_match = re.search(r"\b(\d+)\b", raw)
    number = int(number_match.group(1)) if number_match else None
    order = _target_order(party_id, number)
    if order is None:
        return None

    photos = list(order.photo_urls)
    updates = list(order.updates)
    status = order.status
    if media:
        photos.extend(media)
        if status == WorkOrderStatus.sent:
            status = WorkOrderStatus.accepted
    if lowered.startswith("done") or raw.startswith("✅"):
        status = WorkOrderStatus.done
        updates.append(raw)
    elif lowered.startswith("blocked"):
        status = WorkOrderStatus.blocked
        reason = re.sub(r"(?i)^blocked\s*\d*\s*", "", raw).strip()
        updates.append(reason or raw)
    elif not media:
        updates.append(raw)

    updated = order.model_copy(update={"status": status, "photo_urls": photos, "updates": updates})
    store.workorders.put(updated)
    _emit_order(updated)
    _finish_plan_if_done(updated.plan_id)
    label = updated.status.value
    _send(party_id, f"Got it. {updated.id} is {label}.", MessageKind.task_update, updated.id)
    return updated


def update_work_order(work_order_id: str, status: WorkOrderStatus, note: str | None = None) -> schemas.WorkOrder:
    order = store.workorders.require(work_order_id)
    updates = list(order.updates)
    if note:
        updates.append(note)
    updated = order.model_copy(update={"status": status, "updates": updates})
    store.workorders.put(updated)
    _emit_order(updated)
    _finish_plan_if_done(updated.plan_id)
    return updated
