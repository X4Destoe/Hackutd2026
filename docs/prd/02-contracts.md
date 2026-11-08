# 02 - Contracts (shared types, IDs, API, events)

Status: DRAFT. TASK-001 sets this to `Status: FROZEN`. After that, changes need a line in comms `docs/DECISIONS.md`
and every consumer updated in the same PR. In code: `backend/app/shared/` (owned by core). Frontend: generated
`frontend/src/shared/api-types.ts`. **A field or route that isn't here doesn't exist. Ask instead of inventing.**

## 1. Conventions
- `snake_case` JSON. Money = `int` USD **cents**. Hours = `int`, relative to impact (0), negative = before.
- Coordinates `lat`, `lon` (WGS84). Geometry = GeoJSON (`dict`).
- IDs: `BLD-HOU-01` building (city code + number), `TEN-001` tenant, `UTL-HOU-SUB3` utility node, `ACT-*` action
  catalog code (e.g. `FLOOD_BARRIERS`), `PLAN-001`, `WO-001`, `MSG-0001`, `RES-HOU-01` resource, `REF-0001` referral,
  `RPT-001` report, people/parties: `TECH-HOU-01`, `TEN-001` (tenant contact), `RESIDENT-<phone-last4>` (auto-created).
- Scenario IDs: `harvey_houston`, `uri_dallas`, `ian_fort_myers` (stretch `eaton_altadena`).

## 2. Enums (`app/shared/enums.py`)
| Enum | Values |
|---|---|
| `HazardKind` | `flood, wind, winter, surge, wildfire` |
| `OverlayStyle` | `flood_water, wind_swirl, snow_ice, surge_water, fire_smoke, forecast_cone` |
| `Phase` | `forecast, impact, recovery` |
| `RiskLevel` | `none, low, moderate, high, severe` |
| `BuildingType` | `office, data_center, retail, industrial, multifamily, medical_office` |
| `PlanStatus` | `proposed, approved, executing, done, rejected, missed` |
| `WorkOrderStatus` | `created, sent, accepted, done, blocked` |
| `PartyType` | `technician, tenant, manager, resident` |
| `Direction` | `outbound, inbound` |
| `MessageKind` | `task, task_update, tenant_notice, resident_chat, redirect, approval_request, other` |
| `ResourceType` | `shelter, warming_center, claim_site, hotel, repair_vendor, cbre_help_site` |
| `ResourceStatus` | `open, full, unsafe, closed` |
| `NeedType` | `shelter, warmth, medical, food_water, repair, claim, info` |
| `ReportKind` | `executive_summary, tenant_notice` |

## 3. Models (`app/shared/schemas.py`, Pydantic v2; `?` = optional, `[]` = default empty)

### Portfolio (owned by scenarios)
```
Tenant:        id, name, sqft: int, rent_per_day_cents: int, sla_penalty_per_hour_cents: int = 0,
               critical_ops: bool = False, contact_party_id?: str
Insurance:     carrier: str, deductible_cents: int, limit_cents: int, bi_days_covered: int
Systems:       has_generator: bool, generator_fuel_hours: float = 0, freeze_protection: bool,
               flood_barriers_installed: bool = False, roof_wind_rating_mph: int, ground_floor_equipment: bool
Building:      id, name, type: BuildingType, city, address, lat, lon, sqft: int, floors: int, year_built: int,
               first_floor_elev_ft: float (above local ground), replacement_value_cents: int,
               utility_node_id: str, systems: Systems, tenants: [Tenant], insurance: Insurance,
               onsite_party_id: str, can_host_help_site: bool, host_capacity: int = 0,
               data_sources: [str]           # e.g. ["lease_abstracts","bms","utility_map","insurance_sov"]
UtilityNode:   id, kind: "substation"|"water_plant"|"telecom", name, city, lat, lon
Party:         id, type: PartyType, name, phone, language: str = "en", demo_live: bool = False
```

### Scenarios and hazard (owned by scenarios)
```
Overlay:       id, style: OverlayStyle, hazard: HazardKind, geojson: dict
               # FeatureCollection; each feature has properties.intensity (number) with unit per hazard:
               # flood/surge: water depth ft above ground · wind: sustained mph · winter: ice in / temp °F · wildfire: 1 = burn zone
TimelineStep:  hour: int, phase: Phase, label: str ("−48h · Forecast"), overlays: [Overlay],
               utility_outages: [{node_id: str, hours: float}]   # predicted/actual TOTAL outage duration known at this step
               narrative: str
Scenario:      id, name, real_event: str, date_label: str, city: str, center: {lat, lon}, zoom: float,
               hazards: [HazardKind], steps: [TimelineStep], sources: [str], disclaimer: str
ScenarioMeta:  id, name, real_event, date_label, city, hazards, step_hours: [int]
DemoState:     scenario_id, step_hour: int, phase: Phase, messaging_mode: "sim"|"photon", llm_provider: str
```

