import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Scenario tests never fetch real-time data (CI has no network guarantee)."""
    monkeypatch.setenv("LIVE_FETCH", "0")
