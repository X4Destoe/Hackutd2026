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

## Photon integration (**VERIFY everything here in hour 1**: plan task `photon-spike`)
The Photon 2.0 docs could not be read while writing this PRD. The spike must:
1. Create the project in the Photon dashboard (photon.codes/beta), enable SMS + iMessage.
2. Record in `PHOTON_NOTES.md`: auth, base URL/SDK, send call, inbound webhook payload and registration, media (photos) in and out,
   delivery status, rate limits.
3. Prove a round trip to a teammate's phone through the cloudflared tunnel (`backend/spikes/photon/smoke.py`).
4. Then implement `PhotonChannel` behind:
```python
class Channel(Protocol):
    def send_text(self, to: str, body: str, media_urls: list[str]) -> str   # provider id
    def parse_inbound(self, payload: dict, headers: dict) -> tuple[str, str, list[str]] | None   # (from_phone, text, media)
```
Fallbacks: if webhooks are unreliable, poll the Photon API if possible. If Photon is down on stage, `MESSAGING_MODE=sim` plus the panel's
phone simulator.

## Acceptance
- Sim: `send()` stores the message and emits `message.sent`. Simulated inbound reaches the right handler by party type.
- An unknown number texting in becomes a RESIDENT party and reaches `resources.route`.
- Photon (manual, documented): a real phone receives a task and its "DONE" reply closes the work order within 5s.
