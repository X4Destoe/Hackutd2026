# 00 - Overview: what we're building and why

## 1. One-liner

**Lifeline connects fragmented city and property data into one live dependency map. It predicts
how a disaster cascades from the power grid to individual homes and buildings, then acts:
it contacts every affected State Farm customer through Photon, routes each one to the right help,
and executes approved fixes for CBRE buildings before the failure spreads.**

## 2. The problem (from the three tracks)

| Track | What they asked for | Source |
|---|---|---|
| **CBRE: The Invisible Network** | Connect *fragmented real estate data* to predict cascading operational failures, quantify business impact, or *execute direct solutions before disruptions spread*. Must move **beyond passive dashboards**. Top points need a **clear, live-demoable working prototype**. | CBRE challenge PDF |
| **State Farm: The Worst Day, at Scale** | When a disaster hits thousands at once, use **AI** to identify those with the most urgent needs, coordinate assistance, and make sure **no one is overlooked**. | Ideas PDF (track card) |
| **Photon** | Must integrate **Photon 2.0 / API** (iMessage, SMS, RCS, WhatsApp, Telegram, Email, voice). Judged on Vision, Craft, Depth, Traction, **real human-in-the-loop collaboration (not a demo reel of prompts)**, and *extensive use of Photon*. | Ideas PDF (track card) |

From the State Farm conversation (teammate notes, Ideas PDF):

- They want a **fast way to connect to customers** and **direct them to the resources they need**.
- Customers in a disaster aren't thinking about filing claims, so make it effortless.
- **Prioritize high-priority cases without ignoring low-priority ones.**
- Today **one team handles every kind of claim** (a broken window and a burned house go to the same team).
- They have a lot of **home address / location data**, want **location-based resource allocation**,
  run **mobile catastrophe claim sites** (for example adjusters at a stadium), and partner with Ting
  (sensors that detect electrical faults early).
- It **has to use AI**.

## 3. The demo scenario: Texas winter storm, Dallas–Fort Worth

Modeled on the February 2021 winter storm (Uri): extreme cold, then a generation shortfall, then
rotating grid outages. Homes lose heat, pipes freeze and burst, water pumps lose power, and buildings
run on generators with limited fuel. This is a textbook **cascade**, and it happened where HackUTD
is held. All customer and building data is **synthetic**. Real public weather and disaster data is
used where reachable (see `03-data-and-scenario.md`).

## 4. Users

| Persona | Where they use Lifeline | What they need |
|---|---|---|
| **Policyholder** (State Farm customer) | Photon text, iMessage or voice, plus the **help card** web page linked in texts | Be told what's happening, say what they need in plain words in any language, and be told exactly where to go |
| **State Farm catastrophe coordinator** | **Command Center** web view | See every affected customer by priority and who hasn't been reached, and send adjusters and help |
| **Field claims adjuster** | Photon texts (accept/pass) plus the **field view** PWA on their phone | Get the right cases for their specialty nearby, accept with one reply, and see the address and needs |
| **CBRE facility / portfolio manager** | **Portfolio** web view | See which buildings fail next and what it costs, approve the AI action plan, and offer safe buildings as help sites |
| **Demo operator** (us, on stage) | **Demo console** | Play the storm, control speed, impersonate simulated customers |

## 5. End-to-end flow (the "one engine")

```
fragmented data in                    engine                                 actions out
------------------                    ------                                 -----------
weather/alerts (NWS)  ─┐
grid + feeders         ├─> dependency graph ─> cascade + prediction ─┬─> State Farm: alert affected customers (Photon)
water pump stations    │   (cascade)            "what fails next,     │     -> AI intake (quick replies or free text, any language)
homes (policy data)    │                         and when"            │     -> priority score + contact deadline (triage)
CBRE buildings: BMS,   │                                              │     -> route to nearest fitting help (resources)
  leases, generators,  │                                              │     -> no reply: voice call -> unreached list
  work orders         ─┘                                              │     -> adjuster accept/pass over Photon (dispatch)
                                                                      └─> CBRE: action plan -> manager approves -> work orders
                                                                            -> risk drops live on the map
                                                                            -> safe buildings offered as help sites ──┐
                                                                                                                       │
                     State Farm routing sends customers to those CBRE-hosted sites  <──────────────────────────────────┘
```

