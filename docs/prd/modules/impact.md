# Module: impact (`backend/app/modules/impact/`)

**Skills:** backend, python, data · **Read also:** `03-data-and-scenarios.md` (reference implementation: `demo/model.js`), §3 (implement it exactly)

## Job
The CBRE core: **for every building, what will this disaster cost the business, and why.** Joins the fragmented data
(hazard at the site, utility outage → generator cascade, building systems, tenant leases/SLAs, insurance) into one
`Impact` with a money breakdown and plain-English drivers.

## Owns
`backend/app/modules/impact/**` (including `constants.py` with every curve and constant from `03` §3).

## Interface (`__init__.py`)
```python
def register() -> None                 # bus.on("timeline.changed", recompute) and on("plan.changed", recompute)
def recompute(hour: int | None = None) -> list[Impact]          # all buildings; caches; emits impact.updated
def impact_for(building_id: str, hour: int | None = None, extra_actions: list[str] = []) -> Impact
    # applies approved actions (actions.approved_codes) + extra_actions (what-if). Pure function of inputs
def baseline_for(building_id: str, hour: int | None = None) -> Impact   # with NO actions (for 'avoided' math)
def summary() -> PortfolioSummary
def site_safe(lat: float, lon: float, utility_node_id: str | None = None, hour: int | None = None) -> bool
    # False if flood/surge depth > 0.5 ft, wind > 74 mph, in burn zone, or the utility node is down (for help sites)
router   # GET /api/impact, /api/impact/{id}, /api/portfolio/summary
```
Action effects come from `ActionTemplate.effect` (load the catalog via `from app.modules.actions import catalog`).
`avoided_cents` in the summary = Σ (baseline net − current net) over buildings with approved actions.

## Rules
- Exposure: `scenarios.hazard_at(b.lat, b.lon, hour)`. Power: `power_out_hours = scenarios.outage_hours(b.utility_node_id, hour)`.
  Generator hours = `systems.generator_fuel_hours` + any `add_generator_hours` from actions (RENTAL_GENERATOR gives a building without a generator 72h).
- `cause_chain` examples: `["UTL-HOU-SUB3 down (96h)", "generator covers 18h", "78h unpowered"]`, `["3.1 ft above first floor"]`.
- `drivers`: 2–5 short strings ordered by dollar contribution.
- Buildings outside the scenario's city: risk `none`, all zeros, driver "not in the hazard area".
- Performance: `recompute` for 12 buildings × 1 step in under 50 ms (no network calls).

## Acceptance (pytest)
- The flood curve interpolates correctly (2.5 ft → 0.21).
- Bayou Plaza at hour 0 (Harvey): net exposure is in the high/severe band. Approving FLOOD_BARRIERS + RELOCATE_EQUIPMENT lowers it by ≥ 50%.
- Lone Star Data Center (Uri) without fuel: SLA dominates the drivers. Adding GENERATOR_FUEL cuts unpowered hours by 24.
- `site_safe` is False for a point inside a flood band and for a site whose substation is down.
- The money waterfall always balances: `net = damage + rent + sla + ops − recovery`.
