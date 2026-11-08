# Demo script

What the screen actually does, measured from the API after `POST /api/demo/reset`. The overview's early draft
($6.8M header, Bayou net $1.65M, a $24k barrier plan) is not what the engine computes. Use the figures below.
Dollars on screen come from `money()` in `frontend/src/shared/format.ts` (cents, two decimals once the amount is in the thousands).

Resident routing and printable reports are the routing and reports branches until those merge. On a tree that only
has `main`, Help Sites and Reports have no backend yet. Impact, Fix-First, and work-order texts are on `main`.

No LLM key and no Photon bridge. The header stays on the simulator, and copy comes from templates.

## Harvey, from reset (about a minute of clicking)

1. Open the app. It loads **Hurricane Harvey, Houston** at **−48h**, phase Forecast.
2. Header **Net exposure $8.05M**, **Avoided $0**. Four buildings are at risk. Bayou Plaza is severe, about **$2.98M** net.
   The drivers are 3.0 ft of water above the first floor, the downtown substation down 96h with the generator covering 18h,
   and State Farm recovering about $17.14M after a $1.86M deductible. Gross loss is larger than the header because insurance
   is already subtracted into the net.
3. Click **Bayou Plaza** on the map or in Buildings. The detail waterfall is damage + rent abatement + operations − insurance
   = that net. It balances to the cent.
4. Open **Fix-First**. The top card is Bayou Plaza: pre-book the restoration contractor, move ground-floor equipment,
   deploy temporary flood barriers, and top off fuel. **Cost $32.8k, saves $991.96k (30.2×), act by −24h.**
   Approve it. Status goes to executing. Four work orders are texted to the Houston engineer, and tenant contacts get a
   ground-floor notice. Avoided becomes **$991.96k** and net exposure falls to **$7.06M**.
5. Open **Texts**. Send as the Houston engineer: `DONE WO-001`. The work order closes and a reply says it was recorded.
6. Scrub the timeline to **0h**. Bayou Community Center Shelter (Help Sites) is **Unsafe · do not route**. George R. Brown
   and NRG stay open. The portfolio dollars do not all change at landfall: the model is the predicted loss for the storm,
   which is what Fix-First spends against. The hazard drawing and the unsafe shelter are what change.
7. In Texts, send as a resident from `+17135550199`: `our apartment flooded, 2 kids, need a dry place`.
   One reply starts **Go to George R. Brown Convention Center, 1001 Avenida de las Americas**. A second reply starts
   **State Farm emergency claims adjuster** and names the Galleria claims site, phone `+17135551004`, with the
   policy-number line. Help Sites shows the referral, 3 people, and a history line for that adjuster. The flooded
   community center is not chosen. The adjuster visit does not take a shelter spot.
8. Still on Fix-First, under **Community actions**, approve **Galleria Medical Offices — Offer as community help site**
   ($2k, act by +12h) while the timeline is still at forecast if you want it offered before landfall. That registers
   the building as an open CBRE help site (250 spots). A later text `flooded in the galleria area, need shelter for 2 people`
   routes to that building.
9. Open **Reports**. Generate the executive summary. The printable page repeats the header totals (net $8.05M before the
   approval, or the reduced net after it). Generate a tenant notice for Bayou Plaza.

## Switch storms

- **Winter Storm Uri, Dallas** at −48h: net exposure about **$2.35M**, three buildings at risk. Top Fix-First is
  Lone Star Data Center (continuity, fuel, restoration contractor), cost **$10.3k**, saves about **$1.59M**.
  A resident who texts `it is freezing and we have no heat, 2 kids` is sent to an open warming center, plus the
  North Dallas claims adjuster. The Oak Lawn site sits on a load-shed substation; do not expect it once that node is down.
- **Hurricane Ian, Fort Myers** at 0h: the wind is over 74 mph at every help site, so a shelter text stays **unrouted**
  and is flagged for a coordinator. That is intentional. At **+48h** the wind has dropped, Beachside Rec Center is still
  under surge, and the same request goes to an open inland site (the hotel is closer than the inland shelter for a
  beach-area sender) plus the Fort Myers claims adjuster. Forecast net exposure is about **$3.67M**. Top Fix-First is
  Riverside Commons, cost **$29k**, saves about **$606.32k**.

## API rehearsal (the same beats, no clicking)

```bash
curl -s -X POST localhost:8000/api/demo/reset
curl -s -X POST localhost:8000/api/timeline -H 'content-type: application/json' -d '{"hour":-48}'
curl -s localhost:8000/api/portfolio/summary
curl -s localhost:8000/api/fix-first
curl -s -X POST localhost:8000/api/plans/PLAN-001/approve -H 'content-type: application/json' -d '{"by":"demo"}'
curl -s -X POST localhost:8000/api/timeline -H 'content-type: application/json' -d '{"hour":0}'
curl -s -X POST localhost:8000/api/demo/simulate-message -H 'content-type: application/json' \
  -d '{"phone":"+17135550199","text":"our apartment flooded, 2 kids, need a dry place"}'
```

`PLAN-001` is Bayou's forecast plan on a fresh reset; if the id differs, take the first `plan_id` from `/api/fix-first`.
The pytest that walks all three storms, every hour, the approval, the resident, and both reports is
`cd backend && python3 -m pytest tests_e2e -q` on the smoke-test branch.
