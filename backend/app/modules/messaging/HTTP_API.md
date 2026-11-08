# Real Photon texting locally

With the backend Python environment active, run from `Hackutd2026/backend`:

```sh
python -m app.modules.messaging.live
```

The launcher verifies your configured project/Agent identities and message-read access, enables real Photon mode for this process, then starts API8000 and a two-second reply poller. Polling starts after the scenario and handlers are ready. No public tunnel, open browser, or Node bridge is needed for local texting. Stop an existing API on port8000 first. Connection/configuration failures stop startup instead of silently simulating delivery.

Your private `backend/.env` must exist on the machine running this command; Git does not copy ignored cloud credentials to your laptop. Required settings are `PHOTON_API_KEY`, `PHOTON_PROJECT_ID`, and `DEMO_PHONES` (`+E164:party_id` mappings). Optional `PHOTON_PLATFORM` is `imessage` (default) or `sms`; `PHOTON_SENDER_ID` selects an Agent when needed. Keys are sent only as Bearer headers to `https://api.photon.codes` and never printed.

## Shared iMessage setup

Shared Agents have no resourceId; the adapter accepts their documented type=shared identity. Add each test phone under **iMessage > senders** in the Photon dashboard, and have each phone text its assigned Photon agent number first. The adapter looks up and reuses the existing direct Space with that recipient. It does not try to cold-create a conversation on a shared line. A missing assignment/conversation produces instructions rather than a false success. Dedicated identities can create a direct Space when needed. Multiple matching Agent conversations require explicit `PHOTON_SENDER_ID` selection. No line is purchased or provisioned automatically.

In another terminal, with the same backend folder/environment, send one explicit test:

```sh
python -m app.modules.messaging.live --test-party MGR-01
```

Use another configured party ID to test another recipient. This command sends once and exits; it does not automatically retry. HTTP202 with a valid dispatched/accepted/delivered Message acknowledges a request, not handset delivery. Timeout outcomes may be unknown.

## Roles and claims alerts

`DEMO_PHONES` maps the manager to `MGR-01`, a technician to the relevant `TECH-…` party, and a resident test number to a `RESIDENT-…` identity. Signed/polled messages use the existing handlers: `YES PLAN-…` approves; `DONE WO-…` completes an assigned task. `PHOTON_CLAIMS_ALERT_PHONE` optionally selects an allowlisted contact for new resident insurance-claim assistance requests. Notifications contain a referral ID and status, not private resident prose. They do not submit an insurance claim. Keep unrelated recipients out of the allowlist.

## Optional webhook receiver

Use `python -m app.modules.messaging.live --webhook` instead of polling when a public HTTPS callback is desired. Set `PHOTON_WEBHOOK_SECRET` (`whsec_…`); the existing `SPECTRUM_WEBHOOK_SECRET` name is accepted as a fallback. Expose only the signature-verifying gateway on port8788, and register `https://<tunnel-host>/api/webhooks/photon`. The gateway excludes management APIs and docs, limits request size, preserves signed bytes, and forwards only webhook headers to the private API. Startup checks gateway readiness and reports later child failure. Never expose API8000 or the legacy sending bridge directly.

Standard Webhooks verification checks exact raw bytes, decoded signing secret, five-minute timestamp window, documented `2026-07-01` envelope, project identity, received status, direct conversation, and phone handle. Polling reads authenticated project messages and bounds history/pagination/dedupe. Both paths share message-ID dedupe. Group conversations, outgoing messages, typing and read receipts do not start chat turns.

## Validation and limits

`python -m app.modules.messaging.check_photon --live` performs read-only Agent checks; it never sends. Ordinary demo startup remains simulated. Live texting requires provider access/permissions and assigned numbers; this cloud's egress policy may block Photon even when a laptop can reach it. Real authentication, inbound reachability, and handset delivery must be verified separately from mocked protocol tests.

Contracts were checked against official `@photon-ai/api@0.6.0` types and `@photon-ai/convex@0.1.0`. Attachment-ID-only events do not yet supply downloadable photo evidence; text replies work independently of future attachment retrieval. The legacy Spectrum bridge is supported only when a current Project API key is not configured.
