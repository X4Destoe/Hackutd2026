"""Public webhook-only ingress. Expose this service, not the unauthenticated demo API.
uvicorn app.modules.messaging.webhook_gateway:app --host 127.0.0.1 --port 8788
Photon destination: https://<tunnel-host>/api/webhooks/photon
"""
import httpx
from fastapi import FastAPI, Request, Response
from .photon import settings, verify as verify_spectrum
from .current_api import verify as verify_current

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
FORWARD_HEADERS = {'content-type', 'webhook-id', 'webhook-timestamp', 'webhook-signature',
    'x-spectrum-event', 'x-spectrum-timestamp', 'x-spectrum-signature', 'x-spectrum-webhook-id'}


@app.post('/api/webhooks/photon')
async def receive(request: Request):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 1048576:
            return Response(status_code=413)
        chunks.append(chunk)
    raw = b''.join(chunks)
    cfg = settings()
    signed = (verify_current(raw, dict(request.headers), cfg.photon_webhook_secret.get_secret_value() or cfg.spectrum_webhook_secret)
              if cfg.photon_api_key.get_secret_value() else verify_spectrum(raw, dict(request.headers), cfg.spectrum_webhook_secret))
    if not signed:
        return Response(status_code=401)
    headers = {key: value for key, value in request.headers.items() if key in FORWARD_HEADERS}
    try:
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            result = await client.post('http://127.0.0.1:8000/api/webhooks/photon', content=raw, headers=headers)
    except httpx.HTTPError:
        return Response(content='{"detail":"Webhook receiver unavailable"}', status_code=502, media_type='application/json')
    return Response(content=result.content, status_code=result.status_code, media_type='application/json')
