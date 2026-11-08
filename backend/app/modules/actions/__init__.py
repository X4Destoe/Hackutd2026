"""Actions: catalog, Fix-First plans, approve → work orders.

Other modules import `from app.modules import actions` or
`from app.modules.actions import catalog, approved_codes` (impact does the second).
"""

from __future__ import annotations

import json

from app.shared import schemas
from app.shared.config import DATA_DIR
from app.shared.enums import PlanStatus
from app.shared.events import bus
from app.shared.store import store

from .execute import apply_task_reply, approve, reject, update_work_order
from .planning import fix_first, invalidate, on_world_changed, refresh

catalog: dict[str, schemas.ActionTemplate] = {
    template.code: template
    for template in (
        schemas.ActionTemplate.model_validate(row)
        for row in json.loads((DATA_DIR / "actions.json").read_text())
    )
}


def approved_codes(building_id: str) -> list[str]:
    """Action codes on this building's approved / executing / done plan for the current scenario."""
    from app.modules import scenarios

    scenario_id = scenarios.current().scenario_id
    codes: list[str] = []
    for plan in store.plans.list(building_id=building_id):
        if plan.scenario_id != scenario_id:
            continue
        if plan.status in (PlanStatus.approved, PlanStatus.executing, PlanStatus.done):
            codes.extend(action.code for action in plan.actions)
    return codes


def _on_technician(*args, **kwargs) -> None:
    """Accept the shapes messaging may use: (party, text, media) or a single message-like object."""
    party = args[0] if args else kwargs.get("party")
    text = args[1] if len(args) > 1 else kwargs.get("text", "")
    media = args[2] if len(args) > 2 else kwargs.get("media_urls", kwargs.get("media", []))
    if party is not None and text == "" and not isinstance(party, str) and hasattr(party, "body"):
        text = party.body
        media = getattr(party, "media_urls", media)
        party = getattr(party, "party_id", None)
    party_id = getattr(party, "id", party)
    if party_id:
        apply_task_reply(str(party_id), str(text or ""), list(media or []))


def register() -> None:
    bus.on("scenario.loaded", lambda _payload: invalidate())
    bus.on("timeline.changed", on_world_changed)
    bus.on("impact.updated", on_world_changed)
    try:
        from app.modules import messaging
        messaging.on_inbound("technician", _on_technician)
    except ImportError:
        pass


from .routes import router  # noqa: E402

__all__ = [
    "catalog", "register", "router", "refresh", "approve", "reject", "approved_codes",
    "fix_first", "apply_task_reply", "update_work_order", "invalidate",
]
