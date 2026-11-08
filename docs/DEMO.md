# Demo script (3 minutes)

Every number below was measured on `main` after `POST /api/demo/reset` (2026-11-08), with no LLM key and
`MESSAGING_MODE=sim`. Labels are what the screen shows. If a number differs on your laptop, trust the screen and
re-measure with the API block at the end. (Adapted from Cursor's draft; the overview's early $6.8M / $1.65M / $24k
figures are not what the engine computes.)

Before you start: backend on :8000, frontend on :5173 (README "Run it"), hard-refresh the browser.

## 1. Harvey, Houston (the CBRE story, ~90 s)

1. The app opens on **Hurricane Harvey · Houston** at **−48h · Forecast**: purple dashed forecast water, buildings
   colored and sized by dollars at risk. Header: **Estimated loss $8.05M**, **Avoided $0**; 4 buildings at risk.
2. Click **Bayou Plaza** (red, downtown). Detail: 3.0 ft of water above the first floor, downtown substation down 96 h,
   generator covers 18 h → 78 h without power. The waterfall (damage + rent abatement + operations − insurance)
   balances to the cent: **$2.98M**. Talking point: insurance absorbs most of the damage above the $1.86M deductible,
   so mitigation mostly saves downtime, which is the owner's money.
3. **Fix-First**: top card is Bayou Plaza: pre-book a restoration contractor, move ground-floor equipment, deploy
   flood barriers, top off fuel. **$32.8k → saves $991.96k (30.2×), act within 24 h.** Click **Approve**.
4. The ring turns green; **Avoided $991.96k**, **Estimated loss $7.06M**. Four work orders go to *Marcus (Houston
   engineer)*; each tenant contact gets **one** combined notice ("move servers and critical equipment off the ground
   floor today…").
5. **Texts** → send as the Houston engineer: `DONE WO-001`. Reply: *Recorded WO-001: done.* The work order closes on
   screen (also from the map card).
6. Step the timeline to **0h · Impact**: water turns blue and rises; unapproved plans go **missed**, e.g. Energy Corridor Tower
   *would have saved $865.08k*. Dollars do not jump at landfall on purpose: the estimate is the predicted
   loss Fix-First spends against; what changes is what you can still do.

## 2. Residents (State Farm piece, ~45 s)

7. Still at **0h**, **Help Sites**: *Bayou Community Center Shelter* is **Unsafe · do not route** (flooded, substation down).
8. **Texts** → send as a resident from `+17135550199`: `our apartment flooded, 2 kids, need a dry place`. Reply:
   *Go to George R. Brown Convention Center, 1001 Avenida de las Americas, Houston. 5.9 mi · 24 hours · 2797 spots
   left · Map: <link>*. Three spots are reserved; the flooded center is never chosen. Spanish in → Spanish out
   (*Vaya a…*); `my dad is on oxygen and the power is out` → 911 guidance first, flagged for coordinator follow-up.
9. CBRE buildings as help sites: on **Help Sites → Activate a CBRE help site**, approve **Galleria Medical Offices**
   ($2k, before +12h). It becomes an open site with 250 places, and its setup task goes to the technician. A later `flooded in the galleria area, need shelter for 2 people` routes there.

## 3. Switch storms and close (~45 s)

10. **Winter Storm Uri · Dallas**: cold-blue tint and falling snow. Estimated loss **$2.35M**, 3 at risk. Fix-First
    top: **Lone Star Data Center** (tenant continuity + fuel + contractor) **$10.3k → $1.59M (154×)**: SLA penalties on
    a data center dominate. At 0h a "freezing, no heat, 2 kids" text goes to *Kay Bailey Hutchison Convention Center*.
11. **Hurricane Ian · Fort Myers**: storm-surge waves and wind. Estimated loss **$3.67M**; top plan Riverside Commons
    **$29k → $606.32k**. Note: at **0h** every help site is in >74 mph wind, so shelter texts are honestly
    *unrouted* (flagged for a coordinator); at **+48h** they go to *Daniels Parkway Hotel*. Use Harvey for the live
    resident beat.
12. **Reports** → **Executive summary**: printable, 2 pages, same totals as the header. Close: *"Same engine, any
    disaster: forecast → dollars → action → people helped."*

Optional: **Build simulation** (any supported city + disaster + sliders), and **Live · Houston/Dallas/Fort Myers**:
today's real NWS alerts and forecasts, clearly labeled proxies; missing feeds say *unknown*, never *safe*.

## API rehearsal (same beats, no clicking)

```bash
curl -s -X POST localhost:8000/api/demo/reset
curl -s localhost:8000/api/portfolio/summary
curl -s localhost:8000/api/fix-first
curl -s -X POST localhost:8000/api/plans/PLAN-001/approve -H 'content-type: application/json' -d '{"by":"demo"}'
curl -s -X POST localhost:8000/api/demo/simulate-message -H 'content-type: application/json' -d '{"phone":"+15550100002","text":"DONE WO-001"}'
curl -s -X POST localhost:8000/api/timeline -H 'content-type: application/json' -d '{"hour":0}'
curl -s -X POST localhost:8000/api/demo/simulate-message -H 'content-type: application/json' \
  -d '{"phone":"+17135550199","text":"our apartment flooded, 2 kids, need a dry place"}'
```
`PLAN-001` is Bayou's plan on a fresh reset; otherwise take the first `plan_id` from `/api/fix-first`.
Full automated check: `cd backend && python -m pytest app` and the browser suites in `frontend/e2e/README.md`.
