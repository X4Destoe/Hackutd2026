# impact public interface

Import `from app.modules import impact`. Spec: `docs/prd/modules/impact.md`, formulas `docs/prd/03-data-and-scenarios.md` §3
(every constant in `constants.py`, the model in `model.py` as a pure function).

| Function | Returns |
|---|---|
| `impact_for(building_id, hour=None, extra_actions=None)` | `Impact` with approved actions (`actions.approved_codes`) + what-if `extra_actions`. Unknown building or action code → `KeyError` (404). |
| `baseline_for(building_id, hour=None)` | `Impact` with no plan actions (for "avoided" math) |
| `recompute(hour=None)` | `[Impact]` for all 12 buildings; at the current step it caches and emits `impact.updated {step_hour, summary}` |
| `latest()` | cached `[Impact]` at the current step |
| `summary(impacts=None)` | `PortfolioSummary`; `avoided_cents` = Σ (baseline net − current net) over buildings with approved actions |
| `site_safe(lat, lon, utility_node_id=None, hour=None)` | `False` if water > 0.5 ft, wind > 74 mph or burn zone **right now** (`scenarios.hazard_at(..., present=True)`), or the node is down |

Routes: `GET /api/impact?hour=`, `GET /api/impact/{building_id}?hour=`, `GET /api/portfolio/summary`.
Recomputes on `scenario.loaded`, `timeline.changed`, `plan.changed`.

## Notes for consumers
- **actions** (TASK-019): impact reads `from app.modules.actions import catalog, approved_codes` lazily. Until that module
  exists it uses `data/actions.json` and no approvals. For a plan, use `baseline_for(b).money.net_exposure_cents -
  impact_for(b, extra_actions=codes).money.net_exposure_cents` as `avoided`.
- Avoided dollars are the **owner's net**: insurance absorbs most avoided property damage above the deductible, so savings
  come largely from downtime, SLA and uninsured costs. Bayou Plaza: barriers + relocation cut gross loss 77% but net 30%
  ($894k for $24k, ~37x). This is deliberate and a good CBRE talking point (who actually benefits from mitigation).
- `exposure.cause_chain` e.g. `["Downtown substation down (96h)", "generator covers 18h", "78h unpowered", "3.0 ft above first floor", "tenants out 53 days"]`.
- `drivers`: up to 4 ranked by dollar contribution, then the insurance line.
- A building with `systems.flood_barriers_installed` counts FLOOD_BARRIERS as permanent (also in the baseline).
