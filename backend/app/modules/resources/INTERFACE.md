# resources public interface

Import `from app.modules import resources`. Spec: `docs/prd/modules/resources.md` (the State Farm piece).

| Function | What |
|---|---|
| `route(party_id, text) -> Referral` | classify (ai), locate, pick the nearest **open + safe** site of a matching type with room, reserve `people` spots, text the resident (their language) with address, distance, hours, spots left and a Google Maps link. Urgent medical: 911 guidance first, flagged `URGENT` in history. Nothing fits: `unrouted` + "a coordinator will text you". |
| `refresh_safety() -> [changed ids]` | per step: `unsafe` if `impact.site_safe(...)` is False right now (present hazard, power), `full` if used ≥ capacity, else `open` (`closed` stays). Referrals at sites that became unsafe are re-routed with a change-of-plan text (`rerouted`, spots released at the old site), or `unrouted` if nothing fits. |
| `register_site(resource) -> Resource` | add a site (actions: OFFER_HELP_SITE -> `cbre_help_site`); status computed immediately |
| `seed()` | reload `data/resources.json` after a scenario load (store.reset() clears sites) |

Routes: `GET /api/resources?city=`, `GET /api/referrals` (newest first). Events: `resources.changed {changed_ids}`, `referral.changed {referral_id, status, resource_id}`.
Runs on `scenario.loaded` (seed) and `timeline.changed` (refresh_safety).

- Inbound resident texts come from **messaging**, which already calls `route()`; this module registers no inbound handler (no double routing).
- Location (demo simplification): a neighborhood named in the text (`PLACES`), else the scenario's default flooded neighborhood
  (Houston Memorial, Dallas Oak Lawn, Fort Myers Beach) with a small deterministic offset per resident.
- Repair vendors get "contact" wording, not "go to" (they come to you).
