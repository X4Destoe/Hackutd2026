# Module: messaging (`backend/app/modules/messaging/`)

**Skills:** api, backend, python · **Read also:** `01-architecture.md` §4–5

## Job
The only module that talks to Photon. It sends texts (tasks to technicians, notices to tenants, redirects to residents), receives
replies (including photos), and hands each one to the right module. A **SimChannel** handles everyone not on a real phone.

## Owns
`backend/app/modules/messaging/**` (+ `PHOTON_NOTES.md` from the spike)

## Interface (`__init__.py`)
```python
def register() -> None
def send(party_id: str, body: str, kind: MessageKind, media_urls: list[str] = [],
         work_order_id: str | None = None, referral_id: str | None = None) -> Message   # returns immediately (queued)
def on_inbound(party_type: PartyType, handler) -> None      # handler(party_id: str, text: str, media_urls: list[str])
def party_for_phone(phone: str) -> Party                    # unknown number → creates RESIDENT-<last4> party
def status() -> MessagingStatus
router  # POST /api/webhooks/photon, GET /api/messages, GET /api/messaging/status, POST /api/demo/simulate-message
```
- Routing of inbound messages: technician → actions (`apply_task_reply`). Tenant → stored and shown in the UI (reply "noted").
  Resident (any unknown number, or a resident party) → resources (`route`). Manager (stretch) → "YES <plan>" approves.
- A party with `demo_live=True` and `MESSAGING_MODE=photon` uses **PhotonChannel**. Everyone else uses **SimChannel** (stored and emitted, never sent).
- Sends are async tasks. Failures mark the message `failed` with an error and never raise into callers.
- `POST /api/demo/simulate-message {phone|party_id, text, media_url?}` injects an inbound message (for the demo phone simulator).

## Photon integration (verified 2026-11-08 by the TASK-010 spike; details in `backend/spikes/photon/PHOTON_NOTES.md`)
Photon's product is now **Spectrum**. Facts that shape the code:
- **Sending is only possible through the TypeScript SDK `spectrum-ts`** (pinned 12.15.0). The HTTP API at `https://spectrum.photon.codes`
  (Basic auth `projectId:projectSecret`) manages projects/webhooks/lines; it cannot send. So messaging talks to a small **Node
  photon-bridge** on loopback: `POST http://127.0.0.1:8787/send {phone, text}` -> `{status: "accepted", message_id}` (acknowledged,
  not delivered). Only numbers in `DEMO_PHONES` can be texted. Outbound photos are not supported yet.
- **Credentials:** `SPECTRUM_PROJECT_ID`, `SPECTRUM_PROJECT_SECRET` (SDK), `SPECTRUM_WEBHOOK_SECRET` (inbound), optional `SPECTRUM_SENDER`.
  They live in `backend/.env` (git-ignored) on the demo laptop. Never in chat, comms or git. An iMessage line must be provisioned at
  app.photon.codes. `PHOTON_API_KEY` / `PHOTON_SENDER` in `.env.example` are obsolete.
- **Inbound:** native webhook `POST /api/webhooks/photon` with headers `X-Spectrum-Event`, `X-Spectrum-Signature: v0=<hex>`,
  `X-Spectrum-Timestamp`, `X-Spectrum-Webhook-Id`. Verify HMAC-SHA256 over the exact bytes `v0:<timestamp>:<rawBody>` (constant time,
  ±300 s), then parse. Delivery is at-least-once: dedupe on the webhook id and on `(event, message.id)`. Payload
  `{event: "message.received", message: {id, space, sender, content: {type, text | attachment}}}`; capture a real photo reply before
  finalizing media parsing. Expose the receiver through the tunnel (cloudflared) and register that URL in the dashboard.
- **Not verified yet:** a real round trip (needs credentials + a provisioned line), exact runtime hosts used by the SDK.

`PhotonChannel` (TASK-022) keeps this protocol so `SimChannel` and Photon stay swappable:
```python
class Channel(Protocol):
    def send_text(self, to: str, body: str, media_urls: list[str]) -> str   # provider id (bridge message_id)
    def parse_inbound(self, payload: dict, headers: dict) -> tuple[str, str, list[str]] | None   # (from_phone, text, media)
```
Fallback on stage: `MESSAGING_MODE=sim` plus the panel's phone simulator (always works, no network).

## Acceptance
- Sim: `send()` stores the message and emits `message.sent`. Simulated inbound reaches the right handler by party type.
- An unknown number texting in becomes a RESIDENT party and reaches `resources.route`.
- Photon (manual, documented): a real phone receives a task and its "DONE" reply closes the work order within 5s.
