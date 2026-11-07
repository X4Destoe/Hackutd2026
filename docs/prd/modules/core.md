# Module: core (`backend/app/shared/` + `backend/app/main.py`)

**Skills:** backend, python, architecture · **Read also:** `01-architecture.md` §2–3, `02-contracts.md` (all)

## Job
Turn the contracts into code and provide the four runtime services every other module uses:
**store, event bus, sim clock, app wiring**. Core has no business logic.

## Owns
`backend/app/shared/{schemas,enums,ids,events,store,clock,config}.py`, `backend/app/main.py`,
`backend/app/shared/tests/`. Nobody else edits these files. Changes go through a contract decision.

## Public interface
```python
from app.shared import schemas, enums, ids, config
from app.shared.store import store          # repositories
from app.shared.events import bus, EventType
from app.shared.clock import clock
```

### schemas.py / enums.py
Every model and enum in `02-contracts.md` §2–3, exactly as named. Pydantic v2 `BaseModel`, all optional fields
default `None`, all lists default `[]` (`Field(default_factory=list)`).

### ids.py
`new_id(prefix: str, width: int) -> str`: per-prefix counters, reset by `store.reset()`.
Widths: CASE 4, MSG 6, RSV 4, OFR 4, ACT 3, WO 3, RES 3.

### store.py
In-memory repositories, one per model: `store.nodes, edges, customers, cases, messages, resources,
reservations, adjusters, offers, buildings, actions, workorders`.
```python
class Repo(Generic[T]):
    def get(self, id: str) -> T | None
    def require(self, id: str) -> T            # raises KeyError → API 404
    def list(self, **filters) -> list[T]       # equality filters on fields, e.g. list(status="alerted")
    def put(self, obj: T) -> T                 # insert or replace by obj.id
    def delete(self, id: str) -> None
    def count(self) -> int
store.reset() -> None                          # clears everything + id counters
store.index(name, key_fn)                      # optional secondary index, e.g. customers by home_node_id
```
Single process, so no locking. Callers `put()` a copy after modifying (`obj.model_copy(update=...)`).

### events.py
```python
class EventBus:
    def on(self, type: str, handler: Callable[[dict], None]) -> None
    def emit(self, type: str, payload: dict) -> None   # calls handlers sync, then queues for SSE
    async def stream(self) -> AsyncIterator[str]       # per-client SSE frames: "event: t\ndata: {...}\n\n"
EventType  # str constants for every type in 02-contracts.md §5
```
Handler exceptions are caught and logged. One bad handler never breaks emit. SSE clients each get an
`asyncio.Queue(maxsize=1000)`. If a client is slow, drop its oldest frames. Send a `: ping` comment every 15s.

### clock.py
```python
class SimClock:
    def now(self) -> int                                  # sim_minute
    def iso(self, minute: int | None = None) -> str
    def register(self, name: str, on_tick: Callable[[int], None], order: int) -> None
    def configure(self, start_minute: int, start_iso: str) -> None
    def start(self) / pause(self) / set_speed(self, min_per_sec: float)
    def advance_to(self, minute: int) -> None             # runs every tick in between synchronously (jump)
    running: bool; speed: float
```
The background asyncio task ticks every `TICK_MINUTES / speed` real seconds. Each tick: `now += TICK_MINUTES`,
call registered handlers in `order` (tick order in `01-architecture.md` §2), then emit `clock.tick`.
A handler raising is logged and skipped.

### main.py
`create_app()`: FastAPI app with
1. Settings from env (`config.settings`, pydantic-settings or `os.environ`).
2. Imports every package in `app.modules` (pkgutil). If it has `router`, include it under `/api`.
   If it has `register()`, call it (modules register tick handlers and bus subscriptions there).
3. Core routes: `GET /api/health`, `GET /api/events` (SSE via `StreamingResponse`, media type `text/event-stream`),
   and `GET /api/_contracts`. That last one returns a `Contracts` model with one optional field per schema, so every model
   appears in `/openapi.json` and in the generated frontend types even before its owner's route exists.
4. On startup: `from app.modules import scenario; scenario.load("uri_dfw")` if available, else start empty.
5. CORS allow all (dev only).
`app = create_app()` at module level for uvicorn.

## Acceptance
- `pytest backend/app/shared` passes: store CRUD + filters, id counters reset, bus emit → handler + SSE frame
  format, clock `advance_to` calls handlers in order exactly `(target-now)/5` times.
- `uvicorn app.main:app` starts with zero modules present. `/api/health` returns ok and `/api/events` streams pings.
- `/openapi.json` exposes every schema, so the frontend type generation works.

## Not in scope
Persistence, auth, multi-worker. Don't add business fields that aren't in the contracts.
