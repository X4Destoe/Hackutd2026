# 05 - Build plan (4 people + AI agents, 10–15 hours)

## 1. Principle: vertical slice first
By **hour 5**, one scenario (Harvey) must work end to end: map + flood overlay + colored buildings + Bayou Plaza money waterfall
+ approve → work order → simulated text. Everything after that is breadth (more scenarios, overlays, Photon live, help sites, reports).
A thin product that fully works beats a wide one that half works.

## 2. Lanes (each human runs 1–3 agents)
| Lane | Modules | Comms skills |
|---|---|---|
| A. Engine | core, impact, actions | backend, python, data |
| B. World data | scenarios (overlays, portfolio), resources data | data, python |
| C. Messaging + AI + State Farm | messaging (Photon), ai, resources, reports | api, ai-integration, backend |
| D. Frontend | web-shell, map, panel | frontend, typescript, ui-design |

## 3. Timeline
| Hours | Goal | Exit check |
|---|---|---|
| 0–1 | TASK-001: freeze contracts, publish plan. Photon spike. Skeletons (backend core, Vite shell) | Contracts FROZEN. A Photon text reaches a phone (or a fallback is decided) |
| 1–5 | **Slice:** Harvey data + impact + plans + approve + sim work order. Map with flood + buildings. Panel overview + building detail | Demo beats 1–5 work with the simulator |
| 5–9 | Breadth: Uri + Ian data and overlays (snow, surge, wind), Fix-First view, missed plans, Photon live, help sites + referrals, reports | Every beat in the demo script works |
| 9–11 | **Integration + tuning:** numbers tell the story, animations smooth, real-phone rehearsal | Demo runs twice under 3:30 |
| 11 | **Feature freeze** | |
| 11–13 | Polish, pitch slides, **record the backup video**, Devpost | Video recorded |
| 13–15 | Buffer, rehearse, submit | Submitted |

**Critical path:** core-contracts → core-runtime → harvey-data → impact-engine → actions-plans → actions-execute → e2e → demo-tuning.

## 4. Cut list if behind (cut from the top)
1. Eaton fire scenario (already stretch).
2. Reports → keep the executive summary only.
3. Ian scenario → keep Harvey + Uri (flood vs snow is the visual contrast that matters).
4. Help-site re-routing → keep routing only.
**Never cut:** colored $ map + waterfall + Fix-First + approve → text. That's the CBRE win.

## 5. Risks
| Risk | Mitigation |
|---|---|
| Photon API differs from what we assumed or is flaky | Hour-1 spike, adapter, simulator + phone simulator in the panel, backup video |
| Overlays look fake | Draw along real bayous/coast. Disclaimer chip. Animation sells it |
| Numbers feel arbitrary | Drivers + waterfall on screen. Constants in one file, shown in the appendix slide |
| Map animation is slow | One rAF loop, ≤ 400 particles, no per-frame `setData` |
| Scope creep | Cut list above. Stretch only after the demo runs twice |

## 6. Definition of done (every task)
Module acceptance items pass (pytest / `npm run build` + a manual check noted in the PR), `./comms check` passes, the PR says what
changed / how to test in 60s / what's next, and no files are touched outside the task's `files:`.
