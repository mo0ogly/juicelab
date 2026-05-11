"""Coverage : HTTP path through proof_routes endpoints.

Complements test_proof_signing.py (which covers pure helpers) by hitting
/api/verify-flag, /api/journal-text, /api/proof through the Flask test
client with an isolated sqlite + a fresh PROOF/CTF secret.
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
PROOF_SECRET = "proof-test-secret-very-long-32-chars-min"
CTF_SECRET = "ctf-test-secret-1234567890"


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "dashboard.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", PROOF_SECRET)
    monkeypatch.setenv("JUICESHOP_CTF_SECRET", CTF_SECRET)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db", "proof_routes"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    flask_app = app_mod.create_app()
    flask_app.testing = True
    return flask_app.test_client()


def _post_event(client, **overrides):
    payload = {
        "student_token": "uuid-student-proof-http",
        "cohort_id": "M2-IA-2026",
        "event_type": "journal_filled",
        "challenge_key": "loginAdminChallenge",
        "data": {"phase": "after", "text": "I solved it", "word_count": 3},
        "client_timestamp": "2026-05-11T10:00:00Z",
    }
    payload.update(overrides)
    return client.post("/api/sync", json=payload)


# --- /api/verify-flag ---------------------------------------------------

def test_verify_flag_not_json(isolated_app):
    r = isolated_app.post("/api/verify-flag", data="not json", content_type="text/plain")
    assert r.status_code == 400


def test_verify_flag_missing_fields(isolated_app):
    r = isolated_app.post("/api/verify-flag", json={"flag": "x"})
    assert r.status_code == 400


def test_verify_flag_wrong_flag(isolated_app):
    r = isolated_app.post("/api/verify-flag", json={
        "student_token": "uuid-flag-1",
        "cohort_id": "M2-IA-2026",
        "challenge_key": "loginAdminChallenge",
        "challenge_name": "Login Admin",
        "flag": "obviously-wrong-flag",
    })
    assert r.status_code == 200
    assert r.get_json()["valid"] is False


def test_verify_flag_correct(isolated_app):
    import hashlib
    import hmac as _hmac
    expected = _hmac.new(CTF_SECRET.encode(), b"Login Admin", hashlib.sha1).hexdigest()
    r = isolated_app.post("/api/verify-flag", json={
        "student_token": "uuid-flag-2",
        "cohort_id": "M2-IA-2026",
        "challenge_key": "loginAdminChallenge",
        "challenge_name": "Login Admin",
        "flag": expected,
    })
    assert r.status_code == 200
    assert r.get_json()["valid"] is True


def test_verify_flag_disabled_when_secret_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.delenv("JUICESHOP_CTF_SECRET", raising=False)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db", "proof_routes"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    c = app_mod.create_app().test_client()
    r = c.post("/api/verify-flag", json={
        "student_token": "x", "cohort_id": "c", "challenge_key": "k",
        "challenge_name": "n", "flag": "f",
    })
    assert r.status_code == 503


# --- /api/journal-text --------------------------------------------------

def test_journal_text_requires_auth(isolated_app):
    r = isolated_app.get("/api/journal-text?student_token=x&cohort=c&key=k")
    assert r.status_code in (302, 401)


def test_journal_text_missing_params(isolated_app):
    r = isolated_app.get("/api/journal-text", headers=AUTH)
    assert r.status_code == 400


def test_journal_text_empty_for_unknown_student(isolated_app):
    r = isolated_app.get("/api/journal-text?student_token=nope&cohort=c&key=k", headers=AUTH)
    assert r.status_code == 200
    body = r.get_json()
    assert body["text"] == ""


def test_journal_text_returns_latest_after(isolated_app):
    _post_event(isolated_app)
    r = isolated_app.get(
        "/api/journal-text?student_token=uuid-student-proof-http"
        "&cohort=M2-IA-2026&key=loginAdminChallenge",
        headers=AUTH,
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["text"] == "I solved it"
    assert body["word_count"] == 3


# --- /api/proof ---------------------------------------------------------

def test_proof_missing_student_token(isolated_app):
    r = isolated_app.get("/api/proof?cohort=c&key=k")
    assert r.status_code == 400


def test_proof_missing_cohort(isolated_app):
    r = isolated_app.get("/api/proof?student_token=x&key=k")
    assert r.status_code == 400


def test_proof_missing_key(isolated_app):
    r = isolated_app.get("/api/proof?student_token=x&cohort=c")
    assert r.status_code == 400


def test_proof_no_events(isolated_app):
    r = isolated_app.get(
        "/api/proof?student_token=no-events&cohort=M2-IA-2026&key=loginAdminChallenge"
    )
    assert r.status_code == 404


def test_proof_returns_signed_markdown(isolated_app):
    _post_event(isolated_app)
    r = isolated_app.get(
        "/api/proof?student_token=uuid-student-proof-http"
        "&cohort=M2-IA-2026&key=loginAdminChallenge&name=Login%20Admin"
        "&category=Auth&difficulty=1"
    )
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    assert "SIGNATURE: " in body
    assert "PROOF: HMAC-SHA256" in body
    assert "loginAdminChallenge" in body


def test_proof_disabled_when_secret_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.delenv("DASHBOARD_PROOF_SECRET", raising=False)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db", "proof_routes"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    c = app_mod.create_app().test_client()
    r = c.get("/api/proof?student_token=x&cohort=c&key=k")
    assert r.status_code == 503
