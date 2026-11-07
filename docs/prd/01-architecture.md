# 01 - Architecture, stack, repo layout, run commands

## 1. Tech stack (decided)

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.11+, FastAPI, Uvicorn, Pydantic v2** | Team knows Flask (FastAPI routes look the same). Python suits graph/ML/AI. FastAPI generates the OpenAPI contract the frontend types come from |
| Graph | **networkx** | Dependency graph + traversal in a few lines |
| Numerics / ML | **numpy**; **scikit-learn** (stretch only) | Heat-loss math, optional trained risk model |
| HTTP client | **httpx** | Photon, LLM fallbacks, public data |
| LLM SDKs | `anthropic`, `openai`, `google-genai`. Each is **optional** and imported lazily | Team has mixed keys. One gateway, any provider (`modules/ai.md`) |
| Store | **In-memory repositories** seeded from JSON, `reset()` per demo run | Zero setup, deterministic demos, no DB to break |
| Live updates | **Server-Sent Events** (`GET /api/events`) via FastAPI `StreamingResponse` | One-way server→browser push, no extra infra |
| Frontend | **React 18 + Vite + TypeScript** | Team knows React/Vite |
| UI kit | **Tailwind CSS** + **shadcn/ui** components | Fast, consistent, easy for design agents |
| Map | **MapLibre GL JS** via `react-map-gl` (`react-map-gl/maplibre`) | Free, no token. **VERIFY** tile style URL (default: OpenFreeMap "liberty"; fallback: Carto Positron) |
| Graph view | **@xyflow/react** (React Flow) | Draw the cascade why-chain |
| Charts | **Recharts** | KPI sparklines |
| Data fetching | **TanStack Query** + native `EventSource` | Cache + live invalidation |
| API types | **openapi-typescript** generates `frontend/src/shared/api-types.ts` from FastAPI `/openapi.json` | Backend schemas are the single source of truth. The frontend can't drift |
| PWA | **vite-plugin-pwa** | "Add to Home Screen" for the help card + field view |
| Messaging | **Photon 2.0** (real) + **SimChannel** (built-in simulator) | Live phones for judges, a simulated crowd for scale |
| Tunnel | **cloudflared** quick tunnel (or ngrok) | Photon webhooks need a public URL to reach the laptop |
| Tests | **pytest** (backend), **vitest** (frontend, light) | Each module ships its own smoke test |
| Design | Figma (via design-plugin-capable agents) and/or static HTML mockups in `design/` | Teammates' preference. Mockups are reference only. React is the product |

Not used on purpose: Next.js (no SSR need, and the team knows Vite), a database (in-memory is enough),
WebSockets (SSE is simpler), Flask (no typed contract).

## 2. Runtime picture

```
 Browser (React SPA, PWA)                       FastAPI process (single worker)
 ┌──────────────────────────┐   REST /api/*    ┌───────────────────────────────────────────┐
 │ Command Center           │ ───────────────> │ api routers (one per module, auto-mounted)│
 │ Portfolio                │ <─────────────── │                                           │
 │ Demo console             │   SSE /api/events│ core: store · event bus · sim clock       │
 │ Help card  (/h/:token)   │ <═══════════════ │ scenario · cascade · triage · outreach    │
 │ Field view (/field/:id)  │                  │ resources · dispatch · portfolio · impact │
 └──────────────────────────┘                  │ ai (LLM gateway) · messaging (channels)   │
                                               └───────┬───────────────────────┬───────────┘
 Real phones <── Photon cloud <── PhotonChannel ───────┘                       │
 Real phones ──> Photon cloud ──> cloudflared ──> POST /api/webhooks/photon    │
                                                       LLM provider APIs <─────┘
```

### Tick loop (the heartbeat)

`core.clock` advances sim time in **5-sim-minute steps**. Speed is configurable: default 1 real second
= 5 sim minutes, so 24 sim hours ≈ 4.8 real minutes. On every tick, modules run in this fixed order
(registered in `core`):

1. `scenario.on_tick`: fires timeline events due by now (outages, temperature updates) and simulated-crowd replies.
2. `cascade.on_tick`: propagates failures, updates buffers, recomputes predictions every 30 sim-min (or on change).
3. `outreach.on_tick`: alerts newly affected customers and advances escalation timers.
4. `triage.on_tick`: re-scores open cases (aging, deadline breaches).
5. `resources.on_tick`: re-routes reservations at sites predicted to fail.
6. `dispatch.on_tick`: re-offers PASSed or expired offers.
7. `portfolio.on_tick`: proposes action plans for newly at-risk buildings.
8. `impact.on_tick`: recomputes KPIs (every tick, cheap).

Each `on_tick(now: SimTime)` must run in under 200 ms for the full seed (≈2,000 customers). Slow work
(LLM calls, Photon sends) runs as `asyncio` tasks and never blocks the tick.

