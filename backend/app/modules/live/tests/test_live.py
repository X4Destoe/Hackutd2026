import json
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import app.modules.live as live
from app.modules.live import feeds

FX = Path(__file__).parent / "fixtures"
BUILDINGS = [
    {"id": "B1", "city": "Houston", "lat": 29.7589, "lon": -95.3677},
    {"id": "B2", "city": "Houston", "lat": 29.7600, "lon": -95.3700},
]


def fresh_state():
    return {"snapshot": None, "loaded_at": 0.0, "last_attempt": 0.0, "refreshing": False, "errors": [], "hourly_urls": {}}


def fixture(name):
    return json.loads((FX / name).read_text())


def transport(fail=()):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        assert "User-Agent" in request.headers and "OperationStorm" in request.headers["User-Agent"]  # NWS requires one
        for key in fail:
            if key in url:
                return httpx.Response(503)
        if "/alerts/active" in url:
            return httpx.Response(200, json=fixture("alerts.json"))
        if "/points/" in url:
            return httpx.Response(200, json=fixture("points.json"))
        if "forecast/hourly" in url:
            return httpx.Response(200, json=fixture("forecast_hourly.json"))
        if "waterservices.usgs.gov" in url:
            return httpx.Response(200, json=fixture("usgs_iv.json"))
        return httpx.Response(404)
    return httpx.MockTransport(handler)


def mock_client(**kw):
    return httpx.Client(transport=transport(**kw), headers={"User-Agent": feeds.USER_AGENT})


@pytest.mark.parametrize("text,mph", [("5 mph", 5), ("10 to 20 mph", 20), ("", 0), (None, 0)])
def test_wind_parsing(text, mph):
    assert feeds.parse_wind_mph(text) == mph


def test_snapshot_from_recorded_feeds():
    snap, errors = live.build_snapshot(mock_client(), BUILDINGS)
    assert errors == []
    alerts = snap["alerts"]["features"]
    assert len(alerts) == 3 and snap["alerts"]["without_area"] == 1  # zone-only alerts are counted, not drawn
    assert set(alerts[0]["properties"]) == set(feeds.ALERT_FIELDS)
    hou = snap["conditions"]["Houston"]
    assert hou["hours"] == 48 and hou["min_temp_f"] <= hou["now_temp_f"] and hou["max_wind_mph"] >= 5
    assert len(snap["gauges"]) == 4
    assert snap["building_gauges"]["B1"]["distance_mi"] <= live.GAUGE_RADIUS_MI


def test_each_feed_fails_independently():
    snap, errors = live.build_snapshot(mock_client(fail=("waterservices",)), BUILDINGS)
    assert snap["alerts"]["features"] and snap["conditions"] and snap["gauges"] == []
    assert errors == ["USGS gauges Houston: HTTPStatusError"]


def test_snapshot_never_waits_for_the_network(monkeypatch, tmp_path):
    monkeypatch.setattr(live, "CACHE_FILE", tmp_path / "last.json")
    monkeypatch.setattr(live, "_state", fresh_state())
    monkeypatch.setattr(live, "_portfolio", lambda: BUILDINGS)
    monkeypatch.setattr(feeds, "client", lambda timeout=15.0: _SlowClient())
    t = time.perf_counter()
    first = live.snapshot()  # seed from disk, refresh starts in the background
    assert time.perf_counter() - t < 0.2
    assert first["fetched_at"]  # the committed seed is a real recorded snapshot
    deadline = time.time() + 5
    while time.time() < deadline and live.status()["refreshing"]:
        time.sleep(0.05)
    assert live._state["snapshot"]["gauges"] and (tmp_path / "last.json").exists()  # fresh data cached to disk
    assert live.status()["stale"] is False


class _SlowClient(httpx.Client):
    def __init__(self):
        super().__init__(transport=transport(), headers={"User-Agent": feeds.USER_AGENT})

    def send(self, *a, **kw):
        time.sleep(0.05)
        return super().send(*a, **kw)


def test_status_route_is_honest_about_outages(monkeypatch):
    monkeypatch.setenv("LIVE_FETCH", "0")
    from app.main import create_app
    with TestClient(create_app()) as c:
        s = c.get("/api/live/status").json()
        assert "power-outage" in " ".join(s["notes"]) and s["sources"]
        assert c.get("/api/live/alerts").json()["type"] == "FeatureCollection"


def test_a_failed_feed_keeps_its_last_good_data_and_reports_it():
    warm, _ = live.build_snapshot(mock_client(), BUILDINGS)
    snap, errors = live.build_snapshot(mock_client(fail=("waterservices",)), BUILDINGS, previous=warm)
    assert len(snap["gauges"]) == 4 and snap["building_gauges"]  # last good readings retained
    assert snap["feeds"]["gauges:Houston"] == {"as_of": warm["feeds"]["gauges:Houston"]["as_of"], "error": "HTTPStatusError"}
    assert snap["feeds"]["alerts"]["error"] is None
    cold, _ = live.build_snapshot(mock_client(fail=("waterservices",)), BUILDINGS)
    assert cold["feeds"]["gauges:Houston"]["as_of"] is None  # never fetched = unknown, not 'no gauges'


def test_status_marks_failed_or_missing_feeds_stale(monkeypatch):
    snap, _ = live.build_snapshot(mock_client(fail=("waterservices",)), BUILDINGS)
    monkeypatch.setattr(live, "_state", {**fresh_state(), "snapshot": snap})
    s = live.status()
    assert s["stale"] is True and s["feeds"]["gauges:Houston"]["stale"] is True and s["feeds"]["alerts"]["stale"] is False


def test_total_failure_backs_off_instead_of_retrying_every_request(monkeypatch, tmp_path):
    monkeypatch.setattr(live, "CACHE_FILE", tmp_path / "last.json")
    monkeypatch.setattr(live, "SEED_FILE", tmp_path / "none.json")
    monkeypatch.setattr(live, "_state", fresh_state())
    monkeypatch.setattr(live, "_portfolio", lambda: BUILDINGS)
    monkeypatch.setenv("LIVE_FETCH", "1")
    starts = []
    real = live._refresh_worker
    monkeypatch.setattr(live, "_refresh_worker", lambda: (starts.append(1), real()))
    monkeypatch.setattr(feeds, "client", lambda timeout=15.0: mock_client(fail=("api.weather.gov", "waterservices")))
    live.refresh(block=True)
    assert len(starts) == 1 and live._state["errors"]
    for _ in range(5):
        live.snapshot()
    time.sleep(0.1)
    assert len(starts) == 1  # no retry storm: next attempt only after RETRY_SECONDS
