# Operation Storm build plan for ./comms plan (run from the comms repo):
#   ./comms plan ../Hackutd2026/docs/prd/plan.md --dry-run   then without --dry-run
# depends may name keys here or existing TASK ids (TASK-001 = PRD review/freeze, TASK-002 = backend skeleton/CI).
# Each task's detail is in docs/prd/modules/<module>.md (named in goal).

## photon-spike: Photon 2.0 spike - real text round trip and API notes
priority: p1
size: M
skills: api, backend
files: backend/spikes/photon/
accept: a teammate phone receives a text from backend/spikes/photon/smoke.py and its reply (with a photo) is printed via the tunnel; PHOTON_NOTES.md answers every VERIFY item
goal: modules/messaging.md Photon integration box. Start immediately.

## core-contracts: Shared schemas, enums and ids
priority: p1
size: M
skills: backend, python
files: backend/app/shared/schemas.py, backend/app/shared/enums.py, backend/app/shared/ids.py, backend/app/shared/__init__.py
depends: TASK-001, TASK-002
accept: every model and enum in 02-contracts.md exists with identical names; python -c "import app.shared.schemas" works
goal: modules/core.md schemas, enums, ids

## core-runtime: Store, event bus with SSE, config and app wiring
priority: p1
size: M
skills: backend, python, architecture
files: backend/app/shared/store.py, backend/app/shared/events.py, backend/app/shared/config.py, backend/app/main.py, backend/app/shared/tests/
depends: core-contracts
accept: uvicorn app.main:app starts; /api/health ok; /api/events streams pings; /openapi.json lists all schemas; pytest backend/app/shared passes
goal: modules/core.md store, events, config, main.py

## portfolio-seed: Twelve-building portfolio, utilities and parties
priority: p1
size: M
skills: data, python
files: backend/data/portfolio.json, backend/data/utilities.json, backend/data/parties.json
depends: core-contracts
accept: all records validate against schemas; 12 buildings at plausible coordinates in Houston, Dallas and Fort Myers per 03 section 2
goal: 03-data-and-scenarios.md section 2

## action-catalog: Action catalog JSON
priority: p1
size: S
skills: data
files: backend/data/actions.json
depends: core-contracts
accept: the 13 templates from 03 section 4 validate as ActionTemplate with task_text and tenant_notice_text where relevant
goal: 03-data-and-scenarios.md section 4

## harvey-scenario: Overlay generator and the Harvey Houston scenario
priority: p1
size: M
skills: data, python
files: backend/data/make_overlays.py, backend/data/anchors/harvey_houston.json, backend/data/scenarios/harvey_houston.json
depends: core-contracts
accept: python -m data.make_overlays harvey_houston writes 7 steps with flood_water, wind_swirl and forecast_cone overlays that follow the real bayous on the basemap
goal: 03-data-and-scenarios.md section 1 and modules/scenarios.md data work

## scenarios-module: Scenario loading, timeline, hazard lookup and routes
priority: p1
size: M
skills: backend, python
files: backend/app/modules/scenarios/
depends: core-runtime, portfolio-seed, harvey-scenario
accept: POST /api/scenarios/harvey_houston/load then POST /api/timeline hour 0 emits timeline.changed; hazard_at at Bayou Plaza gives about 3 ft above its first floor
goal: modules/scenarios.md interface and acceptance

## ai-gateway: Provider-agnostic LLM gateway with template fallback
priority: p1
size: M
skills: ai-integration, python
files: backend/app/modules/ai/
depends: core-contracts
accept: pytest backend/app/modules/ai passes with LLM_PROVIDER=none (need classification en and es, compose length and facts, report template)
goal: modules/ai.md

## impact-engine: Exposure, power cascade and money model
priority: p1
size: M
skills: backend, python, data
files: backend/app/modules/impact/
depends: scenarios-module, action-catalog
accept: pytest backend/app/modules/impact passes the acceptance list in modules/impact.md; the waterfall always balances
goal: modules/impact.md and 03-data-and-scenarios.md section 3

