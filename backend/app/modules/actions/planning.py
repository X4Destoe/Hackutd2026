"""Plan building: greedy ROI, missed deadlines, Fix-First ranking.

Spec: docs/prd/modules/actions.md and docs/prd/03-data-and-scenarios.md §4.
Impact is imported inside functions; it calls back into this package for the catalog.
"""

from __future__ import annotations

import threading

from app.shared import ids, schemas
from app.shared.enums import PlanStatus
from app.shared.events import bus
from app.shared.store import store

_lock = threading.RLock()
_stamp: tuple | None = None
_running = False


def _haz(value) -> str:
    return getattr(value, "value", value)


def dollars(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    amount = abs(cents) / 100
    if amount >= 1_000_000:
        text = f"{amount / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{sign}${text}M"
    if amount >= 10_000:
        return f"{sign}${amount / 1000:.0f}k"
    if amount >= 1000:
        return f"{sign}${amount / 1000:.1f}k"
    return f"{sign}${amount:,.0f}"


def _scenario_plans() -> list[schemas.Plan]:
    from app.modules import scenarios

    scenario_id = scenarios.current().scenario_id
    return [plan for plan in store.plans.list() if plan.scenario_id == scenario_id]


def _plan_for(building_id: str, scenario_id: str, community: bool) -> schemas.Plan | None:
    from app.modules.actions import catalog

    for plan in store.plans.list():
        if plan.building_id != building_id or plan.scenario_id != scenario_id or not plan.actions:
            continue
        is_community = all(catalog[action.code].community for action in plan.actions if action.code in catalog)
        if is_community == community:
            return plan
    return None


def _building_hazards(impact: schemas.Impact, scenario: schemas.Scenario) -> set[str]:
    kinds = {_haz(hazard) for hazard in scenario.hazards}
    found: set[str] = set()
    if impact.exposure.flood_depth_ft > 0:
        found.add("surge" if "surge" in kinds and "flood" not in kinds else "flood")
    if impact.exposure.wind_mph > 0 and "wind" in kinds:
        found.add("wind")
    if impact.exposure.temp_f is not None or impact.exposure.ice_in > 0:
        found.add("winter")
    if impact.exposure.in_burn_zone:
        found.add("wildfire")
    return found


def _eligible(template: schemas.ActionTemplate, building: schemas.Building, hazards: set[str], hour: int, safe: bool) -> bool:
    effect = template.effect
    if template.community:
        return bool(building.can_host_help_site and safe and hour <= template.act_by_hour)
    if hour > template.act_by_hour:
        return False
    if effect.requires_generator and not building.systems.has_generator:
        return False
    if effect.requires_no_generator and building.systems.has_generator:
        return False
    wanted = {_haz(hazard) for hazard in effect.hazards}
    if wanted and not wanted.intersection(hazards):
        return False
    return True


def _choose(building: schemas.Building, hour: int, templates: list[schemas.ActionTemplate]) -> tuple[list[schemas.ActionTemplate], int, int]:
    """Greedy marginal ROI. Returns chosen templates, total avoided cents, and the final net."""
    from app.modules import impact

    baseline = impact.baseline_for(building.id, hour)
    cache: dict[tuple[str, ...], int] = {(): baseline.money.net_exposure_cents}

    def net_of(codes: list[str]) -> int:
        key = tuple(codes)
        if key not in cache:
            cache[key] = impact.impact_for(building.id, hour, extra_actions=list(codes)).money.net_exposure_cents
        return cache[key]

    chosen: list[schemas.ActionTemplate] = []
    current = net_of([])
    remaining = list(templates)
    while remaining:
        best = None
        best_roi = 1.0  # strictly greater than 1 to be worth doing
        best_net = current
        for template in remaining:
            gain = current - net_of([item.code for item in chosen] + [template.code])
            roi = gain / template.cost_cents if template.cost_cents else 0
            if roi > best_roi or (roi == best_roi and best is not None and gain > current - best_net):
                best, best_roi, best_net = template, roi, current - gain
        if best is None:
            break
        chosen.append(best)
        remaining.remove(best)
        current = best_net
    avoided = net_of([]) - current
    return chosen, avoided, current


def _miss(plan: schemas.Plan) -> schemas.Plan:
    if plan.status == PlanStatus.missed and plan.rationale.startswith("would have saved"):
        return plan
    note = f"would have saved {dollars(plan.avoided_cents)}"
    rationale = plan.rationale if plan.rationale.startswith(note) else f"{note}. {plan.rationale}"
    updated = plan.model_copy(update={"status": PlanStatus.missed, "rationale": rationale})
    store.plans.put(updated)
    return updated


def _save_plan(
    existing: schemas.Plan | None,
    building: schemas.Building,
    scenario_id: str,
    chosen: list[schemas.ActionTemplate],
    avoided: int,
    hour: int,
) -> schemas.Plan:
    from app.modules import ai

    cost = sum(template.cost_cents for template in chosen)
    roi = (avoided / cost) if cost else 0.0
    act_by = min(template.act_by_hour for template in chosen)
    actions = [
        schemas.PlanAction(code=template.code, title=template.title, cost_cents=template.cost_cents,
                           act_by_hour=template.act_by_hour, feasible=True)
        for template in chosen
    ]
    rationale = ai.rationale({
        "cost_cents": cost,
        "avoided_cents": avoided,
        "building": building.name,
        "actions": [template.code for template in chosen],
    })
    payload = dict(
        building_id=building.id, scenario_id=scenario_id, actions=actions, cost_cents=cost,
        avoided_cents=avoided, roi=roi, act_by_hour=act_by, status=PlanStatus.proposed, rationale=rationale,
    )
    if existing is None:
        plan = schemas.Plan(id=ids.new_id("PLAN"), **payload)
    else:
        plan = existing.model_copy(update=payload)
    store.plans.put(plan)
    return plan


def _drop(plan: schemas.Plan | None) -> None:
    if plan is not None and plan.status == PlanStatus.proposed:
        store.plans.delete(plan.id)


def _rebuild_one(building: schemas.Building, scenario: schemas.Scenario, hour: int, community: bool) -> None:
    from app.modules import impact
    from app.modules.actions import catalog

    existing = _plan_for(building.id, scenario.id, community)
    if existing and existing.status in (PlanStatus.approved, PlanStatus.executing, PlanStatus.done, PlanStatus.rejected):
        return
    if existing and hour > existing.act_by_hour:
        _miss(existing)
        return

    baseline = impact.baseline_for(building.id, hour)
    if not community and (baseline.risk == "none" or building.city != scenario.city):
        _drop(existing)
        return
    hazards = _building_hazards(baseline, scenario)
    safe = impact.site_safe(building.lat, building.lon, building.utility_node_id, hour) if community else False
    templates = [
        template for template in catalog.values()
        if template.community == community and _eligible(template, building, hazards, hour, safe)
    ]
    if community:
        chosen, avoided = templates[:1], 0
        if not chosen:
            _drop(existing)
            return
        _save_plan(existing, building, scenario.id, chosen, avoided, hour)
        return
    if not templates:
        _drop(existing)
        return
    chosen, avoided, _net = _choose(building, hour, templates)
    if not chosen or avoided <= 0:
        _drop(existing)
        return
    _save_plan(existing, building, scenario.id, chosen, avoided, hour)


def refresh() -> list[schemas.Plan]:
    """Rebuild proposed plans for the current step, freeze missed ones, emit plans.updated."""
    global _stamp, _running
    from app.modules import scenarios

    with _lock:
        if _running:
            return _scenario_plans()
        state = scenarios.current()
        scenario = scenarios.scenario()
        hour = state.step_hour
        _running = True
    try:
        for building in store.buildings.list():
            _rebuild_one(building, scenario, hour, community=False)
            _rebuild_one(building, scenario, hour, community=True)
        plans = _scenario_plans()
        _stamp = (scenario.id, hour)
        bus.emit("plans.updated", {
            "count": len(plans),
            "fix_first_top": [item.model_dump(mode="json") for item in fix_first(5)],
        })
        return plans
    finally:
        with _lock:
            _running = False


def invalidate() -> None:
    """Next refresh() rebuilds. Called after approve/reject so a same-hour event is not skipped."""
    global _stamp
    with _lock:
        _stamp = None


def fix_first(limit: int = 10, community: bool = False) -> list[schemas.FixFirstItem]:
    """Proposed plans. Urgent deadlines (≤ 12h left) first, then ROI, then dollars saved."""
    from app.modules import scenarios
    from app.modules.actions import catalog

    hour = scenarios.current().step_hour
    ranked: list[schemas.FixFirstItem] = []
    for plan in _scenario_plans():
        if plan.status != PlanStatus.proposed or not plan.actions:
            continue
        is_community = all(catalog[action.code].community for action in plan.actions if action.code in catalog)
        if is_community != community:
            continue
        building = store.buildings.get(plan.building_id)
        name = building.name if building else plan.building_id
        hours_left = plan.act_by_hour - hour
        driver = ""
        if building is not None:
            from app.modules import impact
            base = impact.baseline_for(building.id, hour)
            driver = base.drivers[0] if base.drivers else ""
        within = max(hours_left, 0)
        why = f"{dollars(plan.avoided_cents)} saved for {dollars(plan.cost_cents)}; {driver}; act within {within}h"
        ranked.append(schemas.FixFirstItem(
            rank=0, plan_id=plan.id, building_id=plan.building_id, building_name=name,
            title=" + ".join(action.title for action in plan.actions),
            cost_cents=plan.cost_cents, avoided_cents=plan.avoided_cents, roi=plan.roi,
            act_by_hour=plan.act_by_hour, hours_left=hours_left, why=why.strip("; "),
        ))
    ranked.sort(key=lambda item: (0 if item.hours_left <= 12 else 1, -item.roi, -item.avoided_cents, item.building_id))
    out = []
    for rank, item in enumerate(ranked[:limit], start=1):
        out.append(item.model_copy(update={"rank": rank}))
    return out


def on_world_changed(_payload: dict) -> None:
    """Timeline and impact events both fire on one step change; rebuild once per step."""
    from app.modules import scenarios

    state = scenarios.current()
    if _stamp == (state.scenario_id, state.step_hour) and not _running:
        return
    refresh()
