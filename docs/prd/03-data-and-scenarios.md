# 03 - Data, scenarios, money model, action catalog, resources

Everything here is the seed for the demo. Buildings, tenants, people and dollars are **synthetic and fictional**.
Disasters are **real events with approximate, hand-drawn footprints** ("illustrative, not official" shown on screen).
Every real-world fact quoted in the pitch is marked **VERIFY** for a teammate to confirm with a source.

## 1. Scenario presets (`backend/data/scenarios/<id>.json`, model `Scenario`)

All scenarios share the same timeline steps: hours `[-48, -24, -12, 0, 12, 48, 168]`.
Phases: `< 0` = **forecast**, `0` and `12` = **impact**, `≥ 48` = **recovery**.
**Forecast** steps hold the *predicted* peak footprint (shown lighter, plus a forecast cone or track). **Impact** steps hold the
actual footprint. **Recovery** steps hold the receding footprint (impact still counts the peak; see §3).

| ID | Real event (VERIFY facts) | City / center | Hazards | Overlay styles | Story |
|---|---|---|---|---|---|
| `harvey_houston` | Hurricane Harvey, Aug 25–30 2017. Landfall near Rockport; catastrophic rain flooding in Houston, reported 50+ in of rain in parts of the region | Houston `29.76, -95.37`, zoom 10 | flood, wind | `flood_water` (blue, rising), `wind_swirl` (light), `forecast_cone` at −48/−24 | Bayou flooding downtown and Meyerland, reservoir-release flooding in the Energy Corridor, a substation outage puts the data hub on its generator |
| `uri_dallas` | Winter Storm Uri, Feb 13–17 2021. ERCOT rotating outages, extreme cold | Dallas `32.82, -96.80`, zoom 10 | winter | `snow_ice` (white tint + falling-snow particles) | Load-shed substations, generators running dry, frozen and burst pipes where there is no freeze protection |
| `ian_fort_myers` | Hurricane Ian, Sep 28 2022. Category 4 landfall in SW Florida, severe storm surge at Fort Myers Beach | Fort Myers `26.56, -81.87`, zoom 10 | surge, wind | `surge_water` (darker blue, waves), `wind_swirl` (strong), `forecast_cone` | Beachfront retail is a near-total loss, downtown has moderate surge, the inland medical pavilion stays up and becomes a help site |
| `eaton_altadena` (stretch) | Eaton Fire, Jan 2025, Altadena CA | Altadena `34.19, -118.13` | wildfire | `fire_smoke` (orange glow + embers) | Burn zone vs. smoke-only buildings |

Each `TimelineStep` has `overlays` (GeoJSON features with `properties.intensity`), `utility_outages` as
`[{node_id, hours}]` (the predicted or actual **total outage duration** known at that step), and a one-line `narrative`
("NWS: Harvey forecast to stall over Houston, 30–40 in rain possible", "Bayous overtop", "Water receding, power restoration begins").

**How the overlays are made:** `backend/data/make_overlays.py` (scenarios module) builds polygons with shapely. It buffers
hand-placed polylines (bayous, coastline) and points (low spots) into 2–4 nested intensity bands. Example bands: flood depth 1, 3, 6 ft;
wind 74, 96, 111, 130 mph; ice 0.25, 0.5, 1.0 in plus temperature 15°F; surge 3, 6, 10 ft. Simple, deterministic, and looks right on the map.
Add `sources` (Wikipedia/NWS/FEMA page titles for the event) and the `disclaimer`.

## 2. Portfolio seed (`backend/data/portfolio.json`, `utilities.json`, `parties.json`)

12 fictional buildings (CBRE-style mixed portfolio). Each has 1–4 tenants, an insurance block, systems, a utility link, and
`data_sources` (to show "fragmented data joined": `lease_abstracts`, `bms`, `utility_map`, `insurance_sov`, `work_orders`).

