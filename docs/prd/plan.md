# Lifeline build plan for ./comms plan (run from the comms repo):
#   ./comms plan ../Hackutd2026/docs/prd/plan.md --dry-run   then without --dry-run
# Keys are local. depends may name keys here or existing TASK ids (TASK-001 = PRD review/freeze, TASK-002 = skeleton).
# Each task's detail lives in docs/prd/modules/<module>.md. The goal line says which file and which section.

## photon-spike: Photon 2.0 spike - real text round trip and API notes
priority: p1
size: M
skills: api, backend
files: backend/spikes/photon/
accept: a teammate phone receives a text sent by backend/spikes/photon/smoke.py and its reply is printed via the tunnel; PHOTON_NOTES.md answers every VERIFY item in modules/messaging.md
goal: modules/messaging.md "Photon integration" box. Start immediately, no dependencies. Ping the team with findings.

## core-contracts: Shared schemas, enums and ids from the contracts
priority: p1
size: M
skills: backend, python
files: backend/app/shared/schemas.py, backend/app/shared/enums.py, backend/app/shared/ids.py, backend/app/shared/__init__.py
depends: TASK-001, TASK-002
accept: pytest backend/app/shared passes; every model and enum in 02-contracts.md exists with identical names
goal: modules/core.md schemas.py, enums.py, ids.py

## core-runtime: Store, event bus, sim clock and app wiring
priority: p1
size: M
skills: backend, python, architecture
files: backend/app/shared/store.py, backend/app/shared/events.py, backend/app/shared/clock.py, backend/app/shared/config.py, backend/app/main.py, backend/app/shared/tests/
depends: core-contracts
accept: uvicorn app.main:app starts; GET /api/health ok; GET /api/events streams pings; clock advance_to tests pass
goal: modules/core.md store, events, clock, main.py (auto-mount routers, tick order, /api/_contracts)

## seed-data: Deterministic seed generator and committed seed JSON
priority: p1
size: M
skills: data, python
files: backend/data/generate_seed.py, backend/data/seed/
depends: core-contracts
accept: python -m data.generate_seed writes every file in 03 section 2 and a second run is byte-identical; all records validate against schemas
goal: 03-data-and-scenario.md sections 1-7 and 9 (reply_templates.json)

## scenario-timeline: Uri DFW timeline and public data snapshots
priority: p1
size: S
skills: data
files: backend/data/scenarios/, backend/data/public/
depends: TASK-001
accept: uri_dfw.json matches 03 section 10; NWS/FEMA snapshot JSON present (verified live, or labeled illustrative)
goal: 03-data-and-scenario.md section 10 and the VERIFY note in section 2

## scenario-module: Scenario loader, timeline player and demo routes
priority: p1
size: M
skills: backend, python
files: backend/app/modules/scenario/
depends: core-runtime, seed-data, scenario-timeline
accept: POST /api/demo/reset gives seed counts and sim_minute -120; jump to 100 emits ADVISORY_BROADCAST, GRID_EMERGENCY, LOAD_SHED SUB-3 in order
goal: modules/scenario.md behavior items 2, 3 and 5 (the crowd is a separate task)

## cascade-graph: Dependency graph, propagation and home thermal model
priority: p1
size: M
skills: backend, python, data
files: backend/app/modules/cascade/
depends: core-runtime, seed-data
accept: load-shed SUB-3 affects every SUB-3 home (customer.affected count equals seed); AND/OR group test passes; thermal test 3.1h
goal: modules/cascade.md graph semantics, event handling, home_status, building_outlook, apply_effect

## cascade-predict: Prediction pass, why-chains and what-if
priority: p1
size: M
skills: backend, python, data
files: backend/app/modules/cascade/predict.py, backend/app/modules/cascade/chains.py, backend/app/modules/cascade/tests/test_predict.py
depends: cascade-graph
accept: BLD-07 predicted near minute 390 with chain ending SYS-BLD-07-GEN, BLD-07; refuel effect pushes it about 24h; predicted pre-alerts emitted
goal: modules/cascade.md prediction pass, chains, predict_with, routes

## ai-gateway: Provider-agnostic LLM gateway with rules fallback
priority: p1
size: M
skills: ai-integration, python
files: backend/app/modules/ai/
depends: core-contracts
accept: pytest backend/app/modules/ai passes with LLM_PROVIDER=none (en, es intake cases, compose length and facts); provider timeout falls back
goal: modules/ai.md (all). Pick current model ids from provider docs in one dict.

## messaging-core: Messaging interface, SimChannel, inbound handling and routes
priority: p1
size: M
skills: backend, api, python
files: backend/app/modules/messaging/
depends: core-runtime
accept: sim send stores and emits message.sent; inbound_sim calls the party handler and emits message.received; GET /api/messages returns the thread
goal: modules/messaging.md everything except PhotonChannel

## photon-channel: PhotonChannel implementation and webhook parsing
priority: p1
size: M
skills: api, backend
files: backend/app/modules/messaging/photon.py, backend/app/modules/messaging/tests/test_photon.py
depends: messaging-core, photon-spike
accept: with MESSAGING_MODE=photon a DEMO_PHONES customer receives an alert and the reply reaches the outreach handler within 5s; webhook parse unit test uses a recorded payload
goal: modules/messaging.md Photon integration items 4 and the fallbacks

