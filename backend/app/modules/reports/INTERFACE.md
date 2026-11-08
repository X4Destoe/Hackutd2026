# reports public interface

Import `from app.modules import reports`. Spec: `docs/prd/modules/reports.md`.

| Function | What |
|---|---|
| `generate(kind, building_id=None, send=False) -> Report` | `executive_summary` (portfolio) or `tenant_notice` (needs `building_id`; `send=True` also texts a short notice to each tenant contact). Stores the report, emits `report.created {report_id, kind}`. Bad kind / missing building -> `ValueError` (422). |
| `html(report_id) -> str` | printable page (escaped; `@media print`; "Print / Save as PDF" button). Unknown id -> 404. |

Routes: `POST /api/reports {kind, building_id?, send?}`, `GET /api/reports` (newest first), `GET /api/reports/{id}/html`.
`send` is an additive, optional field (default false).

- Numbers come only from module data (`impact.summary/latest/impact_for`, plans, work orders, resources, referrals in the store).
  The executive summary's bottom line uses the same totals as `/api/portfolio/summary`.
- `ai.write_report` adds an optional narrative paragraph only when a real LLM provider is configured; the structured report
  is complete without it.
- Sections appear only when there is data (work orders after TASK-021, community after TASK-024).

Reliability rules: unknown live financial inputs reject generation with422 before any report is saved or text sent. Tenant instructions come only from approved/executing actions whose deadline has not passed; proposed and completed actions do not generate new instructions. The printable document distinguishes recorded approvals/completion from unapproved plans. Optional send=True texts the actual approved asks and contact details once per unique existing tenant contact; a configured non-loopback APP_BASE_URL adds a printable link. Localhost links are omitted. Generation is not a delivery receipt; inspect message statuses. Report asks are deterministic and are not rewritten by an LLM.
