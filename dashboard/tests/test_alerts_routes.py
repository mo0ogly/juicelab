"""Alerts CRUD HTTP API + SSE typed event (Phase 2 Task 3).

Not safe under pytest-xdist parallel — module reload pattern.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", "teacher-test-token-very-long-32chars!!")
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_SSE_HEARTBEAT_SEC", "0.5")
    monkeypatch.setenv("DASHBOARD_MONITOR_ENABLED", "0")  # avoid scheduler firing during tests
    for m in ["app", "db", "alerts_routes", "monitor", "sse_pubsub"]:
        if m in sys.modules:
            del sys.modules[m]
    from app import create_app
    return create_app()


AUTH = {"X-Teacher-Token": "teacher-test-token-very-long-32chars!!"}


def test_list_alerts_requires_auth(app):
    c = app.test_client()
    r = c.get("/api/alerts?cohort=demo")
    assert r.status_code in (401, 403)


def test_list_alerts_empty(app):
    c = app.test_client()
    r = c.get("/api/alerts?cohort=demo", headers=AUTH)
    assert r.status_code == 200
    assert r.get_json() == {"alerts": []}


def test_list_alerts_returns_inserted(app):
    import db
    now = datetime.now(timezone.utc).isoformat()
    with db.get_connection() as conn:
        db.insert_alert(conn, "demo", "tok1", "blocked", "xss", now)
        conn.commit()
    c = app.test_client()
    r = c.get("/api/alerts?cohort=demo", headers=AUTH)
    j = r.get_json()
    assert r.status_code == 200
    assert len(j["alerts"]) == 1
    assert j["alerts"][0]["kind"] == "blocked"


def test_ack_alert_sets_ack_at(app):
    import db
    now = datetime.now(timezone.utc).isoformat()
    with db.get_connection() as conn:
        new_id = db.insert_alert(conn, "demo", "tok1", "blocked", "xss", now)
        conn.commit()
    c = app.test_client()
    r = c.post(f"/api/alerts/{new_id}/ack", headers=AUTH)
    assert r.status_code == 200
    assert r.get_json().get("ack_at")
    # Re-ack is idempotent (noop)
    r2 = c.post(f"/api/alerts/{new_id}/ack", headers=AUTH)
    assert r2.status_code == 200
