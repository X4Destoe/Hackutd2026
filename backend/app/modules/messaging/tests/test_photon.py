import hashlib
import hmac
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import messaging
from app.modules.messaging import photon
from app.shared.config import settings
from app.shared.store import store

SECRET = "test-webhook-secret"


def signed(payload: dict, secret: str = SECRET, stamp: int | None = None, delivery: str = "d1"):
    raw = json.dumps(payload).encode()
    ts = str(int(time.time()) if stamp is None else stamp)
    sig = "v0=" + hmac.new(secret.encode(), b"v0:" + ts.encode() + b":" + raw, hashlib.sha256).hexdigest()
    headers = {"X-Spectrum-Event": payload.get("event", ""), "X-Spectrum-Signature": sig, "X-Spectrum-Timestamp": ts,
               "X-Spectrum-Webhook-Id": delivery, "Content-Type": "application/json"}
    return raw, headers


def envelope(phone: str, text: str = "", content: dict | None = None, mid: str = "m1"):
    # Native envelope shape from the spectrum-ts 12.15 types (PHOTON_NOTES.md); confirm against a real delivery.
    return {"event": "message.received", "message": {"id": mid, "space": {"id": "s1"}, "sender": {"id": phone},
                                                     "content": content or {"type": "text", "text": text}}}


@pytest.fixture
def cfg(monkeypatch):
    conf = photon.PhotonSettings(spectrum_webhook_secret=SECRET, photon_bridge_url="http://bridge.test")
    monkeypatch.setattr(photon, "settings", lambda: conf)
    return conf


def test_signature_checks(cfg):
    raw, h = signed(envelope("+17135550100", "hi"))
    assert photon.verify(raw, h, SECRET)
    assert not photon.verify(raw + b" ", h, SECRET)                       # tampered body
    assert not photon.verify(raw, h, "wrong")                             # wrong secret
    old_raw, old_h = signed(envelope("+1", "x"), stamp=int(time.time()) - 301)
    assert not photon.verify(old_raw, old_h, SECRET)                      # replay window
    assert not photon.verify(raw, h, "")                                  # no secret configured -> reject


def test_parse_text_and_photo(cfg):
    ch = photon.PhotonChannel()
    raw, h = signed(envelope("+17135550100", "DONE WO-001"))
    assert ch.parse_inbound(raw, h) == ("+17135550100", "DONE WO-001", [])
    photo = envelope("+17135550100", content={"type": "attachment", "attachment": {"url": "https://cdn.example/p.jpg", "mime": "image/jpeg"}})
    raw, h = signed(photo)
    assert ch.parse_inbound(raw, h) == ("+17135550100", "", ["https://cdn.example/p.jpg"])
    raw, h = signed(envelope("+1", "x"))
    h["X-Spectrum-Event"] = "message.deleted"
    with pytest.raises(PermissionError):
        ch.parse_inbound(raw, h)                                          # header must match the signed body


def test_bridge_responses(cfg):
    def bridge(status, body):
        return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body)))
    assert photon.PhotonChannel(bridge(200, {"status": "accepted", "message_id": "ph-1"})).send_text("+1", "hi", []) == "ph-1"
    for malformed in ({}, [], {"status": "failed"}):
        with pytest.raises(photon.PhotonError, match="acceptance"):
            photon.PhotonChannel(bridge(200, malformed)).send_text("+1", "hi", [])
    with pytest.raises(photon.PhotonError, match="403.*DEMO_PHONES"):
        photon.PhotonChannel(bridge(403, {"error": "Recipient is not listed in DEMO_PHONES"})).send_text("+1", "hi", [])
    with pytest.raises(photon.PhotonError, match="not supported"):
        photon.PhotonChannel(bridge(200, {})).send_text("+1", "hi", ["https://x/p.jpg"])

    def down(_r):
        raise httpx.ConnectError("refused")
    with pytest.raises(photon.PhotonError, match="unreachable"):
        photon.PhotonChannel(httpx.Client(transport=httpx.MockTransport(down))).send_text("+1", "hi", [])


