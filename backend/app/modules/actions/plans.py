"""Plan building (greedy by marginal ROI), missed plans and Fix-First ranking. docs/prd/modules/actions.md."""
from __future__ import annotations

import threading

from app.modules import impact, scenarios
from app.shared import ids, schemas
from app.shared.store import store

from .catalog import catalog, is_community

ACTIVE = ("approved", "executing", "done")
DECIDED = ACTIVE + ("rejected",)
HELP_SITE = "OFFER_HELP_SITE"
_rationale_cache: dict[tuple, str] = {}
LOCK = threading.RLock()  # serializes refresh() and approve/reject so a plan is decided exactly once


def _s(x) -> str:
    return getattr(x, "value", x)


def money(cents: float) -> str:
    d = cents / 100
    for scale, suffix in ((1e6, "M"), (1e3, "k")):
        if abs(d) >= scale:
            return f"${d / scale:.2f}".rstrip("0").rstrip(".") + suffix
    return f"${d:,.0f}"


def plan_is_community(p: schemas.Plan) -> bool:
    return bool(p.actions) and all(is_community(a.code) for a in p.actions)


def _candidates(b: schemas.Building, hour: int) -> list[schemas.ActionTemplate]:
    hazards = {_s(h) for h in scenarios.scenario().hazards}
    out = []
    for t in catalog.values():
        e = t.effect
        if t.community or hour > t.act_by_hour:
            continue
        if (hour < 0) != (t.act_by_hour < 0):  # before landfall: prepare; after: respond (never bundle the two)
            continue
        if (e.requires_generator and not b.systems.has_generator) or (e.requires_no_generator and b.systems.has_generator):
            continue
        if e.hazards and not hazards & {_s(h) for h in e.hazards}:
            continue
        out.append(t)
    return out


def best_plan(b: schemas.Building, hour: int) -> tuple[list[schemas.ActionTemplate], int, int]:
    """Greedy: add the action with the highest marginal avoided/cost while that ratio > 1. Returns (actions, cost, avoided)."""
    base = impact.impact_for(b.id, hour).money.net_exposure_cents
    chosen: list[schemas.ActionTemplate] = []
    current = base
    pool = _candidates(b, hour)
    while pool:
        best = None
        for t in pool:
            net = impact.impact_for(b.id, hour, extra_actions=[c.code for c in chosen] + [t.code]).money.net_exposure_cents
            roi = (current - net) / t.cost_cents
            if roi > 1 and (best is None or roi > best[1]):
                best = (t, roi, net)
        if best is None:
            break
        chosen.append(best[0])
        current = best[2]
        pool.remove(best[0])
    return chosen, sum(t.cost_cents for t in chosen), base - current


def _rationale(b: schemas.Building, codes: list[str], cost: int, avoided: int) -> str:
    """Instant local text; when an LLM provider is configured, a background thread upgrades it (never blocks a request)."""
    try:
        from app.modules import ai
        provider = ai.provider_name()
    except ImportError:
        ai, provider = None, "templates"
    key = (provider, b.id, tuple(codes), cost, avoided)
    if key in _rationale_cache:
        return _rationale_cache[key]
    _rationale_cache[key] = f"Cost {money(cost)}; avoids {money(avoided)} in estimated losses."
    if ai is not None and provider != "templates":
        facts = {"building_name": b.name, "actions": ", ".join(catalog[c].title for c in codes),
                 "cost_cents": cost, "avoided_cents": avoided}
        threading.Thread(target=_enrich, args=(key, facts), daemon=True).start()
    return _rationale_cache[key]


def _enrich(key: tuple, facts: dict) -> None:
    from app.modules import ai
    from app.shared.events import bus
    try:
        text = ai.rationale(facts)
    except Exception:
        return
    with LOCK:
        if not text or _rationale_cache.get(key) == text:
            return
        _rationale_cache[key] = text
        _provider, building_id, codes, cost, avoided = key
        for p in store.plans.list(building_id=building_id, status="proposed"):
            if tuple(a.code for a in p.actions) == codes and p.cost_cents == cost and p.avoided_cents == avoided:
                store.plans.put(p.model_copy(update={"rationale": text}))
    bus.emit("plans.updated", {"count": store.plans.count(), "fix_first_top": []})


