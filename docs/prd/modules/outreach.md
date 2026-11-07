# Module: outreach (`backend/app/modules/outreach/`)

**Skills:** backend, python, ai-integration · **Read also:** `00-overview.md` §6 steps 3–4

## Job
Make sure **every affected customer is contacted and nobody is overlooked**. Send the pre-storm advisory,
the impact alert, run the escalation **text → voice call → unreached list**, and hold the intake conversation
(quick replies + AI free text, multilingual).

## Owns
`backend/app/modules/outreach/**`

## Depends on
core; `messaging` (send, call, on_inbound); `ai` (extract_intake, compose); `triage` (open_case, apply_intake,
set_status); `cascade.home_status`; `resources.help_link`. Consumes `customer.affected`, `scenario.event`
(`ADVISORY_BROADCAST`), `case.updated`.

## Public interface (`__init__.py`)
```python
def register() -> None                     # clock order 30; messaging.on_inbound("customer", handle_customer_reply)
def contact_case(case_id: str) -> None     # (re)start the ladder for a case
def handle_customer_reply(customer_id: str, text: str) -> None
router  # GET /api/customers, GET /api/unreached, POST /api/cases/{id}/call
```

## Flow per customer (state lives on `Case.status` + timestamps; triage owns the Case object)
1. **Advisory** (`ADVISORY_BROADCAST {zips}`): for every customer in those ZIPs send kind `advisory` (template:
   storm warning + 3 tips: drip faucets, open cabinet doors under sinks, charge phones, and "we'll text you if your
   area is affected"). Set `Customer.status=advised`. Batch 200 per tick so the tick stays fast. Live phones go first.
2. **Affected** (`customer.affected`): if the customer has no open case → `triage.open_case(customer_id, reason=cause)`.
   Then send kind `alert` immediately: `ai.compose("alert", facts, lang)` with facts {first_name, cause, predicted
   hours_to_unsafe if any, help-card link}, plus quick replies `["1 SAFE", "2 NEED HELP", "3 DAMAGE"]` and the note
   "or just tell us what's happening". Set `alert_sent_at`, status `alerted`. `predicted=True` events use the
   wording "your area is likely to lose heat/become unsafe in about N hours".
3. **No reply after `ALERT_TO_CALL_MINUTES`** → `messaging.call(...)` with `ai.compose("voice_script", ...)`
   ("This is State Farm Lifeline. Your area has lost power... reply to our text or call ... "). Status `called`, `call_placed_at`.
4. **No reply `CALL_TO_UNREACHED_MINUTES` after the call** → status `unreached`, `unreached_at`. The case shows on
   `GET /api/unreached` (sorted by triage score) for a human callback. Triage adds the unreached points to its score.
   A coordinator can press "Call now" (`POST /cases/{id}/call`) at any time, which places another call and restarts step 4's timer.
5. **Reply received** (any time, any status): `handle_customer_reply`:
   - status → `responded`, `first_contact_at` if unset, `last_touch_at=now`.
   - Extract: `await ai.aextract_intake(text, context)`, with context = household, `cascade.home_status`, last 4 messages.
   - `triage.apply_intake(case_id, extraction)` → triage re-scores, emits `case.updated`, and resources routes (see resources).
   - If `extraction.follow_up` and fewer than 2 follow-ups asked → send it (kind `intake`). Otherwise send an `ack` once
     (`ai.compose("ack", ...)`: "Got it. You're priority {tier}. {next step}"). Routing sends its own message with the
     place to go, so don't duplicate it.
   - Keywords at any time: `SAFE`/`1` → triage sets the case resolved-safe (`needs=[safe]`) unless the home is predicted
     unsafe within 3h (then ask once more: "Your home may become unsafe by {time}. Do you have a warm place to go?").
     `HELP` → treat as `2`. `STOP` → stop messaging (mark a note, no more sends).
6. **No one overlooked guarantee:** every customer with `customer.affected` ends in exactly one visible status among
   `responded/routed/assigned/resolved/unreached`. A test asserts this after the scenario jumps to minute 600.

## Routes
- `GET /api/customers?status=&q=&limit=`: `q` matches name/phone/address substrings.
- `GET /api/unreached` → `[CaseDetail]` with status `unreached`, score desc.
- `POST /api/cases/{id}/call` → `Message`.

## Acceptance
- Jump to minute 100 in sim mode: every SUB-3 home has a case and an `alert` message. None are missing.
- A sim customer who never replies is `called` at alert+30 and `unreached` at alert+60.
- A reply "no heat, 2 kids, pipe burst" moves the case to `responded`, then triage tier ≤ P2, then resources sends a `route` message.
- Advisory batching: 2,000 advisories go out over ≤10 ticks without any tick exceeding 200 ms.

## Not in scope
Opt-out compliance beyond STOP. Multi-case per customer (one open case each). Damage photos (stretch).