| ID | Name | Type | Location (approx) | Key traits | Role in the story |
|---|---|---|---|---|---|
| BLD-HOU-01 | Bayou Plaza | office | downtown Houston near Buffalo Bayou | first floor 1.0 ft, ground-floor equipment, generator 18h, SUB3 | **Hero building**: flood barriers save ~$1M |
| BLD-HOU-02 | Northwest Data Hub | data_center | NW Houston | elevated, generator 30h, SUB5 (outage 72h), 2 critical tenants with SLA | Power cascade. Fuel delivery is a cheap fix |
| BLD-HOU-03 | Meyerland Retail Center | retail | Meyerland (Brays Bayou) | first floor 0.5 ft, no generator | Deep flooding. Barriers are useless above 3 ft, so a post-event dry-out is the best option |
| BLD-HOU-04 | Galleria Medical Offices | medical_office | Uptown/Galleria | high ground, generator 48h, `can_host_help_site`, 250 spots | Stays safe → offered as a help site |
| BLD-HOU-05 | Energy Corridor Tower | office | west Houston, near reservoirs | first floor 2.0 ft, generator 12h | Flooding from reservoir releases. This is the "missed" plan if we don't act by −12h |
| BLD-DAL-01 | Elm Street Tower | office | downtown Dallas | generator 8h, freeze protection on | Moderate |
| BLD-DAL-02 | Lone Star Data Center | data_center | Farmers Branch | generator 5h, 3 critical tenants, SLA total $42k/h | **Headline for Uri**: fuel + tenant continuity |
| BLD-DAL-03 | Lakewood Retail Center | retail | Lakewood | no generator, no freeze protection | Burst pipes. Draining the pipes is cheap |
| BLD-DAL-04 | Market Center Expo Hall | retail (event) | Market Center | on a critical circuit (never shed), `can_host_help_site`, 400 spots | Warming-center help site |
| BLD-FMY-01 | Riverside Commons | office | downtown Fort Myers | first floor 3 ft, surge 4–5 ft | Moderate surge |
| BLD-FMY-02 | Gulf Coast Medical Pavilion | medical_office | inland Fort Myers | generator 48h, `can_host_help_site`, 200 spots | Help site |
| BLD-FMY-03 | Estero Boulevard Retail | retail | Fort Myers Beach | first floor 1 ft, surge 10+ ft | Near-total loss. Shows that some losses can't be avoided, only insured |

Replacement values: $8M–$60M (data centers highest). Rent: $15–$45 per sqft per year, converted to `rent_per_day_cents`.
SLA penalties only for data-center tenants. Insurance: `carrier` = "State Farm" or "Other", deductible 2–5% of value
(named-storm style), limit ≈ value, `bi_days_covered` 30–90.

`utilities.json`: 3 substations per city (`UTL-HOU-SUB1..5` for Houston), with coordinates. `parties.json`: `MGR-01`
(portfolio manager), one technician per city (`TECH-HOU-01`, `TECH-DAL-01`, `TECH-FMY-01`), one contact per tenant
(`TEN-001…`). Phones are fictional (`+1-555-01xx`). `DEMO_PHONES` maps real phones onto chosen parties at reset.

## 3. Money model (`impact` module). All constants live in `backend/app/modules/impact/constants.py`

Inputs per building at step `h`: the hazard at its point (`scenarios.hazard_at`), the utility outage hours, systems, tenants, insurance,
and approved actions (or extra actions for what-if).
**Peak rule:** at forecast and impact steps use that step's hazard. At recovery steps use the **max hazard seen at any
step ≤ h**, because damage doesn't un-happen.

**Damage ratio per hazard** (illustrative curves, combined as `1 − Π(1 − r_i)`):
- **Flood** (depth above first floor `d = flood_depth_ft − first_floor_elev_ft`): `d≤0: 0 · 0.5: 0.05 · 1: 0.10 · 2: 0.18 ·
  3: 0.24 · 4: 0.28 · 6: 0.35 · 8+: 0.42` (linear interpolation). +0.04 if `ground_floor_equipment` and `d>0`.
- **Surge:** flood curve × 1.3 (wave action), cap 0.9.
- **Wind:** `excess = wind_mph − roof_wind_rating_mph`. If `excess ≤ 0`: 0.01 when wind > 74, else 0. If `excess > 0`: `0.02 + 0.004×excess`, cap 0.5.
- **Winter:** unpowered hours `u = max(0, power_out_hours − generator_hours)`. Burst pipes if `!freeze_protection`, `temp_f ≤ 20`
  and `u > 8`: `0.03 + 0.002×(u−8)`, cap 0.10. Ice on the roof: +0.01 if `ice_in ≥ 0.5`.
- **Wildfire:** burn zone 0.65.

**Dollars:**
```
property_damage   = replacement_value × damage_ratio
unpowered_hours   = max(0, power_out_hours − generator_fuel_hours (+ added fuel))
downtime_days     = damage_ratio × 180 + unpowered_hours / 24
rent_abatement    = downtime_days × Σ tenant.rent_per_day                     (lease abatement when untenantable)
sla_penalty       = min(unpowered_hours + downtime_days×24, 720) × Σ tenant.sla_penalty_per_hour
operations        = downtime_days × sqft × 5¢                               (cleanup, security, temporary ops)
insurance_recovery= min(limit, max(0, property_damage − deductible)) + min(downtime_days, bi_days_covered) × Σ rent_per_day
net_exposure      = property_damage + rent_abatement + sla_penalty + operations − insurance_recovery
```
**Risk level by net exposure:** none `0` · low `< $50k` · moderate `< $250k` · high `< $1M` · severe `≥ $1M` (also the map colors).
**Drivers:** plain-English strings, e.g. "3.1 ft of water above first floor", "substation SUB3 down 96h, generator covers 18h",
"2 critical tenants: SLA $1,750/h", "insurance pays $1.1M after $1.2M deductible".

