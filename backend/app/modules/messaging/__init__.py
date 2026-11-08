"""Messaging: sim texts plus inbound routing. Photon live send is TASK-022.

Other modules import `from app.modules import messaging`.
Sends never raise: a channel failure is stored on the message and `status().last_error`.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import defaultdict
from datetime import datetime, timezone

from app.shared import ids, schemas
from app.shared.config import settings
from app.shared.enums import Direction, MessageKind, PartyType
from app.shared.events import bus
from app.shared.store import store

log = logging.getLogger("messaging")

_lock = threading.RLock()
_handlers: dict[str, list] = defaultdict(list)
_last_error: str | None = None
_defaults = False
_seen_webhook_ids: list[str] = []

_INBOUND_KIND = {
    "technician": MessageKind.task_update,
    "tenant": MessageKind.other,
    "resident": MessageKind.resident_chat,
    "manager": MessageKind.other,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _type(value) -> str:
    return getattr(value, "value", value)


def _mode() -> str:
    return "photon" if settings.messaging_mode == "photon" else "sim"


def _channel_for(party: schemas.Party) -> str:
    if _mode() == "photon" and party.demo_live:
        return "photon"
    return "sim"


def _remember_error(message: str) -> None:
    global _last_error
    _last_error = message[:300]


def on_inbound(party_type: PartyType | str, handler) -> None:
    """handler(party_id, text, media_urls) runs for every inbound message of that party type."""
    _handlers[_type(party_type)].append(handler)


def party_for_phone(phone: str) -> schemas.Party:
    """Match a seeded party, else create RESIDENT-<last4> for an unknown number."""
    normalized = _normalize(phone)
    if not normalized:
        raise KeyError("phone number is empty")
    for party in store.parties.list():
        if _normalize(party.phone) == normalized:
            return party
    for party_id, mapped in settings.demo_phone_map().items():
        if _normalize(mapped) == normalized:
            found = store.parties.get(party_id)
            if found is not None:
                return found
    digits = re.sub(r"\D", "", normalized)
    last4 = digits[-4:] if digits else "0000"
    party_id = f"RESIDENT-{last4}"
    existing = store.parties.get(party_id)
    if existing is not None:
        return existing
    created = schemas.Party(
        id=party_id, type=PartyType.resident, name=f"Resident {last4}", phone=normalized, language="en",
    )
    store.parties.put(created)
    return created


def _normalize(phone: str) -> str:
    raw = (phone or "").strip().replace(" ", "").replace("-", "")
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    return raw


def send(
    party_id: str,
    body: str,
    kind: MessageKind | str,
    media_urls: list[str] | None = None,
    work_order_id: str | None = None,
    referral_id: str | None = None,
) -> schemas.Message:
    """Queue a text and deliver it. Sim delivery finishes before return. Failures do not raise."""
    global _last_error
    party = store.parties.require(party_id)
    channel = _channel_for(party)
    message = schemas.Message(
        id=ids.new_id("MSG"),
        party_id=party.id,
        party_type=party.type,
        direction=Direction.outbound,
        kind=kind if isinstance(kind, MessageKind) else MessageKind(kind),
        body=body,
        media_urls=list(media_urls or []),
        work_order_id=work_order_id,
        referral_id=referral_id,
        status="queued",
        channel=channel,
        created_wall=_now(),
    )
    with _lock:
        store.messages.put(message)
        try:
            if channel == "photon":
                _photon_send(party.phone, body, message.media_urls)
            delivered = message.model_copy(update={"status": "sent", "error": None})
            _last_error = None
        except Exception as exc:
            error = str(exc) or exc.__class__.__name__
            _remember_error(error)
            log.warning("outbound message %s failed on %s", message.id, channel)
            delivered = message.model_copy(update={"status": "failed", "error": error[:300]})
        store.messages.put(delivered)
    if delivered.status == "sent":
        bus.emit("message.sent", {"message_id": delivered.id, "party_id": delivered.party_id, "kind": _type(delivered.kind)})
    return delivered


def _photon_send(phone: str, body: str, media_urls: list[str]) -> None:
    """Live Photon send belongs to TASK-022. Without that channel, fail soft."""
    if not settings.photon_api_key or not phone:
        raise RuntimeError("Photon is not configured")
    if media_urls:
        raise RuntimeError("Photon photo send is not available yet")
    raise RuntimeError("PhotonChannel is not installed; use MESSAGING_MODE=sim")


def receive(party: schemas.Party, text: str, media_urls: list[str] | None = None, kind: MessageKind | None = None) -> schemas.Message:
    """Store an inbound message, emit message.received, then run that party type's handlers."""
    media = list(media_urls or [])
    inbound_kind = kind or _INBOUND_KIND.get(_type(party.type), MessageKind.other)
    if _type(party.type) == "manager" and text.strip().lower().startswith("yes "):
        inbound_kind = MessageKind.approval_request
    message = schemas.Message(
        id=ids.new_id("MSG"),
        party_id=party.id,
        party_type=party.type,
        direction=Direction.inbound,
        kind=inbound_kind,
        body=text,
        media_urls=media,
        status="received",
        channel=_channel_for(party),
        created_wall=_now(),
    )
    with _lock:
        store.messages.put(message)
    bus.emit("message.received", {"message_id": message.id, "party_id": message.party_id, "kind": _type(message.kind)})
    for handler in list(_handlers.get(_type(party.type), [])):
        try:
            handler(party.id, text, media)
        except Exception:
            log.warning("inbound handler failed for %s", party.id)
    return message


