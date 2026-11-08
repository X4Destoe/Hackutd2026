# Module: panel (`frontend/src/modules/panel/`)

**Skills:** frontend, typescript, ui-design · **Read also:** `04-ui-spec.md` (esp. §5 final visual decisions), visual reference `demo/`; `04` §1–2, `00-overview.md` §5 · **Uses:** web-shell `shared/*`

## Job
Everything in the 400px left panel: search, the scenario hero card, tabs, layer toggles, and the content views (Overview,
Buildings, Building detail, Fix-First, Work Orders, Help Sites, Reports, Messages). This is where CBRE's "how is it affecting
me as a business, and what do I do" gets answered.

## Owns
`frontend/src/modules/panel/**` (default export `Panel`; one file per view under `views/`).

## Structure (top to bottom)
1. **Search**: filters buildings/tenants by name. Enter → select the first match.
2. **Hero card**: scenario name, real event + date, phase badge (color), this step's `narrative`, **Net exposure** and **$ avoided**
   (big tabular numerals, animated count on change), "Footprints approximate" note.
3. **Tabs**: Overview · Buildings · Help (set `panelView`).
4. **Layer rows** (UTD-style category rows with a checkbox on the right): Hazard, Buildings by $ risk, Power grid, Work orders, Help sites, Messages.
5. **Content area** (scrolls) renders `panelView`:
   - `overview`: KPI grid (at-risk count, gross, insurance recovery, net, avoided) + **Fix-First top 5** compact cards + missed plans list.
   - `buildings`: sortable list (net $ desc default), "only in this scenario" filter, risk dot, mini bar.
   - `building`: header + risk badge; **data-source chips** ("Lease abstracts · BMS · Utility map · Insurance SOV · Work orders → one record");
     exposure readings; **Why** (cause chain as steps + drivers); a **money waterfall** (horizontal bars: damage, rent abatement, SLA, ops, minus
     insurance, equals net); **plan card** (actions with cost and act-by, total cost, saves, ROI ×, rationale, **Approve** / Reject; missed →
     red "would have saved $X"); tenants table; work orders for this building; buttons "Tenant notice" (generate + send) and "Offer as help site" if available.
   - `fixfirst`: ranked cards (rank, building, actions, cost → saves, ROI ×, act-by countdown in hours from the current step, Approve).
     "Community actions" section below.
   - `workorders`: list with status chips, assignee, updates, photo thumbnails (Photon media). Manual status buttons (for the demo without phones).
   - `help`: sites (status, capacity bar, type), referrals (summary → site, distance, rerouted badge), unrouted/urgent in red.
   - `reports`: buttons "Executive summary" / "Tenant notice for…", list of reports with "Open printable" (new tab to `/api/reports/{id}/html`).
   - `messages`: live message feed + a **phone simulator** (pick a party or type a phone number, send text/photo URL →
     `POST /api/demo/simulate-message`) so the demo works without real phones.
6. **Footer**: portfolio name · 12 buildings · scenario city.

## Interaction rules
- Approve shows an optimistic "Approved · sending tasks…" toast, then the real state arrives from SSE.
- Numbers always carry units and come from the API. No client-side money math except formatting.
- Every view has an empty state ("No plans needed at this step: nothing is exposed yet").

## Acceptance
- From Overview, a judge can reach Bayou Plaza's waterfall and approve its plan in ≤ 3 clicks.
- Fix-First countdowns change when the timeline steps. Missed plans appear after their act-by passes.
- Phone simulator messages produce referrals or work-order updates that show up within 2s.
