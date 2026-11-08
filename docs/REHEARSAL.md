# Photon rehearsal

Two ways to run the texting beats. The simulator path always works; the live path needs a Photon Spectrum project, a
provisioned iMessage line and the team's credentials. (Adapted from Cursor's draft and `backend/spikes/photon/PHOTON_NOTES.md`.)
Nothing here has been verified with a real phone yet; do one live round trip before the demo.

## Simulator (default, no account)

`MESSAGING_MODE=sim` (default). Backend :8000, frontend :5173.
1. `POST /api/demo/reset`; Harvey at −48h. **Fix-First** → approve Bayou Plaza (`PLAN-001` on a fresh reset).
   *Marcus (Houston engineer)* gets 4 task texts; each tenant contact gets one combined notice.
2. **Texts** → send as the Houston engineer `DONE WO-001` (optionally a photo URL): work order closes, reply
   *Recorded WO-001: done.* `BLOCKED WO-002 crew stuck` marks it blocked with the note.
3. Step to 0h. Send as a resident `+17135550199`: `our apartment flooded, 2 kids, need a dry place` → *Go to George R.
   Brown Convention Center…* with a map link. The flooded Bayou Community Center is never named.

## Live Photon

1. `backend/.env` (never committed): `SPECTRUM_PROJECT_ID`, `SPECTRUM_PROJECT_SECRET`, `SPECTRUM_WEBHOOK_SECRET`,
   `MESSAGING_MODE=photon`, `DEMO_PHONES=+1<teammate>:TECH-HOU-01,+1<judge>:...` (party ids from `backend/data/parties.json`).
   **Only numbers in `DEMO_PHONES` can be texted** (team decision: keep the allowlist; register judges' phones before the demo).
2. Bridge (Node ≥ 22.9): `cd backend/spikes/photon && npm ci && npm start` → listens on `127.0.0.1:8787`.
   `GET /health` = process up and credentials present, not proof Photon accepted a send.
3. Inbound: expose the **app's** webhook with the tunnel (`cloudflared tunnel --url http://localhost:8000`) and register
   `https://<tunnel>/api/webhooks/photon` in the Spectrum dashboard. The app verifies `X-Spectrum-Signature` (HMAC over
   `v0:<timestamp>:<raw body>`, ±300 s), ignores replays, and answers 401 to anything unsigned.
4. Approve the Bayou plan: the mapped engineer phone gets the task. Reply `DONE WO-001` (and a photo): the work order
   closes on screen. A mapped resident phone texting the shelter sentence gets the George R. Brown reply over Photon.
5. If a send fails, **Texts** shows it as failed with the reason (403 not in DEMO_PHONES, 503 bridge down/credentials
   missing, 504 unknown outcome). Do not resend a 504 until you know whether the first one went out.

Fallback on stage: switch `MESSAGING_MODE=sim`, restart the backend, and use the phone simulator in **Texts**.

## Not evidence of a live round trip
Unit tests, signed fixtures, `accepted` from the bridge without a phone in someone's hand, or any number not in `DEMO_PHONES`.
