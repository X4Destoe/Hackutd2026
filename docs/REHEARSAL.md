# Rehearsal

Two ways to run the Photon beats. The simulator path is what this repo can prove with no credentials.
A real iMessage was not sent from this environment: the Photon spike notes say credentials and a
provisioned line were not present, and that is still true here. Do not treat this file as a log of a live handset.

## Simulator (use this if the bridge is not up)

Backend on port 8000, frontend on port 5173, `MESSAGING_MODE` left at `sim`.

1. `POST /api/demo/reset`. Open Hurricane Harvey. Stay at −48h.
2. Fix-First, approve the top card (Bayou Plaza, plan `PLAN-001` on a fresh reset). The Houston engineer
   (`TECH-HOU-01`) receives four task texts. Tenant contacts receive the ground-floor notice.
3. Texts. Send as the Houston engineer: `DONE WO-001`. The work order status becomes done and the thread
   replies `Recorded WO-001: done.` A photo is optional: put an `https://` URL in Photo URL on that same send.
4. Scrub to 0h. Help Sites: Bayou Community Center Shelter is unsafe.
5. Send as a resident, phone `+17135550199`, text `our apartment flooded, 2 kids, need a dry place`.
   The replies name George R. Brown Convention Center and the State Farm emergency claims adjuster at the
   Galleria desk. The unsafe shelter is not named.

That is the judge path with no Photon account. It needs the resident-routing branch for step 5. Steps 1–3
are on main.

## Live Photon (only with a provisioned line)

Facts below are copied from `backend/spikes/photon/PHOTON_NOTES.md`. Do not invent hosts or skip the signature check.

1. In `backend/.env` set `SPECTRUM_PROJECT_ID`, `SPECTRUM_PROJECT_SECRET`, `SPECTRUM_WEBHOOK_SECRET`,
   and `MESSAGING_MODE=photon`. `DEMO_PHONES` maps a real teammate number to a party, for example
   `+1...:TECH-HOU-01`. Only mapped numbers may be sent to.
2. From `backend/spikes/photon`: `npm ci && npm run build && npm test && npm start`. The bridge listens on
   `127.0.0.1:8787`. `GET /health` means the process is up, not that Photon accepted a send.
3. One authorized probe, from that directory:
   `python send.py --phone <mapped-teammate-phone> --text 'Operation Storm test: reply DONE and a photo'`.
   `status: accepted` means the SDK acknowledged. It does not mean the phone got it. There is no automatic retry.
4. Inbound: run the spike `webhook.py` (binds `127.0.0.1:8788`, `POST /api/webhooks/photon`). Expose only that
   receiver with the tunnel the team already uses, and register the HTTPS URL in the Spectrum dashboard.
   The app's own webhook is `POST /api/webhooks/photon` on the FastAPI process once `MESSAGING_MODE=photon`.
   Headers are `X-Spectrum-Event`, `X-Spectrum-Signature` (`v0=<hex>`), `X-Spectrum-Timestamp`, `X-Spectrum-Webhook-Id`.
   The signature covers the raw bytes `v0:` + timestamp + `:` + body. Reject timestamps more than 300 seconds off.
5. Approve the Bayou plan again. The mapped engineer phone should get the task. Reply `DONE WO-001` and,
   if the dashboard supports it, a photo. The work order should close on screen. A mapped resident number
   texting the shelter sentence should get George R. Brown and the claims desk, never the flooded shelter.

Stop if `/health` is 503, the send returns 403 (number not mapped), 409 (another send in flight), or 504
(unknown outcome). Do not send again until you know whether the first one left the bridge.

## What is not evidence

- The spike's unit tests and the signed photo fixture. Those never left the machine.
- `accepted` from `POST /send` without a phone in someone's hand.
- Any number that is not in `DEMO_PHONES`.