### Impact (owned by impact)
```
Exposure:      building_id, step_hour, flood_depth_ft: float = 0, wind_mph: float = 0, ice_in: float = 0,
               temp_f?: float, in_burn_zone: bool = False, grid_down: bool, power_out_hours: float,
               on_generator: bool, generator_hours_left?: float, cause_chain: [str]   # ["UTL-HOU-SUB3 down","generator 18h"]
MoneyBreakdown: property_damage_cents, downtime_days: float, rent_abatement_cents, sla_penalty_cents,
               operations_cents, insurance_recovery_cents, net_exposure_cents
Impact:        building_id, step_hour, risk: RiskLevel, damage_ratio: float, money: MoneyBreakdown,
               drivers: [str], exposure: Exposure, with_approved_actions: bool
PortfolioSummary: scenario_id, step_hour, buildings_at_risk: int, gross_loss_cents, net_exposure_cents,
               avoided_cents, actions_approved: int, worst_building_ids: [str]
```

### Actions (owned by actions)
```
ActionEffect:  damage_mult?: float, downtime_mult?: float, sla_mult?: float, add_generator_hours?: float,
               max_depth_above_floor_ft?: float, damage_mult_above_max?: float,  # e.g. barriers: ×0.3 up to 3 ft, ×0.85 above
               requires_generator?: bool, requires_no_generator?: bool, hazards: [HazardKind]  # [] = all hazards
ActionTemplate: code, title, description, cost_cents: int, act_by_hour: int,
               effect: ActionEffect, task_text: str, tenant_notice_text?: str,
               creates_help_site: bool = False, community: bool = False
PlanAction:    code, title, cost_cents, act_by_hour: int, feasible: bool
Plan:          id, building_id, scenario_id, actions: [PlanAction], cost_cents, avoided_cents, roi: float,
               act_by_hour: int, status: PlanStatus, rationale: str, approved_by?: str, approved_at_hour?: int
FixFirstItem:  rank: int, plan_id, building_id, building_name, title, cost_cents, avoided_cents, roi,
               act_by_hour, hours_left: int, why: str
WorkOrder:     id, plan_id, building_id, action_code, party_id, text: str, status: WorkOrderStatus,
               created_at_hour: int, updates: [str], photo_urls: [str]
```

### Messaging, resources, reports
```
Message:       id, party_id, party_type: PartyType, direction: Direction, kind: MessageKind, body: str,
               media_urls: [str], work_order_id?, referral_id?, status: "queued"|"sent"|"failed"|"received",
               channel: str, created_wall: str (ISO wall-clock), error?: str
MessagingStatus: mode, live_parties: [str], sent: int, received: int, last_error?: str
Resource:      id, type: ResourceType, name, address, city, lat, lon, capacity: int, used: int = 0,
               status: ResourceStatus, needs_served: [NeedType], building_id?: str, utility_node_id?: str,
               phone?: str, hours: str, source: "statefarm"|"city"|"redcross"|"partner"|"cbre"
Referral:      id, party_id, needs: [NeedType], people: int = 1, summary: str, resource_id?, distance_mi?: float,
               status: "routed"|"rerouted"|"unrouted"|"arrived", history: [str]
Report:        id, kind: ReportKind, scenario_id, building_id?, title, markdown: str, created_wall: str
```

