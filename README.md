# Operation Storm

**See the disaster coming. Know what it will cost your business. Act before it hits.** HackUTD 2026, built for
**CBRE** (primary), **Photon** and **State Farm**.

A CBRE portfolio manager watches a real disaster (Hurricane Harvey, Winter Storm Uri, Hurricane Ian) play across a map of
their buildings. Each building shows the **dollars at risk** and why: flood depth, power cascade, tenant SLAs and insurance.
A **Fix-First** list ranks actions by money saved per dollar. One click approves a plan, which texts tasks to on-site staff and
notices to tenants through Photon. Residents in the area text in and are **sent to safe, open help sites**, including CBRE
buildings offered to the community.

- **Clickable prototype:** [`demo/operation-storm-demo.html`](demo/README.md) (open it in a browser)
- **Product spec (reference pack for the team and AI agents):** [`docs/prd/`](docs/prd/README.md)
- **Team / agent coordination:** [Agent-Communication-](https://github.com/X4Destoe/Agent-Communication-)

## Run it on your computer

About 10 minutes the first time. You will open **two terminals**: one runs the backend (the API), the other runs the
frontend (the web page). Both must stay open while you use the app.

> Every command below starts with `cd ~/Hackutd2026/...`, so it works **no matter which folder your terminal is in**.
> If you put the project somewhere other than your home folder, replace `~/Hackutd2026` with that path.

### Step 1 - check you have the tools (once)

Open a terminal (macOS: **Terminal** app, or in VS Code **Terminal → New Terminal**; Windows: **PowerShell**) and run:

| Tool | Check (macOS / Linux) | Check (Windows) | Need | If missing |
|---|---|---|---|---|
| git | `git --version` | `git --version` | any | macOS: run `xcode-select --install`; Windows: [git-scm.com](https://git-scm.com/download/win) |
| Python | `python3 --version` | `py --version` | **3.11 or newer** | [python.org/downloads](https://www.python.org/downloads/) |
| Node.js | `node --version` | `node --version` | **v20 or newer** | [nodejs.org](https://nodejs.org) (LTS), or macOS `brew install node` |

After installing anything, **close and reopen** the terminal (and VS Code) so it is found.

### Step 2 - get the code (once)

**First time (you do not have the folder yet):**

macOS / Linux:
```bash
cd ~ && git clone https://github.com/X4Destoe/Hackutd2026.git
```
Windows (PowerShell):
```powershell
cd $HOME; git clone https://github.com/X4Destoe/Hackutd2026.git
```

**Already cloned?** (`git clone` says `destination path 'Hackutd2026' already exists`) Don't clone again. Just update it:
```bash
cd ~/Hackutd2026 && git checkout main && git pull
```

**Open it in VS Code:** **File → Open Folder…** → pick the `Hackutd2026` folder in your home folder → Open.
(The `code` terminal command is optional. If you get `command not found: code`, ignore it and use File → Open Folder.)

### Step 3 - Terminal 1: start the backend

macOS / Linux, first time (installs packages, then starts the server):
```bash
cd ~/Hackutd2026/backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]" && uvicorn app.main:app --reload --port 8000
```
Windows (PowerShell), first time:
```powershell
cd $HOME\Hackutd2026\backend; py -m venv .venv; .venv\Scripts\Activate.ps1; pip install -e ".[dev]"; uvicorn app.main:app --reload --port 8000
```

**It worked when** the last lines say `Uvicorn running on http://127.0.0.1:8000` and `Application startup complete`.
Leave this terminal open. (Optional check: http://localhost:8000/api/health shows `{"ok":true}`.)

### Step 4 - Terminal 2: start the frontend

Open a **second** terminal: in VS Code click the **+** at the top right of the terminal panel
(Windows/Terminal app: open a new window or tab).

macOS / Linux, first time:
```bash
cd ~/Hackutd2026/frontend && npm install && npm run dev
```
Windows (PowerShell), first time:
```powershell
cd $HOME\Hackutd2026\frontend; npm install; npm run dev
```

**It worked when** you see `Local: http://localhost:5173/`. Open **http://localhost:5173** in your browser.

### Next time (already installed)

Get the latest code, then the same two terminals without the install steps.

```bash
cd ~/Hackutd2026 && git pull
```
Terminal 1:
```bash
cd ~/Hackutd2026/backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
```
Terminal 2:
```bash
cd ~/Hackutd2026/frontend && npm install && npm run dev
```
Windows: Terminal 1 `cd $HOME\Hackutd2026\backend; .venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000`,
Terminal 2 `cd $HOME\Hackutd2026\frontend; npm install; npm run dev`.
(`npm install` is quick when nothing changed; keep it so new packages from `git pull` are picked up.)

**To stop:** click into each terminal and press **Ctrl+C**.

### Troubleshooting

| What you see | What it means / fix |
|---|---|
| `cd: no such file or directory: backend` (or `frontend`) | The terminal is not in the project. Use the full commands above (they start with `cd ~/Hackutd2026/...`) |
| `fatal: destination path 'Hackutd2026' already exists` | You already have the code. Skip cloning; run `cd ~/Hackutd2026 && git pull` |
| `cd: no such file or directory: /Users/.../Hackutd2026` | The code is not in your home folder. Clone it (Step 2) or `cd` to where you saved it |
| `zsh: command not found: code` | Harmless. Open the folder with VS Code → File → Open Folder. To enable `code`: Cmd+Shift+P → "Shell Command: Install 'code' command in PATH" |
| Prompt starts with `(base)` | Anaconda is active. Usually fine; if the backend install fails, run `conda deactivate` and repeat Step 3 |
| `python3: command not found` (Windows) | Use `py` instead of `python3` |
| PowerShell: `running scripts is disabled on this system` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then Step 3 again |
| `uvicorn: command not found` | The Python environment is not active. Run the "Next time" Terminal 1 command (prompt then shows `(.venv)`) |
| `npm: command not found` | Node.js is not installed (Step 1). Reopen the terminal after installing |
| `Address already in use` (port 8000 or 5173) | The app is already running in another terminal. Use that one, or press Ctrl+C there first |
| `git pull` says your local changes would be overwritten | You edited files. Run `git stash`, then `git pull` again (your edits are saved in the stash) |
| Page opens but numbers say "unavailable" | The backend is not running or crashed: look at Terminal 1 |
| Map is empty or looks old | Run the "Next time" commands (pull, restart both terminals), then reload the page |

### Optional
- **Just want to look?** Open `demo/operation-storm-demo.html` in a browser. No install needed.
- **Settings:** copy `.env.example` (repo root) to `backend/.env`. Everything works with it blank: texts are simulated and AI
  text uses built-in templates. Never commit `backend/.env`.
- **Real Photon texts:** see [`docs/REHEARSAL.md`](docs/REHEARSAL.md) and `backend/spikes/photon/PHOTON_NOTES.md`. The
  Photon credentials go only in `backend/.env`, never in chat or git.
- **AI provider:** `pip install -e ".[dev,ai]"`, then set `LLM_PROVIDER` and its key in `backend/.env`.
- **Tests:** Terminal 1 (environment active): `pytest`. Frontend build: `npm run build` in `frontend/`.
  Browser checks (both servers running): `npm run test:e2e:install` once, then `npm run test:e2e` in `frontend/`.

## Working demo

The React app includes a map, modeled loss estimates, approvals, technician updates, resident routing, help-site activation, printable reports, and a custom simulation builder. Choose Houston, Dallas, or Fort Myers (or randomize among them), then set a disaster and its effects.

Start with **simulated messaging** and `LIVE_FETCH=0` for a repeatable offline rehearsal. Buildings, money, capacities, and custom effects are illustrative; live alerts and forecasts are proxies, and missing inputs display Unknown. Real phone delivery requires a configured Photon bridge and credentials.

- [Measured demo walkthrough](docs/DEMO.md) and [rehearsal checklist](docs/REHEARSAL.md)
- [Track pitch and honest limitations](docs/PITCH.md)
- [Recorded simulator demo](docs/media/operation-storm-demo.mp4)
- [Integration checks](docs/INTEGRATION.md)

Re-record the backup with both servers running in simulator mode: `node docs/media/record-demo.cjs`. This requires Playwright, Chromium, and FFmpeg; `CHROMIUM_PATH`, `FFMPEG_PATH`, and `STORM_URL` can override defaults. The script resets the scenario, performs real API/UI actions, and resets again when finished.