@pytest.fixture
def live(monkeypatch, cfg):
    """Photon mode with one real demo phone (the Bayou Plaza technician) and a fake bridge that records sends."""
    sent = []
    monkeypatch.setattr(settings, "messaging_mode", "photon")
    with TestClient(create_app()) as c:
        tech = store.buildings.require("BLD-HOU-01").onsite_party_id
        phone = store.parties.require(tech).phone
        monkeypatch.setattr(settings, "demo_phones", f"{phone}:{tech}")
        monkeypatch.setattr(photon.PhotonChannel, "send_text", lambda self, to, body, media: sent.append((to, body)) or "ph")
        c.sent, c.tech, c.phone = sent, tech, phone
        yield c


def test_approve_texts_the_real_technician_and_a_signed_done_closes_the_work_order(live):
    c = live
    c.post("/api/timeline", json={"hour": -24})
    pid = c.get("/api/plans?building_id=BLD-HOU-01&status=proposed").json()[0]["id"]
    c.post(f"/api/plans/{pid}/approve", json={"by": "MGR-01"})
    deadline = time.time() + 5
    while time.time() < deadline and not c.sent:
        time.sleep(0.05)
    assert c.sent and all(to == c.phone for to, _ in c.sent)              # only the DEMO_PHONES party goes over Photon
    wo = c.get("/api/workorders?building_id=BLD-HOU-01").json()[0]["id"]
    raw, h = signed(envelope(c.phone, f"DONE {wo}", mid="m-done"), delivery="d-done")
    t = time.time()
    assert c.post("/api/webhooks/photon", content=raw, headers=h).json()["ok"]
    status = next(w["status"] for w in c.get("/api/workorders?building_id=BLD-HOU-01").json() if w["id"] == wo)
    assert status == "done" and time.time() - t < 5
    assert c.post("/api/webhooks/photon", content=raw, headers=h).json().get("duplicate") is True  # at-least-once delivery


def test_unsigned_or_forged_webhooks_are_rejected_in_photon_mode(live):
    raw, h = signed(envelope("+17135550199", "help"), secret="forged")
    assert live.post("/api/webhooks/photon", content=raw, headers=h).status_code == 401
    assert live.post("/api/webhooks/photon", json=envelope("+17135550199", "help")).status_code == 401


def test_a_resident_who_texts_the_photon_line_gets_photon_replies(live):
    raw, h = signed(envelope("+17135550177", "info please", mid="m-res"), delivery="d-res")
    live.post("/api/webhooks/photon", content=raw, headers=h)
    party = messaging.party_for_phone("+17135550177")
    assert party.demo_live is True
    msg = messaging.send(party.id, "test reply", "redirect")
    assert msg.channel == "photon"


@pytest.mark.parametrize("payload", [[], None, {"event": "message.received", "message": []},
    {"event": "message.received", "message": {"sender": [], "content": {}}},
    {"event": "message.received", "message": {"sender": {"phone": "+17135550177"}, "content": []}},
    {"event": "message.received", "message": {"sender": {"phone": "+17135550177"}, "content": {"type": "text", "text": {}}}}])
def test_signed_malformed_structures_return400_not500(live, payload):
    raw = json.dumps(payload).encode()
    stamp = str(int(time.time()))
    signature = "v0=" + hmac.new(SECRET.encode(), b"v0:" + stamp.encode() + b":" + raw, hashlib.sha256).hexdigest()
    headers = {"X-Spectrum-Timestamp": stamp, "X-Spectrum-Signature": signature, "X-Spectrum-Event": "message.received"}
    assert live.post("/api/webhooks/photon", content=raw, headers=headers).status_code == 400


def test_signed_body_without_message_id_cannot_replay_by_changing_delivery_header(live):
    payload = envelope(live.phone, "review-only")
    payload["message"].pop("id")
    before = len(store.messages.list())
    raw, headers = signed(payload, delivery="fallback-one")
    assert live.post("/api/webhooks/photon", content=raw, headers=headers).json()["ok"]
    headers["X-Spectrum-Webhook-Id"] = "fallback-two"
    assert live.post("/api/webhooks/photon", content=raw, headers=headers).json()["duplicate"] is True
    assert len(store.messages.list()) == before + 1


def test_delivery_and_signed_message_id_use_separate_dedupe_namespaces(live):
    first, h1 = signed(envelope(live.phone, "first", mid="signed-first"), delivery="same-text")
    second, h2 = signed(envelope(live.phone, "second", mid="same-text"), delivery="delivery-second")
    assert live.post("/api/webhooks/photon", content=first, headers=h1).json()["ok"]
    assert live.post("/api/webhooks/photon", content=second, headers=h2).json().get("duplicate") is not True
