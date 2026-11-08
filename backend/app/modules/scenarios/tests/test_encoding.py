"""Windows code-page defaults must not corrupt UTF-8 scenario data or report metadata."""
from pathlib import Path

from fastapi.testclient import TestClient
from app.main import create_app
from app.modules import scenarios


def test_timeline_and_printable_report_preserve_utf8_on_windows(monkeypatch):
    original = Path.read_text

    def windows_read(path, encoding=None, errors=None):
        # Reproduce Windows' legacy default even when tests run on Linux.
        return original(path, encoding=encoding or 'cp1252', errors=errors)

    monkeypatch.setattr(Path, 'read_text', windows_read)
    scenarios._file_scenario.cache_clear()
    scenarios._file_anchors.cache_clear()
    try:
        with TestClient(create_app()) as client:
            assert client.post('/api/demo/reset', json={'scenario_id': 'harvey_houston'}).status_code == 200
            timeline = client.get('/api/timeline').json()
            assert timeline[0]['label'] == '\u221248h \u00b7 Forecast'
            metadata = client.get('/api/scenarios').json()
            harvey = next(s for s in metadata if s['id'] == 'harvey_houston')
            assert '\u2013' in harvey['date_label']
            response = client.post('/api/reports', json={'kind': 'executive_summary'})
            assert response.status_code == 200
            report = response.json()
            page = client.get(f"/api/reports/{report['id']}/html")
            assert 'charset=utf-8' in page.headers['content-type'].lower()
            assert '\u221248h' in page.text and '\u2013' in page.text
            assert '\u00e2\u20ac' not in page.text and '\u00c2\u00b7' not in page.text
    finally:
        scenarios._file_scenario.cache_clear()
        scenarios._file_anchors.cache_clear()
