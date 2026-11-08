# simulation frontend public interface

Default export `SimulationBuilder`, a button and accessible modal for a supported/random city, disaster selection, and relevant effect sliders. Mount in the app header or portfolio tool area.

Uses only shared UI/query invalidation and its documented `/api/simulation` endpoints. Maintains form choices after failures; closes only after a real successful start and scenario-cache invalidation. All effects are labelled hypothetical. No financial calculations are done in the client. Storm surge is offered only for Fort Myers; changing cities resets an incompatible disaster to flood.
