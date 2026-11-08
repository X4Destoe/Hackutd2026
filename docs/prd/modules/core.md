# Module: core (`backend/app/shared/` + `backend/app/main.py`)

**Skills:** backend, python, architecture · **Read also:** `01-architecture.md`, `02-contracts.md`

## Job
Turn the contracts into code and provide the runtime every module uses: **schemas, in-memory store, event bus + SSE,
IDs, config, app wiring**. No business logic.

## Owns
`backend/app/shared/{schemas,enums,ids,events,store,config}.py`, `backend/app/shared/tests/`, `backend/app/main.py`.

## Interface
```python
from app.shared import schemas, enums, ids, config
from app.shared.store import store       # store.buildings, utilities, parties, plans, workorders, messages,
                                         # resources, referrals, reports (+ store.state dict for DemoState)
from app.shared.events import bus
```
- **schemas/enums:** every model and enum in `02-contracts.md` with identical names. Optional fields default `None`, lists default `[]`.
- **store:** `Repo[T]` with `get(id)`, `require(id)` (KeyError → 404 handler), `list(**eq_filters)`, `put(obj)`, `delete(id)`,
  `count()`. `store.reset()` clears all repos and id counters.
- **ids:** `new_id(prefix, width)`: `PLAN` 3, `WO` 3, `MSG` 4, `REF` 4, `RPT` 3.
- **events:** `bus.on(type, fn)`, `bus.emit(type, payload)`. Handlers run synchronously and their exceptions are logged.
  Every emit is also queued to SSE clients (`GET /api/events`, `text/event-stream`, a `: ping` every 15s, a per-client queue of 500, drop oldest).
- **config:** env settings per `01-architecture.md` §4.
- **main.py:** `create_app()` imports every package in `app.modules` and includes its `router` under `/api`, calls its
  `register()`, adds `/api/health`, `/api/events`, `/api/_contracts` (a model with every schema as an optional field so
  OpenAPI includes all types), CORS allow-all, and a KeyError → 404 handler. On startup it calls `scenarios.load("harvey_houston")` if that module exists.

## Acceptance
- `pytest backend/app/shared` passes: store CRUD + filters, reset, bus handler + SSE frame format.
- `uvicorn app.main:app` starts with no modules. `/api/health` is ok, `/api/events` streams pings, `/openapi.json` lists all schemas.
