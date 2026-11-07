# Module: command-center (`frontend/src/modules/command-center/`)

**Skills:** frontend, typescript, ui-design · **Read also:** `00-overview.md` §6 steps 3–5 · **Uses:** web-shell `shared/*`

## Job
The State Farm catastrophe coordinator's screen. In one glance: who is affected, who is most urgent, who hasn't been
reached, where help sites are and how full they are. One click to act on any case. This view must look **operational, not
like a passive dashboard**: every panel has an action.

## Owns
`frontend/src/modules/command-center/**` (default export `CommandCenter({ combined?: boolean })`).

## Layout (desktop, 1440×900 target; it must look good on the projector)
```
┌──────────────────────────────── KPI bar ────────────────────────────────┐
│ Affected 912 · Reached 78% · Unreached 64 · P1 open 12 · Median contact 6m · Breaching 3 · Est. loss $8.2M │
├──────────────┬───────────────────────────────────────────┬──────────────┤
│ Queue (tabs) │                MAP                         │ Case drawer  │
│ [Priority]   │  feeders out (red areas/lines)             │ (opens on    │
│ [Unreached]  │  customers: dots colored by tier           │  select)     │
│ [Breaching]  │  sites: pins w/ capacity ring              │              │
│ [No site]    │  adjusters: small van icons                │              │
│ rows: tier,  │  predicted-unsafe homes: pulsing outline   │              │
│ name, needs, │  (combined: CBRE buildings + countdown)    │              │
│ score, age   │                                            │              │
└──────────────┴───────────────────────────────────────────┴──────────────┘
```

## Panels
1. **KPI bar:** `useKpis`. Numbers animate on change. Tooltips explain each definition (from `impact`). "Est." values carry
   an "estimate" badge.
2. **Queue:** tabs are separate queries: Priority (`useCases({status: open})`), Unreached (`useUnreached`), Breaching
   (`deadline_breached`), No site (cases with needs, no reservation, with the "no site available" note). Row: tier badge, name,
   need icons (🔥 heat, 💧 water/pipe, 🏥 medical, 🛠 repair, 📄 claim, 🏨 housing), score, "waiting 34m", deadline
   countdown (red when breached), language flag. Virtualized list (up to 2,000 rows). Click → opens the drawer and flies the map
   to the customer.
3. **Map:** `BaseMap` + layers. Customers as a circle layer colored by tier (resolved = hollow). Failed feeders/substations in red,
   on_backup in violet. Sites as pins with a capacity ring (green → red) and an `at_risk` dashed outline. Adjusters as small markers.
   Clicking anything selects it. A legend sits bottom-left. Combined mode adds CBRE buildings (square markers + countdown
   label) and a toast when a CBRE host site is created ("Trinity Convention Center now a warming center · 400 spots").
4. **Case drawer** (`useCase(id)`): header (name, tier, score with a "why" breakdown bar from `ScoreBreakdown`, status,
   deadline). Household + home facts. **Conversation thread** (`messages`, chat bubbles, channel icon, translated summary
   line). Extracted needs/damages chips. Reservation card (site, ETA, directions link, "Re-route" → `POST /cases/{id}/route`).
   Adjuster card (offers and their status, "Assign specialist" → `POST /cases/{id}/assign`). Actions: **Call now**,
   **Add note**, **Resolve**. Every action shows an optimistic toast and refreshes from SSE.

## Interactions that must be smooth for the demo
- A live phone's reply appears in the open drawer within 2s (SSE `message.received`).
- When a case is created for the judge's phone, pin it (star) to the top of the Priority tab and auto-open it if nothing is selected.
- When a site goes `at_risk`, its pin turns dashed, and the moved reservations show "Re-routed" in the queue rows.

## Acceptance
- Renders with the seed at minute -120 (no cases) and at minute 600 (hundreds of cases) without lag (under 100 ms interactions).
- All five drawer actions call the right endpoints and the UI updates from events, not polling.
- Works on a 1280px laptop and on the projector (minimum font 14px, high-contrast tier colors).

## Not in scope
Editing customer data, bulk actions, user accounts.
