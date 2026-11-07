# Module: cascade (`backend/app/modules/cascade/`)

**Skills:** backend, python, data (ml helpful) · **Read also:** `03-data-and-scenario.md` §3 and §8

## Job
The engine. Hold the dependency graph, propagate failures as they happen, and **predict** what fails
next and when, with a human-readable "why" chain. CBRE's core ask ("predict cascading failures") and
the trigger for everything State Farm does.

## Owns
`backend/app/modules/cascade/**`

## Depends on
core; `scenario.weather_at()` (outdoor temperature). Consumes events `scenario.event`, `weather.updated`.

## Public interface (`__init__.py`)
```python
def register() -> None                     # clock.register("cascade", on_tick, order=20); bus.on("scenario.event", ...)
def predict(horizon_h: int = 12) -> list[Prediction]
def home_status(customer_id: str) -> dict  # {has_power, has_heat, has_water, hours_to_unsafe, hours_to_pipe_burst, lost_heat_at}
def building_outlook(building_id: str) -> dict   # {state, countdown_minutes, cause_chain: [node_id], on_backup: bool}
def apply_effect(effect: dict) -> None     # from approved CBRE actions: {node_id, add_buffer_hours?, restore?, harden?}
def predict_with(effects: list[dict], horizon_h: int = 12) -> list[Prediction]   # what-if on a copy; store untouched
def chains() -> list[CascadeChain]
router                                     # GET /api/graph, /api/cascade/predictions, /api/cascade/chains
```
Emits: `node.changed`, `prediction.updated`, `customer.affected`.

## Graph semantics
Build a `networkx.DiGraph` from `store.nodes`/`store.edges` at load (and on `store.reset`). For node `n`:
- **Supplied** if, for **every** distinct `group` among its incoming edges, **at least one** source in that group is
  in state `ok`/`on_backup`/`restored` (AND across groups, OR within a group). Nodes with no incoming edges are supplied
  unless failed by an event.
- **Losing supply:** if `buffer_hours > 0`, set `state=on_backup`, `lost_supply_at=now`, `buffer_left_hours=buffer_hours`
  and count it down each tick. Fail when it reaches 0. If `buffer_hours == 0`, set `state=failed` immediately.
- **Building generators:** `SYS-BLD-xx-GEN` is a source node in the building's `grid` group, so when the feeder fails the
  building stays supplied **through the generator**. The generator node's own `buffer_hours = generator.fuel_hours_left`
  and only counts down while it is the only live supplier. Fuel exhaustion fails the generator, which fails the building.
- **Restore:** `RESTORE` event or `apply_effect(restore=True)` sets `state=restored`, re-supplies downstream
  (homes regain heat, so their thermal clocks reset).
- **Homes:** state `failed` = no power, so no heat. Thermal model from `03` §8 gives `hours_to_unsafe` and
  `hours_to_pipe_burst` (outdoor temperature = `weather_at(lost_heat_at)`, refreshed on `weather.updated`).
  Home `predicted_fail_at` = time it becomes **unsafe**. A home losing water (pump/zone failed) adds `no_water`.

## Event handling
- `LOAD_SHED {node_id}` / `FAULT {node_id}`: set node `failed`, `failed_at=now`, then propagate (BFS over successors,
  re-evaluating supply). For each node whose state changed: emit `node.changed`. For each home that became
  unsupplied: emit `customer.affected {customer_id, node_id: <root>, cause: "<root name> outage", predicted: False}`.
- `RESTORE {node_id}`: inverse.
- Propagation for the full 2,000-home graph must finish in under 100 ms (BFS from the changed node only).

## Prediction pass (every `PREDICT_EVERY_MINUTES`, and right after any state change)
Copy current states and run a fast forward simulation in 15-min steps up to `horizon_h`, **assuming no new events and
no fixes**. Buffers count down, generators run dry, pumps drain, homes cool (thermal formula, no stepping needed).
Record the first time each currently-ok/on_backup node would fail → `Prediction{node_id, predicted_fail_at, eta_minutes,
cause_chain, confidence}`.
- `cause_chain` = path of failed ancestors from the root cause to this node (walk predecessors that are failed/predicted-failed,
  earliest first). For example `[SUB-3, FDR-3B, SYS-BLD-07-GEN, BLD-07]`.
- `confidence` = 0.9 for buffer exhaustion (deterministic fuel/tank), 0.7 for thermal (model estimate).
- Write `predicted_fail_at`/`predicted_cause` onto the nodes and emit `prediction.updated` with the 10 soonest.
- **Pre-alert:** for homes predicted unsafe within 3h that aren't yet affected, emit
  `customer.affected {..., predicted: True}` once. That lets outreach warn people *before* harm. This is the "before
  disruptions spread" story.

## Chains (`GET /api/cascade/chains`)
Group current + predicted failures by root cause: one `CascadeChain` per failed root (load-shed substation/feeder),
steps ordered by time with `predicted` flags and short reasons ("load-shed", "no supply from FDR-3B",
"generator fuel exhausted", "indoor < 50°F"). `customers_affected` and `buildings_affected` are counts. The frontend draws
these with React Flow.

## apply_effect(effect)
`add_buffer_hours`: add to the node's `buffer_hours` and `buffer_left_hours` (refuel). `restore`: as RESTORE.
`harden`: mark `attrs.hardened=True` (pipe freeze protection), so pipe-burst predictions for that node are skipped.
Then re-run the prediction pass immediately, so the UI updates within 2 seconds (success criterion 4).

## Acceptance (pytest, small hand-built graph)
- AND/OR groups: a node with groups {grid: [FDR, GEN]} stays supplied when FDR fails and fails when GEN's buffer runs out.
- Load-shed SUB-3 on the seed data → every home on SUB-3 feeders gets `customer.affected`. Count matches the seed.
- BLD-07 prediction after SUB-3 load-shed at minute 90 ≈ minute 390 (±15), cause chain ends `... SYS-BLD-07-GEN, BLD-07`.
- `apply_effect({node_id: "SYS-BLD-07-GEN", add_buffer_hours: 24})` moves the prediction later by ~24h.
- Thermal: To=10°F, poor insulation → `hours_to_unsafe` ≈ 3.1 (±0.1).

## Not in scope
ML. Rule/physics-based only for MVP. Stretch: a learned failure probability per node replacing the fixed confidence.
