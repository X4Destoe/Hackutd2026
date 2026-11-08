# Current Photon HTTP API

`PHOTON_API_KEY` selects direct HTTPS using `PHOTON_PROJECT_ID` (`pho_prj_…`). It never falls back to the legacy Spectrum credential scheme after a failure. Secrets stay in ignored `backend/.env` and are sent only to `https://api.photon.codes`.

Additional settings: `PHOTON_PLATFORM` is `imessage` (default) or `sms`; optional `PHOTON_SENDER_ID` selects a canonical project-owned Agent User ID. Without it, discovery selects exactly one dedicated project-owned Agent. Multiple/shared/unavailable lines require explicit configuration and verification. Nothing provisions or purchases a line automatically.

`PHOTON_WEBHOOK_SECRET` holds the `whsec_…` signing secret; `SPECTRUM_WEBHOOK_SECRET` is accepted as a configuration fallback. `DEMO_PHONES` maps authorized `+E164:party_id` recipients. `PHOTON_CLAIMS_ALERT_PHONE` optionally selects an allowlisted recipient for resident claim-assistance notifications. Alerts include a referral ID and status, not private resident prose, and do not file insurance claims.

From `backend/`, run `python -m app.modules.messaging.check_photon` for configuration readiness; add `--live` for read-only project and sender checks. Neither prints keys/phone numbers or sends messages. Restart the API after settings changes. Keep `MESSAGING_MODE=sim` until live verification and public webhook configuration succeed.

Sending reconciles the recipient User, creates a direct Space with the Agent first, then sends plain text. Space/message requests use distinct idempotency keys. HTTP202 and a valid dispatched/accepted/delivered Message acknowledge a send, not handset delivery. No automatic retries occur; timeout outcomes may be unknown.

Inbound `/api/webhooks/photon` verifies Standard Webhooks headers (`webhook-id`, `webhook-timestamp`, `webhook-signature`) over exact raw bytes with the decoded secret. It accepts the documented `2026-07-01` envelope and checks project identity, received status, direct conversation, and phone handle. Group messages, outgoing events, typing and read receipts do not start chat turns. Signed message IDs deduplicate redelivery under a new event ID.

Contracts checked against official `@photon-ai/api@0.6.0` public types and `@photon-ai/convex@0.1.0` webhook parser. Attachment-ID-only events do not yet provide a downloadable photo URL; live attachment retrieval is not verified. Mocked protocol acceptance is separate from real authentication, line provisioning, webhook reachability and handset delivery.
