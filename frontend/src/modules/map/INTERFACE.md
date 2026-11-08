# map public interface

`import MapView from './modules/map'` (default export, mounted in `App.tsx`'s map slot). Spec: `docs/prd/modules/map.md`.

- Reads only shared hooks: `useDemoState`, `useScenarios`, `useBuildings`, `useImpact`, `useUtilities`, `useOverlays(hour)`, `useTimeline`,
  `useSetHour`; and the shared UI store (`selectedBuildingId`, `selectBuilding`, `layers`). Live updates arrive through the shared SSE
  invalidation, so building colors follow `impact.updated` without extra code.
- Basemap: `VITE_MAP_STYLE` or OpenFreeMap "liberty" (free, no key); after 5 s without it, a plain background (labels off).
- Built with `maplibre-gl` 4.7.1 directly (not react-map-gl): one map instance, one animation loop, `setData` only when data changes.

## Layers (`style.ts`)
| Layer ids | Draws | Panel toggle |
|---|---|---|
| `water-fill`, `water-edge` | `flood_water` / `surge_water` bands by depth; forecast = purple dashed | hazard |
| `snow-fill`, `snow-edge` | `snow_ice` area (cold blue tint) | hazard |
| `wind-fill`, `wind-edge`, `track` | `wind_swirl` rings, `forecast_cone` track | hazard |
| `buildings`, `buildings-approved`, `buildings-label` | risk color, radius ∝ √value (8–22 px), selected outline, green ring when approved, "name · $net" at zoom ≥ 9.5 | buildings |
| `power`, `link` | substations (red, pulsing when down), dashed line from the selected building to its substation | power |

## For TASK-030 (snow particles, surge waves, wind rotation, help-site pins)
Add your layers to `LAYERS`/`TOGGLES` in `style.ts` and hook into the existing `requestAnimationFrame` loop in `index.tsx`
(keep one loop, ≤ 400 particles). The `hazard` source already holds every overlay feature with `properties.style`, `.intensity`
and `.forecast`. Help sites: add a `help` source fed by `useResources(city)`.
