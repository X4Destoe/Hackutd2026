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
