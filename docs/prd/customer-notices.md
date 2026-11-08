# Additive contract: customer emergency notices (TASK-065)

POST `/api/customer-notices` accepts `{request_id: string (8–100), scenario_id: string, step_hour: integer, building_id: string, tenant_ids: string[] (1–30), text: string (1–1600), mode: "sim"|"photon"}`. Returns `{messages: Message[], duplicate: boolean}` using the frozen Message shape. Text is prefixed with Operation Storm and building name. No new shared schema fields.

All tenant IDs must belong to the building and resolve to contacts. Contacts are deduplicated. Scenario/hour/mode must still match the reviewed draft (409 otherwise). Repeating an identical request ID returns the original message records; different content with the same ID returns 409. Each demo run keeps up to 500 requests and reset clears them. This is process-local deduplication, not durable delivery or exactly-once semantics. Failed/unknown sends are not retried.

The UI lives in Fix-First. Preview includes selected audience and final text. Photon uses the existing messaging adapter and Spectrum bridge; allowlisted contacts use Photon, other contacts remain simulated. The result lists the actual channel and status for every contact. `sent` means provider acceptance for Photon, not handset delivery. Inbound tenant replies use the existing verified webhook and appear in Texts.

For live setup follow `backend/spikes/photon/PHOTON_NOTES.md`: configure credentials in git-ignored backend/.env, provision a line, map permitted recipients in DEMO_PHONES, start the Node bridge and backend with MESSAGING_MODE=photon, and register the backend HTTPS webhook URL. Never enter credentials in the UI. Real-phone round trip requires separate manual verification.
