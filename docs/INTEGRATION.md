# Integration

How the running app fits together, and the one test that walks the demo path across modules.
The comms repo is not available to every agent. This file is the handoff for that path.

## Run it

```bash
cd backend && python3 -m pytest tests_e2e -q
cd backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

`app.main` discovers each package under `app/modules`, mounts its `router` at `/api`, and calls `register()`.
On startup the lifespan loads `harvey_houston`. `POST /api/demo/reset` does that again and clears the in-memory store.
No `LLM_API_KEY` and no Photon bridge are required: `llm_provider` stays `templates` and `messaging_mode` stays `sim`.

## What calls what

| Step | Call | Module |
|---|---|---|
| Pick a storm | `POST /api/scenarios/{id}/load` | scenarios resets the store, seeds buildings, utilities, parties, emits `scenario.loaded` |
| Move the clock | `POST /api/timeline` with one of the scenario's `step_hours` | scenarios emits `timeline.changed`. impact recomputes dollars. resources refreshes site safety and re-routes anyone at a site that just became unsafe. actions rebuilds plans. |
| Read the money | `GET /api/impact`, `GET /api/portfolio/summary`, `GET /api/overlays` | impact and scenarios. The waterfall is `net = damage + rent + SLA + operations − insurance`, both per building and for the portfolio. |
| Approve | `GET /api/fix-first`, then `POST /api/plans/{id}/approve` | actions creates work orders and messaging sends the task texts on the simulator channel. impact hears `plan.changed` and the summary's `avoided_cents` moves. |
| Resident | `POST /api/demo/simulate-message` with a phone and a need | messaging calls `resources.route`. The reply names a safe, open site with room and a State Farm emergency claims adjuster. An unsafe site is never chosen. |
| Paper | `POST /api/reports` with `executive_summary` or `tenant_notice` | reports reads impact, plans, and the portfolio. `GET /api/reports/{id}/html` is the printable page. `send: true` on a tenant notice texts the building's tenant contacts. |

Money is integer USD cents. Hours are the scenario steps (−48, −24, −12, 0, +12, +48, +168), relative to impact.

## What the smoke test checks

`backend/tests_e2e/test_demo_smoke.py` loads every scenario, steps every hour, and checks the waterfall at each step.
Switching scenario has to return in under a second. The first hour that has a Fix-First plan is approved, and by impact
that approval has reduced net exposure and raised `avoided_cents`, with a work order and an outbound text.
A family of three is routed to an open site that `impact.site_safe` accepts (shelter in Houston, warmth in Dallas),
and the thread also names the emergency claims adjuster. During Ian's landfall the wind is over 74 mph at every
Fort Myers site, so the resident stays unrouted and is not sent to the beach. At +48h the same request goes to
an open inland site, never Beachside Rec Center. Both reports return printable HTML. Houston's flooded
Bayou Community Center Shelter is never the chosen site.

## Still outside this test

Map help-site pins and referral arcs belong to the map overlays. A real Photon handset is the rehearsal doc.
The under-3:30 click script is demo tuning, not this pytest.