## 4. REST API (prefix `/api`; each module owns its own router)
| Route | Body/query | Returns | Owner |
|---|---|---|---|
| `GET /health` | | `{ok}` | core |
| `GET /events` | | SSE | core |
| `GET /_contracts` | | all models (for type generation) | core |
| `GET /scenarios` | | `[ScenarioMeta]` | scenarios |
| `POST /demo/reset` | `{scenario_id?}` | `DemoState` | scenarios |
| `POST /scenarios/{id}/load` | | `DemoState` (step = first step) | scenarios |
| `GET /demo/state` | | `DemoState` | scenarios |
| `POST /timeline` | `{hour}` (must be one of the scenario's step hours) | `DemoState` | scenarios |
| `GET /overlays` | `?hour=` (default current) | GeoJSON FeatureCollection (all overlays at that step, `properties.style`) | scenarios |
| `GET /buildings` | | `[Building]` | scenarios |
| `GET /utilities` | | `[UtilityNode]` + `down: bool` at current step | scenarios |
| `GET /impact` | `?hour=` | `[Impact]` | impact |
| `GET /impact/{building_id}` | `?hour=` | `Impact` | impact |
| `GET /portfolio/summary` | | `PortfolioSummary` | impact |
| `GET /actions/catalog` | | `[ActionTemplate]` | actions |
| `GET /plans` | `?building_id=&status=` | `[Plan]` | actions |
| `POST /plans/{id}/approve` | `{by}` | `Plan` | actions |
| `POST /plans/{id}/reject` | `{by}` | `Plan` | actions |
| `GET /fix-first` | `?limit=10&community=0|1` | `[FixFirstItem]` | actions |
| `GET /workorders` | `?building_id=` | `[WorkOrder]` | actions |
| `POST /workorders/{id}/update` | `{status, note?}` | `WorkOrder` | actions |
| `POST /webhooks/photon` | provider payload (**VERIFY**) | `{ok}` | messaging |
| `GET /messages` | `?party_id=` | `[Message]` | messaging |
| `GET /messaging/status` | | `MessagingStatus` | messaging |
| `POST /demo/simulate-message` | `{phone or party_id, text, media_url?}` | `Message` | messaging |
| `GET /resources` | `?city=` | `[Resource]` | resources |
| `GET /referrals` | | `[Referral]` | resources |
| `POST /reports` | `{kind, building_id?}` | `Report` | reports |
| `GET /reports` · `GET /reports/{id}/html` | | `[Report]` · printable HTML | reports |

## 5. Events (in-process bus + SSE `event: <type>\ndata: <json>`)
| Type | Payload | Emitted by |
|---|---|---|
| `scenario.loaded` | `DemoState` | scenarios |
| `timeline.changed` | `DemoState` | scenarios |
| `impact.updated` | `{step_hour, summary: PortfolioSummary}` | impact |
| `plans.updated` | `{count, fix_first_top: [FixFirstItem] (≤5)}` | actions |
| `plan.changed` | `{plan_id, building_id, status}` | actions |
| `workorder.changed` | `{work_order_id, building_id, status}` | actions |
| `message.sent` / `message.received` | `{message_id, party_id, kind}` | messaging |
| `resources.changed` | `{changed_ids: [str]}` | resources |
| `referral.changed` | `{referral_id, status, resource_id?}` | resources |
| `report.created` | `{report_id, kind}` | reports |

The frontend uses events only to refresh queries (TanStack Query invalidation).

## 6. Python interfaces between modules (import only from `app.modules.<name>`)
| Module | Public functions |
|---|---|
| core (`app.shared`) | `store.<repo>.get/require/list/put`, `store.reset()`, `bus.emit/on`, `ids.new_id(prefix)`, `config.settings` |
| scenarios | `load(scenario_id)`, `current() -> DemoState`, `scenario() -> Scenario`, `step(hour=None) -> TimelineStep`, `set_hour(hour)`, `hazard_at(lat, lon, hour=None) -> dict` (`{flood_depth_ft, wind_mph, ice_in, temp_f, in_burn_zone}`), `utility_down(node_id, hour=None) -> bool`, `outage_hours(node_id, hour=None) -> float` |
| impact | `recompute(hour=None) -> list[Impact]`, `impact_for(building_id, hour=None, extra_actions: list[str] = []) -> Impact`, `baseline_for(building_id, hour=None) -> Impact` (no actions), `summary() -> PortfolioSummary`, `site_safe(lat, lon, utility_node_id=None, hour=None) -> bool` |
| actions | `catalog: dict[str, ActionTemplate]`, `refresh()`, `approve(plan_id, by) -> Plan`, `reject(plan_id, by) -> Plan`, `fix_first(limit=10) -> list[FixFirstItem]`, `apply_task_reply(party_id, text, media_urls) -> WorkOrder | None`, `approved_codes(building_id) -> list[str]` |
| ai | `classify_need(text, language_hint) -> dict` (`{needs: [NeedType], people, urgent: bool, language, summary}`), `compose(purpose, facts, language) -> str`, `rationale(facts) -> str`, `write_report(kind, facts) -> str`, `provider_name()` |
| messaging | `send(party_id, body, kind, media_urls=[], work_order_id=None, referral_id=None) -> Message`, `on_inbound(party_type, handler)`, `party_for_phone(phone) -> Party` (creates a RESIDENT party for unknown numbers), `status()` |
| resources | `refresh_safety()`, `route(party_id, text) -> Referral`, `register_site(resource) -> Resource` |
| reports | `generate(kind, building_id=None) -> Report` |

**Circular imports:** `impact` and `actions` call each other (impact reads approved actions and the catalog; actions asks impact
for what-if numbers). Import the other module *inside the function* (`from app.modules import actions`), never at the top of the file.
