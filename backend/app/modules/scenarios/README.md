# scenarios

Owns the world: disaster presets, the timeline, the portfolio seed, demo state and the hazard lookup.

- `__init__.py`: state, timeline, public functions. `hazard.py`: pure analytic hazard model. `routes.py`: HTTP.
- Data: `backend/data/{portfolio,utilities,parties}.json`, `backend/data/anchors/<id>.json` (hand-placed hazard anchors),
  `backend/data/scenarios/<id>.json` (generated: `cd backend && python -m data.make_overlays <id>`).
- Tests: `cd backend && python -m pytest app/modules/scenarios`.

Tuning a scenario: edit its anchors file (river `peak_ft` / `half_width_mi`, pools, `outages`, `present` share per step),
regenerate, and rerun the tests. `present["0"]` is 1: water reaches its peak at landfall, so impact never shows less
exposure than the forecast did.
