# actions public interface

Import `from app.modules import actions`. Spec: `docs/prd/modules/actions.md`.

| Name | What |
|---|---|
| `catalog` | `dict[code, ActionTemplate]` from `backend/data/actions.json`, validated at import |
| `refresh()` | rebuild plans for the current step, mark missed, emit `plans.updated {count, fix_first_top}`. Runs on `impact.updated` |
| `approve(plan_id, by)` / `reject(plan_id, by)` | proposed → approved / rejected; emits `plan.changed`. Not proposed → `PlanConflict` (HTTP 409) |
| `approved_codes(building_id)` | codes of approved / executing / done plans (impact reads this) |
| `fix_first(limit=10, community=False)` | `[FixFirstItem]`: proposed plans, deadline ≤ 12h first, then ROI, then avoided |
| `plan_is_community(plan)` | True for OFFER_HELP_SITE plans (listed separately, `?community=1`) |

Routes: `GET /actions/catalog`, `GET /plans?building_id=&status=`, `POST /plans/{id}/approve {by}`, `POST /plans/{id}/reject {by}`,
`GET /fix-first?limit=&community=0|1`. **Work-order routes come with TASK-021.**

## Plan rules (as built)
- Greedy by marginal `avoided / cost`, keep while > 1; `avoided` = `impact.impact_for(b).net − impact_for(b, extra_actions=chosen).net`.
- **Two phases, never bundled:** before landfall (hour < 0) only pre-storm actions (act_by < 0); from hour 0 only response
  actions (act_by ≥ 0, e.g. EMERGENCY_DRYOUT, PORTABLE_HEAT).
- `act_by_hour` = earliest chosen action. When it passes unapproved the plan becomes `missed` (keeps `avoided_cents` = "would have
  saved") and a new plan with what is still feasible may appear. Scrubbing back before the deadline revives the missed plan (same id).
- One live plan per building (id stable while it is updated in place). A building with an approved/executing/done/rejected plan
  gets no new proposals.
- Community plan (OFFER_HELP_SITE) for buildings that can host, are safe now (`impact.site_safe`) and dry at the predicted peak.

## For TASK-021 (execute.py)
`approve()` imports `.execute` if it exists and calls `execute.on_approved(plan) -> Plan | None` after setting `approved`, before
emitting `plan.changed`. Create work orders there, set `executing`, send texts, register help sites (OFFER_HELP_SITE). Add
`/workorders` routes in your own router and include it from `routes.py` with one line.
