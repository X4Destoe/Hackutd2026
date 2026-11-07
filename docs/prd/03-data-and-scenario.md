# 03 - Data and the demo scenario

All people, homes, buildings and companies here are **synthetic** and fictional. Real public data is used
only for flavor (warning text, the declared-county list), always from a **cached snapshot** so the demo
never depends on a government API being up.

## 1. Geography

Dallas County, TX. Map center `32.85, -96.80`, zoom 10. Customers spread over 8 ZIP clusters
(75201, 75204, 75206, 75214, 75218, 75228, 75231, 75243), placed with jitter around cluster centers.
Every node and building has coordinates, so everything can be drawn on the map.

## 2. Seed files (`backend/data/seed/`, produced by `backend/data/generate_seed.py`)

The generator is deterministic (`SEED_RANDOM`). Counts are parameters so the team can shrink them for tests.
Each file is a JSON array of the contract model named (fields as in `02-contracts.md`; runtime-only
fields like `status`, `case_id` are omitted).

| File | Model | Count | Notes |
|---|---|---|---|
| `nodes.json` | `Node` | ~2,100 | 2 `generation`, 6 `substation` SUB-1..6, 18 `feeder` (3 per sub, e.g. FDR-3A/B/C), 3 `pump_station`, 3 `water_zone`, 1 `home` per customer, 8 `building` + their `building_system`s |
| `edges.json` | `Edge` | ~4,300 | See §3 |
| `customers.json` | `Customer` | 2,000 | Distributions in §4 |
| `buildings.json` | `Building` | 8 | §5 |
| `resources.json` | `Resource` | 19 | §6 |
| `adjusters.json` | `Adjuster` | 12 | §7 |
| `reply_templates.json` | `{persona: [ {text, language, needs, damages} ]}` | ~60 | Simulated-crowd replies (§9) |

`backend/data/public/` (optional, committed snapshots): `nws_alerts_tx.json`, `fema_declaration.json`.
**VERIFY**: the NWS alerts API (`api.weather.gov/alerts`) and the OpenFEMA Disaster Declarations Summaries
v2 dataset, plus the FEMA disaster number for the Feb 2021 Texas severe winter storm. They weren't reachable while
writing. The data task confirms them with a real request. If they can't be reached, it hand-writes a small snapshot
labeled "illustrative".

## 3. Dependency graph shape (what "connects fragmented data")

```
GEN-1, GEN-2 (generation)
   └─power─> SUB-1..SUB-6 (substation)            group "main" (either GEN is enough → same group = OR)
                └─power─> FDR-xA/B/C (feeder)
                             ├─power─> HOME-xxxx  (home)              group "power"
                             ├─power─> PMP-1..3   (pump station)      group "power"; pumps have buffer_hours 1.5 (tank storage)
                             └─power─> BLD-xx     (building)          group "grid"  ┐ generator is an alternative supply:
                                        SYS-BLD-xx-GEN ──power──> BLD-xx  group "grid" ┘ same group → OR
PMP-n ─water─> WZ-n (water zone) ─water─> HOME-xxxx / BLD-xx           group "water"
BLD-xx ─heat/cooling─> SYS-BLD-xx-HVAC / SYS-BLD-xx-COOL (data centers) / SYS-BLD-xx-PIPE
```

- A **home** has no backup. When its feeder fails it loses power and heat at once, and the thermal model (§8)
  then predicts when it becomes unsafe and when pipes may burst.
- A **building** with a generator keeps running on backup for `generator.fuel_hours_left`, then fails.
- `SUB-2` is a **critical circuit** (hospital feeder in the story). It is never load-shed, so buildings on it
  stay up. That's why BLD-03 can host a warming center.
- The data sources each building was assembled from are listed in `Building.data_sources`
  (`bms`, `lease`, `utility`, `work_orders`, `generator_log`). The Portfolio view shows them joined into one record.
  This is the "fragmented data" the CBRE track asks for.

## 4. Customers (2,000)

