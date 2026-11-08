# 00 - Overview: what Operation Storm is and how it flows

## 1. The problem, in CBRE's words

From our conversation with CBRE's engineers (paraphrased from the transcript):
- They liked a map that shows **cost** as risk ("higher risk area… more red… identified the cost… looks good").
- They want **actionable insights**: "showing upcoming disasters and all, but **as a business, how is it affecting me**."
- They kept returning to **finance**: connect the disaster to money.

From the CBRE challenge statement: connect **fragmented real estate data** (facilities, HVAC, power, leases,
utilities) to **predict cascading failures**, **quantify business impact**, and **execute solutions before disruptions
spread**. Go **beyond passive dashboards**, with a **live-demoable working prototype**.

**Operation Storm's one-line answer:** for every building in the portfolio, *what will this disaster cost us, why, and which
action saves the most money per dollar, starting now?* One click executes it.

## 2. Users

| User | Where | Needs |
|---|---|---|
| **CBRE portfolio manager** (primary) | Operation Storm web app | Total dollar exposure, which buildings first, approve actions, reports for owners and tenants |
| **On-site technician / building engineer** | Photon text | A clear task ("deploy flood barriers by 18:00"). Reply DONE / BLOCKED / photo |
| **Tenant contact** | Photon text | Advance notice ("floor 1 closed tomorrow, move servers by 16:00"). Can reply with problems |
| **Affected resident / State Farm customer** in the area | Photon text | "Where do I go?" Sent to the nearest **safe, open** help site with space |

## 3. The flow (what the product actually does)

```
 1. PICK A REAL DISASTER          2. SEE IT COMING                    3. KNOW THE COST
 Scenario menu: Hurricane         Timeline: Forecast → Impact →       Each building: hazard reading
 Harvey (Houston), Winter Storm   Recovery. Animated overlay:         (flood depth, wind, ice, fire),
 Uri (Dallas), Hurricane Ian      blue water rising, white snow,      power cascade (substation down
 (Fort Myers), Eaton Fire stretch wind swirl, orange fire             → generator hours), then $ damage
                                                                      + $ downtime + $ tenant/SLA − insurance
                                                                      = NET $ EXPOSURE. Map colors = $
        │                                                                         │
        ▼                                                                         ▼
 4. FIX-FIRST LIST                5. ONE-CLICK EXECUTE                6. CLOSE THE LOOP
 Ranked actions across the        Approve → work orders created →     Technician replies DONE (or a
 portfolio: "BLD-04 Houston:      Photon texts the on-site tech       photo) → map + $ update live.
 flood barriers, $18k, saves      with the task + Photon notices      Reports: executive summary for
 $410k (23x), act by -12h".       to affected tenants. Map risk       owners, tenant notice. Export
 Late actions show as missed.     drops. "$ avoided" counter rises.   or print.

 STATE FARM / COMMUNITY LAYER (same hazard engine)
 Residents text the Photon number ("flooded, 2 kids, need somewhere dry") → AI reads the need →
 Operation Storm sends them to the nearest help site that is OPEN, SAFE in this phase (not flooded, has power) and has SPACE:
 shelter, warming center, State Farm mobile claim site, hotel, or a CBRE building offered as a help site.
 If that site becomes unsafe in a later phase, the person is re-routed with a new text.
```

## 4. Why each track wins

| Track | What they judge | Operation Storm's answer |
|---|---|---|
| **CBRE (primary)** | Connect fragmented data, predict cascades, quantify impact, execute, beyond dashboards, live demo | One record per building joins hazard + utility + building systems + leases/tenants + insurance. Power cascade with generator countdown. Dollars per building. Fix-First with ROI. Approve → work orders + texts. Map updates live |
| **Photon** | Real human-in-the-loop, extensive Photon use, craft, traction | Techs get tasks and reply DONE/BLOCKED/photo, which changes the map. Tenants get notices. Residents chat and get redirected. Optional: the manager approves a Fix-First item by replying YES |
| **State Farm** | Find the most urgent needs, coordinate help, no one overlooked | Resident needs are classified by AI and routed only to *safe, open* sites with space. Re-routing when a site fails. Unrouted requests are listed so nobody is lost |

## 5. Demo script (3 minutes, the build target)

1. **0:00 Hook.** "In 2017, Harvey flooded Houston. Every property manager knew it was coming. Few knew what it would
   cost *them*, building by building, or what to do first." Open Operation Storm: a big map, a portfolio of about 12 buildings across Texas and Florida.
2. **0:20 Pick the disaster.** Scenario menu → *Hurricane Harvey – Houston*. Phase = **Forecast (−48h)**. The forecast
   flood area pulses in light blue. Buildings recolor by **dollars at risk**. The header shows "Portfolio exposure $6.8M".