def _on_technician(party_id: str, text: str, media_urls: list[str]) -> None:
    try:
        from app.modules import actions
    except ImportError:
        return
    reply = getattr(actions, "apply_task_reply", None)
    if callable(reply):
        reply(party_id, text, media_urls)


def _on_tenant(party_id: str, text: str, media_urls: list[str]) -> None:
    send(party_id, "Noted. We have your message.", MessageKind.other)


def _on_resident(party_id: str, text: str, media_urls: list[str]) -> None:
    try:
        from app.modules import resources
    except ImportError:
        return
    resources.route(party_id, text)


def _on_manager(party_id: str, text: str, media_urls: list[str]) -> None:
    match = re.match(r"(?i)^yes\s+(\S+)", text.strip())
    if not match:
        return
    try:
        from app.modules import actions
    except ImportError:
        return
    approve = getattr(actions, "approve", None)
    if callable(approve):
        approve(match.group(1), party_id)


def status() -> schemas.MessagingStatus:
    messages = store.messages.list()
    return schemas.MessagingStatus(
        mode=_mode(),
        live_parties=[party.id for party in store.parties.list() if party.demo_live],
        sent=sum(1 for message in messages if message.direction == Direction.outbound and message.status == "sent"),
        received=sum(1 for message in messages if message.status == "received"),
        last_error=_last_error,
    )


def parse_webhook(payload: dict) -> tuple[str, str, list[str]] | None:
    """Best-effort inbound extract. Signature checks belong to TASK-022. Returns (phone, text, media) or None."""
    if not isinstance(payload, dict):
        return None
    phone = payload.get("from") or payload.get("phone")
    text = payload.get("text") or payload.get("body") or ""
    media = list(payload.get("media_urls") or [])
    if payload.get("media_url"):
        media.append(payload["media_url"])
    message = payload.get("message") if isinstance(payload.get("message"), dict) else None
    if message:
        content = message.get("content") if isinstance(message.get("content"), dict) else {}
        text = text or content.get("text") or ""
        sender = message.get("sender") if isinstance(message.get("sender"), dict) else {}
        phone = phone or sender.get("phone") or sender.get("handle")
        for attachment in content.get("attachments") or []:
            if isinstance(attachment, str):
                media.append(attachment)
            elif isinstance(attachment, dict) and attachment.get("url"):
                media.append(attachment["url"])
    if not phone or not str(text).strip():
        return None
    return str(phone), str(text), media


def accept_webhook(payload: dict, headers: dict | None = None) -> dict:
    # Signature verification is TASK-022. Until then, live mode must not trust an unsigned body.
    if _mode() == "photon":
        _remember_error("Photon webhook verification is not installed")
        return {"ok": True}
    event_id = ""
    if isinstance(payload, dict):
        event_id = str((headers or {}).get("x-spectrum-webhook-id") or payload.get("id") or "")
        message = payload.get("message") if isinstance(payload.get("message"), dict) else None
        if message and message.get("id"):
            event_id = event_id or str(message["id"])
    if event_id:
        if event_id in _seen_webhook_ids:
            return {"ok": True}
        _seen_webhook_ids.append(event_id)
        del _seen_webhook_ids[:-1000]
    parsed = parse_webhook(payload)
    if parsed is None:
        _remember_error("webhook had no sender phone")
        return {"ok": True}
    phone, text, media = parsed
    receive(party_for_phone(phone), text, media)
    return {"ok": True}


def register() -> None:
    global _defaults
    if not _defaults:
        on_inbound(PartyType.technician, _on_technician)
        on_inbound(PartyType.tenant, _on_tenant)
        on_inbound(PartyType.resident, _on_resident)
        on_inbound(PartyType.manager, _on_manager)
        _defaults = True


from .routes import router  # noqa: E402

__all__ = [
    "register", "router", "send", "on_inbound", "party_for_phone", "status", "receive", "accept_webhook",
]
