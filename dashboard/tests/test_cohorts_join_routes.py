"""Coverage : cohorts_routes + join_routes.

Uses the same isolated_app fixture pattern as test_app.py : fresh sqlite,
fresh teacher token, fresh CORS allowlist. Covers the four CRUD paths on
/api/cohorts plus the three public join endpoints.
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


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "dashboard.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db", "cohorts_routes", "join_routes"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    flask_app = app_mod.create_app()
    flask_app.testing = True
    return flask_app.test_client()


# --- /api/cohorts CRUD ---------------------------------------------------

def test_admin_cohorts_html_requires_auth(isolated_app):
    r = isolated_app.get("/admin/cohorts")
    assert r.status_code in (302, 401)


def test_admin_cohorts_html_renders_with_auth(isolated_app):
    r = isolated_app.get("/admin/cohorts", headers=AUTH)
    assert r.status_code == 200
    assert b"cohort" in r.data.lower() or b"cohorte" in r.data.lower()


def test_get_cohorts_empty(isolated_app):
    r = isolated_app.get("/api/cohorts", headers=AUTH)
    assert r.status_code == 200
    body = r.get_json()
    assert isinstance(body.get("cohorts"), list)


def test_post_cohort_create(isolated_app):
    r = isolated_app.post("/api/cohorts", headers=AUTH,
                          json={"cohort_id": "TEST-COHORT-1", "label": "Test 1"})
    assert r.status_code in (200, 201)
    body = r.get_json()
    assert body.get("cohort_id") == "TEST-COHORT-1" or body.get("ok") is True


def test_post_cohort_duplicate(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "DUP", "label": "Dup1"})
    r = isolated_app.post("/api/cohorts", headers=AUTH,
                          json={"cohort_id": "DUP", "label": "Dup2"})
    assert r.status_code in (200, 201, 409)


def test_post_cohort_missing_id(isolated_app):
    r = isolated_app.post("/api/cohorts", headers=AUTH, json={"label": "no id"})
    assert r.status_code == 400


def test_post_cohort_no_auth(isolated_app):
    r = isolated_app.post("/api/cohorts", json={"cohort_id": "X"})
    assert r.status_code == 401


def test_reset_cohort(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "RESET-1", "label": "Reset"})
    r = isolated_app.post("/api/cohorts/RESET-1/reset", headers=AUTH)
    assert r.status_code in (200, 204)


def test_reset_cohort_no_auth(isolated_app):
    r = isolated_app.post("/api/cohorts/X/reset")
    assert r.status_code == 401


def test_delete_cohort(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "DEL-1", "label": "Del"})
    r = isolated_app.delete("/api/cohorts/DEL-1", headers=AUTH)
    assert r.status_code in (200, 204)


def test_delete_cohort_no_auth(isolated_app):
    r = isolated_app.delete("/api/cohorts/X")
    assert r.status_code == 401


def test_delete_cohort_idempotent(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "IDEM", "label": "Idem"})
    r1 = isolated_app.delete("/api/cohorts/IDEM", headers=AUTH)
    r2 = isolated_app.delete("/api/cohorts/IDEM", headers=AUTH)
    assert r1.status_code in (200, 204)
    assert r2.status_code in (200, 204, 404)


# --- /api/cohort/exists + /api/cohort/join + /api/student/status --------

def test_cohort_exists_known(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "EXIST-1", "label": "Exist"})
    r = isolated_app.get("/api/cohort/exists?cohort_id=EXIST-1")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("exists") is True


def test_cohort_exists_unknown(isolated_app):
    r = isolated_app.get("/api/cohort/exists?cohort_id=NEVER-CREATED")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("exists") is False


def test_cohort_exists_missing_param(isolated_app):
    r = isolated_app.get("/api/cohort/exists")
    assert r.status_code in (200, 400)


def test_cohort_join_success(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "JOIN-1", "label": "Join"})
    r = isolated_app.post("/api/cohort/join", json={
        "cohort_id": "JOIN-1",
        "student_token": "uuid-student-aaa-bbb-ccc-ddd",
        "email": "student@example.com",
    })
    assert r.status_code in (200, 201, 202)
    body = r.get_json()
    assert body.get("status") in ("pending", "validated") or body.get("ok") is True


def test_cohort_join_unknown_cohort(isolated_app):
    r = isolated_app.post("/api/cohort/join", json={
        "cohort_id": "NONE-1",
        "student_token": "uuid-x", "email": "x@e.com",
    })
    assert r.status_code in (400, 404)


def test_cohort_join_missing_token(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "JOIN-2", "label": "J2"})
    r = isolated_app.post("/api/cohort/join", json={
        "cohort_id": "JOIN-2", "email": "x@e.com",
    })
    assert r.status_code == 400


def test_cohort_join_missing_email(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "JOIN-3", "label": "J3"})
    r = isolated_app.post("/api/cohort/join", json={
        "cohort_id": "JOIN-3", "student_token": "uuid-y",
    })
    assert r.status_code == 400


def test_student_status_pending(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": "STAT-1", "label": "S1"})
    isolated_app.post("/api/cohort/join", json={
        "cohort_id": "STAT-1", "student_token": "uuid-stat-1", "email": "s1@e.com",
    })
    r = isolated_app.get("/api/student/status?student_token=uuid-stat-1&cohort_id=STAT-1")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("status") in ("pending", "validated", "rejected", "unknown")


def test_student_status_unknown(isolated_app):
    r = isolated_app.get("/api/student/status?student_token=nope&cohort_id=NOPE")
    assert r.status_code in (200, 400, 404)
    if r.status_code == 200:
        body = r.get_json()
        assert body.get("status") in ("unknown", "pending", "not_found")


def test_student_status_missing_param(isolated_app):
    r = isolated_app.get("/api/student/status")
    assert r.status_code in (200, 400)