## 4. Action catalog (`backend/data/actions.json`, model `ActionTemplate`; `act_by_hour` replaces lead time)

| Code | Title | Cost | Act by | Effect | Hazards |
|---|---|---|---|---|---|
| FLOOD_BARRIERS | Deploy temporary flood barriers | $18,000 | −12 | damage ×0.3 if water above floor ≤ 3 ft, else ×0.85 | flood, surge |
| SANDBAGS | Sandbag entrances | $2,500 | −6 | damage ×0.85 if water above floor ≤ 1.5 ft | flood, surge |
| RELOCATE_EQUIPMENT | Move ground-floor equipment up | $6,000 | −6 | damage ×0.8, downtime ×0.7 | flood, surge |
| STORM_SHUTTERS | Install storm shutters | $22,000 | −24 | damage ×0.55 | wind |
| SECURE_ROOFTOP | Secure rooftop units and debris | $3,500 | −12 | damage ×0.8 | wind |
| GENERATOR_FUEL | Top off and pre-book a fuel delivery | $3,800 | −6 | +24 generator hours (only if it has a generator) | all |
| RENTAL_GENERATOR | Rent and hook up a portable generator | $9,500 | −24 | +72 generator hours (for buildings without one) | all |
| TENANT_CONTINUITY | Activate tenant continuity (move critical ops) | $1,500 | −12 | SLA ×0.4 | all |
| PIPE_PROTECTION | Drain and heat-trace exposed pipes | $2,100 | −6 | winter damage ×0.1 | winter |
| PORTABLE_HEAT | Portable heat in mechanical rooms | $900 | 0 | winter damage ×0.5 | winter |
| PRESTAGE_CONTRACTOR | Pre-book a restoration contractor (beats post-storm demand surge) | $5,000 | −24 | downtime ×0.6 | all |
| EMERGENCY_DRYOUT | Emergency dry-out and mold prevention | $15,000 | +48 | downtime ×0.7 | flood, surge |
| OFFER_HELP_SITE | Offer the building as a community help site | $2,000 | +12 | creates a `cbre_help_site` resource (needs `can_host_help_site` and a safe site) | all |

Each template has a `task_text` (sent to the technician, with `{building}`, `{deadline}` placeholders) and, where relevant,
`tenant_notice_text`.

**Plan building:** for each exposed building at step `h`, the candidates are templates matching its hazards with `h ≤ act_by_hour`.
Add them greedily by marginal ROI (`avoided / cost`), keeping any with ROI > 1. OFFER_HELP_SITE is listed separately as a
**community** action. A plan whose best actions' `act_by` has passed without approval becomes **missed**, showing "would have saved $X".
This "regret" moment is one of the strongest demo beats.

## 5. Help sites (`backend/data/resources.json`, model `Resource`)

About 5 per city, each with a `utility_node_id` (for power) and a location (for the hazard check):

| City | Sites |
|---|---|
| Houston | Convention center mega-shelter (**VERIFY**: George R. Brown Convention Center was used as a Harvey shelter, 1001 Avenida de las Americas), a second large shelter (**VERIFY** NRG Center), "Bayou Community Center Shelter" (generic, **inside the flood zone**: shows the safety check), "State Farm Catastrophe Claims Site – Galleria" (generic), "Westside Hotel" (generic), "Gulf Restoration Crew" (repair vendor) |
| Dallas | Convention center warming center (**VERIFY**: Kay Bailey Hutchison Convention Center was used as a warming center during Uri), "Oak Lawn Library Warming Center" (generic, **on a load-shed substation**), "State Farm Claims Site – North Dallas" (generic), "Love Field Hotel" (generic), "Metro Plumbing Emergency" (vendor) |
| Fort Myers | "Lee County Inland Shelter" (generic), "Beachside Rec Center" (generic, **in the surge zone**), "State Farm Claims Site – Fort Myers" (generic), "Daniels Parkway Hotel" (generic), "SWFL Roof & Dry-out" (vendor) |

Need → resource type: `shelter → shelter, cbre_help_site, hotel` · `warmth → warming_center, shelter, cbre_help_site` ·
`claim → claim_site` · `repair → repair_vendor` · `food_water → shelter, warming_center` · `medical → none` (reply with
emergency guidance and flag it as urgent) · `info → none`.
