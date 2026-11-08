"""PhotonChannel: real texts through Photon Spectrum (docs/prd/modules/messaging.md, backend/spikes/photon/PHOTON_NOTES.md).

Sending: Spectrum only sends through its TypeScript SDK, so we POST to the loopback Node bridge (backend/spikes/photon, `npm start`):
    POST {PHOTON_BRIDGE_URL}/send {phone, text} -> 200 {status: "accepted", message_id}   (acknowledged, not delivered)
The bridge holds SPECTRUM_PROJECT_ID / SECRET and only texts numbers listed in DEMO_PHONES (403 otherwise).
Receiving: native webhook, HMAC-SHA256 over the exact bytes  b"v0:" + timestamp + b":" + raw_body, ±300 s, constant-time compare.
No secrets, phone numbers or message bodies are logged.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.config import BACKEND_DIR

REPLAY_SECONDS = 300


class PhotonSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")
    spectrum_webhook_secret: str = ""
    photon_bridge_url: str = "http://127.0.0.1:8787"


class PhotonError(RuntimeError):
    """A send the bridge did not accept (message is stored as failed with this text)."""


def settings() -> PhotonSettings:
    return PhotonSettings()


def verify(raw: bytes, headers: dict[str, str], secret: str, now: float | None = None) -> bool:
    h = {k.lower(): v for k, v in headers.items()}
    stamp, signature = h.get("x-spectrum-timestamp", ""), h.get("x-spectrum-signature", "")
    if not secret or not re.fullmatch(r"\d{1,12}", stamp) or not re.fullmatch(r"v0=[0-9a-f]{64}", signature):
        return False
    if abs((time.time() if now is None else now) - int(stamp)) > REPLAY_SECONDS:
        return False
    expected = "v0=" + hmac.new(secret.encode(), b"v0:" + stamp.encode() + b":" + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _urls(content: Any) -> list[str]:
    """Collect http(s) URLs anywhere in an attachment content object (shape not finalized until a real photo reply)."""
    found: list[str] = []
    if isinstance(content, dict):
        for v in content.values():
            found += _urls(v)
    elif isinstance(content, list):
        for v in content:
            found += _urls(v)
    elif isinstance(content, str) and content.startswith(("https://", "http://")):
        found.append(content)
    return found


class PhotonChannel:
    """Channel protocol: send_text(to, body, media_urls) -> provider id; parse_inbound(raw, headers) -> (phone, text, media) | None."""

    def __init__(self, client: httpx.Client | None = None, config: PhotonSettings | None = None):
        self.config = config or settings()
        self.client = client

    def send_text(self, to: str, body: str, media_urls: list[str]) -> str:
        if media_urls:
            raise PhotonError("Photon photo send is not supported yet (the bridge rejects media)")
        url = self.config.photon_bridge_url.rstrip("/") + "/send"
        try:
            if self.client is not None:
                r = self.client.post(url, json={"phone": to, "text": body})
            else:
                with httpx.Client(timeout=20.0, trust_env=False) as c:  # loopback only: never via a proxy
                    r = c.post(url, json={"phone": to, "text": body})
        except httpx.HTTPError as e:
            raise PhotonError(f"Photon bridge unreachable ({type(e).__name__}): start it with 'npm start' in backend/spikes/photon") from e
        if r.status_code != 200:
            try:
                detail = r.json().get("error", "")
            except ValueError:
                detail = ""
            raise PhotonError(f"Photon bridge refused the send ({r.status_code}){': ' + detail if detail else ''}")
        try:
            acknowledgement = r.json()
        except ValueError as exc:
            raise PhotonError("Photon bridge returned an invalid acknowledgement") from exc
        if not isinstance(acknowledgement, dict) or acknowledgement.get("status") != "accepted":
            raise PhotonError("Photon bridge did not confirm acceptance")
        return str(acknowledgement.get("message_id", ""))

    def parse_inbound(self, raw: bytes, headers: dict[str, str]) -> tuple[str, str, list[str]] | None:
        """Verified native envelope -> (sender phone, text, media urls). Raises PermissionError on a bad signature."""
        if not verify(raw, headers, self.config.spectrum_webhook_secret):
            raise PermissionError("invalid Spectrum signature or timestamp")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Webhook body must be an object")
        event = payload.get("event")
        if {k.lower(): v for k, v in headers.items()}.get("x-spectrum-event") != event:
            raise PermissionError("event header does not match the signed body")
        if event != "message.received":
            return None
        message = payload.get("message")
        if not isinstance(message, dict):
            raise ValueError("Webhook message must be an object")
        if message.get("id") is not None and not isinstance(message["id"], str):
            raise ValueError("Webhook message identity must be a string")
        sender = message.get("sender")
        if not isinstance(sender, dict):
            raise ValueError("Webhook sender must be an object")
        phone = sender.get("phone") or sender.get("handle") or sender.get("id") or ""
        if not isinstance(phone, str):
            raise ValueError("Webhook sender handle must be a string")
        content = message.get("content")
        if not isinstance(content, dict):
            raise ValueError("Webhook content must be an object")
        text = content.get("text", "") if content.get("type") == "text" else (content.get("text") or content.get("caption") or "")
        if not isinstance(text, str):
            raise ValueError("Webhook text must be a string")
        media = [] if content.get("type") == "text" else _urls(content)
        return (str(phone), str(text), media) if phone else None
