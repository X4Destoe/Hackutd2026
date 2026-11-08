# Custom simulation builder

Generates hypothetical exercises over the existing fictional portfolios in Houston, Dallas and Fort Myers. It uses a radial synthetic water/winter footprint and an illustrative wind track, not local hydrology or an observed weather forecast. Outages affect the selected city's existing utility nodes. Forecast/impact/recovery share one analytic model.

Run from repository root: `python -m pytest backend/app/modules/simulation/tests -q`.

Activation requires the scenarios owner's public `load_definition(Scenario, anchors)` integration; while absent the preview works and start returns503. No source-data files are generated at runtime. The frontend must label custom IDs as synthetic and invalidate scenarios plus scenario-bound caches after starting. Historical scenarios remain separate choices.
