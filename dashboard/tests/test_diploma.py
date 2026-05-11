"""Coverage : diploma signing, mention auto, batch ZIP.

Mirrors test_proof_signing for the new diploma_routes module : HMAC
roundtrip on sign_diploma, mention thresholds, and HTTP smoke on
/admin/diploma/<token> + /api/diplomas.zip.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import os
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from diploma_routes import (
    _mention_for,
    build_diploma_md,
    sign_diploma,
)
from verify_proof import verify

TOKEN = "teacher-test-token-very-long-32chars!!"
AUTH = {"X-Teacher-Token": TOKEN}
PROOF_SECRET = "diploma-test-secret-very-long-32chars"
SECRET = PROOF_SECRET.encode()
COHORT = "M2-IA-2026"


# --- mention thresholds --------------------------------------------------

def test_mention_tres_bien():
    assert _mention_for(90, 80) == "tres_bien"
    assert _mention_for(80, 70) == "tres_bien"


def test_mention_bien():
    assert _mention_for(70, 60) == "bien"
    assert _mention_for(60, 60) == "bien"


def test_mention_reussite():
    assert _mention_for(50, 40) == "reussite"
    assert _mention_for(40, 0) == "reussite"


def test_mention_participation():
    assert _mention_for(39, 50) == "participation"
    assert _mention_for(0, 0) == "participation"


def test_mention_boundaries():
    # quiz drops just below threshold -> downgrade
    assert _mention_for(80, 69) == "bien"
    assert _mention_for(60, 59) == "reussite"


# --- HMAC roundtrip ------------------------------------------------------

def test_sign_diploma_roundtrip():
    body = build_diploma_md(
        student_token="abc", student_name="Alice", cohort_id=COHORT,
        mention="tres_bien", progress_pct=92, quiz_pct=80,
        challenges_solved=12, hints_used=5, flags_verified=3,
        institution="Sorbonne",
    )
    signed = sign_diploma(body, secret=SECRET, student_token="abc",
                          cohort_id=COHORT, mention="tres_bien", score_pct=92)
    ok, meta = verify(signed, SECRET)
    assert ok is True
    assert meta["scheme"] == "diploma.v1"
    assert meta["student"] == "abc"


def test_sign_diploma_tamper_body():
    body = build_diploma_md(
        student_token="abc", student_name="Alice", cohort_id=COHORT,
        mention="tres_bien", progress_pct=92, quiz_pct=80,
        challenges_solved=12, hints_used=5, flags_verified=3,
        institution="Sorbonne",
    )
    signed = sign_diploma(body, secret=SECRET, student_token="abc",
                          cohort_id=COHORT, mention="tres_bien", score_pct=92)
    tampered = signed.replace("Alice", "Mallory")
    ok, _ = verify(tampered, SECRET)
    assert ok is False


def test_sign_diploma_wrong_secret():
    body = build_diploma_md(
        student_token="abc", student_name="A", cohort_id="C",
        mention="bien", progress_pct=60, quiz_pct=60,
        challenges_solved=8, hints_used=2, flags_verified=1,
        institution="S",
    )
    signed = sign_diploma(body, secret=SECRET, student_token="abc",
                          cohort_id="C", mention="bien", score_pct=60)
    ok, _ = verify(signed, b"y" * 32)
    assert ok is False


def test_sign_diploma_empty_secret_raises():
    with pytest.raises(RuntimeError, match="DASHBOARD_PROOF_SECRET"):
        sign_diploma("body", secret=b"", student_token="s",
                     cohort_id="c", mention="bien", score_pct=60)


def test_diploma_scheme_distinct_from_proof():
    """A diploma must have SCHEME=diploma.v1, not v1 (proof). Defense
    against a forged challenge proof being repackaged as a diploma."""
    body = build_diploma_md(
        student_token="abc", student_name="A", cohort_id="C",
        mention="bien", progress_pct=60, quiz_pct=60,
        challenges_solved=8, hints_used=2, flags_verified=1,
        institution="S",
    )
    signed = sign_diploma(body, secret=SECRET, student_token="abc",
                          cohort_id="C", mention="bien", score_pct=60)
    assert "SCHEME: diploma.v1" in signed
    assert "DIPLOMA: HMAC-SHA256" in signed


# --- HTTP endpoints ------------------------------------------------------

@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", PROOF_SECRET)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db", "diploma_routes", "students_routes",
                "cohorts_routes", "join_routes", "rate_limit"):
        if mod in sys.modules:
            del sys.modules[mod]
    # Rate-limit bucket is module-global ; clear it so /api/cohort/join in
    # _seed_student does not 429 due to bucket pollution from a prior test.
    import rate_limit as _rl
    _rl._buckets.clear()
    import app as app_mod
    flask_app = app_mod.create_app()
    flask_app.testing = True
    return flask_app.test_client()


def _seed_student(client, token="stud-1", email="s@e.com", solve_count=0):
    client.post("/api/cohorts", headers=AUTH,
                json={"cohort_id": COHORT, "label": "Test"})
    client.post("/api/cohort/join", json={
        "cohort_id": COHORT, "student_token": token, "email": email,
    })
    client.post(f"/api/students/{token}/approve", headers=AUTH,
                json={"cohort_id": COHORT, "decided_by": "test"})
    for i in range(solve_count):
        client.post("/api/sync", json={
            "student_token": token, "cohort_id": COHORT,
            "event_type": "challenge_solved",
            "challenge_key": f"challenge_{i}",
            "data": {},
            "client_timestamp": "2026-05-11T10:00:00Z",
        })


def test_diploma_html_renders(isolated_app):
    _seed_student(isolated_app, token="stud-html", solve_count=2)
    r = isolated_app.get(
        "/admin/diploma/stud-html?cohort=" + COHORT,
        headers={"X-Teacher-Token": TOKEN},
    )
    assert r.status_code == 200
    assert b"SIGNATURE" in r.data or b"signature" in r.data.lower()
    assert b"stud-html" in r.data


def test_diploma_html_unknown_student(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": COHORT, "label": "T"})
    r = isolated_app.get(
        "/admin/diploma/nope?cohort=" + COHORT,
        headers={"X-Teacher-Token": TOKEN},
    )
    assert r.status_code == 404


def test_diploma_html_missing_cohort(isolated_app):
    r = isolated_app.get("/admin/diploma/x",
                         headers={"X-Teacher-Token": TOKEN})
    assert r.status_code == 400


def test_diplomas_zip_skips_participation_by_default(isolated_app):
    _seed_student(isolated_app, token="zero-stud", solve_count=0)
    r = isolated_app.get("/api/diplomas.zip?cohort=" + COHORT, headers=AUTH)
    # Only "participation" student in cohort, default skips it -> 404
    assert r.status_code == 404


def test_diplomas_zip_include_all_returns_zip(isolated_app):
    _seed_student(isolated_app, token="zero-include", solve_count=0)
    r = isolated_app.get("/api/diplomas.zip?cohort=" + COHORT + "&include_all=1", headers=AUTH)
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.data)) as zf:
        names = zf.namelist()
        assert len(names) == 1
        content = zf.read(names[0]).decode("utf-8")
        assert "SIGNATURE: " in content
        assert "SCHEME: diploma.v1" in content


def test_diplomas_zip_requires_auth(isolated_app):
    r = isolated_app.get("/api/diplomas.zip?cohort=" + COHORT)
    assert r.status_code in (302, 401)


def test_diplomas_zip_disabled_when_secret_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.delenv("DASHBOARD_PROOF_SECRET", raising=False)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db", "diploma_routes", "students_routes", "cohorts_routes", "join_routes"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    c = app_mod.create_app().test_client()
    r = c.get("/api/diplomas.zip?cohort=X", headers=AUTH)
    assert r.status_code == 503
