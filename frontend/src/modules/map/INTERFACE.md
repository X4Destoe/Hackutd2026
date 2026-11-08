# map public interface

`import MapView from './modules/map'` (default export, mounted in `App.tsx`'s map slot). Spec: `docs/prd/modules/map.md`.

- Reads only shared hooks: `useDemoState`, `useScenarios`, `useBuildings`, `useImpact`, `useUtilities`, `useOverlays(hour)`, `useTimeline`,
  `useSetHour`; and the shared UI store (`selectedBuildingId`, `selectBuilding`, `layers`). Live updates arrive through the shared SSE
  invalidation, so building colors follow `impact.updated` without extra code.
- Basemap: `VITE_MAP_STYLE` or OpenFreeMap "liberty" (free, no key); immediate local approximate roads/coast background; remote style is used only if its public JSON loads within 3.5 seconds. Tile failures return to the local style. No remote glyphs are needed for building labels.
- Built with `maplibre-gl` 4.7.1 directly (not react-map-gl): one map instance, one animation loop, `setData` only when data changes.

## Layers (`style.ts`)

| Layer ids                                            | Draws                                                                                                          | Panel toggle |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------ |
| `water-fill`, `water-edge`                           | `flood_water` / `surge_water` bands by depth; forecast = purple dashed                                         | hazard       |
| `snow-fill`, `snow-edge`                             | `snow_ice` area (cold blue tint)                                                                               | hazard       |
| `wind-fill`, `wind-edge`, `track`                    | `wind_swirl` rings, `forecast_cone` track                                                                      | hazard       |
| `buildings`, `buildings-approved`, `buildings-label` | risk color, radius ∝ √value (8–22 px), selected outline, green ring when approved, "name · $net" at zoom ≥ 9.5 | buildings    |
| `power`, `link`                                      | substations (red, pulsing when down), dashed line from the selected building to its substation                 | power        |

## For TASK-030 (snow particles, surge waves, wind rotation)

Add hazard motion to `LAYERS`/`TOGGLES` in `style.ts` and hook into the existing `requestAnimationFrame` loop in `index.tsx`
(keep one loop, ≤ 400 particles). The `hazard` source already holds every overlay feature with `properties.style`, `.intensity`
and `.forecast`. Help-site pins, capacity rings, unsafe marks, and referral arcs are `HelpLayer.tsx` (the `help` layer toggle). Do not add a second set of help pins.

## Integration follow-up (TASK-046)

Square building markers are accessible HTML buttons positioned by MapLibre. Their labels and selected/approved rings remain available with all external HTTPS blocked. `data-building-id`, `data-risk`, `data-approved`, and aria-pressed expose visible marker state. Root attributes data-map-ready/data-map-moving/data-basemap describe public readiness for browser checks. GPU building sources are retained for layer consumers, but duplicate GPU markers/labels are hidden. Missing impact is labeled unavailable rather than safe/$0.

Selecting through either map or panel recenters on the building. Reduced-motion users do not get the pulse loop. The offline context is approximate prototype geometry, not the real OSM snapshots (TASK-042 remains blocked separately). Real-service smoke command is in frontend/e2e/README.md; it resets an isolated demo before and after testing.

Basemap changes use `diff:false`; every style.load restores current source data and visibility before signaling readiness. Root data-water-rendered/data-power-rendered count actual rendered features for the style-swap acceptance test. The selected-building ResponseCard reads the same server plans and work orders as the panel, approves through the existing mutation, and labels avoided dollars as modeled. It never calls an LLM/feed synchronously or fabricates work-order delivery. The view-sync time is a client cache receipt time, not a hazard observation timestamp; live-source as-of metadata belongs to the live-feed module/UI.
