"""reports: one-click documents for people outside the app (executive summary, tenant notice). Interface: INTERFACE.md.

Every number comes from the other modules' data; the optional AI paragraph only adds narrative and never supplies figures.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit

from app.modules import impact, scenarios
from app.shared import ids, schemas
from app.shared.config import settings
from app.shared.events import bus
from app.shared.store import store

from .render import markdown_to_html

log = logging.getLogger(__name__)
ACTIVE = ("approved", "executing", "done")


def _v(x) -> str:
    return getattr(x, "value", x)


def money(cents: float) -> str:
    d = cents / 100
    for scale, suffix in ((1e6, "M"), (1e3, "k")):
        if abs(d) >= scale:
            return f"${d / scale:.2f}".rstrip("0").rstrip(".") + suffix
    return f"${d:,.0f}"


def hour_label(h: int) -> str:
    return f"{'+' if h > 0 else '−' if h < 0 else ''}{abs(h) // 24}d" if abs(h) >= 48 and h % 24 == 0 else \
        f"{'+' if h > 0 else '−' if h < 0 else ''}{abs(h)}h"


def _cell(text) -> str:
    return str(text).replace("|", "/").replace("\n", " ")


def _table(head: list[str], rows: list[list]) -> list[str]:
    if not rows:
        return []
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows]


def _community(plan: schemas.Plan) -> bool:
    try:
        from app.modules.actions import plan_is_community
        return plan_is_community(plan)
    except ImportError:
        return False


def _narrative(kind: str, facts: dict) -> str:
    """Optional LLM paragraph; empty with the template provider (the structured report is complete on its own)."""
    try:
        from app.modules import ai
        if ai.provider_name() == "templates":
            return ""
        return ai.write_report(kind, facts).strip()
    except Exception:  # noqa: BLE001 - narrative is optional
        return ""


# ---------- executive summary ----------

def _executive_summary() -> tuple[str, str]:
    sc, state = scenarios.scenario(), scenarios.current()
    step = scenarios.step()
    s = impact.summary()
    impacts = {i.building_id: i for i in impact.latest()}
    plans = store.plans.list()
    approved = [p for p in plans if _v(p.status) in ACTIVE]
    missed = [p for p in plans if _v(p.status) == "missed"]
    title = f"Executive summary: {sc.name}, {sc.city}"
    lines = [f"# {title}", "",
             f"*{sc.real_event} ({sc.date_label}) · step {step.label} · generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC*", "",
             "## Bottom line", "",
             f"- **Estimated loss {money(s.net_exposure_cents)}** across {s.buildings_at_risk} buildings at risk "
             f"(gross loss {money(s.gross_loss_cents)}, insurance recovery {money(s.insurance_recovery_cents)}).",
             f"- **Avoided by approved actions: {money(s.avoided_cents)}** ({s.actions_approved} actions approved).",
             f"- **Missed:** {len(missed)} plan(s) passed their deadline unapproved and would have saved "
             f"{money(sum(p.avoided_cents for p in missed))}." if missed else "- **Missed:** none so far.",
             f"- Step narrative: {step.narrative}", ""]
    worst = [impacts[b] for b in s.worst_building_ids if b in impacts]
    if worst:
        lines += ["## Top at-risk buildings", ""]
        lines += _table(["Building", "Risk", "Estimated loss", "Gross loss", "Main driver"], [
            [store.buildings.require(i.building_id).name, _v(i.risk), money(i.money.net_exposure_cents),
             money(i.money.property_damage_cents + i.money.rent_abatement_cents + i.money.sla_penalty_cents + i.money.operations_cents),
             i.drivers[0] if i.drivers else ""] for i in worst]) + [""]
    if plans:
        lines += ["## Response plans", ""]
        lines += _table(["Building", "Actions", "Cost", "Saves", "ROI", "Act by", "Status"], [
            [store.buildings.require(p.building_id).name, ", ".join(a.title for a in p.actions), money(p.cost_cents),
             *(("community", "—") if _community(p) else (money(p.avoided_cents), f"{p.roi:g}x")), hour_label(p.act_by_hour),
             "missed (would have saved)" if _v(p.status) == "missed" else _v(p.status)]
            for p in sorted(plans, key=lambda p: (_v(p.status) != "missed" and _v(p.status) not in ACTIVE, -p.avoided_cents))]) + [""]
    orders = store.workorders.list()
    if orders:
        counts: dict[str, int] = {}
        for w in orders:
            counts[_v(w.status)] = counts.get(_v(w.status), 0) + 1
        lines += ["## Work orders", "", "- " + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())), ""]
        blocked = [w for w in orders if _v(w.status) == "blocked"]
        lines += _table(["Work order", "Building", "Action", "Latest update"], [
            [w.id, store.buildings.require(w.building_id).name, w.action_code, (w.updates or [""])[-1]] for w in blocked]) + ([""] if blocked else [])
    sites = store.resources.list(city=sc.city)
    refs = store.referrals.list()
    if sites or refs:
        by_status: dict[str, int] = {}
        for r in sites:
            by_status[_v(r.status)] = by_status.get(_v(r.status), 0) + 1
        cbre = [r for r in sites if _v(r.type) == "cbre_help_site"]
        lines += ["## Community help", "",
                  f"- Help sites in {sc.city}: " + ", ".join(f"{n} {k}" for k, n in sorted(by_status.items())) + ".",
                  f"- CBRE buildings offered as help sites: {len(cbre)}" + (f" ({', '.join(r.name for r in cbre)})." if cbre else "."),
                  f"- Residents helped: {sum(r.people for r in refs if r.status in ('routed', 'rerouted', 'arrived'))} people in "
                  f"{len(refs)} requests; {sum(1 for r in refs if r.status == 'rerouted')} re-routed to safety, "
                  f"{sum(1 for r in refs if r.status == 'unrouted')} awaiting a coordinator.", ""]
    narrative = _narrative("executive_summary", {"scenario": sc.name, "net_exposure_cents": s.net_exposure_cents,
                                                 "avoided_cents": s.avoided_cents, "buildings_at_risk": s.buildings_at_risk})
    if narrative:
        lines[4:4] = ["## Overview", "", narrative, ""]
    lines += ["## Method and sources", "",
              "Per-building exposure combines the hazard at each site, utility outages and backup power, tenant leases and SLAs, "
              "and insurance terms (damage + rent abatement + SLA penalties + operations − insurance recovery).",
              f"Event sources: {'; '.join(sc.sources)}.", f"*{sc.disclaimer}*", ""]
    return title, "\n".join(lines)


# ---------- tenant notice ----------

def _tenant_notice(building_id: str) -> tuple[str, str]:
    from app.modules.actions import catalog
    b = store.buildings.require(building_id)
    sc, step = scenarios.scenario(), scenarios.step()
    i = impact.impact_for(building_id)
    plans = [p for p in store.plans.list(building_id=building_id) if _v(p.status) in ACTIVE]
    doing = [(a, _v(p.status)) for p in plans for a in p.actions]
    onsite = store.parties.get(b.onsite_party_id)
    title = f"Notice to tenants: {b.name}"
    lines = [f"# {title}", "", f"*{b.address} · {sc.name} · {step.label}*", "", "## What is happening", ""]
    if b.city != sc.city or _v(i.risk) == "none":
        lines += [f"No impact on {b.name} is identified by the selected {sc.name} scenario. This is not a verified assessment of local safety or power availability.", ""]
    else:
        lines += [f"{step.narrative}", ""] + [f"- {d}" for d in i.drivers if not d.startswith("Insurance")] + [""]
        if i.money.downtime_days:
            lines += [f"Current estimate: the building may be unusable for about **{i.money.downtime_days:g} days**.", ""]
    lines += ["## What management is doing", ""]
    lines += [f"- {'Completed' if status == 'done' else 'Approved response'}: {a.title} (by {hour_label(a.act_by_hour)} relative to impact)" for a, status in doing] or ["- No approved response actions are recorded for this step."]
    lines += ["", "## What you need to do", ""]
    asks = []
    for p in plans:
        if _v(p.status) == "done":
            continue
        for action in p.actions:
            if step.hour > action.act_by_hour:
                continue
            template = catalog.get(action.code)
            if template and template.tenant_notice_text:
                deadline = f"{abs(action.act_by_hour)} hours {'before' if action.act_by_hour < 0 else 'after'} impact" if action.act_by_hour else "at impact"
                asks.append(template.tenant_notice_text.replace("{building}", b.name).replace("{deadline}", deadline))
    lines += [f"- {text}" for text in dict.fromkeys(asks)] or ["- Follow official local emergency guidance and contact building management for site-specific instructions."]
    contact = f"{onsite.name}, {onsite.phone}" if onsite else "building management"
    lines += ["", "## Contact", "", f"Questions or urgent issues: **{contact}**.", "", f"*{sc.disclaimer}*", ""]
    return title, "\n".join(lines)


# ---------- public ----------

def generate(kind: str, building_id: str | None = None, send: bool = False) -> schemas.Report:
    """Build a report and store it; emits report.created. send=True also texts a short tenant notice to each tenant contact."""
    kind = _v(kind)
    if impact.summary().data_quality == "unknown":
        raise ValueError("Live financial inputs are unknown; report generation is unavailable until current sources are confirmed")
    if kind == "executive_summary":
        title, md = _executive_summary()
    elif kind == "tenant_notice":
        if not building_id:
            raise ValueError("tenant_notice needs building_id")
        title, md = _tenant_notice(building_id)
    else:
        raise ValueError(f"unknown report kind {kind}")
    report = store.reports.put(schemas.Report(
        id=ids.new_id("RPT"), kind=kind, scenario_id=scenarios.current().scenario_id, building_id=building_id, title=title,
        markdown=md, created_wall=datetime.now(timezone.utc).isoformat(timespec="seconds")))
    bus.emit("report.created", {"report_id": report.id, "kind": kind})
    if send and kind == "tenant_notice":
        _text_tenants(report)
    return report


def _text_tenants(report: schemas.Report) -> None:
    from app.modules import messaging
    b = store.buildings.require(report.building_id)
    section = report.markdown.split("## What you need to do\n", 1)[1].split("\n## ", 1)[0]
    asks = [line[2:].strip() for line in section.splitlines() if line.startswith("- ")]
    short = f"Notice from {b.name} management: " + " ".join(asks)
    onsite = store.parties.get(b.onsite_party_id)
    if onsite:
        short += f" Questions: {onsite.name}, {onsite.phone}."
    parsed = urlsplit(settings.app_base_url)
    if parsed.scheme in ("https", "http") and parsed.hostname and parsed.hostname not in ("localhost", "127.0.0.1", "::1", "0.0.0.0") and not parsed.username and not parsed.password:
        short += f" Full notice: {parsed.scheme}://{parsed.netloc}/api/reports/{report.id}/html"
    for contact in dict.fromkeys(t.contact_party_id or t.id for t in b.tenants):
        if store.parties.get(contact):
            messaging.send(contact, short, "tenant_notice")


def html(report_id: str) -> str:
    r = store.reports.require(report_id)
    return markdown_to_html(r.markdown, r.title)


def register() -> None:
    """Nothing to subscribe to."""


from .routes import router  # noqa: E402

__all__ = ["generate", "html", "register", "router"]