The **bridge between the tracks**: the cascade engine knows which CBRE buildings will *keep* power
and heat. Those become warming centers and claim sites, and State Farm customers are routed to them.
If a site is later predicted to fail, the people assigned there are automatically re-routed.

## 6. Demo script (3 minutes, the build target)

Everything in MVP exists to make this script work live. Times are approximate.

1. **0:00 Hook.** "Feb 2021: millions of Texans lost power and heat, and nobody saw the cascade coming." (Check the exact figure before the pitch.) The map of DFW shows the
   storm forecast. Lifeline has already sent **pre-storm safety texts** (drip faucets, charge phones).
2. **0:20 The cascade.** Press Play. Temperatures drop and substation SUB-3 load-sheds. The map shows feeders going
   dark, then homes losing heat. **Predicted** failures appear ahead of time: "Water pump PMP-2 fails in
   1h 30m (tank runs dry)" and "BLD-7 data center: generator fuel runs out in 5h, $42k/h SLA exposure".
3. **0:50 State Farm reaches everyone.** About 900 affected customers are alerted automatically. A **judge's real
   phone** receives the Photon text. The judge replies in their own words (or in Spanish). The AI extracts
   "no heat, 2 kids, pipe burst", assigns priority P1, and replies within seconds with **the nearest open
   warming center**, its address, a directions link and a link to the **help card**.
4. **1:30 No one overlooked.** The Command Center shows the queue sorted by priority, plus the
   **Unreached** list: customers who didn't answer the text got an automated voice call, and the rest
   are listed for a human callback. Low-priority cases climb as they wait, so none are forgotten.
5. **1:50 Human in the loop.** A P1 burst-pipe case goes to the **water-damage specialist** adjuster
   (not "one team for everything"). Their phone gets "Reply ACCEPT/PASS". They reply ACCEPT and
   the case shows them en route.
6. **2:10 CBRE acts.** The Portfolio view shows BLD-7's countdown and an AI action plan (refuel generator,
   shed non-critical load). The manager clicks **Approve**, work orders are created, and the countdown
   jumps from 5h to 29h. The risk and dollar exposure drop live. The convention center BLD-3 is predicted
   to keep power: "Offer as warming center" is approved, and it **appears as a help site that State Farm
   customers are now routed to**.
7. **2:40 Impact.** KPIs: % of affected customers reached, median time to first contact, P1s resolved,
   estimated insured loss, CBRE cost avoided. Close: "From grid failure to front door, before it spreads."

A recorded backup video of this exact script is a required deliverable (see `04-build-plan.md`).

## 7. Scope

### MVP (must work live)
- Seeded DFW scenario: customers, homes, grid, pumps, CBRE buildings, resources, adjusters.
- Sim clock with play, pause, speed and jump. A storm timeline drives outages.
- Cascade: propagation through the dependency graph, buffers (generator fuel, home heat loss), and
  **predicted** fail times 12 hours ahead, with a readable "why" chain.
- Outreach: pre-storm advisory, impact alert, quick replies plus AI free-text intake (multilingual),
  then the escalation **text → voice call → unreached list**.
- Triage: priority score 0–100, tiers P1–P4, contact deadline per tier, wait-time aging, case lifecycle.
- Resource routing: nearest open site with capacity whose building is predicted to stay up. Reserve a
  slot, send address and directions, and re-route if a site goes down.
- Dispatch: specialty and distance-matched adjuster, **ACCEPT/PASS over Photon**.
- Portfolio: building risk and countdowns, AI action plans, approve leads to work orders and an updated
  cascade, help-site offers that create State Farm resources.
- Impact: dollar estimates and KPIs.
- Frontend: Command Center, Portfolio, Demo console, customer help card PWA, adjuster field view PWA.
- Photon live on at least 1–3 real team or judge phones. Everyone else is simulated.

### Stretch (only after the demo script runs end to end)
- Trained ML risk model (scikit-learn) calibrated on historical storm/claims data, replacing the
  hand-tuned score weights (see `modules/triage.md` §ML).
- Swift iOS adjuster app, or an iOS Shortcut "Get help" button that opens an iMessage to the Photon number.
- Icy-road closures affecting routing ETAs.
- Ting-style electrical-fault sensor feed as an extra cascade input.
- Spanish/Vietnamese voice calls.
- Photon channels beyond SMS/iMessage (WhatsApp, Email for CBRE managers).

