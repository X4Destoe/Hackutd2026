# Module: scenario (`backend/app/modules/scenario/` + `backend/data/`)

**Skills:** data, python, backend · **Read also:** `03-data-and-scenario.md` (all of it, this module implements it)

## Job
Own the demo world: generate and load seed data, play the storm timeline on the sim clock, drive the
**simulated crowd** (replies from non-live customers and adjusters), and expose the demo controls.

## Owns
`backend/app/modules/scenario/**`, `backend/data/generate_seed.py`, `backend/data/seed/*.json`,
`backend/data/scenarios/*.json`, `backend/data/public/*.json`.

## Depends on
core (store, bus, clock, ids). Calls `messaging.inbound_sim(...)` to inject simulated replies (see messaging).
Doesn't import any other module.

## Public interface (`__init__.py`)
```python
def load(scenario_id: str = "uri_dfw") -> None     # store.reset(); load seed + scenario; apply DEMO_PHONES; clock.configure()
def timeline() -> list[TimelineEvent]
def weather_at(minute: int) -> dict                 # {"temp_f": float, "wind_chill_f": float}, linear interpolation
def scenario_meta() -> dict                         # {id, name, start_iso, center, zoom}
def register() -> None                              # clock.register("scenario", on_tick, order=10); bus.on("message.sent", ...)
router                                              # /api/demo/*
```

## Behavior
1. **Seed generation** (`generate_seed.py`, run manually, outputs are committed): implements the counts and
   distributions in `03-data-and-scenario.md` §2–7. Deterministic. Validates every record against `schemas`
   before writing. CLI: `python -m data.generate_seed --customers 2000 --seed 42`.
2. **Load:** read JSON → `schemas` objects → `store.put`. Apply `DEMO_PHONES` (`+1214...:CUS-0007`): set that
   customer's/adjuster's `phone` and `demo_live=True`. Move a live customer onto a SUB-3 feeder if needed, so they're
   affected early in the demo.
3. **on_tick(now):** for each timeline event with `prev < at <= now`, emit `scenario.event` (`{at, code, description}`
   plus the payload). Emit `weather.updated` when the interpolated temperature changes by ≥1°F.
   **Don't** change node states yourself. `cascade` reacts to `scenario.event` (`LOAD_SHED`, `RESTORE`, `FAULT`),
   `resources` to `SITE_OPEN`, and `outreach` to `ADVISORY_BROADCAST`.
4. **Simulated crowd:** subscribe to `message.sent`. When an outbound `alert`/`voice_call` goes to a non-live customer,
   decide (seeded) per `03` §9 whether and when they reply, and push `(due_minute, party, text)` onto a heap.
   On tick, deliver due replies via `messaging.inbound_sim(party_type, party_id, text)`. Same for `adjuster_offer`
   to non-live adjusters (`ACCEPT` 80% / `PASS`). Choose reply text with
   `cascade.home_status(customer_id)`-consistent needs. That's the one allowed cross-module read, done lazily via
   `from app.modules import cascade` inside the function.
5. **Demo routes:** `POST /demo/reset` → `load()` and paused at `start_minute`. `start/pause/speed`. `jump` →
   `clock.advance_to` (forward only, reject backward with 409). `simulate-reply` → `messaging.inbound_sim` for any
   customer (used by the demo console phone simulator). `GET /demo/status` → `DemoStatus`
   (`messaging_mode`/`llm_provider` read from `config.settings`).

## Acceptance
- `python -m data.generate_seed` writes all files, and re-running gives byte-identical output.
- After `POST /api/demo/reset`: store counts match `03` §2. `GET /api/demo/status` shows `sim_minute = -120`.
- `POST /api/demo/jump {sim_minute: 100}` emits `ADVISORY_BROADCAST`, `GRID_EMERGENCY` and `LOAD_SHED SUB-3` events in order.
- With messaging in sim mode, a test alert to a non-live customer yields a reply event within the configured window
  (seeded test).

## Not in scope
Live API calls during the demo (snapshots only). Editing node states. Scoring or routing anything.
