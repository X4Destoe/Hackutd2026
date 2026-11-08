# Module: reports (`backend/app/modules/reports/`)

**Skills:** backend, docs, ai-integration · **Read also:** `00-overview.md` §3 step 6

## Job
One-click documents that make the output **actionable for people outside the app**:
- **Executive summary** (portfolio): the disaster, total gross/net exposure, the top 5 at-risk buildings with drivers, plans approved and
  dollars avoided, missed actions ("would have saved"), work-order status, community help sites offered, and referrals served.
- **Tenant notice** (per building): what's happening, what management is doing, what the tenant must do and by when, and a contact.

## Owns
`backend/app/modules/reports/**`

## Interface
```python
def generate(kind: ReportKind, building_id: str | None = None) -> Report   # markdown; emits report.created
router  # POST /api/reports, GET /api/reports, GET /api/reports/{id}/html
```
- Facts come from `impact.summary()`, `impact.impact_for`, `actions` (plans, work orders), `resources` (sites, referrals).
- The body comes from `ai.write_report(kind, facts)` (an LLM polishes the narrative). The template fallback must produce a complete,
  good-looking report on its own. **Numbers always come from facts, never from the LLM.**
- `/html`: a printable HTML page (simple CSS, `@media print`). The browser's "Save as PDF" is the PDF path. No PDF library needed.
- "Send tenant notice" in the UI = `generate("tenant_notice", b)`, then `messaging.send` a short version to each tenant contact.

## Acceptance
- With `LLM_PROVIDER=none`, both report kinds render with correct totals that match `/api/portfolio/summary`.
- `/api/reports/{id}/html` prints cleanly on one or two pages.
