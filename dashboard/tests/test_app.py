"""Pytest suite for the JuiceLab dashboard.

Each test runs against a fresh isolated SQLite file by setting
DASHBOARD_DB to a tempdir-scoped path before importing the app
factory.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    """Provide a Flask test client backed by a temp sqlite file."""
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "dashboard.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", "teacher-test-token-very-long-32chars!!")
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")

    if "app" in sys.modules:
        del sys.modules["app"]
    if "db" in sys.modules:
        del sys.modules["db"]
    import app as app_mod

    flask_app = app_mod.create_app()
    flask_app.testing = True
    return flask_app.test_client()


def _post_event(client, **overrides):
    payload = {
        "student_token": "uuid-fake-student-1",
        "cohort_id": "M2-IA-2026",
        "event_type": "hint_revealed",
        "challenge_key": "loginAdminChallenge",
        "data": {"level": "N1", "consumed_levels": ["N1"], "score_after": 95, "cost_pct": 5},
        "client_timestamp": "2026-05-09T14:00:00Z",
    }
    payload.update(overrides)
    return client.post("/api/sync", json=payload)


def test_health_endpoint(isolated_app):
    response = isolated_app.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_post_event_valid(isolated_app):
    response = _post_event(isolated_app)
    assert response.status_code == 201
    body = response.get_json()
    assert body["ok"] is True
    assert isinstance(body["id"], int) and body["id"] > 0


def test_post_event_invalid_event_type(isolated_app):
    response = _post_event(isolated_app, event_type="not_a_real_type")
    assert response.status_code == 400
    assert "event_type" in response.get_json()["error"]


def test_post_event_missing_student_token(isolated_app):
    response = _post_event(isolated_app, student_token="")
    assert response.status_code == 400


def test_post_event_non_json_body(isolated_app):
    response = isolated_app.post("/api/sync", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_cohort_endpoint_requires_token(isolated_app):
    response = isolated_app.get("/api/cohort?cohort=M2-IA-2026")
    assert response.status_code == 401


def test_cohort_endpoint_with_token(isolated_app):
    _post_event(isolated_app)
    _post_event(
        isolated_app,
        event_type="quiz_completed",
        data={"score": 67, "q1_score": 100, "q2_score": 0, "q3_score": 100},
    )
    response = isolated_app.get(
        "/api/cohort?cohort=M2-IA-2026",
        headers={"X-Teacher-Token": os.environ["DASHBOARD_TEACHER_TOKEN"]},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["cohort_id"] == "M2-IA-2026"
    assert body["events_total"] == 2
    assert body["students"] == ["uuid-fake-student-1"]
    assert "loginAdminChallenge" in body["challenges"]
    slot = body["matrix"]["uuid-fake-student-1"]["loginAdminChallenge"]
    assert slot["hints"] >= 1
    assert slot["quiz_score"] == 67


def test_cohort_endpoint_isolates_cohorts(isolated_app):
    _post_event(isolated_app, cohort_id="M2-IA-2026")
    _post_event(isolated_app, cohort_id="M2-IA-2027", student_token="other-student")
    headers = {"X-Teacher-Token": os.environ["DASHBOARD_TEACHER_TOKEN"]}

    a = isolated_app.get("/api/cohort?cohort=M2-IA-2026", headers=headers).get_json()
    b = isolated_app.get("/api/cohort?cohort=M2-IA-2027", headers=headers).get_json()
    assert a["events_total"] == 1
    assert b["events_total"] == 1
    assert a["students"] == ["uuid-fake-student-1"]
    assert b["students"] == ["other-student"]


def test_dashboard_html_requires_token(isolated_app):
    response = isolated_app.get("/dashboard?cohort=X")
    assert response.status_code == 401


def test_dashboard_html_renders(isolated_app):
    _post_event(isolated_app)
    _post_event(isolated_app, event_type="challenge_solved")
    response = isolated_app.get(
        "/dashboard?cohort=M2-IA-2026",
        headers={"X-Teacher-Token": os.environ["DASHBOARD_TEACHER_TOKEN"]},
    )
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "JuiceLab dashboard" in body
    assert "uuid-fake-student-1" in body
    assert "loginAdminChallenge" in body
    assert "solved" in body
