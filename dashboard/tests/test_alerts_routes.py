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


# --- Group ack + display name (alerts panel groups identical alerts) ---

def _seed_group(db):
    now = datetime.now(timezone.utc).isoformat()
    with db.get_connection() as conn:
        ids = [db.insert_alert(conn, "demo", "tok1", "idle", None, now) for _ in range(3)]
        other_kind = db.insert_alert(conn, "demo", "tok1", "blocked", "xss", now)
        other_student = db.insert_alert(conn, "demo", "tok2", "idle", None, now)
        other_cohort = db.insert_alert(conn, "other", "tok1", "idle", None, now)
        conn.commit()
    return ids, [other_kind, other_student, other_cohort]


def test_ack_group_acks_only_matching_alerts(app):
    import db
    ids, others = _seed_group(db)
    c = app.test_client()
    r = c.post(f"/api/alerts/{ids[0]}/ack-group", headers=AUTH)
    assert r.status_code == 200
    assert r.get_json()["acked"] == 3
    with db.get_connection() as conn:
        state = dict(conn.execute("SELECT id, ack_at IS NOT NULL FROM alerts").fetchall())
    assert all(state[i] == 1 for i in ids)
    assert all(state[i] == 0 for i in others)
    # Idempotent : nothing left to ack in that group.
    r2 = c.post(f"/api/alerts/{ids[1]}/ack-group", headers=AUTH)
    assert r2.status_code == 200 and r2.get_json()["acked"] == 0


def test_ack_group_unknown_id_is_404(app):
    c = app.test_client()
    r = c.post("/api/alerts/999999/ack-group", headers=AUTH)
    assert r.status_code == 404


def test_ack_group_requires_auth(app):
    c = app.test_client()
    assert c.post("/api/alerts/1/ack-group").status_code in (401, 403)


def test_list_alerts_carries_display_name(app):
    import db
    now = datetime.now(timezone.utc).isoformat()
    with db.get_connection() as conn:
        db.upsert_student_name(conn, "demo", "tok1", "Alice", now)
        db.insert_alert(conn, "demo", "tok1", "idle", None, now)
        db.insert_alert(conn, "demo", "tok-unnamed", "idle", None, now)
        conn.commit()
    c = app.test_client()
    alerts = c.get("/api/alerts?cohort=demo", headers=AUTH).get_json()["alerts"]
    by_token = {a["student_token"]: a["display_name"] for a in alerts}
    assert by_token == {"tok1": "Alice", "tok-unnamed": None}


def test_list_alerts_grouped(app):
    import db
    ids, _others = _seed_group(db)
    with db.get_connection() as conn:
        db.ack_alert(conn, ids[0], datetime.now(timezone.utc).isoformat())
        conn.commit()
    c = app.test_client()
    alerts = c.get("/api/alerts?cohort=demo&group=true", headers=AUTH).get_json()["alerts"]
    got = {(a["student_token"], a["kind"], a["challenge_key"]): a for a in alerts}
    # 3 groups in cohort demo; the acked alert no longer counts; cohort "other" excluded.
    assert set(got) == {("tok1", "idle", None), ("tok1", "blocked", "xss"), ("tok2", "idle", None)}
    grp = got[("tok1", "idle", None)]
    assert grp["count"] == 2 and grp["id"] == ids[2] and grp["first_at"]
