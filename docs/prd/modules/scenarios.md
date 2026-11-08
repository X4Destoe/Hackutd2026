# Module: scenarios (`backend/app/modules/scenarios/` + `backend/data/`)

**Skills:** data, python, backend · **Read also:** `03-data-and-scenarios.md` §1–2

## Job
Own the world: the real-disaster presets (timeline steps, hazard overlays, utility outages), the portfolio seed
(buildings, utilities, parties), the demo state, and the hazard lookup every other module uses.

## Owns
`backend/app/modules/scenarios/**`, `backend/data/scenarios/*.json`, `backend/data/anchors/*.json`, `backend/data/make_overlays.py`,
`backend/data/{portfolio,utilities,parties}.json`.

## Interface (`__init__.py`)
```python
def register() -> None
def load(scenario_id: str) -> DemoState        # store.reset(); seed portfolio/utilities/parties; apply DEMO_PHONES; step = -48
def current() -> DemoState
def scenario() -> Scenario
def step(hour: int | None = None) -> TimelineStep
def set_hour(hour: int) -> DemoState           # validates the hour, emits timeline.changed
def hazard_at(lat: float, lon: float, hour: int | None = None) -> dict
    # {"flood_depth_ft","wind_mph","ice_in","temp_f","in_burn_zone"}: max intensity of overlay features containing the point;
    # at recovery steps returns the PEAK over all steps <= hour (damage doesn't un-happen)
def utility_down(node_id: str, hour: int | None = None) -> bool
def outage_hours(node_id: str, hour: int | None = None) -> float   # total predicted/actual outage duration at that step (0 if none)
router   # /api/scenarios, /api/demo/*, /api/timeline, /api/overlays, /api/buildings, /api/utilities
```
Order on `set_hour`: update state → emit `timeline.changed`. `impact`, `actions` and `resources` subscribe and recompute (see their files).
Reset (`POST /api/demo/reset`) = `load()` + clear approvals, work orders, messages, referrals and reports (store.reset covers it).

**Implementation note (TASK-015):** compute `hazard_at` analytically from `data/anchors/<id>.json` (same formulas as
`demo/model.js`: smooth depth by distance to river lines/pools, wind by distance to the track, ice/temperature inside the
winter area). The banded overlay polygons in `data/scenarios/<id>.json` are for drawing and are coarser (3 bands).

## Data work (this is the biggest part of the module)
1. `make_overlays.py` (generic) reads `backend/data/anchors/<scenario_id>.json` (hand-placed polylines for bayous/coast, points for
   low spots, per step: intensity bands + buffer distances) and writes the overlay GeoJSON into `scenarios/<scenario_id>.json`,
   buffered with shapely into nested intensity bands per `03` §1. One anchors file per scenario lets each scenario be built in parallel.
   Keep shapes plausible against the real basemap: water follows the actual bayous and coast.
2. Fill in the 12 buildings from `03` §2 with real-ish coordinates in the named neighborhoods (check them on the map), plus tenants,
   insurance, systems and `data_sources`.
3. Tune overlays/outages so the story beats in `00-overview.md` §5 come out. Bayou Plaza ≈ 3 ft above its first floor at impact.
   BLD-HOU-03 > 3 ft (barriers useless). BLD-HOU-04 dry. Uri: BLD-DAL-02 net ≈ $1–2M without action.

## Acceptance
- `POST /api/scenarios/uri_dallas/load` then `GET /api/overlays?hour=0` returns `snow_ice` features. `GET /api/buildings` returns 12.
- `hazard_at` for Bayou Plaza at hour 0 gives a flood depth that puts it about 3 ft above its first floor. At hour 168 it still gives the peak.
- Stepping through all 7 hours via `POST /api/timeline` emits `timeline.changed` each time, in under 50 ms per call (excluding subscribers).
