# scenarios public interface

Import `from app.modules import scenarios`. Spec: `docs/prd/modules/scenarios.md`, contracts `docs/prd/02-contracts.md`.

| Function | Returns |
|---|---|
| `load(scenario_id)` | `DemoState`. Resets the store, seeds buildings/utilities/parties (DEMO_PHONES applied), starts at the first step (−48), emits `scenario.loaded`. Unknown id → `KeyError` (404). |
| `load_definition(scenario, anchors)` | `DemoState`. Validates/copies a synthetic `custom_` definition, keeps at most 16 in memory, and uses normal seeding/events. Registered definitions appear in metadata and work with `load` / `/demo/reset`. No source files are written; historical IDs cannot be overridden. |
| `current()` | `DemoState` (loads the default scenario if nothing is loaded) |
| `scenario()` | `Scenario` currently loaded |
| `step(hour=None)` | `TimelineStep`. A non-step hour snaps to the latest step at or before it. |
| `set_hour(hour)` | `DemoState`. Hour must be one of the step hours (`ValueError` → 422). Updates state, then emits `timeline.changed`. |
| `hazard_at(lat, lon, hour=None, present=False)` | `{"flood_depth_ft", "wind_mph", "ice_in", "temp_f", "in_burn_zone"}` |
| `utility_down(node_id, hour=None)` | `True` while actually out: `0 <= hour < outage_hours` |
| `outage_hours(node_id, hour=None)` | total predicted (forecast) / actual outage duration known at that step, 0 if none |
| `overlays(hour=None)` | one GeoJSON FeatureCollection; each feature has `properties.style`, `.hazard`, `.intensity`, `.overlay_id` |
| `scenarios_meta()` | `[ScenarioMeta]` |

## Two readings of `hazard_at`
- **Default (damage)**, for money (`impact`): forecast steps give the **predicted peak**; impact and recovery steps give the
  **worst seen so far** (PRD 03 §3 peak rule). So a building's hazard does not drop in recovery.
- **`present=True`**, for "is this place safe right now" (`impact.site_safe`, `resources`): what is physically there at that
  step. Zero at forecast steps, receding in recovery. This keyword is an addition to the frozen contract (backward compatible).

`flood_depth_ft` is storm surge when `"surge" in scenario().hazards` (Ian). `temp_f` is `None` outside the winter area.
Values come from the analytic model over `data/anchors/<id>.json` (see `hazard.py`), not from the coarser drawn bands.

## Routes (under /api)
`GET /scenarios` · `POST /scenarios/{id}/load` · `POST /demo/reset {scenario_id?}` · `GET /demo/state` ·
`GET /timeline` (steps: hour, phase, label, narrative, utility_outages; no geometry) · `POST /timeline {hour}` · `GET /overlays?hour=` · `GET /buildings` · `GET /utilities` (each with `down` at the current step)

## Events
`scenario.loaded` and `timeline.changed`, payload `DemoState`. `store.reset()` on load clears plans, work orders, messages,
resources, referrals and reports: modules that seed data (e.g. `resources`) re-seed on `scenario.loaded`.

## Live scenarios (TASK-050)
`live_houston`, `live_dallas`, `live_fort_myers` appear in `GET /scenarios`. Built from `app.modules.live.snapshot()` (real NWS
alerts + hourly forecast; never blocks): steps `-24` "Now · act before the window" (forecast) and `0` "Next 48 h" (impact).
- Overlays = NWS alert polygons near the city, mapped by event (`live_scenario.py` table): flood -> `flood_water`, coastal/surge ->
  `surge_water`, hurricane/tropical/high wind -> `wind_swirl`, winter/ice/freeze -> `snow_ice`. Feature properties add
  `proxy: true, event, severity, headline, ends`.
- `hazard_at` = strongest containing alert's **proxy** value (depth/wind) + the city's forecast min temp / max wind, plus
  `sources` naming the alert; impact appends "— NWS Flood Warning (proxy)" to the matching driver.
- No utility outages (no free real-time feed). Stale/missing feeds are named in the "Now" narrative as unknown, not safe.
- On `live.updated` while a live scenario is shown: rebuilt and `timeline.changed` is emitted (everything recomputes).