Modules talk through **(a) another module's public interface functions** and **(b) events on the bus**.
Never through another module's internals. The event list is in `02-contracts.md` §5.

## 3. Repo layout (product repo `Hackutd2026`)

```
backend/
  pyproject.toml              # deps + pytest config (TASK-002)
  app/
    main.py                   # create_app(): loads modules, auto-mounts each module's `router`
    shared/                   # = contracts in code. Owned by `core`. Changes need a decision.
      schemas.py              # every Pydantic model in 02-contracts.md
      enums.py                # every enum in 02-contracts.md
      ids.py                  # ID helpers (CUS-0001 ...)
      events.py               # event bus + event type constants
      store.py                # in-memory repositories
      clock.py                # sim clock
      config.py               # env settings
    modules/
      <name>/
        __init__.py           # PUBLIC interface: the only thing other modules import
        INTERFACE.md          # ≤30 lines: functions, events emitted/consumed, routes
        README.md             # 1 paragraph
        router.py             # FastAPI APIRouter named `router` (optional)
        *.py                  # private implementation
        tests/test_*.py       # smoke tests, runnable alone
  data/
    seed/*.json               # synthetic DFW data (scenario module)
    scenarios/uri_dfw.json    # storm timeline
    public/*.json             # cached NWS/FEMA snapshots (optional)
frontend/
  package.json  vite.config.ts  index.html  tailwind.config.ts
  src/
    main.tsx  App.tsx         # router (web-shell)
    shared/                   # api client, generated api-types.ts, useEvents hook, tokens, ui/ (shadcn)
    modules/
      command-center/  portfolio-view/  demo-console/  mobile-pwa/   # one folder per frontend module
design/                       # Figma exports / static HTML mockups (reference only)
docs/prd/                     # this pack
.env.example
```

**Auto-mounting rule (no shared-file edits):** `backend/app/main.py` imports every package under
`app/modules/` and includes its `router` if it has one. `tick_order` lives in `core`. Frontend routes are
declared once in `frontend/src/App.tsx` by web-shell, each pointing at a module's default export, so
feature tasks never edit `App.tsx`.

## 4. Environment variables (`.env.example`)

```
# --- app ---
APP_BASE_URL=http://localhost:5173        # used to build help-card links in texts
API_BASE_URL=http://localhost:8000
PUBLIC_WEBHOOK_URL=                        # cloudflared URL, e.g. https://xyz.trycloudflare.com
SIM_SPEED_MIN_PER_SEC=5
SEED_RANDOM=42                             # deterministic simulated crowd
# --- ai (any one, or none) ---
LLM_PROVIDER=none                          # anthropic | openai | gemini | none
LLM_MODEL=                                 # optional override; provider default otherwise
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
# --- messaging ---
MESSAGING_MODE=sim                         # sim | photon  (photon = live for DEMO_PHONES only)
PHOTON_API_KEY=                            # VERIFY name/format in Photon docs
PHOTON_SENDER=                             # VERIFY: number/handle provisioned in Photon dashboard
DEMO_PHONES=                               # comma list: +12145550101:CUS-0007,+1...:ADJ-03
```

Never commit `.env`. With everything blank the app still runs fully: sim messaging and the rules-only AI.

## 5. Run commands (target for TASK-002)

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"            # add ".[ai]" to install LLM SDKs
uvicorn app.main:app --reload --port 8000
pytest -q                          # all module smoke tests

# frontend
cd frontend && npm install
npm run gen:api                    # openapi-typescript http://localhost:8000/openapi.json -o src/shared/api-types.ts
npm run dev                        # http://localhost:5173 (proxy /api -> :8000)

# live Photon webhooks (demo day)
cloudflared tunnel --url http://localhost:8000   # put URL in PUBLIC_WEBHOOK_URL + Photon dashboard
```

Vite dev server proxies `/api` to `:8000`, so the browser uses same-origin `/api/...` (no CORS work).

## 6. Demo-day deployment

Run everything on **one laptop** (backend + Vite) and use a cloudflared tunnel for Photon webhooks.
Hosting is optional and not in MVP. If time allows: frontend on Vercel/Netlify (static `vite build`) and
backend on Render/Fly. Then judges can open the help card on their own phone outside the venue Wi-Fi.
Keep the laptop path as the primary demo either way.

## 7. Cross-cutting rules

- **Determinism:** all randomness uses `SEED_RANDOM`. The same reset gives the same demo.
- **Fail soft:** any LLM/Photon error is logged and the fallback is used (rules / SimChannel). Never crash the tick.
- **Time:** all business logic uses sim time (`SimTime`), never wall-clock, except in logs.
- **Money:** integers in **USD cents** in data. Format in the UI.
- **Distances:** miles, haversine. Travel ETA = miles / 25 mph (icy roads), minimum 5 min.
- **Text to customers:** ≤ 320 characters per SMS, plain language, and always the next action plus a way to reply.
