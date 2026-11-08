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

## Run (backend)
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"            # add ".[ai]" for Claude/OpenAI/Gemini
uvicorn app.main:app --reload --port 8000     # API docs at http://localhost:8000/docs
pytest                              # all module tests + end-to-end smoke
```
Configuration: copy `.env.example` to `backend/.env` (optional, everything works blank).
Frontend: see `docs/prd/modules/web-shell.md` (React + Vite, `npm run dev`).
