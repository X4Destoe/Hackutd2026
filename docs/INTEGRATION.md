# Working-demo integration gate

Run from a checkout containing the integrated modules. The historical, custom-simulation and live-screening modes share one scenario store and event stream. Changing a scenario resets its plans, work orders, messages, resources, referrals and reports. The demo is a single shared workspace, not independent sessions per viewer.

## Automated checks

From the repository root, with the documented backend virtual environment active:

```sh
python -m pytest backend/app backend/tests_e2e -q
cd frontend
npm ci
npm run build
```

Run the backend on port8000 and Vite on5173 using README instructions, with `MESSAGING_MODE=sim`. Then from the repository root:

```sh
cd frontend
npm run test:e2e:install  # once, if Chromium is not already installed
npm run test:e2e
# List checks or run one when investigating a failure:
npm run test:e2e -- --list
npm run test:e2e -- simulation
```

Playwright is pinned as a frontend development dependency. The runner verifies simulator mode before starting, selects installed Chromium, stops on the first failed check, and prevents concurrent runners against the same origin. It does not start the servers. The browser scripts require Chromium; set `CHROMIUM_PATH` if needed and `STORM_URL` for a different local origin. They reset demo state, so run them sequentially on an isolated instance. Scripts that mutate state verify simulator mode first. The live-status test uses explicit browser fixtures plus a local SSE server; it does not claim a real weather observation. Message-followup uses an explicit provider-failure fixture. Other workflow assertions use the real application API.

The backend integration gate loads all three historical scenarios, approves and completes tasks, routes a resident, steps every timeline hour, checks financial arithmetic and capacity/safety, and generates printable reports. It also repeats custom reset and verifies unknown live inputs cannot produce financial reports or automated help-site offers.

## Three-track demo sequence

1. Select Harvey/Houston, inspect a building's loss drivers, and approve a Fix-First response.
2. Open Work Orders, then Texts. Use the technician identity to reply `DONE WO-…`; show task completion arriving without a page reload.
3. In Texts, submit a resident shelter request through the simulator. Open Help Sites and show the reserved capacity and referral. Unsafe sites are excluded; an unplaced request stays visible for coordinator follow-up.
4. In Help Sites, approve an eligible CBRE building activation. Show actual registered capacity and its engineer setup task; an approval alone is not confirmed registration.
5. Generate an executive report and open its printable URL. Tenant instructions reflect approved actions; report generation does not prove message delivery.
6. Use Build simulation: choose a supported/random city, choose a disaster, adjust effects, and run. Show the custom label, changed building losses and the same response workflow.
7. Switch to Uri and Ian to show distinct snow, wind and surge motion. Reduced-motion preference and the hazard toggle stop decorative particles.

## Honest limits and release gates

- Portfolio, financial values and custom hazard geometry are synthetic; historical footprints are approximate. Live NWS intensities are screening proxies, not measured flood depths. Source fetch time is not measurement time.
- Missing/stale live financial inputs are unknown, not zero loss. Live automated help-site routing is disabled because working power is unverified.
- Photon software tests cover signed webhooks, mapped recipients, refusal/failure, duplicate delivery and inbound responsiveness. A real phone round trip still requires securely configured Spectrum credentials, a provisioned line, webhook/tunnel setup and allowlisted demo phones. Simulator acceptance is not a hardware-delivery claim.
- A provider request already in flight cannot be recalled by resetting a scenario. Batch senders must stop remaining recipients when context changes; old completions must not overwrite the reset workspace.
- Use a stable integration checkout for a demonstration. Do not point a running demo at a worktree that is switching feature branches during development.
