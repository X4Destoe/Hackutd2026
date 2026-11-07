# AGENTS.md - this repo is CODE ONLY

AI agents: all coordination (who you are, what work is assigned to you, messages,
contracts) lives in the separate comms repo, cloned next to this one:

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
- Code against `../Agent-Communication-/docs/CONTRACTS.md` and other modules' `INTERFACE.md` only.
- Never add coordination files (tasks, status, inbox) here.
- Never commit secrets or `.env` - use `.env.example`.
