# AGENTS.md - this repo is CODE ONLY

**What we're building:** Lifeline. The full spec is in [`docs/prd/`](docs/prd/README.md). Read `docs/prd/README.md` first.
It tells you exactly which files to read for your task (the overview, the contracts, and your one module file).

AI agents: all coordination (who you are, what work is assigned to you, messages)
lives in the separate comms repo, cloned next to this one:

```
../Agent-Communication-/    https://github.com/X4Destoe/Agent-Communication-
```

Missing it? `git clone https://github.com/X4Destoe/Agent-Communication-.git ../Agent-Communication-`

Then read `../Agent-Communication-/AGENTS.md` and start every turn with:

```bash
cd ../Agent-Communication- && ./comms sync
```

Rules that apply in this repo:
- Only work on a task you started with `./comms start`, on its branch `feat/TASK-NNN-...`, touching only its `files:`.
- Never push to `main`, never merge your own PR. Open a PR and fill in the template.
- Code against `docs/prd/02-contracts.md` (in code: `backend/app/shared/`, generated `frontend/src/shared/api-types.ts`)
  and other modules' public interfaces only. Never import another module's private files.
- Never add coordination files (tasks, status, inbox) here.
- Never commit secrets or `.env`. Use `.env.example`.
