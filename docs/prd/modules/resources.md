# Module: resources (`backend/app/modules/resources/` + `backend/data/resources.json`) - the State Farm piece

**Skills:** backend, python, api · **Read also:** `03-data-and-scenarios.md` §5, `00-overview.md` §5 step 7

## Job
When a disaster hits, **send people to the right help, and only to places that are actually safe and open right now**.
It uses the same hazard engine as the CBRE side. This answers State Farm's "identify the most urgent needs, coordinate
assistance, no one overlooked", and it's where CBRE buildings become community help sites.

## Owns
`backend/app/modules/resources/**`, `backend/data/resources.json`.

## Interface (`__init__.py`)
```python
def register() -> None              # on timeline.changed → refresh_safety(); messaging.on_inbound("resident", handle)
def refresh_safety() -> list[str]   # update each site's status; re-route active referrals at sites that became unsafe; returns changed ids
def route(party_id: str, text: str) -> Referral
def register_site(resource: Resource) -> Resource     # used by actions for OFFER_HELP_SITE (type cbre_help_site)
router  # GET /api/resources, GET /api/referrals
```

## Behavior
1. **Safety per step:** a site is `unsafe` if `not impact.site_safe(lat, lon, utility_node_id)`. It's `full` if `used ≥ capacity`,
   else `open` (respect `closed` from the seed). Only sites in the scenario city are considered.
2. **route(party, text):** `ai.classify_need(text)`.
   - `medical` + `urgent` → reply immediately with emergency guidance ("Call 911 now…"), and mark the referral urgent at the top of the
     Help Sites view.
   - Otherwise map needs to resource types (`03` §5) and pick the **nearest open, safe** site with `capacity − used ≥ people`.
     The resident's location is a demo simplification: use the phone's mapped location from `DEMO_PHONES`, otherwise a random point in the
     current hazard area, or a ZIP/neighborhood if they mention one (keyword lookup). Reserve the spots (`used += people`) and create
     a `Referral` with distance.
   - Reply (`ai.compose("redirect", …)` in their language): site name, address, distance, hours, spots left, and a maps link
     `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lon>`. State Farm claim sites add "bring your policy number if you have it".
   - Nothing fits → referral `unrouted`, reply "We're finding you a place; a coordinator will text you", and show it in red in the UI.
3. **Re-route:** when `refresh_safety` marks a site unsafe, every `routed` referral there gets re-routed (excluding that site) and a
   "Change of plan: … lost power / is flooding. Go to … instead." text is sent. Status → `rerouted`.
4. Emit `resources.changed`, `referral.changed`.

## Acceptance
- Harvey hour 0: "Bayou Community Center Shelter" is `unsafe` (inside a flood band) and never chosen.
- "our apartment flooded, 2 kids, need a dry place" → routed to the nearest safe shelter or cbre_help_site, with 3 spots reserved.
- Approving OFFER_HELP_SITE for Galleria Medical Offices adds a `cbre_help_site` that later referrals can be routed to.
- Stepping to a step where a site's substation goes down re-routes its referrals and sends change-of-plan texts.
