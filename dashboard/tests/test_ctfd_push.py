"""Pytest suite for the CTFd push integration (Mode C).

Exercises the dashboard hook that pushes negative awards to CTFd on every
hint_revealed event, plus the admin endpoints (ctfd-status, reconcile).
The CTFd HTTP layer is mocked at app.requests.request so no actual server
is required.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---- Fixtures --------------------------------------------------------------

def _fresh_modules():
    if "app" in sys.modules:
        del sys.modules["app"]
    if "db" in sys.modules:
        del sys.modules["db"]


def _make_response(status: int = 200, body: dict | None = None) -> SimpleNamespace:
    """Minimal stand-in for requests.Response; matches the calls our code
    actually makes (status_code attr + .json() method + .text attr)."""
    payload = body if body is not None else {}
    return SimpleNamespace(
        status_code=status,
        text=json.dumps(payload),
        json=lambda: payload,
    )


def _enable_ctfd(monkeypatch):
    monkeypatch.setenv("CTFD_URL", "http://ctfd.test")
    monkeypatch.setenv("CTFD_ADMIN_TOKEN", "ctfd_test_token_aaaaaaaa")
    monkeypatch.setenv("CTFD_TEAM_MODE", "team")
    monkeypatch.setenv("CTFD_PENALTY_FORMULA", "mirror_juicelab")


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    """Boot the Flask factory with a temp DB. Returns the live module so
    tests can patch app.requests.request and inspect helpers."""
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "dashboard.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", "teacher-test-token-very-long-32chars!!")
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    _fresh_modules()
    import app as app_mod
    return app_mod


@pytest.fixture
def ctfd_client(app_module, monkeypatch):
    _enable_ctfd(monkeypatch)
    flask_app = app_module.create_app()
    flask_app.testing = True
    return flask_app.test_client(), app_module


@pytest.fixture
def disabled_client(app_module):
    """No CTFD_URL / TOKEN set : Mode A regression."""
    flask_app = app_module.create_app()
    flask_app.testing = True
    return flask_app.test_client(), app_module


def _hint_event(level: str = "N1", cost_pct: int = 5, email: str | None = "alice@td.fr"):
    data = {"level": level, "consumed_levels": [level], "score_after": 100 - cost_pct, "cost_pct": cost_pct}
    if email is not None:
        data["student_email"] = email
    return {
        "student_token": "uuid-fake-alice",
        "cohort_id": "M2-IA-2026",
        "event_type": "hint_revealed",
        "challenge_key": "loginAdminChallenge",
        "data": data,
        "client_timestamp": "2026-05-09T14:00:00Z",
    }


def _team_lookup_response():
    return _make_response(200, {
        "data": [
            {"id": 42, "name": "Alice", "email": "alice@td.fr", "affiliation": "M2-IA-2026"},
            {"id": 43, "name": "Bob", "email": "bob@td.fr", "affiliation": "M2-IA-2026"},
        ]
    })


def _user_lookup_response():
    return _make_response(200, {"data": [
        {"id": 142, "email": "alice@td.fr", "team_id": 42},
    ]})


# ---- Mode A regression : push disabled when env missing -------------------

def test_push_disabled_when_env_missing(disabled_client, monkeypatch):
    client, app_mod = disabled_client
    mock_request = MagicMock()
    monkeypatch.setattr(app_mod.requests, "request", mock_request)

    response = client.post("/api/sync", json=_hint_event())
    assert response.status_code == 201
    # No CTFd call should have happened in Mode A
    mock_request.assert_not_called()


# ---- Mode C : core push behaviour -----------------------------------------

def test_hint_revealed_pushes_award_to_ctfd(ctfd_client, monkeypatch):
    client, app_mod = ctfd_client

    calls = []

    def fake_request(method, url, headers=None, json=None, timeout=None):
        calls.append((method, url, headers, json))
        if method == "GET" and "/api/v1/teams" in url:
            return _team_lookup_response()
        if method == "GET" and "/api/v1/users" in url:
            return _user_lookup_response()
        if method == "POST" and "/api/v1/awards" in url:
            return _make_response(200, {"data": {"id": 999}})
        return _make_response(404, {"error": "unexpected"})

    monkeypatch.setattr(app_mod.requests, "request", fake_request)

    response = client.post("/api/sync", json=_hint_event(level="N3", cost_pct=20))
    assert response.status_code == 201

    award_calls = [c for c in calls if c[0] == "POST" and "/api/v1/awards" in c[1]]
    assert len(award_calls) == 1
    sent_body = award_calls[0][3]
    assert sent_body["team_id"] == 42
    assert sent_body["value"] == -20
    assert sent_body["category"] == "loginAdminChallenge"
    assert "Hint N3" in sent_body["name"]

    # Auth header present and well-formed
    headers = award_calls[0][2]
    assert headers["Authorization"].startswith("Token ")


def test_uniform_10pct_formula(ctfd_client, monkeypatch):
    client, app_mod = ctfd_client
    monkeypatch.setenv("CTFD_PENALTY_FORMULA", "uniform_10pct")

    award_bodies = []

    def fake_request(method, url, headers=None, json=None, timeout=None):
        if method == "GET" and "/api/v1/teams" in url:
            return _team_lookup_response()
        if method == "GET" and "/api/v1/users" in url:
            return _user_lookup_response()
        if method == "POST" and "/api/v1/awards" in url:
            award_bodies.append(json)
            return _make_response(200)
        return _make_response(404)

    monkeypatch.setattr(app_mod.requests, "request", fake_request)
    client.post("/api/sync", json=_hint_event(level="N5", cost_pct=50))

    assert award_bodies and award_bodies[0]["value"] == -10


def test_team_resolution_uses_cache(ctfd_client, monkeypatch):
    client, app_mod = ctfd_client

    team_lookups = 0

    def fake_request(method, url, headers=None, json=None, timeout=None):
        nonlocal team_lookups
        if method == "GET" and "/api/v1/teams" in url:
            team_lookups += 1
            return _team_lookup_response()
        if method == "GET" and "/api/v1/users" in url:
            return _user_lookup_response()
        if method == "POST" and "/api/v1/awards" in url:
            return _make_response(200)
        return _make_response(404)

    monkeypatch.setattr(app_mod.requests, "request", fake_request)

    # Two distinct hint reveals for the same student → cache hit on the
    # second one, no second team lookup.
    client.post("/api/sync", json=_hint_event(level="N1", cost_pct=5))
    client.post("/api/sync", json=_hint_event(level="N2", cost_pct=10))

    assert team_lookups == 1


def test_push_failure_leaves_award_pushed_at_null(ctfd_client, monkeypatch):
    client, app_mod = ctfd_client

    def fake_request(method, url, headers=None, json=None, timeout=None):
        if method == "GET" and "/api/v1/teams" in url:
            return _team_lookup_response()
        if method == "GET" and "/api/v1/users" in url:
            return _user_lookup_response()
        if method == "POST" and "/api/v1/awards" in url:
            return _make_response(500, {"error": "ctfd is sad"})
        return _make_response(404)

    monkeypatch.setattr(app_mod.requests, "request", fake_request)

    response = client.post("/api/sync", json=_hint_event())
    assert response.status_code == 201
    new_id = response.get_json()["id"]

    with app_mod.get_connection() as conn:
        row = conn.execute(
            "SELECT award_pushed_at FROM events WHERE id = ?", (new_id,)
        ).fetchone()
    assert row["award_pushed_at"] is None


def test_non_hint_event_skips_push(ctfd_client, monkeypatch):
    client, app_mod = ctfd_client
    mock_request = MagicMock()
    monkeypatch.setattr(app_mod.requests, "request", mock_request)

    payload = {
        "student_token": "uuid-fake-alice",
        "cohort_id": "M2-IA-2026",
        "event_type": "journal_filled",
        "challenge_key": "loginAdminChallenge",
        "data": {"phase": "after", "word_count": 80, "text": "..."},
        "client_timestamp": "2026-05-09T14:00:00Z",
    }
    response = client.post("/api/sync", json=payload)
    assert response.status_code == 201
    mock_request.assert_not_called()


def test_award_idempotence(ctfd_client, monkeypatch):
    """Two distinct hint events trigger two pushes (one per event_id), but
    a reconcile run does NOT re-push events whose award_pushed_at is set."""
    client, app_mod = ctfd_client

    posts = []

    def fake_request(method, url, headers=None, json=None, timeout=None):
        if method == "GET" and "/api/v1/teams" in url:
            return _team_lookup_response()
        if method == "GET" and "/api/v1/users" in url:
            return _user_lookup_response()
        if method == "POST" and "/api/v1/awards" in url:
            posts.append(json)
            return _make_response(200)
        return _make_response(404)

    monkeypatch.setattr(app_mod.requests, "request", fake_request)
    client.post("/api/sync", json=_hint_event(level="N1", cost_pct=5))
    assert len(posts) == 1

    response = client.post(
        "/api/admin/reconcile-awards",
        headers={"X-Teacher-Token": os.environ["DASHBOARD_TEACHER_TOKEN"]},
    )
    assert response.status_code == 200
    body = response.get_json()
    # Already pushed → reconcile finds nothing to retry
    assert body["retried"] == 0
    assert len(posts) == 1


def test_reconcile_awards_retries_failed(ctfd_client, monkeypatch):
    client, app_mod = ctfd_client

    award_attempts = 0
    fail_first = True

    def fake_request(method, url, headers=None, json=None, timeout=None):
        nonlocal award_attempts, fail_first
        if method == "GET" and "/api/v1/teams" in url:
            return _team_lookup_response()
        if method == "GET" and "/api/v1/users" in url:
            return _user_lookup_response()
        if method == "POST" and "/api/v1/awards" in url:
            award_attempts += 1
            if fail_first:
                return _make_response(503)
            return _make_response(200)
        return _make_response(404)

    monkeypatch.setattr(app_mod.requests, "request", fake_request)

    response = client.post("/api/sync", json=_hint_event())
    assert response.status_code == 201
    new_id = response.get_json()["id"]

    with app_mod.get_connection() as conn:
        row = conn.execute(
            "SELECT award_pushed_at FROM events WHERE id = ?", (new_id,)
        ).fetchone()
    assert row["award_pushed_at"] is None

    fail_first = False
    response = client.post(
        "/api/admin/reconcile-awards",
        headers={"X-Teacher-Token": os.environ["DASHBOARD_TEACHER_TOKEN"]},
    )
    body = response.get_json()
    assert body["retried"] == 1
    assert body["succeeded"] == 1
    assert body["failed"] == 0

    with app_mod.get_connection() as conn:
        row = conn.execute(
            "SELECT award_pushed_at FROM events WHERE id = ?", (new_id,)
        ).fetchone()
    assert row["award_pushed_at"] is not None


# ---- Admin status endpoint ------------------------------------------------

def test_ctfd_status_disabled(disabled_client):
    client, _ = disabled_client
    response = client.get(
        "/api/admin/ctfd-status",
        headers={"X-Teacher-Token": os.environ["DASHBOARD_TEACHER_TOKEN"]},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["enabled"] is False
    assert body["ctfd_url"] is None


def test_ctfd_status_enabled(ctfd_client, monkeypatch):
    client, app_mod = ctfd_client

    def fake_request(method, url, headers=None, json=None, timeout=None):
        if method == "GET" and "/api/v1/teams" in url:
            return _team_lookup_response()
        if method == "GET" and "/api/v1/users" in url:
            return _user_lookup_response()
        if method == "POST" and "/api/v1/awards" in url:
            return _make_response(200)
        return _make_response(404)

    monkeypatch.setattr(app_mod.requests, "request", fake_request)
    client.post("/api/sync", json=_hint_event())

    response = client.get(
        "/api/admin/ctfd-status",
        headers={"X-Teacher-Token": os.environ["DASHBOARD_TEACHER_TOKEN"]},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["enabled"] is True
    assert body["ctfd_url"] == "http://ctfd.test"
    assert body["teams_mapped"] == 1
    assert body["pending_pushes"] == 0


def test_admin_endpoints_require_token(disabled_client):
    client, _ = disabled_client
    assert client.get("/api/admin/ctfd-status").status_code == 401
    assert client.post("/api/admin/reconcile-awards").status_code == 401
