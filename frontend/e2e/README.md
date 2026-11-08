# Live map acceptance

`map-smoke.cjs` exercises real API requests and rendered browser controls. It resets the demo before and after: use an isolated development instance, not a shared presentation session.

Run the backend and Vite with `/api` proxying to that backend, then:

```sh
STORM_URL=http://127.0.0.1:5173 node frontend/e2e/map-smoke.cjs
```

The runner needs Playwright and Chromium (`CHROMIUM_PATH` overrides `/usr/bin/chromium`). If Playwright is not installed, use an external test-tools installation exposed through NODE_PATH; no application dependency change is needed. `STORM_TEST_OUTPUT` chooses screenshot location (default `/tmp/storm-map-acceptance`). It uses the map workspace's accessible building controls and timeline controls; no private module imports or test-only API routes are required.

Checks: real map replaces placeholder; building selection opens detail and waterfall; timeline POST changes server state and native SSE refreshes hero; switching to Uri gives clickable Dallas buildings; disabling all external HTTPS still leaves a usable local map/marker fallback. Screenshots are evidence for visual review, not pixel-diff assertions. The live approval check requires the actions backend: it verifies a green-ring state within two seconds and server-calculated avoided/net exposure changes. The buildings layer toggle must hide and restore marker controls. Screenshots capture the 800ms flood rise after the real hour-0 overlay response. A missing map causes a failing check, not a skipped/pass result.

`node frontend/e2e/map-style-swap.cjs` adds a deterministic remote-style swap using a local background style response while keeping hazard, impact, plan and work-order API calls real. It verifies rendered water and power survive the swap, then approves a response through the map card and checks actual model changes, distinct marker sizes and in-bounds labels. The card explicitly distinguishes an approved plan from unconfirmed dispatch; missing work-order services never appear as sent texts.

`node frontend/e2e/execution-smoke.cjs` verifies the closed response loop using real APIs: map-card approval creates work orders and simulator messages; technician DONE replies submitted through the UI close each task and the plan through SSE. It requires MESSAGING_MODE=sim and rejects other channel modes before any approval. Like the map smoke, it resets an isolated demo before/after. No real phone is messaged by this test.
