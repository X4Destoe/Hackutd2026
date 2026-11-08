# messaging

The only module that sends and receives texts: sim channel (default) and, with TASK-022, Photon Spectrum through the Node bridge
in `backend/spikes/photon/`. Inbound messages are routed by party type (technician, tenant, resident, manager).
Tests: `cd backend && python -m pytest app/modules/messaging`.
