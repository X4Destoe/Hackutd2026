"""Smoke the demo path the modules have to survive together.

Covers the backend half of docs/prd/00-overview.md §7: each scenario recomputes in under a second,
every hour's waterfall balances, approving the top Fix-First plan creates work orders and texts,
a resident is routed only to a safe open site (and told about a claims adjuster), and both reports
render. No LLM key and no Photon. The timed click-through and a real handset are demo-tuning and
photon-rehearsal.
"""
import time

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import impact

RESIDENT = {
    "Houston": ("+17135550901", "our apartment flooded, 2 kids, need a dry place"),
    "Dallas": ("+12145550901", "it is freezing and we have no heat, 2 kids"),
    "Fort Myers": ("+12395550901", "our apartment flooded, 2 kids, need a dry place"),
}


def _waterfall(c: TestClient, hour: int) -> dict:
    moved = c.post("/api/timeline", json={"hour": hour})
    assert moved.status_code == 200 and moved.json()["step_hour"] == hour, moved.text
    impacts = c.get("/api/impact")
    assert impacts.status_code == 200 and impacts.json(), impacts.text
    for row in impacts.json():
        money = row["money"]
        assert money["net_exposure_cents"] == (
            money["property_damage_cents"] + money["rent_abatement_cents"]
            + money["sla_penalty_cents"] + money["operations_cents"] - money["insurance_recovery_cents"]
        )
        assert money["net_exposure_cents"] >= 0
    overlays = c.get("/api/overlays")
    assert overlays.status_code == 200 and overlays.json().get("type") == "FeatureCollection"
    summary = c.get("/api/portfolio/summary")
    assert summary.status_code == 200, summary.text
    totals = summary.json()
    assert totals["step_hour"] == hour
    assert totals["gross_loss_cents"] - totals["insurance_recovery_cents"] == totals["net_exposure_cents"]
    return totals


def _ask(c: TestClient, phone: str, text: str) -> tuple[dict, list[str]]:
    sent = c.post("/api/demo/simulate-message", json={"phone": phone, "text": text})
    assert sent.status_code == 200, sent.text
    party = sent.json()["party_id"]
    referral = next(row for row in c.get("/api/referrals").json() if row["party_id"] == party)
    replies = [m["body"] for m in c.get("/api/messages").json() if m["party_id"] == party and m["direction"] == "outbound"]
    return referral, replies


def _assert_routed(c: TestClient, meta: dict, referral: dict, replies: list[str], hour: int) -> None:
    assert referral["status"] == "routed" and referral["people"] == 3, (meta["id"], referral)
    site = next(row for row in c.get("/api/resources").json() if row["id"] == referral["resource_id"])
    assert site["city"] == meta["city"] and site["status"] == "open"
    assert impact.site_safe(site["lat"], site["lon"], site.get("utility_node_id"), hour)
    assert any(body.startswith("Go to") for body in replies)
    assert any("emergency claims adjuster" in body for body in replies)
    assert all(len(body) <= 320 for body in replies)


def test_each_scenario_steps_approves_routes_and_reports():
    with TestClient(create_app()) as c:
        reset = c.post("/api/demo/reset")
        assert reset.status_code == 200
        assert reset.json()["messaging_mode"] == "sim"
        assert reset.json()["llm_provider"] == "templates"
        listed = c.get("/api/scenarios")
        assert listed.status_code == 200
        scenarios = listed.json()
        assert {s["id"] for s in scenarios} >= {"harvey_houston", "uri_dallas", "ian_fort_myers"}

        for meta in scenarios:
            started = time.perf_counter()
            loaded = c.post(f"/api/scenarios/{meta['id']}/load")
            elapsed = time.perf_counter() - started
            assert loaded.status_code == 200, loaded.text
            assert elapsed < 1.0, f"{meta['id']} took {elapsed:.2f}s"
            state = loaded.json()
            assert state["scenario_id"] == meta["id"] and state["messaging_mode"] == "sim"
            assert state["llm_provider"] == "templates"

            approved = None
            saw_savings = False
            for hour in meta["step_hours"]:
                totals = _waterfall(c, hour)
                if approved is None:
                    ranked = c.get("/api/fix-first")
                    assert ranked.status_code == 200, ranked.text
                    if ranked.json():
                        top = ranked.json()[0]
                        decision = c.post(f"/api/plans/{top['plan_id']}/approve", json={"by": "e2e smoke"})
                        assert decision.status_code == 200, decision.text
                        approved = decision.json()
                        assert approved["status"] in ("approved", "executing")
                        orders = c.get("/api/workorders").json()
                        assert any(order["plan_id"] == approved["id"] for order in orders)
                        texts = c.get("/api/messages").json()
                        assert any(message["direction"] == "outbound" for message in texts)
                        totals = c.get("/api/portfolio/summary").json()
                if hour == 0 and approved is not None:
                    assert totals["actions_approved"] >= 1
                    assert totals["avoided_cents"] > 0
                    assert totals["net_exposure_cents"] < totals["gross_loss_cents"]
                    saw_savings = True

            assert approved is not None, meta["id"]
            assert saw_savings, meta["id"]
            _waterfall(c, 0)

            phone, ask = RESIDENT[meta["city"]]
            referral, replies = _ask(c, phone, ask)
            if meta["id"] == "ian_fort_myers":
                # Cat-4 wind at landfall is over 74 mph across the city, so every site is unsafe.
                assert referral["status"] == "unrouted" and referral["resource_id"] is None
                assert any("coordinator follow-up" in body for body in replies)
                assert not any(body.startswith("Go to") or "claims adjuster" in body.lower() for body in replies)
                _waterfall(c, 48)  # wind has dropped; the beach shelter is still under surge
                referral, replies = _ask(c, "+12395550902", ask)
                _assert_routed(c, meta, referral, replies, 48)
                assert referral["resource_id"] != "RES-FMY-02"  # still under surge; the hotel inland is closer
            else:
                _assert_routed(c, meta, referral, replies, 0)
                if meta["city"] == "Houston":
                    assert referral["resource_id"] != "RES-HOU-03"

            summary = c.post("/api/reports", json={"kind": "executive_summary"})
            assert summary.status_code == 200, summary.text
            report = summary.json()
            page = c.get(f"/api/reports/{report['id']}/html")
            assert page.status_code == 200 and "text/html" in page.headers["content-type"]
            assert meta["name"] in page.text

            notice = c.post("/api/reports", json={"kind": "tenant_notice", "building_id": approved["building_id"], "send": True})
            assert notice.status_code == 200, notice.text
            assert notice.json()["building_id"] == approved["building_id"]
            building = next(b for b in c.get("/api/buildings").json() if b["id"] == approved["building_id"])
            printable = c.get(f"/api/reports/{notice.json()['id']}/html")
            assert printable.status_code == 200 and building["name"] in printable.text
            assert any(m["kind"] == "tenant_notice" for m in c.get("/api/messages").json())
