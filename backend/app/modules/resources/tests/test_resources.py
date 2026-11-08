import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import resources
from app.shared import schemas
from app.shared.store import store


@pytest.fixture
def c():
    with TestClient(create_app()) as client:
        yield client


def step(c, hour):
    assert c.post("/api/timeline", json={"hour": hour}).status_code == 200


def texts_to(party_id):
    return [m.body for m in store.messages.list(party_id=party_id, direction="outbound")]


def text(c, phone, body):
    r = c.post("/api/demo/simulate-message", json={"phone": phone, "text": body})
    assert r.status_code == 200
    return r.json()["party_id"]


def test_flooded_community_center_is_unsafe_at_impact_and_never_chosen(c):
    step(c, 0)
    assert store.resources.require("RES-HOU-03").status == "unsafe"
    for i in range(5):
        pid = text(c, f"+1713555010{i}", "our apartment flooded, need a dry place")
        ref = next(r for r in store.referrals.list() if r.party_id == pid)
        assert ref.resource_id != "RES-HOU-03"


def test_family_routed_to_nearest_safe_shelter_with_spots_reserved(c):
    step(c, 0)
    before = store.resources.require("RES-HOU-01").used
    pid = text(c, "+17135550111", "our apartment flooded, 2 kids, need a dry place")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert ref.status == "routed" and ref.people == 3 and ref.resource_id == "RES-HOU-01"  # George R. Brown
    assert store.resources.require("RES-HOU-01").used == before + 3
    reply = texts_to(pid)[-1]
    assert "1001 Avenida de las Americas" in reply and "google.com/maps" in reply and len(reply) <= 320


def test_spanish_text_gets_a_spanish_reply(c):
    step(c, 0)
    pid = text(c, "+17135550112", "se inundó mi casa, necesito refugio, 4 personas")
    assert texts_to(pid)[-1].startswith("Vaya a")


def test_urgent_medical_gets_911_guidance_and_is_flagged(c):
    step(c, 0)
    pid = text(c, "+17135550113", "my dad is on oxygen and the power is out, he is hurt")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert "medical" in ref.needs and "URGENT" in ref.history[0]
    assert any("911" in t for t in texts_to(pid))


def test_cbre_help_site_can_receive_referrals(c):
    step(c, 0)
    galleria = store.buildings.require("BLD-HOU-04")
    resources.register_site(schemas.Resource(id="RES-CBRE-BLD-HOU-04", type="cbre_help_site", name="Galleria Medical Offices (CBRE)",
                                             address=galleria.address, city="Houston", lat=galleria.lat, lon=galleria.lon,
                                             capacity=galleria.host_capacity, status="open", needs_served=["shelter"],
                                             utility_node_id=galleria.utility_node_id, hours="24 hours", source="cbre", building_id=galleria.id))
    pid = text(c, "+17135550114", "flooded in the galleria area, need shelter for 2 people")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert ref.resource_id == "RES-CBRE-BLD-HOU-04"


def test_site_losing_power_reroutes_its_referrals_with_a_change_of_plan_text(c):
    step(c, -24)  # forecast: nothing has happened yet, the community center is still open and nearest
    pid = text(c, "+17135550115", "we need a dry place to stay, memorial area")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert ref.resource_id == "RES-HOU-03"
    step(c, 0)  # its substation goes down and the bayou floods
    ref = store.referrals.require(ref.id)
    assert ref.status == "rerouted" and ref.resource_id != "RES-HOU-03"
    assert store.resources.require("RES-HOU-03").used == 40  # spots released
    assert any("previous site is unavailable" in t for t in texts_to(pid))


def test_unrouted_when_nothing_fits(c):
    step(c, 0)
    pid = text(c, "+17135550116", "we need a dry place for 50000 people")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert ref.status == "unrouted" and "coordinator" in texts_to(pid)[-1]


def test_routes(c):
    assert len(c.get("/api/resources?city=Houston").json()) == 6
    assert c.get("/api/referrals").json() == []
