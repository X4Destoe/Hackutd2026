# Lifeline PRD: reference pack for humans and AI agents

**Lifeline** (working name) is one engine that predicts how a disaster cascades through a city's
infrastructure, with two views on top of it:

- **State Farm view:** finds every affected policyholder, contacts them through Photon (text, iMessage
  or voice), and routes them to the help they need right now. Nobody is overlooked.
- **CBRE view:** predicts which commercial buildings fail next and what that costs, executes
  approved fixes, and turns safe buildings into help sites for State Farm customers.

## How to read this (AI agents: follow this exactly)

Read **only** these, in order:

1. `00-overview.md`: what we're building, why, the demo story, and scope. Everyone reads it once per task.
2. `02-contracts.md`: every shared type, API route, event and ID format. Everyone reads it.
   **If code and this file disagree, this file wins.**
3. `modules/<your-module>.md`: your module only. It lists exactly what you own, what you
   consume, what you must expose, and how to prove it works.

Read the rest only when your task says so:

| File | Read it when |
|---|---|
| `01-architecture.md` | You touch app wiring, the repo layout, env vars, run commands or deploy |
| `03-data-and-scenario.md` | You work on seed data, the storm timeline, or the simulated crowd |
| `04-build-plan.md` | You plan or reassign work (humans, the planning agent) |
| `plan.md` | Machine-readable task list for `./comms plan` (comms repo) |
| `modules/*.md` (others) | Never. Read the other module's `INTERFACE.md` in code instead |

## Module index

| Module file | Side | One-line job |
|---|---|---|
| `modules/core.md` | backend | Shared schemas, in-memory store, event bus, sim clock, app wiring |
| `modules/scenario.md` | backend | Seed data loaders, storm timeline player, simulated crowd |
| `modules/cascade.md` | backend | Dependency graph and failure propagation, plus *predicted* failures |
| `modules/ai.md` | backend | Provider-agnostic LLM gateway (Claude, OpenAI, Gemini, or rules) |
| `modules/messaging.md` | backend | Photon adapter, simulator channel, inbound webhook, voice |
| `modules/outreach.md` | backend | Who to alert, when; text, then call, then unreached list; AI intake chat |
| `modules/triage.md` | backend | Priority score, tiers, contact deadlines (SLAs), aging, case lifecycle |
| `modules/resources.md` | backend | Help sites, nearest-fit routing, capacity reservation, help-site re-routing |
| `modules/dispatch.md` | backend | Claims adjuster matching and accept/pass over Photon |
| `modules/portfolio.md` | backend | CBRE buildings, action plans, work orders, help-site offers |
| `modules/impact.md` | backend | Dollar impact: insured loss, SLA exposure, cost avoided, KPIs |
| `modules/web-shell.md` | frontend | App shell, routing, API client, live events hook, design tokens, PWA |
| `modules/command-center.md` | frontend | State Farm operations view |
| `modules/portfolio-view.md` | frontend | CBRE view |
| `modules/mobile-pwa.md` | frontend | Customer help card + adjuster field view (phone, installable) |
| `modules/demo-console.md` | frontend | Scenario controls, phone simulator, live event log |

## Status

`DRAFT`. The team reviews it in TASK-001. Then `02-contracts.md` changes to `Status: FROZEN`,
and from then on changes need a line in the comms repo's `docs/DECISIONS.md`.
Items marked **VERIFY** could not be confirmed while writing (no network access to those docs).
Each one has a first-hour task in `plan.md`.