| Attribute | Distribution |
|---|---|
| language | en 70%, es 22%, vi 8% |
| household.over_75 ≥1 | 12% |
| household.infants ≥1 | 8% |
| household.medical_device | 4% (oxygen concentrator, dialysis, etc.) |
| household.mobility_limited | 6% |
| home.year_built | <1980 35% (insulation poor), 1980–2000 40% (avg), >2000 25% (good) |
| home.pipes_exposed | 30% |
| feeder | spread so SUB-3 and SUB-5 feeders hold ≈ 900 customers total (the outage area) |
| demo_live | false. The `DEMO_PHONES` env var maps 1–3 real phones onto chosen customers at reset |

Names are generated from neutral first/last name lists. Phones use the reserved fictional range
`+1-214-555-01xx`. Real numbers come only from `DEMO_PHONES`.

## 5. CBRE portfolio (8 fictional buildings)

| ID | Name | Type | Grid | Generator (fuel h) | Story role |
|---|---|---|---|---|---|
| BLD-01 | Elm Street Tower | office | FDR-1A | yes (8) | Low risk baseline |
| BLD-02 | Commerce Plaza | office | FDR-5B | no | Fails at load-shed. Tenant rent abatement exposure |
| BLD-03 | Trinity Convention Center | convention_center | FDR-2A (critical) | yes (24) | **Stays up → host_offer: warming center 400 + claim site** |
| BLD-04 | Lakeside Retail Center | retail | FDR-3C | no | Pipe-burst risk (`freeze_protection: false`) |
| BLD-05 | North Dallas Office Park | office | FDR-6A | yes (6) | Moderate |
| BLD-06 | Mockingbird Multifamily | multifamily | FDR-3A | no | Residents overlap with State Farm customers on the same feeder |
| BLD-07 | Lone Star Data Center | data_center | FDR-3B | yes (5) | **Headline: generator fuel runs out about 6.5h after the load-shed (≈ minute 390) → cooling loss → SLA $42k/h** |
| BLD-08 | Fair Oaks Stadium | stadium | FDR-2B (critical) | yes (24) | Hosts the State Farm **mobile claim site** (opens at minute 360) |

Tenants carry the SLA and penalty data (for example BLD-07: 3 tenants, 99.99% uptime, combined
`penalty_per_hour_cents` = 4,200,000). All dollar figures are **illustrative** and labeled that way in the UI.

## 6. Resources (19)

| Type | Count | Source | Notes |
|---|---|---|---|
| claim_site | 2 | statefarm | RES-001 at BLD-08 stadium (opens minute 360, capacity 300/day), RES-002 State Farm agency office (always open, capacity 60) |
| warming_center | 6 | city | 2 sit on feeders that get load-shed (→ `at_risk`, then closed) to demo **re-routing** |
| shelter | 2 | partner | Overnight, capacity 150 each |
| hotel | 3 | partner | Additional Living Expense rooms, capacity 20–40 |
| vendor | 6 | partner | Plumbers ×3, electrician ×1, restoration (water) ×2. Capacity = jobs/day |
| (runtime) | +1–2 | cbre | Created when a `host_offer` is approved (BLD-03 warming center, capacity 400) |

`services` maps needs to resource types (used by `resources` routing):
`heat_shelter → warming_center, shelter, hotel` · `housing → hotel, shelter` · `claim → claim_site` ·
`repair → vendor` · `water → warming_center, shelter` · `medical → none` (P1 + "call 911" message) ·
`info/safe → none`.

## 7. Adjusters (12)

