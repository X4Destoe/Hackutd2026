# simulation public interface

Module routes are mounted automatically by app.main. No historical data files are written.

- GET `/api/simulation/options`: supported city IDs/names/centers, disaster IDs and compatible cities, synthetic-exercise disclaimer.
- POST `/api/simulation/preview`: validated `SimulationRequest`; returns `{scenario: Scenario, configuration: SimulationRequest}` with a resolved concrete city. Read-only: does not reset the active scenario.
- POST `/api/simulation/start`: same request; returns existing `DemoState` after calling public `scenarios.load_definition(scenario, anchors)`. Missing loader returns explicit 503, never fake success. It must use the same seeding/events path as historical loads.

Request: city `houston|dallas|fort_myers|random`; disaster `flood|hurricane|windstorm|winter|surge`; optional water_ft 0..20 (default6), wind_mph 0..180 (100), outage_hours integer0..168 (24), temperature_f -30..32 (10), ice_in 0..2 (0.5). Nonfinite numbers, unknown fields/IDs and surge outside Fort Myers are rejected. Random surge resolves to Fort Myers. Other random choices use only supported cities. Relevant knobs drive analytic anchors and rendered geometry; irrelevant knobs do not add unrelated hazards.

`model.build(request, utilities)` is module-internal. Other modules use HTTP or the declared scenario-loader extension, not generator internals. Shared frozen schemas are unchanged. Contract additions are documented in docs/prd/modules/simulation.md.
