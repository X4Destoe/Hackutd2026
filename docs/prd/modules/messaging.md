# Module: messaging (`backend/app/modules/messaging/`)

**Skills:** backend, api, python (+ whoever has Photon dashboard access) · **Read also:** `01-architecture.md` §4–6

## Job
The only module that talks to Photon. It sends texts and voice calls, receives replies, and records every message.
Two channels behind one interface:
- **PhotonChannel**: real Photon 2.0 API, used **only** for parties with `demo_live=True` (1–3 real phones).
- **SimChannel**: in-process. Messages are stored and emitted, never leave the laptop. Used for everyone else, and for
  everyone when `MESSAGING_MODE=sim`.

## Owns
`backend/app/modules/messaging/**`

## Depends on
core. Nothing else. Other modules call it. It calls back through `on_inbound` handlers and events.

## Public interface (`__init__.py`)
```python
def register() -> None
def send(party_type: PartyType, party_id: str, body: str, kind: MessageKind,
         quick_replies: list[str] = [], link: str | None = None, case_id: str | None = None) -> Message
def call(party_type: PartyType, party_id: str, script: str, case_id: str | None = None) -> Message  # voice
def on_inbound(party_type: PartyType, handler: Callable[[str, str], None]) -> None   # handler(party_id, text)
def inbound_sim(party_type: PartyType, party_id: str, text: str) -> Message           # simulated reply / demo console
def status() -> MessagingStatus
router  # POST /api/webhooks/photon, GET /api/messages, GET /api/messaging/status
```
`send`/`call` return immediately with `status=queued`. The actual send runs as an asyncio task, then updates the
message to `sent`/`failed` and emits `message.sent`. Inbound: normalize → store `Message(direction=inbound,
status=received)` → emit `message.received` → call the registered handler for that party type.
Quick replies: if the channel supports native quick-reply buttons (**VERIFY**), use them. Otherwise append
`"\nReply 1 SAFE · 2 NEED HELP · 3 DAMAGE"` style text. Links are appended as plain URLs.

## Photon integration (**VERIFY everything in this box in hour 1. It's the first task in plan.md**)
The Photon docs could not be read while writing this PRD. The spike task must:
1. Sign up at the Photon 2.0 beta dashboard (`photon.codes/beta`), create a project, enable SMS + iMessage (+ voice if available).
2. Find out and record in `backend/app/modules/messaging/PHOTON_NOTES.md`: auth (key, header), base URL or SDK,
   send-message call, channel selection, quick-reply/button support, inbound webhook payload + how to register the URL,
   delivery status callbacks, **voice: outbound call with text-to-speech or voicemail**, rate limits, test numbers.
3. Prove it: a script `python -m app.modules.messaging.photon_smoke +1214...` sends "Lifeline test" to a teammate's
   phone and prints the inbound reply received through the tunnel.
4. Implement `PhotonChannel` to match:
```python
class Channel(Protocol):
    def send_text(self, to: str, body: str, quick_replies: list[str], link: str | None) -> str   # provider_id
    def place_call(self, to: str, script: str) -> str                                           # provider_id
    def parse_inbound(self, request_json: dict, headers: dict) -> InboundMessage | None
```
**Fallbacks** (decide during the spike and note in PHOTON_NOTES.md):
- No voice in Photon → `call()` sends a text marked `[Voice call]` with the script, kind `voice_call`, and the
  demo says "voice". Flag it to the team. Voice is a Photon track criterion, so look hard first.
- Webhooks unreliable → poll Photon for new messages every 5s, if the API allows.
- Photon down on stage → `MESSAGING_MODE=sim` and the demo console phone simulator. The recorded backup video covers the rest.

Channel choice per party: prefer iMessage for iPhones if Photon picks it automatically, otherwise SMS (**VERIFY**).
Record the channel actually used in `Message.channel`.

## Address book
`phone → (party_type, party_id)` built from `store.customers` + `store.adjusters` at load. An unknown inbound number
gets logged and stored with `party_id="unknown"`, then answered once with "This is Lifeline storm support. Reply HELP
to reach State Farm." No further handling (out of scope).

## SimChannel
`send_text` returns `sim-<n>` and marks the message sent after a 0–1 tick delay. `place_call` is the same with kind
`voice_call`. The simulated crowd (scenario) listens to `message.sent` and answers through `inbound_sim`.

## Acceptance
- Sim mode: `send(customer, ...)` → message stored, `message.sent` emitted. `inbound_sim` → handler called with
  `(party_id, text)` and `message.received` emitted.
- `GET /api/messages?party_id=CUS-0007` returns the thread in time order.
- Photon mode (manual, documented in PHOTON_NOTES.md): a real phone receives an alert, and its reply reaches the
  outreach handler within 5s.
- A send failure marks the message `failed` with `error` and never raises into the caller.

## Not in scope
Opt-in/consent flows, TCPA compliance, delivery analytics, MMS photos (stretch: damage photo intake).
