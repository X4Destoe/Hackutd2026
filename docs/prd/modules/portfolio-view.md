# Module: portfolio-view (`frontend/src/modules/portfolio-view/`)

**Skills:** frontend, typescript, ui-design · **Read also:** `00-overview.md` §6 step 6 · **Uses:** web-shell `shared/*`

## Job
The CBRE facility/portfolio manager's screen. It shows **what fails next, why, and what it costs**, and lets the manager
**approve the fix** and watch the risk drop. It must read as "actionable intelligence", not a dashboard.

## Owns
`frontend/src/modules/portfolio-view/**` (default export `PortfolioView`).

## Layout
```
┌──────── Portfolio header: buildings at risk 3/8 · exposure $61k/h · avoided $1.2M · work orders 4 ────────┐
├──────────────────────┬──────────────────────────────────────────────┬─────────────────────────┤
│ Building list         │ Selected building                            │ Action plans            │
│ sorted by countdown   │  ┌ fragmented sources joined: BMS · Lease ·  │ cards: title, trigger,  │
│ name, type icon,      │  │ Utility · Generator log · Work orders     │ steps, cost vs avoided, │
│ risk bar, countdown   │  ├ Cascade chain (React Flow, left→right):   │ AI rationale,           │
│ "Cooling loss 3h 40m" │  │ SUB-3 → FDR-3B → GEN (fuel 3.7h) → BLD-07 │ [Approve] [Reject]      │
│ exposure $/h          │  │ → COOL → tenants (SLA)   predicted nodes  │ ───────────────         │
│                       │  │ dashed, failed red                        │ Host offers (State Farm │
│ mini map (optional)   │  ├ Tenants table: SLA, penalty/h, rent/day   │ help sites)             │
│                       │  └ Timeline: countdown sparkline              │ Work orders (status,ETA)│
└──────────────────────┴──────────────────────────────────────────────┴─────────────────────────┘
```

## Behavior
- Data: `useBuildings`, `useActions`, `useChains`, `usePredictions`, `useWorkorders`. All refreshed by SSE.
- **Countdown** ticks with sim time (derived from `countdown_minutes` and `useDemoStatus().sim_minute`), not wall-clock.
- **Cascade chain:** build React Flow nodes from the `CascadeChain` that contains the selected building (or from
  `Prediction.cause_chain`). Node colors follow the shared state tokens. Edge labels show the dependency kind (power, cooling).
  Predicted steps are dashed and labeled "in 3h 40m".
- **Approve** → `POST /api/actions/{id}/approve {by: "CBRE manager"}`. Then animate: the countdown jumps (e.g. 3h 40m → 27h 40m),
  the risk bar turns green, "avoided" counts up, work orders appear with ETAs. This is the CBRE "execute solutions" moment,
  so make it satisfying and obvious.
- **Host offers:** a separate card style (green). Approve → toast "Now a State Farm warming center · 400 spots", with a link to
  `/combined` showing the new site.
- Show `data_sources` badges per building to make "fragmented data, now connected" explicit.

## Acceptance
- At minute ~200, BLD-07 is at the top with a correct countdown and a chain that includes its generator.
- Approve updates the countdown within 2s via SSE without a reload. Reject removes the card.
- The view is understandable without narration: every number has a label and unit.

## Not in scope
Editing buildings, uploading data, multi-portfolio switching.
