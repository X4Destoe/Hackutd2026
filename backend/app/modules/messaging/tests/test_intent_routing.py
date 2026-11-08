"""TASK-089: four real demo phones play all 25 people; a text is routed by what it says. Fictional 555-01xx numbers."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import messaging
from app.modules.messaging import photon
from app.shared.config import settings
from app.shared.store import store

ME, MANAGER, DALLAS, FORT_MYERS = "+19725550101", "+19725550102", "+19725550103", "+19725550104"


def mapping():
    roles = {"MGR-01": MANAGER, "TECH-HOU-01": ME, "TECH-DAL-01": DALLAS, "TECH-FMY-01": FORT_MYERS}
    order = [ME, MANAGER, DALLAS, FORT_MYERS]
    roles.update({f"TEN-{i:03d}": order[(i - 1) % 4] for i in range(1, 22)})
    return ",".join(f"{phone}:{pid}" for pid, phone in roles.items())


@pytest.fixture
def live(monkeypatch):
    """Real-Photon mode with the shared-phone mapping; sends are recorded instead of hitting the provider."""
    sent = []
    monkeypatch.setattr(settings, "demo_phones", mapping())
    monkeypatch.setattr(settings, "messaging_mode", "photon")
    cfg = photon.PhotonSettings(_env_file=None, photon_api_key="unit-test-credential", photon_project_id="pho_prj_test",
                                demo_phones=mapping(), photon_claims_alert_phone=MANAGER)
    monkeypatch.setattr(photon, "settings", lambda: cfg)
    monkeypatch.setattr(photon.PhotonChannel, "send_text", lambda self, to, body, media: sent.append((to, body)) or "ph")
    with TestClient(create_app()) as c:
        c.sent = sent
        yield c


def text(phone, body):
    """What the poller/webhook does with a real inbound text."""
    party = messaging.party_for_message(phone, body)
    if not party.demo_live:
        party = store.parties.put(party.model_copy(update={"demo_live": True}))
    messaging.receive(party, body, [])
    return party


def wait_for(c, predicate):
    import time
    deadline = time.time() + 5
    while time.time() < deadline and not predicate():
        time.sleep(0.02)
    return predicate()


def bodies_to(c, phone):
    return [body for to, body in c.sent if to == phone]


def test_a_claim_request_from_a_staff_phone_gets_the_state_farm_adjuster_and_alerts_the_claims_contact(live):
    live.post("/api/timeline", json={"hour": 0})
    party = text(DALLAS, "I need to file a claim, our house flooded")  # 470 also plays the Dallas technician
    assert party.type == "resident" and party.phone == DALLAS
    assert wait_for(live, lambda: any(b.startswith("State Farm emergency claims adjuster") for b in bodies_to(live, DALLAS)))
    adjuster = next(b for b in bodies_to(live, DALLAS) if b.startswith("State Farm emergency claims adjuster"))
    assert "Call +1" in adjuster and "google.com/maps" in adjuster and len(adjuster) <= 320
    assert wait_for(live, lambda: any("new claims-assistance request" in b for b in bodies_to(live, MANAGER)))


def test_a_flooded_resident_gets_a_shelter_and_an_adjuster_text_on_their_real_phone(live):
    live.post("/api/timeline", json={"hour": 0})
    text(ME, "our apartment flooded, 2 kids, need a dry place")
    assert wait_for(live, lambda: any(b.startswith("Go to") for b in bodies_to(live, ME)))
    assert wait_for(live, lambda: any("emergency claims adjuster" in b for b in bodies_to(live, ME)))


def test_done_from_a_shared_phone_still_closes_the_technicians_work_order(live):
    live.post("/api/timeline", json={"hour": -24})
    plan = live.get("/api/plans?building_id=BLD-HOU-01&status=proposed").json()[0]["id"]
    live.post(f"/api/plans/{plan}/approve", json={"by": "MGR-01"})
    assert wait_for(live, lambda: bodies_to(live, ME))  # the task text reaches the real phone
    wo = live.get("/api/workorders?building_id=BLD-HOU-01").json()[0]["id"]
    assert text(ME, "on my way").id == "TECH-HOU-01"  # chatter stays a progress note, not a resident request
    assert text(ME, f"DONE {wo}").id == "TECH-HOU-01"
    assert next(w["status"] for w in live.get("/api/workorders?building_id=BLD-HOU-01").json() if w["id"] == wo) == "done"


def test_yes_from_the_manager_phone_approves_although_tenants_share_it(live):
    live.post("/api/timeline", json={"hour": -24})
    plan = live.get("/api/plans?building_id=BLD-HOU-02&status=proposed").json()[0]["id"]
    assert text(MANAGER, f"YES {plan}").id == "MGR-01"
    assert live.get("/api/plans?building_id=BLD-HOU-02").json()[0]["status"] in ("approved", "executing", "done")


def test_two_technicians_on_one_phone_done_reaches_the_owner_of_the_work_order(live, monkeypatch):
    for tech in ("TECH-HOU-01", "TECH-DAL-01"):
        store.parties.put(store.parties.require(tech).model_copy(update={"phone": ME}))
    live.post("/api/scenarios/uri_dallas/load")
    for tech in ("TECH-HOU-01", "TECH-DAL-01"):  # the load reseeds parties from DEMO_PHONES; share the phone again
        store.parties.put(store.parties.require(tech).model_copy(update={"phone": ME}))
    live.post("/api/timeline", json={"hour": -24})
    building = next(b for b in store.buildings.list() if b.onsite_party_id == "TECH-DAL-01")
    plan = live.get(f"/api/plans?building_id={building.id}&status=proposed").json()[0]["id"]
    live.post(f"/api/plans/{plan}/approve", json={"by": "MGR-01"})
    wo = live.get(f"/api/workorders?building_id={building.id}").json()[0]["id"]
    assert messaging.party_for_message(ME, f"DONE {wo}").id == "TECH-DAL-01"


def test_a_phone_that_plays_nobody_is_unchanged():
    assert messaging.party_for_message("+19725550199", "hello").id == messaging.party_for_phone("+19725550199").id


def test_the_reply_poller_uses_intent_routing(live):
    """A real reply arriving through Photon polling reaches the resident flow, not the phone's technician role."""
    import httpx
    from datetime import datetime, timezone
    from app.modules.messaging import polling
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    msg = {"id": "msg-intent-1", "projectId": "pho_prj_test", "platform": "imessage", "status": "received", "createdAt": now,
           "space": {"id": "s", "kind": "direct"}, "sentBy": {"id": "u", "kind": "human", "handle": DALLAS},
           "content": {"type": "text", "format": "plain", "text": "I need to file a claim"}}
    fake = httpx.MockTransport(lambda req: httpx.Response(200, json={"items": [msg]}))
    live.post("/api/timeline", json={"hour": 0})
    assert polling.PhotonPoller(photon.settings(), httpx.Client(transport=fake)).poll_once() == 1
    assert wait_for(live, lambda: any(b.startswith("State Farm emergency claims adjuster") for b in bodies_to(live, DALLAS)))
