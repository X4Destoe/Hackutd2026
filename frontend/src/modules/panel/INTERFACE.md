# Panel public interface
Default export `Panel({onClose?})` renders the contents of the app's portfolio aside. Import from the module root only. UIProvider and QueryClientProvider are required above it.

Shared useUIStore controls panelView, selectedBuildingId, and layers. Map selection calls selectBuilding(id); the panel renders the selected building. API data comes from shared query hooks. This task owns overview/building list/building detail. Other views remain explicit placeholders for TASK-032/033.

Search matches building or tenant names, Enter selects the first match. Buildings default to current scenario city and descending net exposure. Unknown financial values never become zero placeholders. Financial arithmetic stays server-side; bar widths are visual normalization only. ScenarioMeta lacks step narratives and PortfolioSummary lacks insurance totals, so these are not fabricated; insurance recovery appears in each building's waterfall.

Plan actions use MGR-01 as the demo manager; no mutation retry or silent approval is performed. Requests show success/error status and await query refresh. Tenant notice generation creates a report for review, not a send operation. Work orders and offer-help actions remain owned by their tasks.
