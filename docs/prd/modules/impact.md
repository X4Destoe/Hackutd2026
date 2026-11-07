# Module: impact (`backend/app/modules/impact/`)

**Skills:** backend, python, data · **Read also:** `00-overview.md` §8 (success criteria)

## Job
Put numbers on everything: KPIs for the Command Center header and the closing demo beat, insured-loss estimates for State
Farm, SLA exposure and cost avoided for CBRE. Every number traces to one constant or one stored field.

## Owns
`backend/app/modules/impact/**` (including `constants.py` with every dollar assumption)

## Depends on
core (reads store: cases, customers, reservations, buildings, actions). Consumes `case.updated`, `action.changed`,
`clock.tick`.

## Public interface (`__init__.py`)
```python
def register() -> None                    # clock order 80
def kpis() -> Kpis
def breakdown() -> ImpactBreakdown
def claim_estimate_cents(case: Case) -> int
router  # GET /api/kpis, GET /api/impact
```
Emit `kpis.updated` every tick when any value changed (cheap: computed from the store in under 20 ms).

## Definitions
- `customers_affected` = customers with a case. `customers_reached_pct` = cases with `first_contact_at` / affected.
- `unreached` = cases in status `unreached`. `open_by_tier` = non-resolved cases by tier.
- `median_minutes_to_contact` = median(`first_contact_at - alert_sent_at`).
- `deadline_breaches` = cases with `deadline_breached`. `routed` = cases with an active reservation.
  `p1_resolved` = resolved cases whose highest tier was P1 (keep `max_tier` in a dict here).
- `est_insured_loss_cents` = Σ `claim_estimate_cents` over cases.
- `cbre_exposure_cents` = Σ over buildings of `exposure_cents_per_hour × hours at risk or failed so far`.
- `cbre_avoided_cents` = Σ `avoided_cents` of approved plans.
- `sites_open`, `site_capacity_free` from resources.

## Claim estimate (illustrative constants, `constants.py`, shown in the UI as "estimates")
`burst_pipe 1_800_000` · `flooding 2_500_000` · `structure 4_000_000` · `roof 1_200_000` · `no_heat 0` ·
`ALE per displaced household per night 15_000` (hotel/shelter reservation × 3 nights). Sum the damage values per case.
`ImpactBreakdown.assumptions` lists every constant in words. The team should replace them with sourced figures if found
(a FEMA/insurer report on the 2021 storm) and cite the source in that list.

## Acceptance
- With seeded data at minute 600 (sim), every KPI is non-null and `customers_reached_pct` is between 0 and 100.
- Approving the BLD-07 plan increases `cbre_avoided_cents` by that plan's `avoided_cents`.
- `GET /api/impact` lists its assumptions.

## Not in scope
Actuarial accuracy. These are demo-grade estimates with clearly labeled assumptions.