## actions-plans: Plans with ROI, act-by, missed plans and Fix-First
priority: p1
size: M
skills: backend, python
files: backend/app/modules/actions/
depends: impact-engine, ai-gateway
accept: Harvey at -24 Bayou Plaza plan has FLOOD_BARRIERS with ROI above 10 in Fix-First top 3; stepping to 0 marks Energy Corridor Tower missed
goal: modules/actions.md plan building and Fix-First

## messaging-core: Messaging interface, simulator, inbound routing and routes
priority: p1
size: M
skills: backend, api
files: backend/app/modules/messaging/
depends: core-runtime
accept: sim send stores and emits; simulate-message from an unknown number creates a RESIDENT party and reaches the resident handler
goal: modules/messaging.md except PhotonChannel

## actions-execute: Approve to work orders, task and tenant texts, technician replies
priority: p1
size: M
skills: backend, python
files: backend/app/modules/actions/execute.py, backend/app/modules/actions/tests/test_execute.py
depends: actions-plans, messaging-core
accept: approving the Bayou Plaza plan creates work orders, sends task and tenant messages, lowers its net exposure; a simulated DONE reply closes the work order
goal: modules/actions.md approve and technician replies

## photon-channel: PhotonChannel and webhook parsing
priority: p1
size: M
skills: api, backend
files: backend/app/modules/messaging/photon.py, backend/app/modules/messaging/tests/test_photon.py
depends: messaging-core, photon-spike
accept: MESSAGING_MODE=photon sends a real task to a DEMO_PHONES technician and their DONE reply closes the work order within 5s; parse test uses a recorded payload
goal: modules/messaging.md Photon integration items 4 and fallbacks

## resources-seed: Help sites per city
priority: p2
size: S
skills: data
files: backend/data/resources.json
depends: core-contracts
accept: about 5 sites per city per 03 section 5 with utility links, including one deliberately inside each hazard zone; VERIFY notes on real venue names
goal: 03-data-and-scenarios.md section 5

## resources-router: Safe help-site routing and re-routing for residents
priority: p2
size: M
skills: backend, python, api
files: backend/app/modules/resources/
depends: impact-engine, messaging-core, ai-gateway, resources-seed
accept: the acceptance list in modules/resources.md passes (unsafe site never chosen, spots reserved, CBRE help site usable, reroute texts)
goal: modules/resources.md

## uri-ian-scenarios: Winter Storm Uri Dallas and Hurricane Ian Fort Myers scenarios
priority: p2
size: M
skills: data, python
files: backend/data/anchors/uri_dallas.json, backend/data/anchors/ian_fort_myers.json, backend/data/scenarios/uri_dallas.json, backend/data/scenarios/ian_fort_myers.json
depends: harvey-scenario
accept: both scenarios load with snow_ice and surge_water plus wind_swirl overlays; Lone Star Data Center net exposure about 1 to 2 million dollars without action
goal: 03-data-and-scenarios.md section 1 and the story column in section 2

## reports-module: Executive summary and tenant notice with printable HTML
priority: p2
size: M
skills: backend, docs
files: backend/app/modules/reports/
depends: actions-execute, resources-router
accept: with LLM_PROVIDER=none both report kinds render and totals match /api/portfolio/summary; /html prints cleanly
goal: modules/reports.md

## web-shell: Vite React app, UTD-style layout, tokens and UI primitives
priority: p1
size: M
skills: frontend, typescript, ui-design
files: frontend/package.json, frontend/vite.config.ts, frontend/index.html, frontend/tailwind.config.ts, frontend/tsconfig.json, frontend/src/main.tsx, frontend/src/App.tsx, frontend/src/shared/ui/, frontend/src/shared/tokens.css, frontend/src/shared/format.ts, frontend/src/shared/ui-store.ts
depends: TASK-001
accept: npm run dev shows top bar, 400px left panel and map area with placeholders; npm run build passes
goal: modules/web-shell.md layout, tokens, ui, ui-store and 04-ui-spec.md section 1

