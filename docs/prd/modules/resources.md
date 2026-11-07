# Module: resources (`backend/app/modules/resources/`)

**Skills:** backend, python, api · **Read also:** `03-data-and-scenario.md` §6

## Job
Tell each customer **exactly where to go or who is coming**: pick the nearest fitting help site that is open, has
capacity, and whose building is predicted to stay up. Reserve a spot, send the details, give them a **help card** link,
and **re-route** them if the site goes down. This is the "direct them to resources" ask (including State Farm's stadium
claim sites) and the bridge that makes CBRE-hosted sites useful.

## Owns
`backend/app/modules/resources/**`

## Depends on
core; `cascade.building_outlook` (site safety); `messaging.send`; `ai.compose`; `triage.set_status`.
Consumes `case.updated`, `scenario.event` (`SITE_OPEN`), `node.changed`, `prediction.updated`.

## Public interface (`__init__.py`)
```python
def register() -> None                                            # clock order 50
def route_case(case_id: str, resource_id: str | None = None, exclude: list[str] | None = None) -> Reservation | None
def register_resource(resource: Resource) -> Resource             # used by portfolio host_offer
def help_link(case_id: str) -> str                                # f"{APP_BASE_URL}/h/{case.help_token}"
router  # GET /api/resources, POST /api/cases/{id}/route, GET /api/help/{token}
```

## Matching (`route_case` with no explicit resource)
1. **Needed types** from the case needs, in priority order (map in `03` §6): `medical` → no site. Send "Call 911 now" guidance,
   P1, and continue with heat if also needed. `heat_shelter` → warming_center, shelter, hotel. `housing` → hotel, shelter.
   `claim` → claim_site. `repair` → vendor. Route the **first** need that maps to a type. Also route `claim` additionally if
   damages are present and a claim_site is open (one extra message, no reservation needed).
2. **Candidates:** `status == open`, `capacity_used < capacity_total`, and **safe**: if `building_id` is set,
   `cascade.building_outlook(building_id).countdown_minutes` is None or > `SITE_SAFE_HORIZON_MINUTES`. Otherwise use the
   resource's own `predicted_down_at` (warming centers on load-shed feeders get one from cascade predictions, see below).
3. **Rank:** distance (haversine from customer) ascending. Hotels get +3 miles of penalty unless the need is `housing`.
   Vendors are ranked by soonest availability, i.e. fewest active reservations.
4. **Reserve:** `Reservation(eta_minutes = max(5, miles/ROAD_MPH*60))`, `capacity_used += 1` (vendors: +1 job).
   Emit `reservation.changed`, `resource.changed`. `triage.set_status(case, routed, reservation_id=...)`.
5. **Message** (kind `route`): `ai.compose("route", facts, lang)`. Facts: name, address, hours, ETA, what to bring
   (ID, medications, phone charger), directions URL `https://www.google.com/maps/dir/?api=1&destination={lat},{lon}`, and the
   help-card link. Quick replies `["YES", "OTHER OPTION"]`. `YES` → `last_touch_at=now` (confirmed). `OTHER OPTION` → route
   to the next candidate and cancel the first reservation. Both come in through outreach's reply handler, which calls
   `route_case(..., exclude=[old_resource_id])`.
6. **No candidate:** add a case note "no site available: {types}", keep the status `responded`, leave it to the
   coordinator (shown in the Command Center), and send "We're finding you a place; a State Farm agent will call you".

Trigger: on `case.updated` when the case has needs and no active reservation → `route_case`. Debounce per case (one
routing per case per tick).

## Site safety and re-routing (on_tick and on events)
- `prediction.updated` / `node.changed`: for each resource with a `building_id` or a `node_id` (the feeder a city site
  sits on), update `status` (`at_risk` if predicted down within the safe
  horizon, `closed` if failed) and `predicted_down_at`.
- For every **active reservation** at a site that became `at_risk`/`closed` → mark it `moved`, route the case again
  (excluding that site), and send "Change of plan: {old site} may lose power. Please go to {new site} instead." This is a
  showcase moment, so keep it working.
- `SITE_OPEN {resource_id}` → status `open` (the stadium claim site at minute 360).

## register_resource(resource)
Assign an ID if missing, store it, emit `resource.changed`. CBRE `host_offer` approvals call this with `source=cbre`, so
those sites immediately become candidates.

## Help card (`GET /api/help/{token}`) → `HelpCard`
Public, no auth. It's what the customer sees on their phone (rendered by `mobile-pwa`). Include up to 3 tips relevant to their
needs (e.g. burst pipe: "shut off the main water valve"). `updated_at` = latest change.

## Routes
`GET /api/resources?type=` (all, including capacity and status). `POST /api/cases/{id}/route {resource_id?}` (coordinator
override).

## Acceptance
- A heat need near a warming center that will be load-shed in 2h is routed to a different, safe site.
- Load-shedding the feeder of a site with active reservations moves all of them and sends a "change of plan" message to each.
- Capacity is never exceeded. With no capacity left, the case gets the "finding you a place" path.
- After portfolio approves the BLD-03 host offer, new heat cases near downtown get routed to the CBRE site.

## Not in scope
Real geocoding or turn-by-turn directions (a map link only). Real hotel booking. Queue/wait-time modeling beyond capacity.
