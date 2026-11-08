"""TASK-088: a plain `uvicorn app.main:app` with MESSAGING_MODE=photon + PHOTON_API_KEY sends AND receives real texts."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules import messaging
from app.modules.messaging import photon, polling
from app.shared.config import settings


class FakePoller:
    """Stands in for PhotonPoller: records construction and start, never touches the network."""
    made = []

    def __init__(self, config):
        self.config, self.error, self.started = config, None, 0
        self._thread = None
        FakePoller.made.append(self)

    def start(self):
        self.started += 1

        class Alive:
            @staticmethod
            def is_alive():
                return True
        self._thread = Alive()
        return self


@pytest.fixture
def real_mode(monkeypatch):
    FakePoller.made = []
    cfg = photon.PhotonSettings(_env_file=None, photon_api_key="unit-test-credential", photon_project_id="pho_prj_test",
                                demo_phones="+19725550101:TECH-HOU-01")
    monkeypatch.setattr(photon, "settings", lambda: cfg)
    monkeypatch.setattr(polling, "PhotonPoller", FakePoller)
    monkeypatch.setattr(settings, "messaging_mode", "photon")
    monkeypatch.setattr(messaging, "_AUTOSTART", True)
    monkeypatch.setattr(messaging, "_receiver", None)
    monkeypatch.delenv("PHOTON_RECEIVER", raising=False)
    return cfg


def test_normal_startup_in_photon_mode_starts_one_reply_poller(real_mode):
    with TestClient(create_app()) as c:
        assert len(FakePoller.made) == 1 and FakePoller.made[0].started == 1
        c.post("/api/demo/reset", json={"scenario_id": "uri_dallas"})  # scenario.loaded again: still one poller
        c.post("/api/scenarios/harvey_houston/load")
    assert len(FakePoller.made) == 1


def test_the_live_command_keeps_its_own_receiver(real_mode, monkeypatch):
    monkeypatch.setenv("PHOTON_RECEIVER", "external")
    with TestClient(create_app()):
        pass
    assert FakePoller.made == []


@pytest.mark.parametrize("change", ["sim", "no_key"])
def test_nothing_polls_without_real_mode_and_a_key(real_mode, monkeypatch, change):
    if change == "sim":
        monkeypatch.setattr(settings, "messaging_mode", "sim")
    else:
        real_mode.photon_api_key = photon.SecretStr("")
    with TestClient(create_app()):
        pass
    assert FakePoller.made == []


def test_a_bad_config_is_reported_in_messaging_status_not_a_crash(real_mode, monkeypatch):
    def refuse(config):
        raise photon.PhotonError("Photon API key and project ID must be configured")
    monkeypatch.setattr(polling, "PhotonPoller", refuse)
    with TestClient(create_app()) as c:
        assert "Photon replies are off" in c.get("/api/messaging/status").json()["last_error"]


def test_a_failing_poller_shows_its_reason_in_messaging_status(real_mode):
    with TestClient(create_app()) as c:
        FakePoller.made[0].error = "Photon reply polling failed: Photon API refused the request (401)"
        status = c.get("/api/messaging/status").json()
        assert status["mode"] == "photon" and "401" in status["last_error"]