def _put_plan(plan_id: str | None, b: schemas.Building, chosen: list[schemas.ActionTemplate], cost: int, avoided: int,
              hour: int, rationale: str) -> schemas.Plan:
    plan = schemas.Plan(
        id=plan_id or ids.new_id("PLAN"), building_id=b.id, scenario_id=scenarios.current().scenario_id,
        actions=[schemas.PlanAction(code=t.code, title=t.title, cost_cents=t.cost_cents, act_by_hour=t.act_by_hour,
                                    feasible=hour <= t.act_by_hour) for t in chosen],
        cost_cents=cost, avoided_cents=avoided, roi=round(avoided / cost, 1) if cost else 0.0,
        act_by_hour=min(t.act_by_hour for t in chosen), status="proposed", rationale=rationale)
    return store.plans.put(plan)


def _live(building_id: str, community: bool) -> list[schemas.Plan]:
    return [p for p in store.plans.list(building_id=building_id) if plan_is_community(p) == community]


def _refresh_building(b: schemas.Building, hour: int) -> None:
    plans = _live(b.id, community=False)
    if any(_s(p.status) in DECIDED for p in plans):
        return  # a decision was made for this building in this scenario: no new proposals
    # time moved backwards past a missed plan's deadline: it is live again (keep its id)
    proposed = [p for p in plans if _s(p.status) == "proposed"]
    revived = sorted((p for p in plans if _s(p.status) == "missed" and p.act_by_hour >= hour), key=lambda p: p.id)
    if revived:  # the oldest plan comes back under its own id; anything proposed after it is dropped
        for p in revived[1:] + proposed:
            store.plans.delete(p.id)
        live = revived[0]
    else:
        live = proposed[0] if proposed else None
    if live and live.act_by_hour < hour:
        store.plans.put(live.model_copy(update={"status": "missed"}))  # keeps avoided_cents = "would have saved"
        live = None
    if impact.impact_for(b.id, hour).risk == "none":
        chosen = []
    else:
        chosen, cost, avoided = best_plan(b, hour)
    if not chosen:
        if live:
            store.plans.delete(live.id)
        return
    codes = [t.code for t in chosen]
    _put_plan(live.id if live else None, b, chosen, cost, avoided, hour, _rationale(b, codes, cost, avoided))


def _refresh_community(b: schemas.Building, hour: int) -> None:
    plans = _live(b.id, community=True)
    if any(_s(p.status) in DECIDED for p in plans):
        return
    t = catalog.get(HELP_SITE)
    live = next((p for p in plans if _s(p.status) == "proposed"), None)
    eligible = (t is not None and b.can_host_help_site and b.city == scenarios.scenario().city and hour <= t.act_by_hour
                and impact.site_safe(b.lat, b.lon, b.utility_node_id, hour)
                and impact.impact_for(b.id, hour).exposure.flood_depth_ft <= 0.5)  # also dry at the predicted peak
    if not eligible:
        for p in plans:
            store.plans.delete(p.id)
        return
    rationale = f"{b.name} stays dry and powered: offer {b.host_capacity} spots to residents as a help site."
    _put_plan(live.id if live else None, b, [t], t.cost_cents, 0, hour, rationale)


def refresh() -> list[schemas.Plan]:
    with LOCK:
        hour = scenarios.current().step_hour
        for b in store.buildings.list():
            _refresh_building(b, hour)
            _refresh_community(b, hour)
        return store.plans.list()


def _why(p: schemas.Plan, hours_left: int, b: schemas.Building) -> str:
    if plan_is_community(p):
        return f"Safe and powered: {b.host_capacity} spots for residents; act within {hours_left}h."
    driver = impact.baseline_for(b.id).drivers[0] if b else ""
    when = f"act within {hours_left}h" if hours_left > 0 else "act now"
    return f"{money(p.avoided_cents)} saved for {money(p.cost_cents)}; {driver[:1].lower() + driver[1:]}; {when}."


def fix_first(limit: int = 10, community: bool = False) -> list[schemas.FixFirstItem]:
    hour = scenarios.current().step_hour
    plans = [p for p in store.plans.list(status="proposed") if plan_is_community(p) == community]
    plans.sort(key=lambda p: (0 if p.act_by_hour - hour <= 12 else 1, -p.roi, -p.avoided_cents))
    out = []
    for rank, p in enumerate(plans[:limit], start=1):
        b = store.buildings.require(p.building_id)
        left = p.act_by_hour - hour
        out.append(schemas.FixFirstItem(
            rank=rank, plan_id=p.id, building_id=b.id, building_name=b.name, title=" + ".join(a.title for a in p.actions),
            cost_cents=p.cost_cents, avoided_cents=p.avoided_cents, roi=p.roi, act_by_hour=p.act_by_hour, hours_left=left,
            why=_why(p, left, b)))
    return out