## triage-core: Case lifecycle, priority score, tiers, deadlines and aging
priority: p1
size: M
skills: backend, python
files: backend/app/modules/triage/
depends: core-runtime, cascade-graph
accept: pytest backend/app/modules/triage passes (P1 medical case, aging P4 to P3, deadline breach and clear, ordering)
goal: modules/triage.md (all except the ML stretch)

## outreach-ladder: Advisory, impact alerts and text-call-unreached escalation
priority: p1
size: M
skills: backend, python
files: backend/app/modules/outreach/
depends: triage-core, messaging-core, ai-gateway
accept: jump to 100 in sim mode gives every SUB-3 home a case and an alert; a silent customer is called at +30 and unreached at +60; advisories batch without slow ticks
goal: modules/outreach.md flow steps 1-4 and 6, routes

## outreach-intake: Reply handling with quick replies and AI intake
priority: p1
size: M
skills: backend, ai-integration
files: backend/app/modules/outreach/intake.py, backend/app/modules/outreach/tests/test_intake.py
depends: outreach-ladder
accept: reply "no heat 2 kids pipe burst" makes the case responded, tier P2 or higher, and one follow-up at most; SAFE, HELP and STOP keywords behave as specified
goal: modules/outreach.md flow step 5

## resources-routing: Help-site matching, reservations, route messages and help card
priority: p1
size: M
skills: backend, python, api
files: backend/app/modules/resources/
depends: triage-core, cascade-predict, messaging-core, ai-gateway
accept: heat case routed to the nearest safe open site with capacity; capacity never exceeded; GET /api/help/{token} returns a HelpCard
goal: modules/resources.md matching, register_resource, help card, routes

## resources-reroute: Site safety and automatic re-routing
priority: p2
size: S
skills: backend, python
files: backend/app/modules/resources/safety.py, backend/app/modules/resources/tests/test_reroute.py
depends: resources-routing
accept: load-shedding a site feeder moves every active reservation there and sends each a change-of-plan message; SITE_OPEN opens the stadium claim site
goal: modules/resources.md site safety and re-routing

## scenario-crowd: Simulated crowd replies for customers and adjusters
priority: p2
size: M
skills: backend, python, data
files: backend/app/modules/scenario/crowd.py, backend/app/modules/scenario/tests/test_crowd.py
depends: scenario-module, messaging-core, cascade-graph
accept: seeded run gives about 65/15/20 percent reply-to-text, reply-after-call and never; replies match each home_status; adjusters accept about 80 percent
goal: modules/scenario.md behavior item 4 and 03-data-and-scenario.md section 9

## dispatch-adjusters: Specialist matching and ACCEPT/PASS over Photon
priority: p2
size: M
skills: backend, api
files: backend/app/modules/dispatch/
depends: triage-core, messaging-core, ai-gateway
accept: burst-pipe P1 goes to the nearest water specialist; PASS and expiry re-offer; ACCEPT by text or field button assigns and messages the customer
goal: modules/dispatch.md (all)

## portfolio-plans: Building risk, countdowns, exposure and AI action plans
priority: p2
size: M
skills: backend, ai-integration
files: backend/app/modules/portfolio/
depends: cascade-predict, ai-gateway
accept: after SUB-3 load-shed BLD-07 has an extend-runtime plan with about 300 min countdown and 42k per hour exposure; BLD-03 gets a host offer; no duplicate plans
goal: modules/portfolio.md building risk, action catalog, routes

## portfolio-execute: Approve to work orders, cascade effects and host sites
priority: p2
size: M
skills: backend, python
files: backend/app/modules/portfolio/execute.py, backend/app/modules/portfolio/tests/test_execute.py
depends: portfolio-plans, resources-routing
accept: approving the BLD-07 plan moves its countdown by 24h or more in one call and creates work orders; approving the BLD-03 host offer creates a cbre resource
goal: modules/portfolio.md approve and reject

## impact-kpis: KPIs, claim estimates and impact breakdown
priority: p2
size: M
skills: backend, data
files: backend/app/modules/impact/
depends: triage-core
accept: at sim minute 600 every KPI is non-null; approving a plan raises cbre_avoided_cents; GET /api/impact lists assumptions
goal: modules/impact.md (all)

## web-scaffold: Vite React app, routes, desktop shell and PWA config
priority: p1
size: M
skills: frontend, typescript
files: frontend/package.json, frontend/vite.config.ts, frontend/index.html, frontend/tailwind.config.ts, frontend/tsconfig.json, frontend/src/main.tsx, frontend/src/App.tsx, frontend/public/
depends: TASK-001
accept: npm run dev serves every route in modules/web-shell.md with placeholders; /api proxied; npm run build passes; installable manifest
goal: modules/web-shell.md routes, desktop shell, PWA, Vite config

