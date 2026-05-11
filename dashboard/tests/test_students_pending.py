"""Coverage : pending / approve / reject path in students_routes.

Hits /api/students/pending, /api/students/<token>/approve and /reject.
The pending list is populated via /api/cohort/join, then the teacher
acts on it. Reflects the trilateral workflow (prof creates - student
joins - prof validates) wired in cycle 0.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOKEN = "teacher-test-token-very-long-32chars!!"
AUTH = {"X-Teacher-Token": TOKEN}
COHORT = "M2-IA-2026"


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "dashboard.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db", "students_routes", "cohorts_routes", "join_routes"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    flask_app = app_mod.create_app()
    flask_app.testing = True
    return flask_app.test_client()


def _create_cohort_and_join(client, cohort_id=COHORT, student_token="uuid-stud-1", email="s@example.com"):
    client.post("/api/cohorts", headers=AUTH, json={"cohort_id": cohort_id, "label": "Test"})
    return client.post("/api/cohort/join", json={
        "cohort_id": cohort_id, "student_token": student_token, "email": email,
    })


# --- /api/students/pending ----------------------------------------------

def test_pending_requires_auth(isolated_app):
    r = isolated_app.get(f"/api/students/pending?cohort={COHORT}")
    assert r.status_code in (302, 401)


def test_pending_empty(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH, json={"cohort_id": COHORT, "label": "T"})
    r = isolated_app.get(f"/api/students/pending?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200
    assert r.get_json()["pending"] == []


def test_pending_lists_joiners(isolated_app):
    _create_cohort_and_join(isolated_app, student_token="uuid-pend-1", email="p1@e.com")
    _create_cohort_and_join(isolated_app, student_token="uuid-pend-2", email="p2@e.com")
    r = isolated_app.get(f"/api/students/pending?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200
    pending = r.get_json()["pending"]
    tokens = {p["student_token"] for p in pending}
    assert "uuid-pend-1" in tokens
    assert "uuid-pend-2" in tokens


def test_pending_missing_cohort(isolated_app):
    r = isolated_app.get("/api/students/pending", headers=AUTH)
    assert r.status_code in (200, 400)


# --- /api/students/<token>/approve --------------------------------------

def test_approve_requires_auth(isolated_app):
    r = isolated_app.post("/api/students/x/approve",
                          json={"cohort_id": COHORT, "decided_by": "test"})
    assert r.status_code in (302, 401)


def test_approve_unknown_student(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH, json={"cohort_id": COHORT, "label": "T"})
    r = isolated_app.post("/api/students/no-such-student/approve", headers=AUTH,
                          json={"cohort_id": COHORT, "decided_by": "test"})
    assert r.status_code in (200, 404)


def test_approve_pending_promotes_to_validated(isolated_app):
    _create_cohort_and_join(isolated_app, student_token="uuid-app-1", email="a1@e.com")
    r = isolated_app.post("/api/students/uuid-app-1/approve", headers=AUTH,
                          json={"cohort_id": COHORT, "decided_by": "prof@unit"})
    assert r.status_code == 200
    s = isolated_app.get("/api/student/status?student_token=uuid-app-1&cohort_id=" + COHORT)
    assert s.status_code == 200
    assert s.get_json()["status"] == "validated"


# --- /api/students/<token>/reject ---------------------------------------

def test_reject_requires_auth(isolated_app):
    r = isolated_app.post("/api/students/x/reject",
                          json={"cohort_id": COHORT})
    assert r.status_code in (302, 401)


def test_reject_pending_marks_rejected(isolated_app):
    _create_cohort_and_join(isolated_app, student_token="uuid-rej-1", email="r1@e.com")
    r = isolated_app.post("/api/students/uuid-rej-1/reject", headers=AUTH,
                          json={"cohort_id": COHORT, "decided_by": "prof@unit"})
    assert r.status_code == 200
    s = isolated_app.get("/api/student/status?student_token=uuid-rej-1&cohort_id=" + COHORT)
    assert s.get_json()["status"] == "rejected"


def test_reject_then_approve_promotes(isolated_app):
    _create_cohort_and_join(isolated_app, student_token="uuid-flip-1", email="f1@e.com")
    isolated_app.post("/api/students/uuid-flip-1/reject", headers=AUTH,
                      json={"cohort_id": COHORT})
    r = isolated_app.post("/api/students/uuid-flip-1/approve", headers=AUTH,
                          json={"cohort_id": COHORT})
    assert r.status_code == 200
    s = isolated_app.get("/api/student/status?student_token=uuid-flip-1&cohort_id=" + COHORT)
    assert s.get_json()["status"] == "validated"


# --- /admin/students renders with pending count -------------------------

def test_admin_students_shows_pending_count(isolated_app):
    _create_cohort_and_join(isolated_app, student_token="uuid-disp-1", email="d1@e.com")
    r = isolated_app.get(f"/admin/students?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200
    assert b"uuid-disp-1" in r.data or b"pending" in r.data.lower()


# --- /api/students/<token>/detail + /admin/student/<token> -----------

def test_student_detail_api_unknown_404(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH, json={"cohort_id": COHORT, "label": "T"})
    r = isolated_app.get(f"/api/students/nope/detail?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 404


def test_student_detail_api_missing_cohort(isolated_app):
    r = isolated_app.get("/api/students/x/detail", headers=AUTH)
    assert r.status_code in (200, 400)


def test_student_detail_api_requires_auth(isolated_app):
    r = isolated_app.get(f"/api/students/x/detail?cohort={COHORT}")
    assert r.status_code in (302, 401)


def test_student_detail_api_full_dump(isolated_app):
    _create_cohort_and_join(isolated_app, student_token="uuid-detail-1", email="d@e.com")
    isolated_app.post("/api/students/uuid-detail-1/approve", headers=AUTH,
                      json={"cohort_id": COHORT, "decided_by": "prof@unit"})
    isolated_app.post("/api/sync", json={
        "student_token": "uuid-detail-1", "cohort_id": COHORT,
        "event_type": "hint_revealed", "challenge_key": "loginAdminChallenge",
        "data": {"level": "N1", "cost_pct": 5},
        "client_timestamp": "2026-05-11T08:00:00Z",
    })
    isolated_app.post("/api/sync", json={
        "student_token": "uuid-detail-1", "cohort_id": COHORT,
        "event_type": "journal_filled", "challenge_key": "loginAdminChallenge",
        "data": {"phase": "after", "text": "I solved by tampering JWT", "word_count": 5},
        "client_timestamp": "2026-05-11T08:30:00Z",
    })
    r = isolated_app.get(f"/api/students/uuid-detail-1/detail?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200
    body = r.get_json()
    assert body["identity"]["student_token"] == "uuid-detail-1"
    assert body["identity"]["status"] == "validated"
    assert body["total_events"] >= 2
    pc = body["per_challenge"]
    assert len(pc) == 1
    assert pc[0]["challenge_key"] == "loginAdminChallenge"
    assert pc[0]["hint_cost_total"] == 5
    assert pc[0]["journal_after_text"] == "I solved by tampering JWT"
    assert pc[0]["journal_after_words"] == 5


def test_student_detail_page_renders(isolated_app):
    _create_cohort_and_join(isolated_app, student_token="uuid-page-1", email="p@e.com")
    r = isolated_app.get(f"/admin/student/uuid-page-1?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200
    assert b"uuid-page-1" in r.data
