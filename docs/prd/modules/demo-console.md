# Module: demo-console (`frontend/src/modules/demo-console/`)

**Skills:** frontend, typescript · **Read also:** `00-overview.md` §6 · **Uses:** web-shell `shared/*`

## Job
The stage controller. It runs the storm reliably during a 3-minute pitch, impersonates simulated customers, and shows a live
event log that proves things are really happening. It's also the team's main debugging tool.

## Owns
`frontend/src/modules/demo-console/**` (default export `DemoConsole`).

## Panels
1. **Scenario controls:** Reset (confirm), Play/Pause, speed presets (1×, 5×, 15×, 30× sim-min/sec), **Jump to** buttons
   for each demo beat (labels from `GET /api/demo/timeline`: "Advisory", "SUB-3 load-shed", "Claim site opens", ...),
   and the current sim clock + weather. Calls `/api/demo/*`.
2. **Mode status:** messaging mode (sim/photon) and live phones with their mapped customer/adjuster IDs, LLM provider
   (`provider_name`), last messaging error. Big red banner if Photon errors, so the presenter can switch to sim.
3. **Phone simulator:** pick any customer (search) or a preset persona ("Maria – oxygen, Spanish", "Tran – burst pipe,
   Vietnamese", "Sam – no reply"). Shows their thread as a phone mock (`useMessages(partyId)`) with quick-reply chips and a
   text box. Send → `POST /api/demo/simulate-reply`. Lets the team demo the full conversation even without real phones.
4. **Event log:** the last 200 SSE events from `useEvents` with type filters, color-coded (cascade/outreach/dispatch/portfolio).
5. **Beat checklist:** the 7 demo-script beats with an auto-check when their event is seen (e.g. beat 6 checks on
   `action.changed status=done`). This makes rehearsals measurable.

## Acceptance
- From Reset, the presenter can hit every demo beat using only this page, in under 3:30.
- Simulated replies typed here appear in the Command Center drawer within 2s.

## Not in scope
Authoring scenarios in the UI (edit JSON), recording/replay.
