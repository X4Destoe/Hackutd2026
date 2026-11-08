"""TASK-086: Photon replies by polling. The fake API returns the official @photon-ai/api 0.6.0 MessagePage/Message shapes."""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import messaging
from app.modules.messaging import current_api, photon, polling
from app.shared.config import settings
from app.shared.store import store

PROJECT = "pho_prj_test"
KEY = "unit-test-credential"
SECRET = "whsec_" + base64.b64encode(b"unit-test-signing-key").decode()
T0 = 1_800_000_000.0  # fixed clock
RUN = 0


@pytest.fixture(autouse=True)
def _unique_ids():
    global RUN
    RUN += 1


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def message(text, mid, phone, at=T0 + 1, **over):
    mid = f"{mid}-{RUN}"  # unique per test run: the dedupe list is process-wide
    m = {"id": mid, "projectId": PROJECT, "platform": "imessage", "status": "received", "createdAt": iso(at),
         "space": {"id": "space-1", "kind": "direct"}, "sentBy": {"id": "user-1", "kind": "human", "handle": phone},
         "receivedBy": {"id": "agent-1", "kind": "agent"}, "content": {"type": "text", "format": "plain", "text": text}}
    m.update(over)
    if m.get("createdAt") is None:
        m.pop("createdAt", None)
    return m


class FakePhoton:
    """Serves pages of messages; records every request."""
    def __init__(self, pages=None):
        self.pages, self.requests, self.fail = pages or [[]], [], None

    def __call__(self, req):
        self.requests.append(req)
        assert req.url.host == "api.photon.codes" and req.headers["authorization"] == "Bearer " + KEY
        assert req.method == "GET" and req.url.path == f"/v1/projects/{PROJECT}/messages"
        if self.fail:
            return httpx.Response(self.fail, json={"code": "X"})
        token = req.url.params.get("pageToken")
        index = int(token) if token else 0
        body = {"items": self.pages[index]}
        if index + 1 < len(self.pages):
            body["nextPageToken"] = str(index + 1)
        return httpx.Response(200, json=body)


@pytest.fixture
def app():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def tech(app):
    party = store.parties.require(store.buildings.require("BLD-HOU-01").onsite_party_id)
    return party


RESIDENT_PHONE = "+17135550188"


def poller(fake, clock=lambda: T0, phones=None, **kw):
    if phones is None:  # the Bayou Plaza technician and one mapped resident phone
        tech_phone = store.parties.require(store.buildings.require("BLD-HOU-01").onsite_party_id).phone
        phones = f"{tech_phone}:TECH,{RESIDENT_PHONE}:RESIDENT-0188"
    cfg = photon.PhotonSettings(_env_file=None, photon_api_key=KEY, photon_project_id=PROJECT, photon_webhook_secret=SECRET,
                                demo_phones=phones)
    return polling.PhotonPoller(cfg, httpx.Client(transport=httpx.MockTransport(fake)), clock=clock, **kw), cfg


def inbound_bodies(party_id):
    return [m.body for m in store.messages.list(party_id=party_id, direction="inbound")]


def test_request_matches_the_official_list_messages_query(app):
    fake = FakePhoton()
    p, _ = poller(fake)
    assert p.poll_once() == 0
    q = fake.requests[0].url.params
    assert q["direction"] == "received" and q["platform"] == "imessage" and q["order"] == "asc" and q["pageSize"] == "100"
    assert q["createdSince"] == iso(T0 - 5)  # never earlier than startup: old history is not replayed


def test_a_reply_is_delivered_once_even_when_listed_again(app, tech):
    fake = FakePhoton([[message("progress update", "m-1", tech.phone)]])
    p, _ = poller(fake)
    assert p.poll_once() == 1 and p.poll_once() == 0
    assert inbound_bodies(tech.id) == ["progress update"]
    assert p.error is None and p.last_ok == T0


def test_pages_are_followed(app, tech):
    fake = FakePhoton([[message("one", "m-1", tech.phone)], [message("two", "m-2", tech.phone)]])
    p, _ = poller(fake)
    assert p.poll_once() == 2 and fake.requests[1].url.params["pageToken"] == "1"
    assert inbound_bodies(tech.id) == ["one", "two"]


@pytest.mark.parametrize("change", [
    {"projectId": "pho_prj_other"}, {"status": "delivered"}, {"platform": "sms"},
    {"space": {"id": "g", "kind": "group"}},
    {"sentBy": {"id": "agent-1", "kind": "agent", "handle": "+17135550100"}},
    {"sentBy": {"id": "u", "kind": "human", "handle": "someone@example.com"}},
    {"content": {"type": "space.typing.update"}}, {"content": {"type": "message.read"}},
    {"createdAt": iso(T0 - 600)},  # sent before polling started
    {"createdAt": None}, {"createdAt": "2027-01-15T08:00:00"},  # unknown age / no timezone: could be old history
])
def test_non_replies_are_ignored(app, tech, change):
    p, _ = poller(FakePhoton([[message("ignored", "m-x", tech.phone, **change)]]))
    assert p.poll_once() == 0 and inbound_bodies(tech.id) == []


