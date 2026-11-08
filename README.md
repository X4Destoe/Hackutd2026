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
- **Pitch map:** [`docs/PITCH.md`](docs/PITCH.md)

## Demo flow

Reset, then leave Hurricane Harvey at forecast (−48h). The header net exposure is about **$8.05M**. Open Bayou Plaza, then Fix-First, and approve the top card (about **$32.8k**, saves about **$991.96k**). Avoided rises and the Houston engineer and the tenants get texts. Scrub to impact (0h): one Houston shelter is marked unsafe and is not used. A resident text asking for a dry place for 2 kids is sent to George R. Brown Convention Center and to the State Farm claims desk. Switch the scenario menu to Winter Storm Uri to show the same engine on a different storm. The click-by-click script with the API figures is `docs/DEMO.md` on the demo-script branch until that file is on main.

## Architecture

The backend is FastAPI. `app.main` loads each package under `backend/app/modules`, mounts its router at `/api`, and the modules talk through the in-memory store and the event bus (SSE at `/api/events`). Scenarios own the timeline and the hazard lookup. Impact turns that into dollars. Actions turn an approval into work orders and texts. Messaging delivers those texts, through the simulator or the Photon bridge. Resources routes residents to help sites that are safe at the current hour. Reports render the same numbers. The frontend is Vite and React: the map and the left panel read the shared API client and refresh from the event stream. Money is integer cents. No LLM key and no Photon credentials are required.

## Run it (VS Code terminal)

You need **Python 3.11+**, **Node.js 20+** and **git** (check with `python3 --version`, `node --version`; on Windows use
`py --version`). No Node? macOS: `brew install node`, or download the LTS installer from nodejs.org.

### Step 0 - get the code and open it in VS Code (once)

```bash
cd ~
git clone https://github.com/X4Destoe/Hackutd2026.git
code Hackutd2026        # or: VS Code → File → Open Folder… → Hackutd2026
```
Every command below runs **from inside the `Hackutd2026` folder**. VS Code's terminal starts there when you open the folder;
check with `pwd` (it should end in `/Hackutd2026`). Already cloned? `cd` into it and run `git pull`.
If your prompt starts with `(base)` (Anaconda), run `conda deactivate` first so the project uses its own Python environment.

The app is two processes, so use **two terminals** (Terminal → New Terminal, then the split button). Paste each block as a whole:
the lines are joined with `&&`, so if one step fails the rest stop instead of running in the wrong folder.

### Terminal 1 - backend (API on http://localhost:8000)

macOS / Linux:
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]" && uvicorn app.main:app --reload --port 8000
```
Next time (already installed): `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`

Windows (PowerShell):
```powershell
cd backend; py -m venv .venv; .venv\Scripts\Activate.ps1; pip install -e ".[dev]"; uvicorn app.main:app --reload --port 8000
```
If PowerShell says running scripts is disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.

You should see `Uvicorn running on http://127.0.0.1:8000`. Check http://localhost:8000/api/health (`{"ok":true}`) or the API
docs at http://localhost:8000/docs.

### Terminal 2 - frontend (app on http://localhost:5173)

```bash
cd frontend && npm install && npm run dev
```
Open **http://localhost:5173**. The frontend forwards `/api` to the backend, so keep Terminal 1 running.

### Optional
- **Settings:** copy `.env.example` (repo root) to `backend/.env`. Everything works with it blank: texts are simulated and AI
  text uses built-in templates. Never commit `backend/.env`.
- **Real Photon texts:** put the Photon Spectrum project ID, project secret and webhook secret in `backend/.env` (see
  `backend/spikes/photon/PHOTON_NOTES.md`) and set `MESSAGING_MODE=photon`. With those blank, texts stay on the simulator.
- **AI provider:** `pip install -e ".[dev,ai]"`, then set `LLM_PROVIDER` and its key in `backend/.env`.
- **Tests:** in Terminal 1 (venv active) run `pytest`; frontend type-check and build: `npm run build` in `frontend/`.
- **Just want to look?** Open `demo/operation-storm-demo.html` in a browser. No install needed.

### Troubleshooting
| Problem | Fix |
|---|---|
| `cd: no such file or directory: backend` | You are not in the project folder: `cd ~/Hackutd2026` (or wherever you cloned it), then retry |
| `does not appear to be a Python project` | Same cause: run it from `Hackutd2026/backend`, not your home folder |
| `python3: command not found` (Windows) | Use `py` instead of `python3` |
| `uvicorn: command not found` | The venv is not active: run the `activate` line again (prompt shows `(.venv)`) |
| `Address already in use` / port 8000 or 5173 busy | Stop the other server (Ctrl+C in its terminal) or change `--port` |
| Page loads but numbers say "unavailable" | The backend is not running, or crashed: look at Terminal 1 |
| Map stays on the plain local backdrop | Remote tiles did not load. The app still draws buildings, hazards and help sites on that backdrop. Check the network, then reload |
