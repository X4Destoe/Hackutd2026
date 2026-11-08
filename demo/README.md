# Operation Storm: clickable demo (prototype)

A throwaway, browser-only prototype to see how Operation Storm will look and feel. **Not the product.** The real
build follows `docs/prd/` (FastAPI + React) and is split into tasks in the comms repo. Nothing here is in any task's `files:`.

## Open it
- Easiest: double-click **`operation-storm-demo.html`** (single file, everything inlined).
- Or serve the folder: `cd demo && python3 -m http.server 8000`, then open http://localhost:8000.

The street map (OpenFreeMap "Liberty" style: roads, labels, buildings, 3D) needs internet. Without it you get a plain
offline backdrop with approximate highways and the Gulf, and everything else still works.

## Try this (about 3 minutes)
1. Scenario **Hurricane Harvey · Houston**, hour **−24h** (the vertical HOUR control on the map, or ↑/↓ keys).
2. Click **Bayou Plaza**: see why it's at risk and the money waterfall. **Approve** the plan. The texts to the engineer
   and tenants appear (simulated Photon), and the engineer replies DONE a few seconds later.
3. Step to **+12h**: water rises. Plans you didn't approve in time show as **Missed · would have saved $X**.
4. **Help Sites**: type a resident text ("our apartment flooded, 2 kids, need a dry place"). They're routed to a safe
   shelter; the shelter inside the flood zone is struck through and skipped.
5. Switch to **Winter Storm Uri · Dallas** (snow) or **Hurricane Ian · Fort Myers** (surge + wind).
6. **Reports**: executive summary (printable) or tenant notices. **3D** button (stacked squares, right side) tilts the map.

## Files
`index.html` · `styles.css` · `app.js` (UI) · `model.js` (hazard, money, plans, routing per PRD 03) · `data.js` (scenarios,
12 buildings, help sites, actions) · `context.js` (offline backdrop) · `icons.js` (Lucide icons, ISC) · `vendor/` (MapLibre, BSD-3) ·
`assets/` (optional hero photos, see assets/README.md). After edits, rebuild the single file: `python3 demo/build_single.py`.

All buildings, tenants and dollars are synthetic. Disaster footprints are hand-drawn approximations of real events.
