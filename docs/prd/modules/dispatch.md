# Module: dispatch (`backend/app/modules/dispatch/`)

**Skills:** backend, python, api · **Read also:** `00-overview.md` §6 step 5

## Job
Send the **right specialist** to each case that needs an in-person adjuster (fixing State Farm's "one team for every
disaster"). Adjusters accept or pass **from their phone over Photon**: the human in the loop.

## Owns
`backend/app/modules/dispatch/**`

## Depends on
core; `messaging` (send, on_inbound "adjuster"); `ai.compose`; `triage.set_status`. Consumes `case.updated`.

## Public interface (`__init__.py`)
```python
def register() -> None                    # clock order 60; messaging.on_inbound("adjuster", handle_adjuster_reply)
def offer_case(case_id: str, adjuster_id: str | None = None) -> DispatchOffer | None
def handle_adjuster_reply(adjuster_id: str, text: str) -> None
router  # GET /api/adjusters, POST /api/cases/{id}/assign, GET /api/field/{adjuster_id}, POST /api/field/offers/{id}
```

## When a case needs an adjuster
Tier P1/P2 **and** damages ∩ {burst_pipe, structure, roof, flooding} ≠ ∅ **and** no adjuster yet **and** no pending offer.
Triggered on `case.updated`. A coordinator can also force it with `POST /cases/{id}/assign` (optionally naming an adjuster).

## Matching (best adjuster)
1. Required specialty from damages: burst_pipe/flooding → `water`, structure → `structure`, roof → `roof`. Fallback order:
   `catastrophe`, then `general`.
2. Eligible: `len(active_case_ids) < max_cases`, not in this case's passed/expired list.
3. Rank: has the required specialty first, then distance, then current load. Pick the top.

## Offer over Photon
`DispatchOffer(status=pending, expires_at=now+OFFER_EXPIRES_MINUTES)` → `messaging.send(adjuster, kind=adjuster_offer)`:
`"New P1 case CASE-0042: burst pipe + no heat, 2 kids, 2.1 mi (Lakewood). Reply ACCEPT or PASS."` plus the field-view link
`{APP_BASE_URL}/field/{adjuster_id}` and quick replies `["ACCEPT", "PASS"]`. Emit `offer.changed`.
- `ACCEPT` (or `Y`/`YES`/`1`, or the field-view button) → `accepted`, append the case to `active_case_ids`,
  `triage.set_status(case, assigned, adjuster_id=..., last_touch_at=now)`. Send the customer (kind `route`) a message:
  "{adjuster first name}, a State Farm water-damage specialist, is on the way, about {eta} min." Reply to the adjuster with the address +
  needs summary + directions link.
- `PASS` (`N`/`NO`/`2`) or expiry on tick → mark it, offer the next best. If nobody is eligible → case note "no adjuster
  available", and the coordinator sees it.
- An adjuster with several pending offers replies `ACCEPT 42` / `PASS 42`. Plain `ACCEPT` applies to their oldest pending offer.

## Field view (`GET /api/field/{adjuster_id}` → `FieldView`)
Rendered by `mobile-pwa` (installable). Shows pending offers (accept/pass buttons → `POST /api/field/offers/{id}`) and
accepted cases (address, needs, household flags, notes, directions link).

## Acceptance
- A P1 burst-pipe case is offered to the nearest **water** specialist even if a general adjuster is closer.
- PASS → next adjuster within the same tick. Expiry after 10 sim-min → next adjuster.
- ACCEPT via SMS text or the field-view button gives the same result. The customer gets the "on the way" message.
- An adjuster at `max_cases` never gets an offer.

## Not in scope
Route optimization across multiple stops, scheduling, adjuster availability calendars, claim payment.
