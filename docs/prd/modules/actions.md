# Module: actions (`backend/app/modules/actions/` + `backend/data/actions.json`)

**Skills:** backend, python · **Read also:** `03-data-and-scenarios.md` §4

## Job
Turn dollars into **decisions CBRE can execute**: build per-building plans from the action catalog with cost, money saved,
ROI and an act-by deadline. Rank them into the **Fix-First** list. On approval, create **work orders** and send them (and
tenant notices) through messaging. Then close the loop from technician replies.

## Owns
`backend/app/modules/actions/**`, `backend/data/actions.json`.

## Interface (`__init__.py`)
```python
catalog: dict[str, ActionTemplate]              # loaded at import
def register() -> None                          # on timeline.changed/impact.updated → refresh(); messaging.on_inbound("technician", ...)
def refresh() -> list[Plan]                     # rebuild proposed plans for the current step; mark missed; emit plans.updated
def approve(plan_id: str, by: str) -> Plan
def reject(plan_id: str, by: str) -> Plan
def approved_codes(building_id: str) -> list[str]
def fix_first(limit: int = 10) -> list[FixFirstItem]
def apply_task_reply(party_id: str, text: str, media_urls: list[str]) -> WorkOrder | None
router  # /api/actions/catalog, /api/plans, approve/reject, /api/fix-first, /api/workorders, /api/workorders/{id}/update
```

## Plan building (`refresh`)
For each building with risk ≠ none and no approved plan for this scenario:
1. Candidates = templates whose `effect.hazards` intersect the building's hazards (or are empty), whose requirements match
   (generator / no generator), with `current_hour ≤ act_by_hour`. Community templates (OFFER_HELP_SITE) only if `can_host_help_site`
   and `impact.site_safe(building)`.
2. Greedy: repeatedly add the candidate with the highest marginal `avoided / cost`, where
   `avoided = baseline.net − impact_for(b, extra_actions=chosen+[c]).net`. Stop when the best marginal ROI ≤ 1.
3. `Plan.act_by_hour` = min of the chosen actions' `act_by_hour`. `rationale` = `ai.rationale(facts)` (a template fallback is fine).
4. If the step is past a previously proposed plan's act-by and it wasn't approved, set status `missed` and keep
   `avoided_cents` as "would have saved". Keep missed plans visible.
5. Keep plan IDs stable per (building, scenario) so the UI doesn't flicker. Update in place.

**Fix-First:** proposed plans sorted by `(hours_left ≤ 12 first, roi desc, avoided desc)`. `why` = one sentence ("$980k saved
for $24k; water expected 3 ft above first floor; act within 12h"). Community actions go in a separate list (`?community=1`).

## approve(plan_id)
Status `approved` → for each action: create a `WorkOrder` (party = the building's `onsite_party_id`, text = `task_text`
filled with building name and deadline) → `messaging.send(..., kind=task, work_order_id=...)` → status `sent`. For templates with
`tenant_notice_text` → send to every tenant contact (kind `tenant_notice`). OFFER_HELP_SITE → `resources.register_site(...)`.
Plan status `executing`, then `done` when all work orders are `done`. Emit `plan.changed`, `workorder.changed`. Impact recomputes via the event.

## Technician replies (`apply_task_reply`)
Match the party's open work orders (most recent if several. `DONE 7` / `BLOCKED 7` targets WO-007). `DONE`/`✅`/`done` → `done`.
`BLOCKED <reason>` → `blocked` + the note (UI shows it red and Fix-First flags the plan). Any media → append to `photo_urls`,
status `accepted` if it was `sent`. Anything else → append as an update note. Send a short ack.

## Acceptance
- Harvey at −24: Bayou Plaza plan includes FLOOD_BARRIERS with ROI > 10 and act-by −12. Fix-First top 3 contains it.
- Step to 0 without approving Energy Corridor Tower → its plan is `missed` with "would have saved $X".
- Approve → work orders created and sent (sim). Impact net for that building drops within the same request cycle.
- A simulated technician reply "DONE" closes the work order and emits `workorder.changed`.
