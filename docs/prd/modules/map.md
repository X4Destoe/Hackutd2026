# Module: map (`frontend/src/modules/map/`)

**Skills:** frontend, typescript, ui-design · **Read also:** `04-ui-spec.md` (esp. §5 final visual decisions), visual reference `demo/`; `04` §1 and §3 · **Uses:** web-shell `shared/*`

## Job
The big interactive map on the right: risk-colored buildings, **animated hazard overlays** that make the disaster
feel real (rising blue water, falling snow, swirling wind), the power grid, help sites, and the **vertical timeline control**.

## Owns
`frontend/src/modules/map/**` (default export `MapView`).

## Components
- `MapView`: `react-map-gl/maplibre` map, style from `VITE_MAP_STYLE` or the default (**VERIFY** a free style URL: OpenFreeMap "liberty"
  or Carto Positron). On `scenario.loaded`, fly to the scenario center/zoom. Clicking a building sets `selectedBuildingId` and `panelView='building'`.
- `HazardLayers`: GeoJSON source from `useOverlays(hour)`. One layer group per `properties.style`:
  - `flood_water` / `surge_water`: fill by `intensity` (step color ramp of light → deep blue). Animate with a `requestAnimationFrame`
    loop that eases `fill-opacity` (0.35 ↔ 0.55, 2.5s period). When the hour changes into impact, tween the new layer's opacity 0 → target
    over 800ms ("rising"). `surge_water` adds a moving line pattern (offset dash animation) for waves.
  - `snow_ice`: white/ice-blue fill (opacity 0.25–0.45 by intensity) + `<SnowCanvas>`, an absolutely positioned `<canvas>` over the
    map drawing about 300 falling flakes, clipped to the overlay's bounding box projected to screen (recompute on move). Pauses when the layer is hidden.
  - `wind_swirl`: concentric ring fills with low opacity, rotated by updating a rotating-points source every frame (or a CSS-rotated SVG marker
    at the storm center). Plus a track `LineString` if present.
  - `forecast_cone`: dashed purple line + 10% purple fill.
  - `fire_smoke` (stretch): orange radial fill + ember particles (reuse the SnowCanvas engine with upward drift).
- `BuildingLayer`: circles (radius ∝ √replacement value, 8–22px), fill by `useImpact(hour)` risk color, white stroke. The selected one gets a thick
  outline + pulse. Approved ones get a green dashed ring + ✓ symbol. Labels "name · $1.65M" at zoom ≥ 10. Hover tooltip: name, net $, risk, top driver.
- `PowerLayer`: ⚡ substations (red and pulsing when down). On select or hover, a line from the building to its substation.
- `HelpLayer`: pins by type (icons). Unsafe ones get a red ✕. Capacity ring. Referral animation: a short-lived arc from the resident point to the site on `referral.changed`.
- `WorkOrderBadges`: a small 🛠 count badge on buildings with open work orders. It turns green on done and red on blocked.
- `TimelineControl`: a vertical segmented control on the map's left edge (like UTD's floor selector) listing the scenario's `step_hours`
  ("−48h", …, "+7d") with phase color bands and ▲▼ arrows. Click → `setHour`. ←/→ keys too.
- `MapTools`: right-edge buttons (home = fly to the scenario, layers popover bound to the layer toggles, zoom ±, legend).
- `Legend` (bottom right): $ color scale + the active hazard's intensity ramp. `Disclaimer` chip (bottom left): "Footprints approximate · illustrative".

## Performance
60fps on a laptop. At most 1 rAF loop for all animations. Particles ≤ 400. Don't re-create sources per frame (use `setData` only on hour change).

## Acceptance
- Switching among the 3 scenarios shows 3 visibly different hazard animations.
- Stepping −48 → 0 in Harvey visibly "raises" the water. Building colors update within 1s via events.
- Clicking a building opens its detail in the panel. Approving a plan turns its ring green without a reload.
