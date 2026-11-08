# OSM base geometry snapshots
The fetch utility is ready, but **no real OSM snapshots are committed yet**. This cloud instance's proxy rejects Overpass with CONNECT 403. Do not describe the current hand-placed anchors as OSM-derived.

From backend, once `overpass-api.de` access is active:
```
python -m data.fetch_osm harvey_houston ian_fort_myers
```
Inspect the resulting GeoJSON line groups and source metadata before `--apply`. Disconnected ways remain separate lines. Each part has at most 150 vertices. River/coast geometry is real base-map geometry; width, depth, storm timing and reservoir-release pools remain synthetic. OSM attribution and license links are written into each fetched snapshot, and into anchor sources when applied.

`python -m data.fetch_osm harvey_houston ian_fort_myers --apply` updates river/coast coordinates only after every expected group for that scenario is nonempty. Then run `python -m data.make_overlays harvey_houston ian_fort_myers`, scenario/impact tests and building-depth checks. Adjust the illustrative half_width_mi/peak_ft only after checking real fetched geometry: Bayou above-floor 2.5–3.5 ft at hour 0; Meyerland >3 ft; Galleria/medical pavilion dry; Estero deep surge. Addicks and Barker boundaries are fetched as closed-way or multipolygon reference features, including holes. Incomplete rings fail rather than being implicitly closed. These reference polygons never replace or relabel the existing synthetic reservoir-release pools; a reservoir boundary is not an inundation footprint.

Tests in this directory use **synthetic fixtures**, never published as OSM data: `python -m unittest discover -s data/osm/tests -v`. They verify merging, clipping, disconnected components, vertex limits, attribution, partial-response rejection and preserving existing anchor data on missing groups. Application startup never fetches OSM; only committed snapshots will be used after this task's network prerequisite is resolved.
