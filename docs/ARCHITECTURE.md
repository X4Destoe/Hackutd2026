# Resolve AI architecture

Resolve AI is a local-first decision and recovery workflow for synthetic
commercial property incidents and catastrophe assistance. The application
connects observations, risk estimates, financial scenarios, qualified response
recommendations, human approval, communications and a durable event history.

## Runtime

- `src/app/`: FastAPI composition root, database/session setup, seed/reset,
  routers, and static service configuration.
- `src/shared/`: contracts mirrored from the coordination repository's frozen
  `docs/CONTRACTS.md`.
- `src/modules/{portfolio,dispatch,communications,assistance,dashboard}/`:
  isolated feature modules. Each exposes its public interface in `INTERFACE.md`.
- `web/`: React and TypeScript client. The Vite development server proxies `/api`
  to FastAPI.
- SQLAlchemy uses SQLite for local demos and PostgreSQL when `DATABASE_URL` is
  configured. Currency is integer cents.

## Request and event flow

`observation or intake -> incident -> risk and impact estimate -> eligible
expert proposal -> human approval -> communication -> acknowledgment or
response -> state update -> append-only audit event`.

The simulator and Photon adapter feed the same inbound message processor. The
simulator is identified as simulated in stored records and the UI. Photon Beta
2.0 uses its own API host, bearer credentials, request schemas and documented
webhook signature verification; no Stable/Spectrum SDK or webhook contract is
mixed in. Live calls are disabled without credentials. Provider acceptance,
delivery, recipient acknowledgment and completed work remain distinct states.

## Decision services

- Operational risk is a transparent trend/threshold estimator over synthetic
  sensor readings. It reports assumptions, data confidence, and projected
  threshold time only when the sample supports an estimate.
- Financial totals use integer cents and explicit hours/rates. Scenario controls
  recalculate the same service used by the API.
- Dispatch treats qualifications, availability, capacity, safety review and
  approved commitments as hard constraints. OR-Tools is optional; the fallback
  preserves these constraints and identifies itself. Catastrophe assistance
  sorts by urgent need and wait time rather than commercial cost.
- Structured message extraction validates against a Pydantic schema. A local
  deterministic parser is labeled as a simulator; it cannot approve claims,
  safety actions or assignments.

## Trust and limits

Only synthetic people, buildings and operational readings are seeded. Maps use
approximate regional coordinates and remain useful without external tiles.
The prototype is not a trained predictive maintenance model, insurer claims
system, safety authority, or source of real-world savings claims. A human must
approve safety-critical assignments and response actions.