def test_a_message_seen_by_the_signed_webhook_is_not_delivered_again(app, tech, monkeypatch):
    cfg = photon.PhotonSettings(_env_file=None, photon_api_key=KEY, photon_project_id=PROJECT, photon_webhook_secret=SECRET)
    monkeypatch.setattr(photon, "settings", lambda: cfg)
    monkeypatch.setattr(settings, "messaging_mode", "photon")  # the signed path only runs in real mode
    event = {"apiVersion": current_api.API_VERSION, "type": "message.received",
             "data": {"object": message("from webhook", "m-both", tech.phone)}}
    raw, stamp = json.dumps(event).encode(), str(int(time.time()))
    sig = base64.b64encode(hmac.new(b"unit-test-signing-key", b"evt-1." + stamp.encode() + b"." + raw, hashlib.sha256).digest()).decode()
    headers = {"webhook-id": "evt-1", "webhook-timestamp": stamp, "webhook-signature": "v1," + sig, "content-type": "application/json"}
    assert app.post("/api/webhooks/photon", content=raw, headers=headers).json()["ok"]
    p, _ = poller(FakePhoton([[message("from webhook", "m-both", tech.phone)]]))
    assert p.poll_once() == 0 and inbound_bodies(tech.id) == ["from webhook"]


def test_a_mapped_resident_phone_is_routed_and_gets_photon_replies(app):
    p, _ = poller(FakePhoton([[message("our apartment flooded, need a dry place", "m-r", RESIDENT_PHONE)]]))
    assert p.poll_once() == 1
    party = messaging.party_for_phone(RESIDENT_PHONE)
    assert party.type == "resident" and party.demo_live is True


def test_a_phone_not_in_demo_phones_is_ignored_before_any_party_exists(app):
    stranger = "+17135550177"
    before = len(store.parties.list())
    p, _ = poller(FakePhoton([[message("DONE WO-001", "m-s", stranger)]]))
    assert p.poll_once() == 0
    assert len(store.parties.list()) == before and not any(m.body == "DONE WO-001" for m in store.messages.list())


def test_an_unexpected_failure_logs_no_message_text(app, tech, monkeypatch, caplog):
    def boom(*_a, **_k):
        raise RuntimeError("private reply text and token-123")
    monkeypatch.setattr(messaging, "receive", boom)
    p, _ = poller(FakePhoton([[message("private reply text", "m-e", tech.phone)]]), interval=0.01)
    p.start()
    try:
        deadline = time.time() + 2
        while p.error is None and time.time() < deadline:
            time.sleep(0.01)
    finally:
        p.stop()
    assert p.error and "private" not in p.error
    assert "private" not in caplog.text and "token-123" not in caplog.text and "RuntimeError" in caplog.text


def test_a_refusal_sets_a_safe_error_and_the_loop_keeps_going(app, tech):
    fake = FakePhoton([[message("later", "m-1", tech.phone)]])
    fake.fail = 403
    p, _ = poller(fake, interval=0.01)
    p.start()
    try:
        deadline = time.time() + 2
        while p.error is None and time.time() < deadline:
            time.sleep(0.01)
        assert p.error and "403" in p.error and KEY not in p.error and tech.phone not in p.error
        fake.fail = None  # Photon recovers: the next poll clears the error and delivers
        deadline = time.time() + 5
        while (p.error or not inbound_bodies(tech.id)) and time.time() < deadline:
            time.sleep(0.02)
        assert p.error is None and inbound_bodies(tech.id) == ["later"]
    finally:
        p.stop()
    assert not p._thread.is_alive()


def test_missing_credentials_refuse_to_start():
    cfg = photon.PhotonSettings(_env_file=None, photon_api_key="", photon_project_id="")
    with pytest.raises(photon.PhotonError):
        polling.PhotonPoller(cfg)


def test_technician_done_reply_by_polling_closes_the_work_order(app, tech):
    app.post("/api/timeline", json={"hour": -24})
    plan = app.get("/api/plans?building_id=BLD-HOU-01&status=proposed").json()[0]["id"]
    app.post(f"/api/plans/{plan}/approve", json={"by": "MGR-01"})
    wo = app.get("/api/workorders?building_id=BLD-HOU-01").json()[0]["id"]
    p, _ = poller(FakePhoton([[message(f"DONE {wo}", "m-done", tech.phone)]]))
    assert p.poll_once() == 1
    status = next(w["status"] for w in app.get("/api/workorders?building_id=BLD-HOU-01").json() if w["id"] == wo)
    assert status == "done"
