"""Coverage : remaining app.py route handlers.

Targets lines 612-651 (login GET/POST, logout) and 411-434, 285-292,
306-311 (cohort/sync edge cases) that test_app.py and test_proof_http
don't already cover.
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
    for mod in ("app", "db"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    flask_app = app_mod.create_app()
    flask_app.testing = True
    return flask_app.test_client()


# --- /login GET ---------------------------------------------------------

def test_login_get_renders_form(isolated_app):
    r = isolated_app.get("/login")
    assert r.status_code == 200
    assert b"<form" in r.data
    assert b'name="token"' in r.data


def test_login_get_with_next_param(isolated_app):
    r = isolated_app.get("/login?next=/admin/cohorts")
    assert r.status_code == 200
    assert b"/admin/cohorts" in r.data


# --- /login POST -------------------------------------------------------

def test_login_post_wrong_token(isolated_app):
    r = isolated_app.post("/login", data={
        "token": "obviously-wrong-token",
        "next": "/dashboard",
    })
    assert r.status_code == 401
    assert b"Token incorrect" in r.data or b"login" in r.data.lower()


def test_login_post_correct_token_sets_cookies(isolated_app):
    r = isolated_app.post("/login", data={
        "token": TOKEN,
        "next": "/dashboard",
    })
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/dashboard")
    cookies = r.headers.getlist("Set-Cookie")
    cookie_blob = " ".join(cookies)
    assert "teacher_token=" in cookie_blob
    assert "csrf_token=" in cookie_blob
    assert "HttpOnly" in cookie_blob
    assert "SameSite=Lax" in cookie_blob


def test_login_post_default_next(isolated_app):
    r = isolated_app.post("/login", data={"token": TOKEN})
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_login_post_disabled_when_no_teacher_token(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", "")
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    c = app_mod.create_app().test_client()
    r = c.post("/login", data={"token": "x"})
    assert r.status_code == 503
    assert b"Dashboard disabled" in r.data


# --- /logout -----------------------------------------------------------

def test_logout_clears_cookies(isolated_app):
    isolated_app.set_cookie("teacher_token", TOKEN)
    isolated_app.set_cookie("csrf_token", "abc")
    r = isolated_app.get("/logout")
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/login")
    cookie_blob = " ".join(r.headers.getlist("Set-Cookie"))
    # both cookies should be cleared (Max-Age=0 or Expires in the past)
    assert "teacher_token=" in cookie_blob
    assert "csrf_token=" in cookie_blob


# --- /api/cohort -------------------------------------------------------

def test_api_cohort_missing_param(isolated_app):
    r = isolated_app.get("/api/cohort", headers=AUTH)
    assert r.status_code == 400
    assert "missing cohort" in r.get_json()["error"]


def test_api_cohort_empty_param(isolated_app):
    r = isolated_app.get("/api/cohort?cohort=", headers=AUTH)
    assert r.status_code == 400


def test_api_cohort_unknown_returns_empty(isolated_app):
    r = isolated_app.get("/api/cohort?cohort=NEVER-CREATED-X", headers=AUTH)
    assert r.status_code == 200
    body = r.get_json()
    assert body["events_total"] == 0
    assert body["students"] == []
