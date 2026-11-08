# Operation Storm PRD: reference pack for humans and AI agents

**Operation Storm**: *see the disaster coming, know what it will cost your business, act before it hits.*

A CBRE portfolio manager opens a map of their buildings. A real-world disaster (a flood, a hurricane, a winter
storm) plays across it with a visual overlay. Every building is colored by **dollars at risk**. Operation Storm answers the
question CBRE asked us: **"as a business, how is this affecting me, and what do I do about it?"** It does that with a
**Fix-First list** of actions, each justified by money saved per dollar spent. Approving an action sends tasks to
on-site staff and notices to tenants by text (Photon). People affected in the area are **redirected to the right
help** (shelters, State Farm claim sites, warming centers), and that includes CBRE buildings offered as help sites.

**See it first:** `demo/` in this repo is a clickable prototype of the whole flow (open `demo/operation-storm-demo.html`).
It is the **visual and behavioral reference**: match its look, layout and interactions. `demo/model.js` implements the
money formulas in `03` and is a good reference for the `impact` and `actions` modules. Don't copy the demo's code
structure, though. The real build is FastAPI + React per `01-architecture.md`.

## How to read this (AI agents: follow this exactly)

Every agent reads, in order:
1. `00-overview.md`: the product, the flow, the demo script, scope.
2. `02-contracts.md`: every shared type, route and event. **If code and this file disagree, this file wins.**
3. `modules/<your-module>.md`: the one your task's `goal:` line names.

Read the rest only when your task says so:

| File | Read it when |
|---|---|
| `01-architecture.md` | You touch wiring, layout, env vars, run commands |
| `03-data-and-scenarios.md` | You touch scenarios, the portfolio seed, money formulas, the action catalog, resources |
| `04-ui-spec.md` | You build any frontend piece |
| `05-build-plan.md` | You plan or reassign work |
| `plan.md` | Machine-readable task list for `./comms plan` (comms repo) |

## Module index

| Module | Side | Job |
|---|---|---|
| `modules/core.md` | backend | Shared schemas, in-memory store, event stream, app wiring |
| `modules/scenarios.md` | backend | Real-disaster presets, phases and timeline, hazard overlays, portfolio seed |
| `modules/impact.md` | backend | Hazard exposure per building, power cascade, **dollar impact** |
| `modules/actions.md` | backend | Action catalog, plans with ROI, **Fix-First** ranking, approve → work orders |
| `modules/ai.md` | backend | Provider-agnostic LLM gateway (Claude/OpenAI/Gemini) with template fallback |
| `modules/messaging.md` | backend | Photon adapter + simulator: technician tasks, tenant notices, resident chats |
| `modules/resources.md` | backend | State Farm piece: help sites, safety from the hazard engine, redirecting people |
| `modules/reports.md` | backend | Executive summary + tenant notice, printable |
| `modules/web-shell.md` | frontend | UTD-style layout, API client, live events, design tokens |
| `modules/map.md` | frontend | MapLibre map, risk-colored buildings, **animated hazard overlays**, timeline |
| `modules/panel.md` | frontend | Left panel: overview, Fix-First, building detail, work orders, resources, reports |

Status: `DRAFT` until TASK-001 freezes `02-contracts.md`. Items marked **VERIFY** need a real check in hour 1.
