# Module: portfolio (`backend/app/modules/portfolio/`)

**Skills:** backend, python, ai-integration · **Read also:** `03-data-and-scenario.md` §5, `00-overview.md` §6 step 6

## Job
The CBRE side: turn fragmented building data (BMS, lease, utility, generator log, work orders) into **risk, countdowns
and dollars per building**. Propose **AI action plans**, and on human approval **execute** them as work orders that change
the cascade. Offer buildings predicted to stay up as **help sites** for State Farm customers.

## Owns
`backend/app/modules/portfolio/**`

## Depends on
core; `cascade` (building_outlook, apply_effect, predict_with); `ai.action_rationale`; `resources.register_resource`. Consumes `prediction.updated`, `node.changed`.

## Public interface (`__init__.py`)
```python
def register() -> None                                  # clock order 70
def propose_plans() -> list[ActionPlan]                 # idempotent: one open plan per (building, kind)
def approve(action_id: str, by: str) -> ActionPlan
def reject(action_id: str, by: str) -> ActionPlan
router  # GET /api/buildings, /api/buildings/{id}, /api/actions, POST approve/reject, GET /api/workorders
```

## Building risk (recomputed on prediction.updated / node.changed)
From `cascade.building_outlook(id)`:
- `countdown_minutes` = minutes until the building (or its critical system) is predicted to fail. None = not at risk within 12h.
- `risk` = 1.0 if failed, else `clamp(1 - countdown_minutes/720, 0, 1)`. 0 if no countdown.
- `exposure_cents_per_hour` = Σ tenant `penalty_per_hour_cents` + Σ `rent_per_day_cents`/24 (rent abatement risk), applied only
  while at risk or failed.

## Action catalog (rules propose, AI explains)
| Trigger | Plan (`mitigation`) | Steps → `effect` |
|---|---|---|
| On generator, countdown < 12h | "Extend generator runtime" | `FUEL_DELIVERY` (vendor "North Texas Fuel", $3,800) → `add_buffer_hours: 24` on `SYS-…-GEN`; `SHED_NONCRITICAL` ($0) → `add_buffer_hours: 4` |
| No generator, grid failed or predicted to fail, `freeze_protection: false` | "Prevent pipe freeze damage" | `DRAIN_SPRINKLER_DRY` ($1,200), `PORTABLE_HEAT` ($900) → `harden: true` on `SYS-…-PIPE` |
| Data center, countdown < 12h | add step `PRECOOL_AND_MIGRATE` ($0) → `add_buffer_hours: 1` on `SYS-…-COOL` | |
| Failed grid, tenants with SLA | add step `TENANT_NOTICE` ($0, no effect) | |
| `can_host` and countdown None (stays up ≥12h) | `host_offer`: "Offer as warming center / claim site" | creates `Resource(source=cbre, type=host_types[0], capacity=host_capacity, building_id)` on approval |

`cost_cents` = sum of steps. `avoided_cents` = `exposure_cents_per_hour × hours of downtime avoided` (from re-running
`cascade.predict_with(effects)`, which predicts on a copy with the effects applied. If that's not ready yet, use an
estimate: added buffer hours × exposure, capped by the horizon). `rationale` = `ai.action_rationale`
(rules fallback works). Emit `action.proposed`.

## approve(action_id, by)
Status `approved` → create one `WorkOrder` per step with a vendor (`status=dispatched`, `eta_minutes` 30–90) → status
`executing` → **immediately** call `cascade.apply_effect` for each step's effect (the demo needs instant visible change;
the work orders still show ETAs) → status `done` when every work order is done (sim: done after its eta).
`host_offer` approval → `resources.register_resource(...)`, set `resource_id` on the plan. Emit `action.changed`,
`workorder.changed`. `reject` → status `rejected`. The plan isn't re-proposed unless the countdown drops by more than 50%.

## Routes
`GET /api/buildings` (with live risk fields), `GET /api/buildings/{id}`, `GET /api/actions?status=&building_id=`,
`POST /api/actions/{id}/approve|reject {by}`, `GET /api/workorders`.

## Acceptance
- After SUB-3 load-shed: BLD-07 has a "Extend generator runtime" plan with countdown ≈ 300 min and exposure $42k/h.
- Approving it moves BLD-07's countdown by ≥ 24h within one API call. Work orders exist. `cbre_avoided_cents` in KPIs rises.
- BLD-03 gets a `host_offer`. Approving it creates a `cbre` warming-center resource that `GET /api/resources` lists.
- Re-calling `propose_plans()` doesn't duplicate open plans.

## Not in scope
Real CMMS/work-order integrations, vendor APIs, lease legal analysis (lease data is just tenant SLA/penalty/rent fields).
