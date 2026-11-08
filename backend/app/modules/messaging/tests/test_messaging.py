"""Acceptance from docs/prd/modules/messaging.md: sim send, routing, unknown residents."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import messaging, scenarios as sc
from app.shared.config import settings
from app.shared.enums import MessageKind
from app.shared.events import bus
from app.shared.store import store


def test_sim_send_stores_and_emits():
    sc.load("harvey_houston")
    seen = []
    bus.on("message.sent", seen.append)
    message = messaging.send("TECH-HOU-01", "Deploy flood barriers.", MessageKind.task, work_order_id="WO-001")
    assert message.status == "sent" and message.channel == "sim" and message.direction == "outbound"
    assert store.messages.get(message.id) is not None
    assert seen and seen[-1]["message_id"] == message.id and seen[-1]["party_id"] == "TECH-HOU-01"
    assert messaging.status().sent >= 1 and messaging.status().mode == "sim"


def test_simulated_inbound_reaches_the_party_type_handler():
    sc.load("harvey_houston")
    messaging.register()
    seen = []
    messaging.on_inbound("technician", lambda party_id, text, media: seen.append((party_id, text, media)))
    inbound = messaging.receive(store.parties.require("TECH-HOU-01"), "DONE", ["https://example.com/photo.jpg"])
    assert inbound.status == "received" and inbound.direction == "inbound"
    assert seen[-1] == ("TECH-HOU-01", "DONE", ["https://example.com/photo.jpg"])


def test_unknown_number_becomes_a_resident_and_reaches_the_resident_handler():
    sc.load("harvey_houston")
    messaging.register()
    seen = []
    messaging.on_inbound("resident", lambda party_id, text, media: seen.append(party_id))
    messaging.receive(messaging.party_for_phone("+12145550999"), "need a dry place for 2 kids")
    party = store.parties.require("RESIDENT-0999")
    assert party.type == "resident" and party.phone == "+12145550999"
    assert seen[-1] == "RESIDENT-0999"


def test_tenant_reply_is_noted_without_raising():
    sc.load("harvey_houston")
    messaging.register()
    messaging.receive(store.parties.require("TEN-001"), "We are moving servers upstairs.")
    notes = [message for message in store.messages.list(party_id="TEN-001") if message.direction == "outbound"]
    assert notes and notes[-1].body.startswith("Noted")
    assert notes[-1].status == "sent"


def test_photon_failure_is_stored_and_does_not_raise(monkeypatch):
    sc.load("harvey_houston")
    monkeypatch.setattr(settings, "messaging_mode", "photon")
    tech = store.parties.require("TECH-HOU-01").model_copy(update={"demo_live": True})
    store.parties.put(tech)
    message = messaging.send(tech.id, "Task", MessageKind.task)
    assert message.status == "failed" and message.error
    assert messaging.status().last_error


def test_routes_simulate_list_and_webhook():
    with TestClient(create_app()) as client:
        client.post("/api/scenarios/harvey_houston/load")
        sent = client.post("/api/demo/simulate-message", json={"party_id": "TECH-HOU-01", "text": "DONE"})
        assert sent.status_code == 200 and sent.json()["status"] == "received"
        resident = client.post("/api/demo/simulate-message", json={"phone": "+12145550199", "text": "need shelter"})
        assert resident.status_code == 200
        assert resident.json()["party_id"] == "RESIDENT-0199"
        listed = client.get("/api/messages", params={"party_id": "RESIDENT-0199"})
        assert listed.status_code == 200 and listed.json()[0]["body"] == "need shelter"
        assert client.get("/api/messaging/status").json()["received"] >= 2
        assert client.post("/api/demo/simulate-message", json={"text": "no sender"}).status_code == 422
        webhook = client.post("/api/webhooks/photon", json={"from": "+15550100002", "text": "BLOCKED gate locked", "id": "evt-1"})
        duplicate = client.post("/api/webhooks/photon", json={"from": "+15550100002", "text": "BLOCKED gate locked", "id": "evt-1"})
        assert webhook.status_code == 200 and webhook.json()["ok"] is True and duplicate.status_code == 200
        bodies = [row["body"] for row in client.get("/api/messages", params={"party_id": "TECH-HOU-01"}).json()]
        assert bodies.count("BLOCKED gate locked") == 1
