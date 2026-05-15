"""Phase 2 Task 4 : alerts panel UI markup smoke.

Verifies that the dashboard.html template renders the alerts panel
partial with the expected hook ids and ARIA labelling, so the live
SSE `alert` event listener has somewhere to attach.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOKEN = "teacher-test-token-very-long-32chars!!"
AUTH = {"X-Teacher-Token": TOKEN}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    monkeypatch.setenv("DASHBOARD_SSE_HEARTBEAT_SEC", "0.5")
    for m in ("app", "db", "sse_pubsub", "sse_routes"):
        if m in sys.modules:
            del sys.modules[m]
    from app import create_app
    a = create_app()
    a.testing = True
    c = a.test_client()
    # Cohort must exist before /dashboard can render the matrix.
    r = c.post("/api/cohorts", json={"cohort_id": "demo", "label": "demo"}, headers=AUTH)
    assert r.status_code in (200, 201), r.data
    return c


def test_dashboard_renders_alerts_panel(client):
    r = client.get("/dashboard?cohort=demo", headers=AUTH)
    assert r.status_code == 200, r.data
    body = r.data.decode("utf-8")
    assert 'id="alerts-panel"' in body, "alerts panel root id missing"
    assert 'id="alerts-list"' in body, "alerts list ul id missing"
    assert "/api/alerts?cohort=" in body, "boot fetch for /api/alerts missing"
    assert "addEventListener('alert'" in body or 'addEventListener("alert"' in body, (
        "EventSource 'alert' listener missing"
    )


def test_alerts_panel_has_aria_label(client):
    r = client.get("/dashboard?cohort=demo", headers=AUTH)
    body = r.data.decode("utf-8")
    assert "alerts-panel" in body
    # The aside carries aria-label translated via t('ALERT_TITLE').
    assert "aria-label=" in body
    # Empty state placeholder must be there so the panel is not blank.
    assert 'id="alerts-empty"' in body
