# 01 - Architecture, stack, layout, run commands

## 1. Stack (decided)

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.11+, FastAPI, Uvicorn, Pydantic v2** | The team knows Python/Flask. Typed contract → generated frontend types |
| Geometry | **shapely** (point-in-polygon, distances) | Hazard footprint lookups in a few lines |
| HTTP | **httpx** | Photon, LLMs |
| LLM | Optional `anthropic` / `openai` / `google-genai`, lazy-imported behind `ai` | Team has mixed keys. Templates when none |
| Store | **In-memory** repositories, seeded from JSON, reset per demo | No database to break |
| Live updates | **Server-Sent Events** `GET /api/events` | One-way push, simple |
| Frontend | **React 18 + Vite + TypeScript** | Team knows it |
| UI | **Tailwind CSS + shadcn/ui** | Fast and consistent |
| Map | **MapLibre GL JS** via `react-map-gl/maplibre` | Free, no token, GeoJSON fill/line/circle layers. **VERIFY** tile style URL (OpenFreeMap "liberty" or Carto Positron) |
| Overlay animation | MapLibre layer paint animation + one `<canvas>` particle layer (snow/rain/embers) | See `modules/map.md` |
| Data fetching | **TanStack Query** + `EventSource` | Cache + live invalidation |
| API types | **openapi-typescript** → `frontend/src/shared/api-types.ts` | Backend schemas are the single source of truth |
| Messaging | **Photon 2.0** (real phones) + **SimChannel** | Live for judges, simulated for scale |
| Tunnel | **cloudflared** quick tunnel | Photon webhooks reach the laptop |
| Tests | pytest (backend), `npm run build` (frontend) | |

## 2. Runtime

```
Browser (React SPA)                               FastAPI (one process)
┌──────────────────────────────────┐  REST /api   ┌──────────────────────────────────────────┐
│ Top bar: scenario · Fix-First ·  │ ───────────> │ scenarios → impact → actions             │
│ Work orders · Resources · Reports│ <─────────── │        │        │        └→ messaging ──┼──> Photon ──> phones
│ Left panel │ Big map + overlays  │   SSE        │        └→ resources (safety from impact) │
│            │ + timeline control  │ <═════════   │ reports · ai · core (store, events)      │
└──────────────────────────────────┘              └──────────────────────────────────────────┘
                                   Photon ──> cloudflared ──> POST /api/webhooks/photon
```

**No running clock.** The demo moves between discrete **timeline steps** (e.g. −48h, −24h, −12h, 0h, +12h, +48h, +7d)
grouped into three phases. Changing the step (`POST /api/timeline`) does the following, synchronously and in under 1 second:
1. `scenarios` sets the current step and emits `timeline.changed`.
2. `impact.recompute()` (pure function over buildings × hazard at this step), then emits `impact.updated`.
3. `actions.refresh()` (plans, ROI, act-by, overdue flags), then emits `plans.updated`.
4. `resources.refresh_safety()`. Sites inside the hazard or without power close. Active referrals there are re-routed.

Modules communicate only through public interface functions and events (`02-contracts.md`).

## 3. Repo layout (product repo)

```
backend/
  pyproject.toml
  app/
    main.py                 # create_app(): auto-mounts each module's `router`, calls `register()`
    shared/                 # contracts in code (owned by core): schemas.py enums.py ids.py events.py store.py config.py
    modules/<name>/         # __init__.py = public interface · INTERFACE.md · README.md · router.py · *.py · tests/
  data/
    scenarios/*.json        # real-disaster presets (scenarios module)
    portfolio.json          # buildings + tenants + insurance (scenarios module)
    utilities.json          # substations etc. (scenarios module)
    resources.json          # help sites per city (resources module)
    actions.json            # action catalog (actions module)
frontend/
  src/App.tsx               # layout + routes (web-shell)
  src/shared/               # api client, generated types, useEvents, tokens, ui/ (web-shell)
  src/modules/map/          # map + overlays + timeline (map)
  src/modules/panel/        # left panel views (panel)
docs/prd/                   # this pack
.env.example
```

## 4. Environment (`.env.example`)
```
APP_BASE_URL=http://localhost:5173
PUBLIC_WEBHOOK_URL=                 # cloudflared URL for Photon
LLM_PROVIDER=none                   # anthropic | openai | gemini | none
LLM_MODEL=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
MESSAGING_MODE=sim                  # sim | photon
PHOTON_API_KEY=                     # VERIFY name/format
PHOTON_SENDER=                      # VERIFY
DEMO_PHONES=                        # +1214...:TECH-HOU-01,+1469...:TEN-003,+1972...:RESIDENT
VITE_MAP_STYLE=                     # optional tile style URL override
```
Blank values still give a full working demo (sim messaging, template AI).

## 5. Run
```bash
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run gen:api && npm run dev     # http://localhost:5173 (proxy /api → :8000)
cloudflared tunnel --url http://localhost:8000                    # demo day, for Photon webhooks
```

## 6. Cross-cutting rules
- **Money** is an integer number of **USD cents** in data. Format it in the UI. **Hours** are relative to landfall/impact (0 = impact).
- **Deterministic:** same scenario + same step + same approvals gives the same numbers. No randomness in money.
- **Fail soft:** LLM or Photon errors are logged, then the template or simulator is used. Never block a timeline change on network calls.
- **Explainable:** every dollar figure carries a `drivers` list of plain-English reasons, shown in the UI.
