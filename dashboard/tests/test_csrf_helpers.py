"""Coverage : csrf module pure functions + check_csrf branches.

Tests issue_csrf_token, set_csrf_cookie, clear_csrf_cookie, check_csrf
with all four branches : safe-method bypass, X-Teacher-Token bypass,
matching cookie+header, mismatching cookie+header, missing cookie.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from flask import Flask, jsonify, make_response

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from csrf import (
    COOKIE_NAME,
    HEADER_NAME,
    check_csrf,
    clear_csrf_cookie,
    issue_csrf_token,
    set_csrf_cookie,
)


@pytest.fixture
def flask_app():
    app = Flask(__name__)

    @app.route("/probe", methods=["GET", "POST", "DELETE", "PUT", "PATCH", "OPTIONS"])
    def probe():
        return jsonify({"csrf_ok": check_csrf()})

    return app.test_client()


# --- issue_csrf_token ---------------------------------------------------

def test_issue_csrf_token_is_64_hex_chars():
    tok = issue_csrf_token()
    assert len(tok) == 64
    int(tok, 16)


def test_issue_csrf_token_unique():
    assert issue_csrf_token() != issue_csrf_token()


# --- set_csrf_cookie / clear_csrf_cookie --------------------------------

def test_set_csrf_cookie_writes_header():
    app = Flask(__name__)
    with app.test_request_context("/"):
        r = make_response("ok")
        set_csrf_cookie(r, "abcd1234")
        sc = r.headers.get("Set-Cookie", "")
        assert "csrf_token=abcd1234" in sc
        assert "HttpOnly" not in sc  # explicitly readable to JS
        assert "SameSite=Lax" in sc


def test_set_csrf_cookie_https_secure(monkeypatch):
    monkeypatch.setenv("DASHBOARD_HTTPS", "true")
    app = Flask(__name__)
    with app.test_request_context("/"):
        r = make_response("ok")
        set_csrf_cookie(r, "t")
        assert "Secure" in r.headers.get("Set-Cookie", "")


def test_clear_csrf_cookie_expires():
    app = Flask(__name__)
    with app.test_request_context("/"):
        r = make_response("ok")
        clear_csrf_cookie(r)
        sc = r.headers.get("Set-Cookie", "")
        assert COOKIE_NAME in sc
        assert "Expires=" in sc or "Max-Age=0" in sc


# --- check_csrf branches via probe endpoint -----------------------------

def test_check_csrf_safe_method_get(flask_app):
    r = flask_app.get("/probe")
    assert r.get_json()["csrf_ok"] is True


def test_check_csrf_safe_method_options(flask_app):
    r = flask_app.open("/probe", method="OPTIONS")
    assert r.get_json()["csrf_ok"] is True


def test_check_csrf_api_client_with_teacher_token(flask_app):
    r = flask_app.post("/probe", headers={"X-Teacher-Token": "ignored-value"})
    assert r.get_json()["csrf_ok"] is True


def test_check_csrf_browser_missing_header(flask_app):
    r = flask_app.post("/probe")
    assert r.get_json()["csrf_ok"] is False


def test_check_csrf_browser_missing_cookie(flask_app):
    r = flask_app.post("/probe", headers={HEADER_NAME: "any-value"})
    assert r.get_json()["csrf_ok"] is False


def test_check_csrf_browser_mismatched(flask_app):
    flask_app.set_cookie("csrf_token", "abc")
    r = flask_app.post("/probe", headers={HEADER_NAME: "xyz"})
    assert r.get_json()["csrf_ok"] is False


def test_check_csrf_browser_match(flask_app):
    flask_app.set_cookie("csrf_token", "matching-token")
    r = flask_app.post("/probe", headers={HEADER_NAME: "matching-token"})
    assert r.get_json()["csrf_ok"] is True


def test_check_csrf_browser_match_delete(flask_app):
    flask_app.set_cookie("csrf_token", "t1")
    r = flask_app.delete("/probe", headers={HEADER_NAME: "t1"})
    assert r.get_json()["csrf_ok"] is True


def test_check_csrf_browser_match_put(flask_app):
    flask_app.set_cookie("csrf_token", "t2")
    r = flask_app.put("/probe", headers={HEADER_NAME: "t2"})
    assert r.get_json()["csrf_ok"] is True
