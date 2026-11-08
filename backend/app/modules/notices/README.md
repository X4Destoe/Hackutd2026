# Customer emergency notices

Portfolio managers explicitly select a building and its tenant contacts, review text and dispatch through the existing messaging module. Request IDs suppress duplicate dispatch within one in-memory demo run. Reset clears history. Tests: `cd backend && python -m pytest app/modules/notices`.

Real sends require the Photon adapter from TASK-022 and a running configured bridge. Without it use simulator mode. Provider acceptance is not proof of handset delivery. No automatic retries.
