import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.reports.render import markdown_to_html
from app.shared.store import store


@pytest.fixture
def c():
    with TestClient(create_app()) as client:
        yield client


def money(cents):
    from app.modules.reports import money as m
    return m(cents)


def test_executive_summary_matches_the_portfolio_summary(c):
    c.post("/api/timeline", json={"hour": -24})
    bayou = c.get("/api/plans?building_id=BLD-HOU-01&status=proposed").json()[0]["id"]
    c.post(f"/api/plans/{bayou}/approve", json={"by": "MGR-01"})
    c.post("/api/timeline", json={"hour": 0})  # unapproved plans become missed
    s = c.get("/api/portfolio/summary").json()
    r = c.post("/api/reports", json={"kind": "executive_summary"}).json()
    md = r["markdown"]
    for cents in (s["net_exposure_cents"], s["gross_loss_cents"], s["avoided_cents"], s["insurance_recovery_cents"]):
        assert money(cents) in md
    assert f"{s['buildings_at_risk']} buildings at risk" in md and "would have saved" in md and "Bayou Plaza" in md
    assert r["kind"] == "executive_summary" and r["scenario_id"] == "harvey_houston"


def test_tenant_notice_lists_what_management_does_and_who_to_call(c):
    c.post("/api/timeline", json={"hour": -24})
    pid = c.get("/api/plans?building_id=BLD-HOU-01&status=proposed").json()[0]["id"]
    c.post(f"/api/plans/{pid}/approve", json={"by": "MGR-01"})
    md = c.post("/api/reports", json={"kind": "tenant_notice", "building_id": "BLD-HOU-01"}).json()["markdown"]
    assert "Deploy temporary flood barriers" in md and "## What you need to do" in md
    onsite = store.parties.require(store.buildings.require("BLD-HOU-01").onsite_party_id)
    assert onsite.phone in md


def test_send_texts_each_tenant_contact(c):
    b = store.buildings.require("BLD-HOU-01")
    contacts = {t.contact_party_id for t in b.tenants if t.contact_party_id}
    c.post("/api/reports", json={"kind": "tenant_notice", "building_id": b.id, "send": True})
    sent = {m.party_id for m in store.messages.list(direction="outbound") if str(getattr(m.kind, "value", m.kind)) == "tenant_notice"}
    assert contacts and sent == contacts


def test_printable_html_escapes_data_and_prints(c):
    b = store.buildings.require("BLD-HOU-01")
    store.buildings.put(b.model_copy(update={"name": "<script>alert(1)</script> Plaza"}))
    rid = c.post("/api/reports", json={"kind": "tenant_notice", "building_id": "BLD-HOU-01"}).json()["id"]
    page = c.get(f"/api/reports/{rid}/html")
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert "<script>alert" not in page.text and "&lt;script&gt;" in page.text and "@media print" in page.text


def test_tables_and_lists_render():
    out = markdown_to_html("# T\n\n- **a** b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n", "T")
    assert "<li><strong>a</strong> b</li>" in out and "<th>x</th>" in out and "<td>2</td>" in out and "---" not in out


def test_bad_requests_are_rejected(c):
    assert c.post("/api/reports", json={"kind": "tenant_notice"}).status_code == 422
    assert c.post("/api/reports", json={"kind": "nonsense"}).status_code == 422
    assert c.get("/api/reports/RPT-999/html").status_code == 404
    assert c.get("/api/reports").json() == []
