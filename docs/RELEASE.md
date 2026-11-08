# Tested demo release candidate

This candidate combines the illustrated UI and glossary explanations (TASK-073), repeatable browser tooling (TASK-075), demo documentation/backup recording (TASK-037), and the reviewed resident follow-up and claims-adjuster workflow (TASK-071). It is a single shared simulator workspace. Independent review found no blocking issues for this simulator release.

## Run and rehearse

Follow [README](../README.md) to start the API and frontend. Use `MESSAGING_MODE=sim` and `LIVE_FETCH=0` for a predictable rehearsal. Never run reset-based acceptance against an active real-phone demonstration.

From the repository root:

```sh
cd backend
python -m pytest app tests_e2e -q
cd ../frontend
npm ci
npm run build
npm run test:e2e:install  # once, if Chromium is not already installed
npm run test:e2e
```

The browser runner checks simulator mode, runs checks serially, and stops on a failure. It requires the API and frontend to be running already. Set `STORM_URL` and `CHROMIUM_PATH` for another local origin or installed browser. Do not run other reset-based tests against the same backend concurrently.

Use the circular-arrow **Restart current scenario** button to repeat an exercise. Cancel preserves the current run; confirmation clears the shared demo records and returns the selected scenario to its first step. Failed requests remain visible and can be retried. Already-sent real texts cannot be recalled.

Use [DEMO.md](DEMO.md) for the three-track story, [PITCH.md](PITCH.md) for accurate sponsor claims, and [the backup video](media/operation-storm-demo.mp4) when a live presentation is unavailable. The recording uses simulated texts and synthetic buildings/finances; it is not evidence of real message delivery. `STORM_RECORD_VIDEO=0 node docs/media/record-demo.cjs` repeats the actual API/UI story without encoding a video.

## Verified behavior

- Historical Harvey, Uri, and Ian; custom supported/random city and disaster effects; timeline changes and reset.
- Building response cards can minimize, restore, or close (including Escape). Minimizing preserves unsaved work-order notes; dismissal leaves approved tasks intact and frees the map. Focused acceptance: `node frontend/e2e/response-card-smoke.cjs`.
- Map selection, modeled financial impact, approval, technician work orders and replies, live UI invalidation, reports, and offline map fallback.
- Work-order progress and blocker notes are saved with status changes; blocked tasks require a reason. Failed saves preserve drafts, and failed report-list loads can be retried.
- Community-site activation, safety/capacity checks, resident routing, and waiting-request follow-up when a site becomes available. Modeled hurricane-force wind triggers shelter guidance; live forecast proxies never assert observed winds.
- Resident claims requests receive an available modeled State Farm desk contact/map. This does not file a claim or guarantee coverage.
- Circled information icons explain financial and hazard terms on hover, keyboard focus, and tap. Help-site load failures can be retried; only open sites with places expose directions.
- Missing/stale live inputs display Unknown; automated live site routing remains disabled without verified power.

Validation: 211 backend tests, nine serial browser checks, and the production build pass. Focused browser checks also verify glossary interactions/mobile bounds and recovery from failed site/referral requests. A clean lockfile installation includes the declared Playwright dependency. The final recorded walkthrough, including glossary explanations and the in-app restart, passes in 60 seconds; the encoded backup is 59 seconds. Restart cancellation, request failure, retry, and cleared records are covered by the expanded navigation check.

## External work still required

Real Photon sending/replies need Spectrum project credentials, a provisioned line, mapped demo recipients, a signing secret, and an HTTPS webhook endpoint configured securely. The code is already on main and its messaging tests pass; the running demonstration uses the simulator. Provider acknowledgement is not proof of delivery. Follow [REHEARSAL.md](REHEARSAL.md) before claiming real-phone acceptance.

Official flood-zone/waterway source expansion and the separately scoped grounded assistant are follow-up work. Current hazard footprints and custom effects are illustrative, not official flood maps. There is no insurance claim submission, authentication, or real property-management-system integration in this hackathon demo.

## Review follow-ups for provider expansion

The independent review identified two nonblocking follow-ups outside the simulator release: unusually long external site names/addresses need a guaranteed message-length bound, and resource notification sends remain synchronous outside the resource lock. Seeded demo messages fit the current limit. Moving sends outside the lock avoids lock contention; it does not make provider I/O asynchronous. Address these before expanding the real-phone workflow beyond the verified rehearsal.