3. **0:45 Why.** Click *Bayou Plaza*: predicted flood depth 3.1 ft above the first floor, substation down → generator 18h →
   tenants down 21 days. Breakdown: damage $1.9M + downtime $640k + SLA $210k − insurance $1.1M = **net $1.65M**.
4. **1:10 Fix-First.** Open Fix-First. Top item: *Bayou Plaza – flood barriers + move ground-floor equipment: cost $24k,
   saves $980k (41×), act by −12h*. Click **Approve**.
5. **1:30 Execute (Photon).** A teammate's real phone gets: "BRACE TASK WO-007 Bayou Plaza: deploy flood barriers at
   south entrance by 18:00 Sat. Reply DONE, BLOCKED or send a photo." Tenant phone: "Notice from Bayou Plaza
   management: ground floor closes 16:00 Sat…". The map ring turns from red to amber, and **$ avoided** counts up.
6. **1:55 Impact phase.** Scrub the timeline to **Impact**. The blue water rises and spreads (animation). One building we didn't act on
   goes deep red, while the protected one holds. The tech replies "DONE" with a photo, and the work order closes on screen.
7. **2:20 Community (State Farm + Photon).** A judge texts the number: "our apartment flooded, 2 kids, need a dry
   place". Within seconds: "Go to George R. Brown shelter, 1001 Avenida de las Americas, 4.2 mi, open, 310 spots left…"
   One shelter shows a red ✕ because it's in the flood zone, and Operation Storm skipped it on purpose. Then one of *our* buildings,
   offered as a help site, appears as an option.
8. **2:45 Switch disaster.** One click → *Winter Storm Uri – Dallas*. White snow animation. The cascade story changes
   (substation → generator fuel → frozen pipes), and so do the Fix-First items. Close: "Same engine, any disaster: from forecast
   to dollars to action."

## 6. Scope

### MVP (must work live)
- 3 real-disaster presets (Harvey/Houston flood+wind, Uri/Dallas winter storm, Ian/Fort Myers surge+wind), each with
  3 phases (Forecast, Impact, Recovery) and distinct animated overlays.
- Portfolio of about 12 fictional buildings in those cities, with tenants, systems, utility links, insurance.
- Impact engine: exposure → power cascade → dollars (damage, downtime, tenant/SLA, insurance, net).
- Action catalog → per-building plans with ROI and act-by time. Fix-First list. Approve → work orders.
- Photon: technician tasks + replies (DONE/BLOCKED/photo) that update work orders; tenant notices; resident redirect chat.
  Simulator fallback for everything.
- Resources (State Farm): seeded help sites per city, safety check from the hazard engine, routing + capacity, re-route.
- Reports: executive summary + tenant notice (printable HTML).
- UI: UTD-style layout (top buttons, left panel, big map on the right), timeline control, layer toggles.

### Stretch (only after the demo runs end to end)
- 4th preset: Eaton Fire (Altadena, Jan 2025) with an orange smoke/fire overlay.
- "Ask Operation Storm" natural-language box ("which Houston buildings lose the most if barriers fail?").
- Manager approves Fix-First items by text (YES/NO).
- Live NWS alerts feed showing real "upcoming disasters" (**VERIFY** network access).
- What-if: toggle an action on/off and see the dollars before approving.

### Out of scope
Auth, real CBRE data (synthetic portfolio until CBRE gives data), real work-order/CMMS integrations, insurance claim
filing, fraud detection, security hardening, edge cases beyond the demo.

## 7. Success criteria
1. The demo script runs start to finish in under 3:30, twice in a row, from `POST /api/demo/reset`.
2. Switching scenario re-renders the overlay and recomputes every building's dollars in under 1 second.
3. Approving a plan changes the map color, net exposure and $ avoided within 2 seconds, and sends the Photon texts.
4. A real phone's technician reply "DONE" closes the work order on screen within 5 seconds.
5. A resident text gets a safe, open, in-capacity site within 10 seconds, and never a site inside the hazard zone.
6. It runs with no LLM key (template fallback) and no Photon (simulator).

## 8. Honesty rules for the demo
- Disasters are **real events with approximate, hand-drawn footprints**, labeled "illustrative, not official" on screen.
- Buildings, tenants and dollar figures are **synthetic**. Formulas and constants are visible in `03-data-and-scenarios.md`.
- Help-site names may be real public venues used as shelters in those events (**VERIFY** each one before the pitch).
  Otherwise use generic names ("Convention Center Shelter").

## 9. Open questions (confirm at the event)
| # | Question | Default until answered |
|---|---|---|
| Q1 | **VERIFY** Photon 2.0 API (send, inbound webhook, media) | Adapter + simulator. Hour-1 spike task |
| Q2 | Will CBRE share any sample building/lease data? | Synthetic portfolio, loader accepts a CSV swap-in |
| Q3 | Which LLM key do we use on demo day? | `LLM_PROVIDER` env. Templates when none |
| Q4 | Exact real-world facts quoted in the pitch | Teammate verifies each number in `03` before slides |
