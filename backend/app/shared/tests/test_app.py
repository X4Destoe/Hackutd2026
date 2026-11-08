from fastapi.testclient import TestClient

from app.main import create_app
from app.shared import schemas


def test_health_and_contract_types_in_openapi():
    client = TestClient(create_app())
    assert client.get("/api/health").json() == {"ok": True}
    names = set(client.get("/openapi.json").json()["components"]["schemas"])
    missing = [m.__name__ for m in schemas.ALL_MODELS if m.__name__ not in names]
    assert not missing, missing


def test_keyerror_becomes_404():
    app = create_app()

    @app.get("/api/boom")
    def boom():
        raise KeyError("plans: PLAN-404 not found")

    r = TestClient(app).get("/api/boom")
    assert r.status_code == 404 and "PLAN-404" in r.json()["detail"]
