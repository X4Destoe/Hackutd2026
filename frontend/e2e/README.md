# Live map acceptance
`map-smoke.cjs` exercises real API requests and rendered browser controls. It resets the demo before and after: use an isolated development instance, not a shared presentation session.

Run the backend and Vite with `/api` proxying to that backend, then:
```sh
STORM_URL=http://127.0.0.1:5173 node frontend/e2e/map-smoke.cjs
```
The runner needs Playwright and Chromium (`CHROMIUM_PATH` overrides `/usr/bin/chromium`). If Playwright is not installed, use an external test-tools installation exposed through NODE_PATH; no application dependency change is needed. `STORM_TEST_OUTPUT` chooses screenshot location (default `/tmp/storm-map-acceptance`). It uses the map workspace's accessible building controls and timeline controls; no private module imports or test-only API routes are required.

Checks: real map replaces placeholder; building selection opens detail and waterfall; timeline POST changes server state and native SSE refreshes hero; switching to Uri gives clickable Dallas buildings; disabling all external HTTPS still leaves a usable local map/marker fallback. Screenshots are evidence for visual review, not pixel-diff assertions. Water animation/risk-color changes and approval-ring refresh still need direct browser inspection or additional checks once TASK-029's interface is published. A missing map causes a failing check, not a skipped/pass result.