## web-data: Typed API client, query hooks and live events hook
priority: p1
size: M
skills: frontend, typescript
files: frontend/src/shared/api.ts, frontend/src/shared/queries.ts, frontend/src/shared/useEvents.ts, frontend/src/shared/format.ts, frontend/src/shared/api-types.ts
depends: web-scaffold, core-runtime
accept: npm run gen:api generates types; every route in 02-contracts section 4 has a wrapper; SSE invalidation works and reconnects
goal: modules/web-shell.md provides list (api, queries, useEvents, format)

## web-ui-map: Design tokens, UI primitives and base map layers
priority: p1
size: M
skills: frontend, ui-design
files: frontend/src/shared/ui/, frontend/src/shared/map/, frontend/src/shared/tokens.css
depends: web-scaffold
accept: storybook-style demo page or test route shows tier and state colors, shadcn primitives and BaseMap with points, outage and site layers over DFW
goal: modules/web-shell.md tokens, ui, map

## design-mockups: Screen designs for the four main views
priority: p2
size: M
skills: ui-design
files: design/
depends: TASK-001
accept: mockups (Figma export or static HTML) exist for Command Center, Portfolio, Help card and Field view, following the layouts in their module files
goal: Use design plugins if available. Reference only; React is the product.

## cc-map-queue: Command Center layout, KPI bar, queue tabs and map
priority: p1
size: M
skills: frontend, typescript
files: frontend/src/modules/command-center/
depends: web-data, web-ui-map
accept: renders at sim minute 600 with hundreds of cases without lag; queue tabs work; clicking a row flies the map; combined mode shows CBRE buildings
goal: modules/command-center.md panels 1-3

## cc-case-drawer: Case drawer with conversation, reasons and actions
priority: p1
size: M
skills: frontend, typescript
files: frontend/src/modules/command-center/drawer/
depends: cc-map-queue
accept: all five drawer actions call the right endpoints; a live reply appears within 2s; the score breakdown shows why this priority
goal: modules/command-center.md panel 4 and the demo interactions

## portfolio-view: CBRE portfolio view with cascade chain and approvals
priority: p2
size: M
skills: frontend, typescript, ui-design
files: frontend/src/modules/portfolio-view/
depends: web-data, web-ui-map
accept: BLD-07 on top with a live countdown and chain; Approve updates the countdown within 2s via SSE; host offer approval toast links to combined view
goal: modules/portfolio-view.md (all)

## mobile-help-card: Customer help card (installable)
priority: p2
size: M
skills: frontend, mobile, typescript
files: frontend/src/modules/mobile-pwa/help/
depends: web-data, web-ui-map
accept: /h/{token} renders at 360px in en, es and vi; updates within about 2s on re-route; Add to Home Screen gives a standalone app
goal: modules/mobile-pwa.md help card

## mobile-field-view: Adjuster field view (installable)
priority: p2
size: S
skills: frontend, mobile
files: frontend/src/modules/mobile-pwa/field/
depends: web-data, web-ui-map
accept: /field/{id} shows pending offers and accepted cases; Accept equals replying ACCEPT by text
goal: modules/mobile-pwa.md field view

## demo-console: Demo console with controls, phone simulator and event log
priority: p2
size: M
skills: frontend, typescript
files: frontend/src/modules/demo-console/
depends: web-data, web-ui-map
accept: from Reset every demo beat can be reached from this page; simulated replies reach the Command Center within 2s
goal: modules/demo-console.md (all)

## e2e-smoke: End-to-end smoke test and integration guide
priority: p1
size: M
skills: integration, testing
files: backend/tests_e2e/, docs/INTEGRATION.md
depends: TASK-002, scenario-crowd, outreach-intake, resources-reroute, dispatch-adjusters, portfolio-execute, impact-kpis
accept: pytest backend/tests_e2e runs reset, jump to 600, and asserts no affected customer is missing a visible status, BLD-07 plan exists, KPIs non-null; INTEGRATION.md has the 60-second manual check
goal: 00-overview.md section 8 success criteria 1, 3, 4, 5

## demo-tuning: Tune the scenario so every demo beat lands
priority: p1
size: M
skills: integration, data
files: backend/data/scenarios/uri_dfw.json, docs/DEMO.md
depends: e2e-smoke, cc-case-drawer, portfolio-view, demo-console, mobile-help-card
accept: the 00-overview section 6 script runs from reset in under 3:30 twice in a row; DEMO.md lists the exact clicks and jump points
goal: 00-overview.md section 6

## live-phone-rehearsal: Rehearse with real phones over Photon
priority: p1
size: S
skills: testing, api
files: docs/REHEARSAL.md
depends: demo-tuning, photon-channel, mobile-field-view
accept: a judge-style phone gets the alert, replies in Spanish, is routed within 15s, and an adjuster phone ACCEPTs; tunnel and dashboard steps written down
goal: 00-overview.md section 8 criterion 2

## pitch-and-video: Pitch, README demo section and backup video
priority: p2
size: M
skills: docs
files: docs/PITCH.md, README.md
depends: live-phone-rehearsal
accept: README has one-command run, demo script and architecture; PITCH.md maps each track's criteria to demo moments; backup video link recorded
goal: 00-overview.md sections 6 and 9, 04-build-plan.md section 6