### Explicitly out of scope (hackathon)
- Authentication, roles, real PII, security hardening, encryption, audit, multi-tenant.
- Production scale, persistence beyond the demo (in-memory store, reset per run).
- Edge cases beyond what the demo exercises. Fail soft (log and keep going), don't over-engineer.
- Real claim filing into State Farm systems, and real payments or vouchers.

## 8. Success criteria (how we know it's done)

1. The demo script in §6 runs start to finish in under 3:30 from `POST /api/demo/reset`, twice in a row.
2. A real phone receives a Photon alert, replies in free text, and gets a routed resource within 15 seconds.
3. 100% of affected simulated customers end in a **visible** state (responded, called, or unreached). None are missing.
4. Approving a CBRE plan visibly changes the prediction (countdown and $) within 2 seconds.
5. The app runs from a fresh clone with the commands in `01-architecture.md`, even with no LLM key
   (rules fallback) and no Photon (simulator).

## 9. How each track's judging is hit

| Criterion | Where it's satisfied |
|---|---|
| CBRE: connects fragmented data | Grid, water, BMS telemetry, leases, generator fuel and work orders unified in one graph (`cascade`, `portfolio`) |
| CBRE: predicts cascades | Forward simulation with "fails in Xh" plus why-chains (`cascade`) |
| CBRE: quantifies impact | SLA $/h exposure, insured loss, cost avoided (`impact`) |
| CBRE: executes solutions, beyond dashboards | Approve, then work orders, then a re-computed cascade; help-site conversion (`portfolio`) |
| State Farm: most urgent first | Priority score + tiers + deadlines (`triage`) |
| State Farm: no one overlooked | Escalation ladder, unreached list, aging, 100% status coverage (`outreach`, `triage`) |
| State Farm: coordinate assistance | Resource routing + capacity + specialty adjuster dispatch (`resources`, `dispatch`) |
| State Farm: uses AI | Multilingual intake extraction, reply generation, action plans (`ai`) |
| Photon: extensive use | Advisory, alerts, quick replies, free-text chat, voice calls, adjuster ACCEPT/PASS, help-card links (`messaging`, `outreach`, `dispatch`) |
| Photon: human-in-the-loop | Adjusters accept/pass, customers co-decide (YES to reserve, or MORE), the coordinator overrides |
| Photon: traction | Works over plain SMS with no app and weak data. The help card is installable (PWA) |

## 10. Glossary

- **Cascade:** a failure spreading along dependencies (substation, then feeder, then home heat, then pipes).
- **Buffer:** time a node survives after losing a dependency (generator fuel hours, home heat-loss hours).
- **Prediction:** the fail time computed by simulating ahead, shown *before* it happens.
- **Case:** one customer's situation in the system (needs, priority, status, assignments).
- **Tier / SLA:** P1–P4 bucket and the maximum time until first human-quality contact.
- **Resource / help site:** claim site, warming center, shelter, hotel or vendor that a customer is routed to.
- **Action plan:** AI-proposed CBRE fix. It only executes after human approval.
- **Sim time:** scenario clock, `sim_minute` 0 = storm start. Runs faster than real time.

## 11. Assumptions and open questions (confirm at the event)

| # | Item | Default until confirmed |
|---|---|---|
| Q1 | **VERIFY** Photon 2.0 API: send, inbound webhooks, quick replies, voice/TTS | Adapter interface in `modules/messaging.md`. The first-hour spike task fills in the real calls |
| Q2 | CBRE extra data (posted in their Discord after opening) | `scenario` loaders accept a swap-in file. The synthetic CBRE portfolio is used until then |
| Q3 | Real State Farm catastrophe-site / resource data | Synthetic DFW sites at real public venues (for example stadium, convention center) |
| Q4 | Which LLM key is used on demo day | `LLM_PROVIDER` env var. The rules fallback keeps the demo alive with no key |
| Q5 | **VERIFY** NWS / OpenFEMA endpoints and fields | Cached JSON snapshot committed in `backend/data/`. Live fetch is optional |
| Q6 | Dollar constants (avg burst-pipe claim etc.) | Illustrative constants in one file, labeled as estimates in the UI |
