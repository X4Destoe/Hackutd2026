# 04 - Build plan (4 people, 24 hours, many AI agents)

## 1. How work flows

1. **TASK-001** (comms repo, already exists): one planning agent plus a human read this pack, fix anything wrong, set
   `02-contracts.md` to `Status: FROZEN`, run `./comms plan ../Hackutd2026/docs/prd/plan.md --dry-run`, then publish it.
   The tasks are routed to agents by skill automatically.
2. Every agent reads `docs/prd/README.md` → `00-overview.md` → `02-contracts.md` → its own `modules/<x>.md`, then works its
   queue (`./comms sync`, `./comms start`).
3. Humans: review/merge PRs **at least once an hour** (merging is the bottleneck), answer `./comms inbox --person <you>`,
   and test on real phones.

## 2. Human lanes (each human runs 1–3 agents in their lane)

| Lane | Modules | Suggested agent skills |
|---|---|---|
| A. Engine | core, scenario, cascade, impact | backend, python, data |
| B. Comms + AI | messaging (Photon), ai, outreach | backend, api, ai-integration |
| C. Operations | triage, resources, dispatch, portfolio | backend, python, api |
| D. Frontend + design | web-shell, command-center, portfolio-view, mobile-pwa, demo-console, design | frontend, typescript, ui-design, mobile |

Lanes are a suggestion. The comms router assigns by skill and load. Whoever finishes early takes the next ready task.

## 3. Timeline (H = hours since hacking starts)

| When | Goal | Exit check |
|---|---|---|
| H0–1 | Kickoff. **Photon spike** (real text to a phone and reply received through the tunnel). TASK-001 freeze. TASK-002 skeleton. Web shell scaffold. Ask CBRE in Discord for their data | Contracts FROZEN. Photon round trip works or a fallback is decided |
| H1–6 | **Vertical slice**: core → seed → cascade load-shed → one customer alerted (sim + 1 live phone) → reply → case with tier on the map | Live phone gets an alert, the reply shows on the Command Center map |
| H6–14 | **Feature build**: prediction + chains, triage aging/deadlines, escalation ladder, routing + re-routing, dispatch ACCEPT/PASS, portfolio plans + approve, impact, all five frontend screens | Every module's acceptance tests pass |
| H14–18 | **Integration**: e2e smoke, scenario tuning so the demo beats land, rehearse with real phones | The demo script runs end to end twice |
| H18 | **Feature freeze.** Only fixes and polish after this | |
| H18–21 | Polish (design pass), pitch deck, **record the backup demo video**, Devpost write-up | Video recorded |
| H21–24 | Rehearse 3+ times, buffer for disasters, submit | Submitted with 1h to spare |

**Critical path:** core-contracts → core-runtime → cascade-graph → triage → outreach → resources → e2e → demo-tuning.
Anything blocking it gets p1 and a human's attention first.

## 4. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Photon beta API differs from our assumptions or has no voice | Medium | Hour-1 spike. Adapter interface. Text fallback for voice. Flag to the team early |
| Photon or venue Wi-Fi fails on stage | Medium | `MESSAGING_MODE=sim` + demo console phone simulator. Backup video. Phone hotspot |
| LLM key runs out or the call is slow | Medium | Rules fallback (tested). 8s timeout. LLM never in the tick's critical path |
| Too much scope for 24h | High | MVP list in `00-overview.md` §7. Feature freeze at H18. Stretch only after the demo runs end to end |
| Frontend/backend drift | Medium | Generated API types. Contracts frozen. SSE event table |
| Agents duplicate work or edit the same files | Low | comms CLI: assignment, file overlap blocking, single owner per module |
| CBRE releases data we didn't plan for | Medium | Adapter in `scenario`. Synthetic data keeps working. Map their fields onto `Building` |
| Webhook needs a public URL | High | cloudflared quick tunnel. Re-register the URL in the Photon dashboard each restart (note it in REHEARSAL.md) |

## 5. Definition of done (every task)
- The module acceptance items it covers pass (`pytest backend/app/modules/<x>` / `npm run build` + a manual check noted in the PR).
- `./comms check` passes. PR description: what changed, how to test in 60 seconds, what the next agent needs.
- No contract changes without a decision. No edits outside the task's `files:`.

## 6. Submission checklist (H21+)
- Devpost: title, tagline, the 3-track story (§9 of the overview), screenshots, the video link, the repo link, built-with list.
- README: one-command run, demo script, architecture diagram, team.
- Make sure the product repo is clean: no secrets, `.env.example` only. This pack stays in `docs/prd/` (it shows the planning).
