# Photon Spectrum spike (TASK-010)

## Evidence and limits

Inspected the published `spectrum-ts@12.15.0` package README and TypeScript definitions. SDK/provider imports compile against that exact version; package-lock records integrity hashes. Local checks exercise the loopback bridge, Python-to-Node HTTP, raw-byte HMAC, replay rejection and duplicate delivery handling. **No real text, provisioning, paid API request or photo reply has been verified:** credentials, recipient mapping and a provisioned line are absent in this cloud machine.

## Required configuration

Supply secrets through the user's secure local configuration, never chat, comms, Git or the environment snapshot. `backend/.env` is already Git-ignored. Runtime SDK credentials are `SPECTRUM_PROJECT_ID` and `SPECTRUM_PROJECT_SECRET`; inbound verification requires the webhook's `SPECTRUM_WEBHOOK_SECRET`. `DEMO_PHONES` uses `+12145550100:TECH-HOU-01,+14695550100:TEN-001` format; these are example placeholders only. Only those numbers may receive a bridge send. Optional `SPECTRUM_SENDER` selects the provisioned sending number when multiple lines exist. Provision an iMessage line at app.photon.codes first.

Proxy placeholders cannot be assumed to be usable as a local HMAC signing secret or SDK gRPC credential. Do not copy/extract proxy-held credentials. This spike does not manufacture environment bindings: validate the platform's supported credential path with the real configuration before live sends.

## SDK and hosts

Runtime sending uses `Spectrum({projectId, projectSecret, providers:[imessage.config()]})`, then `imessage(app).space.create(recipient, optionalSender)` and `space.send(text)`. It does **not** POST a message to a made-up REST endpoint. `https://spectrum.photon.codes` is the SDK cloud management/token destination; it uses project credentials (the management API uses Basic authentication). SDK source also references `wss://fusor-ws.spectrum.photon.codes/v1/subscribe` and `https://otlp.photon.codes`. Provisioned iMessage runtime/gRPC destinations are returned dynamically by the cloud; exact hosts still require a real initialization trace with credential values redacted. Do not replace an unknown network allowlist or disable TLS to make it work.

## Local commands

Use Node 22.9 or newer (Node 24 recommended). From `backend/spikes/photon`:

```sh
npm ci
npm run build
npm test
../../.venv/bin/python -m unittest discover -s tests -v
npm start
```

`npm start` reads `../../.env` if present using Node’s `--env-file-if-exists` option (requires Node 22.9+). The Python examples use the backend virtual environment created during setup; if yours lives elsewhere, substitute its Python executable. The bridge binds **127.0.0.1:8787** only. `GET /health` reports configuration presence, not provider connectivity. `POST /send` accepts JSON `{phone, text}` and returns `{status:"accepted", message_id}` on SDK acknowledgement, **not delivery**. Invalid bodies return 400; unconfigured 503; unmapped recipient 403; concurrent send 409; SDK failure 502. A 15-second timeout returns 504 with outcome unknown and keeps the underlying send slot occupied until completion. No automatic send retries. This does not provide durable idempotency: after failure/timeout check provider status before any manual retry.

Explicit real-send probe, once an authorized recipient and credentials are supplied:

```sh
../../.venv/bin/python send.py --phone <mapped-teammate-phone> --text 'Operation Storm test: reply DONE and a photo'
```

No example phone is sent automatically. Outbound media_url is currently rejected (400); inbound photo replies are supported by the signed-envelope verifier. A constrained attachment-upload path belongs in TASK-022 rather than unrestricted SDK URL fetching.

## Inbound native webhook

Run `../../.venv/bin/python webhook.py` with the webhook signing secret configured. It binds **127.0.0.1:8788**, route `POST /api/webhooks/photon`. Expose only this receiver through the team's approved tunnel, then register that HTTPS URL in the Spectrum dashboard/management API. Tunnel/provisioning was not performed in this spike.

Native envelope shape from SDK definitions:

```json
{
  "event": "message.received",
  "message": {
    "id": "...",
    "space": { "id": "..." },
    "sender": { "id": "..." },
    "content": { "type": "text", "text": "DONE" }
  }
}
```

Photo replies use the SDK's slim content object with its content type and attachment metadata; do not invent a flat `media_urls` field. Keep unknown fields for TASK-022's payload adapter. Capture actual content shape locally during the authorized live round trip before finalizing that adapter.

Headers: `X-Spectrum-Event`, `X-Spectrum-Signature: v0=<lowercase hex>`, `X-Spectrum-Timestamp` (Unix seconds), `X-Spectrum-Webhook-Id`. Verify HMAC-SHA256 over the **exact bytes** `b"v0:" + timestamp + b":" + rawBody`, constant-time compare, and reject timestamps more than 300 seconds in the past or future. Parse JSON only after verification. Header event must match the signed body. Deduplicate delivery ID and `(event,message.id)` independently; acknowledge duplicates with 200. Spike dedupe is bounded to 10k keys/10 minutes, process-local, and not durable across restart. Production integration needs persistent dedupe before side effects and lifecycle-aware event keys.

Receiver logs only verified event/id/content-type/duplicate status, never credentials, raw messages, phone numbers or attachment URLs. Valid signed photo fixture and replay are tested over HTTP; they are not evidence of a real phone reply.
