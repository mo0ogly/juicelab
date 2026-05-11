"""Pytest suite for the /api/students CRUD + auto-discovery hook.

Mirrors the fixture style of test_app.py : each test runs against a
fresh isolated SQLite file by setting DASHBOARD_DB before importing the
app factory.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


TOKEN = "teacher-test-token-very-long-32chars!!"
COHORT = "M2-IA-2026"
AUTH = {"X-Teacher-Token": TOKEN}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "dashboard.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    monkeypatch.setenv("DASHBOARD_DEFAULT_COHORT", COHORT)
    monkeypatch.setenv("DASHBOARD_ROSTER", str(tmp_path / "no-roster.txt"))

    for m in ("app", "db", "students_routes"):
        sys.modules.pop(m, None)
    import app as app_mod  # noqa: E402

    flask_app = app_mod.create_app()
    flask_app.testing = True
    return flask_app.test_client()


def test_get_empty_returns_empty_list(client):
    r = client.get(f"/api/students?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200
    body = r.get_json()
    assert body["cohort_id"] == COHORT
    assert body["students"] == []


def test_get_requires_auth(client):
    r = client.get(f"/api/students?cohort={COHORT}")
    assert r.status_code == 401


def test_post_requires_auth(client):
    r = client.post("/api/students", json={"student_token": "t", "cohort_id": COHORT})
    assert r.status_code == 401


def test_delete_requires_auth(client):
    r = client.delete(f"/api/students/foo?cohort={COHORT}")
    assert r.status_code == 401


def test_post_missing_token_returns_400(client):
    r = client.post("/api/students", json={"cohort_id": COHORT}, headers=AUTH)
    assert r.status_code == 400


def test_post_too_long_name_returns_400(client):
    r = client.post(
        "/api/students",
        json={"cohort_id": COHORT, "student_token": "t", "display_name": "x" * 101},
        headers=AUTH,
    )
    assert r.status_code == 400


def test_upsert_then_get_then_clear_then_delete(client):
    tok = "uuid-test-roundtrip"
    r = client.post(
        "/api/students",
        json={"cohort_id": COHORT, "student_token": tok, "display_name": "Alice Test"},
        headers=AUTH,
    )
    assert r.status_code == 200 and r.get_json()["ok"] is True

    r = client.get(f"/api/students?cohort={COHORT}", headers=AUTH)
    names = {s["student_token"]: s["display_name"] for s in r.get_json()["students"]}
    assert names.get(tok) == "Alice Test"

    r = client.post(
        "/api/students",
        json={"cohort_id": COHORT, "student_token": tok, "display_name": ""},
        headers=AUTH,
    )
    assert r.get_json()["display_name"] is None

    r = client.get(f"/api/students?cohort={COHORT}", headers=AUTH)
    names = {s["student_token"]: s["display_name"] for s in r.get_json()["students"]}
    assert names.get(tok) is None

    r = client.delete(f"/api/students/{tok}?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200 and r.get_json()["deleted"] == 1

    r = client.delete(f"/api/students/{tok}?cohort={COHORT}", headers=AUTH)
    assert r.get_json()["deleted"] == 0


def test_sync_auto_registers_student(client):
    r = client.post(
        "/api/sync",
        json={
            "student_token": "uuid-auto-discover",
            "cohort_id": COHORT,
            "event_type": "challenge_solved",
            "challenge_key": "loginAdminChallenge",
            "data": {},
            "client_timestamp": "2026-05-11T12:00:00Z",
        },
    )
    assert r.status_code in (200, 201, 204)

    r = client.get(f"/api/students?cohort={COHORT}", headers=AUTH)
    tokens = [s["student_token"] for s in r.get_json()["students"]]
    assert "uuid-auto-discover" in tokens
    by_tok = {s["student_token"]: s for s in r.get_json()["students"]}
    assert by_tok["uuid-auto-discover"]["display_name"] is None
    assert by_tok["uuid-auto-discover"]["event_count"] == 1


def test_admin_page_redirects_when_unauth(client):
    r = client.get(f"/admin/students?cohort={COHORT}")
    assert r.status_code in (302, 303)


def test_admin_page_renders_with_auth(client):
    r = client.get(f"/admin/students?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200
    assert b"Eleves - cohorte" in r.data


def test_cohort_summary_uses_students_table_for_names(client):
    """End-to-end check : POSTing an event + renaming the student should
    make the new name appear in /api/cohort.names ."""
    tok = "uuid-summary-check"
    client.post(
        "/api/sync",
        json={
            "student_token": tok, "cohort_id": COHORT,
            "event_type": "challenge_solved", "challenge_key": "scoreBoardChallenge",
            "data": {}, "client_timestamp": "2026-05-11T12:00:00Z",
        },
    )
    client.post(
        "/api/students",
        json={"cohort_id": COHORT, "student_token": tok, "display_name": "Bob Renamed"},
        headers=AUTH,
    )
    r = client.get(f"/api/cohort?cohort={COHORT}", headers=AUTH)
    assert r.status_code == 200
    assert r.get_json()["names"].get(tok) == "Bob Renamed"