## web-data: Typed API client, query hooks and live events
priority: p1
size: M
skills: frontend, typescript
files: frontend/src/shared/api.ts, frontend/src/shared/queries.ts, frontend/src/shared/useEvents.ts, frontend/src/shared/api-types.ts
depends: web-shell, core-runtime
accept: npm run gen:api works; every route in 02-contracts section 4 has a wrapper; SSE invalidation refreshes data and reconnects
goal: modules/web-shell.md provides list

## map-base: Map, risk-colored buildings, flood overlay, power, timeline control
priority: p1
size: M
skills: frontend, typescript
files: frontend/src/modules/map/
depends: web-data
accept: Harvey shows animated flood water and buildings colored by net exposure; the vertical timeline steps -48 to +7d and colors update within 1s
goal: modules/map.md MapView, BuildingLayer, PowerLayer, flood_water, TimelineControl, MapTools, Legend

## map-overlays: Snow, surge, wind, forecast cone and help-site layers
priority: p2
size: M
skills: frontend, ui-design
files: frontend/src/modules/map/overlays/
depends: map-base
accept: the three scenarios show three visibly different animated hazards at 60fps; help sites show unsafe markers and referral arcs
goal: modules/map.md HazardLayers (non-flood styles), HelpLayer, WorkOrderBadges

## panel-core: Left panel shell, hero card, overview and building detail
priority: p1
size: M
skills: frontend, typescript, ui-design
files: frontend/src/modules/panel/
depends: web-data
accept: Overview shows KPIs and Fix-First top 5; building detail shows data-source chips, why chain, money waterfall and an Approve button that works
goal: modules/panel.md structure items 1-5 (overview, buildings, building)

## panel-actions: Fix-First and Work Orders views
priority: p1
size: M
skills: frontend, typescript
files: frontend/src/modules/panel/views/actions/
depends: panel-core
accept: Fix-First cards show cost, saves, ROI and act-by countdown with Approve; missed plans show would-have-saved; work orders show status and photo thumbnails
goal: modules/panel.md fixfirst and workorders views

## panel-community: Help Sites, Reports and Messages views with phone simulator
priority: p2
size: M
skills: frontend, typescript
files: frontend/src/modules/panel/views/community/
depends: panel-core
accept: phone simulator messages create referrals or work-order updates visible within 2s; reports open printable; help sites show capacity and unsafe status
goal: modules/panel.md help, reports and messages views

## e2e-smoke: End-to-end backend smoke test and integration guide
priority: p1
size: M
skills: integration, testing
files: backend/tests_e2e/, docs/INTEGRATION.md
depends: TASK-002, actions-execute, resources-router, reports-module, uri-ian-scenarios
accept: pytest backend/tests_e2e loads each scenario, steps every hour, approves the top Fix-First plan, routes a resident, generates both reports, with no errors and a balanced waterfall
goal: 00-overview.md section 7 criteria 1-3, 5, 6

## demo-tuning: Tune data so every demo beat lands
priority: p1
size: M
skills: integration, data
files: backend/data/scenarios/, backend/data/portfolio.json, docs/DEMO.md
depends: e2e-smoke, map-overlays, panel-actions, panel-community
accept: the 00-overview section 5 script runs from reset in under 3:30 twice; DEMO.md lists every click and expected number
goal: 00-overview.md section 5

## photon-rehearsal: Rehearse live with real phones
priority: p1
size: S
skills: testing, api
files: docs/REHEARSAL.md
depends: demo-tuning, photon-channel
accept: technician phone gets a task and DONE plus photo closes it on screen; a judge-style phone gets redirected to a safe site; tunnel and dashboard steps documented
goal: 00-overview.md section 7 criteria 4 and 5

## pitch-and-video: Pitch deck notes, README and backup video
priority: p2
size: M
skills: docs
files: docs/PITCH.md, README.md
depends: photon-rehearsal
accept: README has run steps, the demo flow and architecture; PITCH.md maps each track's criteria to demo moments with verified real-world facts; backup video link recorded
goal: 00-overview.md sections 4, 5 and 8
