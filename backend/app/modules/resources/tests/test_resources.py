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
    shelter = next(t for t in texts_to(pid) if t.startswith("Go to"))
    assert "1001 Avenida de las Americas" in shelter and "google.com/maps" in shelter and len(shelter) <= 320
    adjuster = next(t for t in texts_to(pid) if "emergency claims adjuster" in t)
    assert "Galleria" in adjuster and "+17135550104" in adjuster and len(adjuster) <= 320
    assert store.resources.require("RES-HOU-04").used == 60  # pointing them at the adjuster does not take a spot


def test_spanish_text_gets_a_spanish_reply(c):
    step(c, 0)
    pid = text(c, "+17135550112", "se inundó mi casa, necesito refugio, 4 personas")
    assert any(t.startswith("Vaya a") for t in texts_to(pid))
    assert any(t.startswith("Ajustador de reclamos de emergencia de State Farm") for t in texts_to(pid))


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
    assert any(t.startswith("Change of plan: Bayou Community Center Shelter is no longer safe") for t in texts_to(pid))


def test_unrouted_when_nothing_fits(c):
    step(c, 0)
    pid = text(c, "+17135550116", "we need a dry place for 50000 people")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert ref.status == "unrouted" and any("flagged for coordinator follow-up" in t for t in texts_to(pid))


def test_routes(c):
    assert len(c.get("/api/resources?city=Houston").json()) == 6
    assert c.get("/api/referrals").json() == []


def test_reroute_that_takes_the_last_spots_marks_the_site_full(c):
    step(c, -24)
    pid = text(c, "+17135550117", "we need a dry place to stay, memorial area")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert ref.resource_id == "RES-HOU-03"
    # make the nearest alternative have exactly one spot left
    for rid in ("RES-HOU-01", "RES-HOU-02", "RES-HOU-05"):
        r = store.resources.require(rid)
        store.resources.put(r.model_copy(update={"used": r.capacity - (ref.people if rid == "RES-HOU-01" else 0)}))
    step(c, 0)
    moved = store.referrals.require(ref.id)
    assert moved.resource_id == "RES-HOU-01"
    site = store.resources.require("RES-HOU-01")
    assert site.used == site.capacity and site.status == "full"


def test_replies_never_call_the_llm(c, monkeypatch):
    from app.modules import ai
    monkeypatch.setattr(ai, "compose", lambda *a, **k: (_ for _ in ()).throw(AssertionError("compose called")))
    step(c, 0)
    pid = text(c, "+17135550118", "flooded, need shelter for 2")
    assert any(t.startswith("Go to") for t in texts_to(pid))  # the adjuster text follows the shelter text


def test_hurricane_force_wind_means_shelter_in_place_then_automatic_routing(c):
    c.post("/api/scenarios/ian_fort_myers/load")
    step(c, 0)  # Ian landfall: every site is in hurricane-force wind
    pid = text(c, "+12395550100", "we need shelter, 2 people")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert ref.status == "unrouted" and "shelter in place" in ref.history[-1]
    assert texts_to(pid)[-1].startswith("Hurricane-force winds now: stay where you are")
    step(c, 48)  # winds drop: the waiting resident is routed and told where to go, without texting again
    ref = store.referrals.require(ref.id)
    site = store.resources.require(ref.resource_id)
    assert ref.status == "routed" and "a safe site opened" in ref.history[-1]
    assert texts_to(pid)[-1].startswith(f"Go to {site.name}")


def test_shelter_in_place_texts_fit_one_sms():
    assert all(len(t) <= 320 for t in resources.SHELTER.values())


def test_a_claim_request_is_sent_straight_to_the_adjuster(c):
    step(c, 0)
    pid = text(c, "+17135550119", "I need to file a claim")
    ref = next(r for r in store.referrals.list() if r.party_id == pid)
    assert ref.resource_id == "RES-HOU-04"
    reply = texts_to(pid)[-1]
    assert reply.startswith("State Farm emergency claims adjuster") and "policy number" in reply and len(reply) <= 320


def test_an_unsafe_claims_site_is_not_named(c):
    bayou = store.resources.require("RES-HOU-03")
    desk = store.resources.require("RES-HOU-04")
    store.resources.put(desk.model_copy(update={"lat": bayou.lat, "lon": bayou.lon}))
    step(c, 0)
    assert store.resources.require("RES-HOU-04").status == "unsafe"
    pid = text(c, "+17135550120", "our apartment flooded, 2 kids, need a dry place")
    assert all("Galleria" not in t and "claims adjuster" not in t.lower() for t in texts_to(pid))


def test_a_long_adjuster_text_keeps_its_address_and_map_link():
    site = schemas.Resource(id="X", type="claim_site", name="State Farm Catastrophe Claims Site " + "Galleria " * 12,
                            address="5100 Post Oak Blvd, Houston", city="Houston", lat=29.74, lon=-95.46, capacity=10,
                            status="open", hours="24 hours", source="statefarm", phone="+17135550104")
    for lang in ("en", "es", "vi"):
        body = resources._adjuster_message(site, 3.2, lang)
        assert len(body) <= 320 or "google.com/maps" in body
        assert "5100 Post Oak Blvd" in body and body.rstrip().endswith("29.7400,-95.4600")
