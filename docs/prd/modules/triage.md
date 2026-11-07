# Module: triage (`backend/app/modules/triage/`)

**Skills:** backend, python, data (ml for stretch) · **Read also:** `00-overview.md` §2 (State Farm asks)

## Job
Own the **Case**: open it, score it, tier it, set and watch its contact deadline, and move it through its
lifecycle. Answers "who is most urgent" **and** "nobody low-priority gets forgotten".

## Owns
`backend/app/modules/triage/**`. The only module that writes `store.cases`, except for the fields listed under
"Shared case fields" below.

## Depends on
core; `cascade.home_status`. Consumes `intake.parsed` (optional, outreach calls `apply_intake` directly),
`reservation.changed`, `offer.changed`, `message.received`.

## Public interface (`__init__.py`)
```python
def register() -> None                                     # clock order 40
def open_case(customer_id: str, reason: str) -> Case       # idempotent: returns the existing open case
def apply_intake(case_id: str, extraction: IntakeExtraction) -> Case
def score(case_id: str) -> Case                            # recompute + persist + emit case.updated if tier/score changed
def set_status(case_id: str, status: CustomerStatus, **timestamps) -> Case
router  # GET /api/cases, GET /api/cases/{id}, POST /api/cases/{id}/resolve, POST /api/cases/{id}/note
```
**Shared case fields** that other modules may update **only through** `set_status(...)` / these helpers:
outreach → `status, alert_sent_at, call_placed_at, unreached_at, first_contact_at, last_touch_at`;
resources → `reservation_id`; dispatch → `adjuster_id`. Triage persists the change and emits `case.updated`.

## Priority score (0–100) = sum of five capped parts (`ScoreBreakdown`)
| Part | Max | Rule |
|---|---|---|
| `life_safety` | 40 | medical_device 40 · injuries 40 · over_75 25 · infants 15 · mobility_limited 15 (take the max of present items, plus 5 per additional item, cap 40). **Multiply by 0.25** if `home_status` says they still have heat and they didn't report `no_heat` |
| `time_to_harm` | 25 | from `hours_to_unsafe`: <2h 25 · <6h 18 · <12h 10 · else 3 · already unsafe 25. `medical` need → 25 |
| `property` | 15 | burst_pipe/structure/flooding 15 · roof 10 · no_water 6 · other 5 · predicted pipe-burst <6h (exposed pipes) 8 |
| `unreached` | 10 | status `unreached` 10 · `called` 5 |
| `waiting` | 10 | +1 per 20 sim-min since `last_touch_at` (or `opened_at`), cap 10. **Aging: low tiers rise while they wait** |

Tier = `P1 ≥70`, `P2 ≥50`, `P3 ≥30`, else `P4` (`config.TIER_THRESHOLDS`). Store the breakdown. The UI shows it as
"why this priority" (explainability).

## Deadlines (the "not overlooked" contract)
`deadline_at = (last_touch_at or opened_at) + TIER_DEADLINE_MINUTES[tier]` (P1 15 · P2 60 · P3 240 · P4 720).
On each tick: if `now > deadline_at` and the case isn't `resolved` → `deadline_breached=True` (emit once) and add it to the
Command Center "breaching" filter. A human touch (message from a coordinator, adjuster accept, route confirm) updates
`last_touch_at` and clears the breach.

## Lifecycle (`Case.status`)
`alerted → called → unreached` (outreach) · `→ responded` (reply) · `→ routed` (reservation active) ·
`→ assigned` (adjuster accepted) · `→ resolved` (coordinator resolves, customer SAFE with no predicted harm, or
check-in at a site). Transitions are permissive: any → `resolved`, and any → `responded` on a new reply.

## apply_intake(case, x)
Merge `needs`/`damages` (set union), set `people_count`, `injuries`, `language`, append `x.summary` to `summary`
(keep ≤ 240 chars, newest first), status `responded`, `last_touch_at=now`, re-score, emit `case.updated`
(resources + dispatch react to that event).

## on_tick (order 40)
Re-score all open cases whose `waiting` part or `home_status` may have changed (every 15 sim-min is enough). Check deadlines.
It must run in under 50 ms for 1,000 open cases (pure arithmetic, no I/O).

## Routes
`GET /api/cases?tier=&status=&limit=` → score desc, then `opened_at` asc. `GET /api/cases/{id}` → `CaseDetail`
(join customer, messages via `store.messages.list(case_id=...)`, reservation + resource, adjuster, offers).
`POST /resolve {note?}`, `POST /note {note}`.

## Stretch: ML risk model
Train a scikit-learn GradientBoosting / logistic model on synthetic+historical features
(household flags, insulation, outdoor temp, hours without heat) → P(serious harm or claim > $X). Use it to replace
`life_safety + time_to_harm` weights, with the same 0–65 range and the same breakdown keys. Only after MVP. Keep the rule
score as a fallback.

## Acceptance (pytest)
- Medical device + no heat + unsafe in 1h → P1 (≥70). Same household with heat → not P1.
- A P4 case left untouched gains +1 per 20 min and reaches P3 after enough waiting (aging works).
- Deadline breach flips at deadline+5 for a P1 untouched case and clears after `set_status(..., last_touch_at=now)`.
- `GET /api/cases` ordering is stable and score-descending.

## Not in scope
Fraud checks, claim valuation (impact estimates dollars), multi-case households.