Specialties: water ×4, structure ×2, roof ×2, general ×3, catastrophe ×1. Spread across the county.
`max_cases` 4. One or two can be `demo_live` (a teammate's real phone) via `DEMO_PHONES`.
This directly answers "one team handles every disaster type": dispatch matches specialty to damage.

## 8. Home thermal model (used by `cascade` to predict harm)

After a home loses heat at minute `t0` with indoor temperature `T0 = 68°F` and outdoor temperature `To`
(from the scenario weather at that time):

```
T(t) = To + (T0 - To) * exp(-k * hours_since_t0)
hours_until(Tx) = -ln((Tx - To) / (T0 - To)) / k          # if Tx <= To → never reaches; treat as None
k by insulation: poor 0.12/h, avg 0.08/h, good 0.05/h
unsafe   : Tx = UNSAFE_INDOOR_F (50)
pipe risk: Tx = PIPE_BURST_INDOOR_F (28), only if home.pipes_exposed
```

Example: To = 10°F, poor insulation → unsafe in about 3.1h, pipe risk in about 9.8h. These numbers drive
predictions, triage time-to-harm, and "your home may become unsafe in about 3 hours" messages.

## 9. Simulated crowd (`scenario` module)

For each non-live customer who gets an alert (seeded by `SEED_RANDOM`):

| Outcome | Share | Timing |
|---|---|---|
| Replies to the text | 65% | 5–40 sim-min after the alert (log-normal) |
| Replies only after the voice call | 15% | 2–20 sim-min after the call |
| Never replies → unreached list | 20% | |

The content is drawn from `reply_templates.json` and depends on the customer's real situation (has heat? exposed
pipes? infants?). That way replies are consistent with the model. About 30% are quick replies (`1`, `2`, `3`)
and about 70% are free text in the customer's language, some deliberately messy
(`"no heat since 9 pipes broke kitchen water everywhere 2 kids"`, `"sin calefacción, mi mamá usa oxígeno"`).
Adjusters (non-live) accept 80% of offers after 2–8 sim-min and pass on the rest.

## 10. Scenario `backend/data/scenarios/uri_dfw.json`

```
{ "id": "uri_dfw", "name": "Texas winter storm – Dallas County",
  "start_iso": "2021-02-14T18:00:00-06:00", "start_minute": -120, "end_minute": 1440,
  "center": {"lat": 32.85, "lon": -96.80}, "zoom": 10,
  "weather": [ {"at": -120, "temp_f": 24, "wind_chill_f": 12}, {"at": 0, "temp_f": 18, "wind_chill_f": 5},
               {"at": 240, "temp_f": 10, "wind_chill_f": -2}, {"at": 480, "temp_f": 4, "wind_chill_f": -9},
               {"at": 900, "temp_f": 8, "wind_chill_f": -4}, {"at": 1200, "temp_f": 15, "wind_chill_f": 4} ],
  "events": [ TimelineEvent, ... ] }
```

Timeline events (`code`, `payload`):

| at (min) | code | payload | Effect |
|---|---|---|---|
| -120 | `NWS_WARNING` | `{text}` from snapshot | UI banner |
| -110 | `ADVISORY_BROADCAST` | `{zips: [...]}` | outreach sends pre-storm safety texts to every customer in those ZIPs |
| 60 | `GRID_EMERGENCY` | `{text: "Generation shortfall – rotating outages ordered"}` | UI banner |
| 90 | `LOAD_SHED` | `{node_id: "SUB-3"}` | SUB-3 feeders fail → ~500 homes, PMP-2, BLD-04/06/07 |
| 150 | `LOAD_SHED` | `{node_id: "SUB-5"}` | ~400 homes, BLD-02, one warming center |
| 360 | `SITE_OPEN` | `{resource_id: "RES-001"}` | State Farm stadium claim site opens |
| 420 | `LOAD_SHED` | `{node_id: "FDR-6A"}` | Smaller wave, BLD-05 to generator |
| 900 | `RESTORE` | `{node_id: "SUB-5"}` | Partial restoration (recovery shown) |
| 1200 | `RESTORE` | `{node_id: "SUB-3"}` | |

The cascade engine **predicts** consequences between these events (PMP-2 failing after its tank buffer, BLD-07
fuel exhaustion, homes going unsafe). The timeline only contains causes, never results. The data task
tunes the times so the §6 demo script beats land in the first ~3 real minutes at default speed
(use `POST /demo/jump` to skip quiet stretches).
