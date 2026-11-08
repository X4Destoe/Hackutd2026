# messaging public interface

Import `from app.modules import messaging`. Spec: `docs/prd/modules/messaging.md` (Photon facts: `backend/spikes/photon/PHOTON_NOTES.md`).
Written from the merged TASK-020 code (owner x4destoe-cursor); TASK-022 adds the real Photon channel.

| Function | What |
|---|---|
| `send(party_id, body, kind, media_urls=None, work_order_id=None, referral_id=None) -> Message` | Stores and delivers a text. Sim channel delivers before returning (`status: sent`). Never raises on channel failure: the message is stored `failed` with `error`, and `status().last_error` is set. Unknown `party_id` -> `KeyError`. Emits `message.sent`. |
| `on_inbound(party_type, handler)` | `handler(party_id, text, media_urls)` runs for every inbound message of that party type |
| `party_for_phone(phone) -> Party` | match a seeded party (or a `DEMO_PHONES` mapping); unknown number -> creates `RESIDENT-<last4>` |
| `receive(party, text, media_urls=None, kind=None) -> Message` | store an inbound message, emit `message.received`, run that type's handlers |
| `status() -> MessagingStatus` | `{mode, live_parties, sent, received, last_error}` |
| `accept_webhook(payload, headers=None) -> dict` | sim/demo inbound webhook (dedupes by webhook/message id); ignored in photon mode |
| `accept_photon_webhook(raw, headers) -> dict` | photon mode: verifies HMAC over the exact raw bytes (`photon.verify`, ±300 s), dedupes delivery + message ids, marks the sender `demo_live` so replies go back over Photon. Bad signature -> `PermissionError` (HTTP 401) |

Routes: `GET /api/messages?party_id=`, `GET /api/messaging/status`, `POST /api/demo/simulate-message {phone | party_id, text, media_url?}`,
`POST /api/webhooks/photon`.

## Inbound routing (registered by `register()`)
- technician -> `actions.apply_task_reply` (DONE / BLOCKED / photo closes or updates work orders, TASK-021)
- tenant -> stored, replied "Noted. We have your message."
- resident (any unknown number) -> `resources.route(party_id, text)`. **Do not register another resident handler**: resources relies on this one.
- manager -> "YES <plan_id>" approves that plan

## Channels
`MESSAGING_MODE=sim` (default): everything is stored and emitted, nothing leaves the machine; the panel's phone simulator drives inbound.
`MESSAGING_MODE=photon` + a party in `DEMO_PHONES` or with `demo_live=True` (a resident who texted the Photon line): Photon Spectrum
via the loopback Node bridge (`photon.PhotonChannel`, `POST {PHOTON_BRIDGE_URL}/send`). The bridge only texts numbers in `DEMO_PHONES`
(403 otherwise: the message is stored `failed`), so add judges' phones to `DEMO_PHONES` before the demo. Outbound photos are not supported yet. Credentials
`SPECTRUM_PROJECT_ID`, `SPECTRUM_PROJECT_SECRET`, `SPECTRUM_WEBHOOK_SECRET` live in `backend/.env` only.

Webhook boundary guarantees: a verified non-object or malformed message/sender/content produces400, not500. Delivery and signed-message IDs use separate deduplication namespaces; if the signed body lacks a message ID, a SHA-256 of the exact body is the fallback identity, so changing an unsigned delivery header cannot replay that same body. Deduplication remains process-local and bounded to the existing last1000 keys, not durable exactly-once delivery. A200 bridge response must explicitly acknowledge status=accepted before the app records a send; acknowledgement is not proof of handset delivery.

Provider I/O runs outside the inbound lock, so slow sends do not stall signed DONE replies. Before persisting a completion, the queued-message object identity is checked: scenario reset may reuse IDs, and an old completion must not overwrite a new scene's record. An already-started provider request cannot be recalled; callers dispatching a batch must recheck their scenario context before each recipient and after each attempt.

## Current Photon Project API

A configured `PHOTON_API_KEY` selects direct HTTPS with `PHOTON_PROJECT_ID`. Without it, the legacy Spectrum bridge remains supported. See [HTTP_API.md](HTTP_API.md) for sender discovery, recipient restrictions, Standard Webhooks verification, and read-only readiness checks. Claim-assistance requests optionally notify `PHOTON_CLAIMS_ALERT_PHONE`, which must be mapped in `DEMO_PHONES`. No private resident prose is copied. Manager roles remain limited to existing seeded/mapped identities.
