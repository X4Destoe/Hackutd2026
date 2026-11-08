# Shared UI
Import primitives from `shared/ui`. Buttons forward refs for Radix triggers. Dialog, tooltip, tabs, dropdown menu and scroll area use Radix keyboard/focus behavior; style new parts with the shared tokens. All corners stay square.

`UIProvider` wraps the application. `useUIStore()` exposes `panelView`, `selectedBuildingId`, `selectBuilding(id)`, `layers`, `toggleLayer(key)` and `setAllLayers(boolean)`. Selection and layers are local UI state, not API state. Format cents and relative hours using `shared/format`.

TASK-027 deliberately ships shell placeholders. TASK-028 owns API and events; map and panel tasks replace their named slots in App. Scenario selection and money totals remain disabled/empty until API wiring. No synthetic metrics are presented as live data.
