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

from diploma_routes import build_diploma_md, sign_diploma
from diploma_scores import mention_for as _mention_for
from verify_proof import verify

TOKEN = "teacher-test-token-very-long-32chars!!"
AUTH = {"X-Teacher-Token": TOKEN}
PROOF_SECRET = "diploma-test-secret-very-long-32chars"
SECRET = PROOF_SECRET.encode()
COHORT = "M2-IA-2026"


ISSUED = "2026-11-16T10:00:00+00:00"
FIGURES = {
    "mention": "tres_bien", "progress_pct": 92, "challenges_solved": 12,
    "score_challenge": 85, "quiz_pct": 80, "quiz_missing": 1, "final_score": 83,
    "flags_verified": 3, "hints_used": 5, "hint_penalty": 15,
    "journals_written": 3, "journal_words": 420,
}


def _body(name, cohort):
    return build_diploma_md(student_token="abc", student_name=name, cohort_id=cohort,
                            institution="Sorbonne", figures=FIGURES, td_total=13)


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
    body = _body("Alice", COHORT)
    signed = sign_diploma(body, secret=SECRET, student_token="abc",
                          cohort_id=COHORT, mention="tres_bien", progress_pct=92,
                          final_score=75, issued_at=ISSUED)
    ok, meta = verify(signed, SECRET)
    assert ok is True
    assert meta["scheme"] == "diploma.v2"
    assert meta["student"] == "abc"


def test_sign_diploma_tamper_body():
    body = _body("Alice", COHORT)
    signed = sign_diploma(body, secret=SECRET, student_token="abc",
                          cohort_id=COHORT, mention="tres_bien", progress_pct=92,
                          final_score=75, issued_at=ISSUED)
    tampered = signed.replace("Alice", "Mallory")
    ok, _ = verify(tampered, SECRET)
    assert ok is False


def test_sign_diploma_wrong_secret():
    body = _body("A", "C")
    signed = sign_diploma(body, secret=SECRET, student_token="abc",
                          cohort_id="C", mention="bien", progress_pct=60,
                          final_score=75, issued_at=ISSUED)
    ok, _ = verify(signed, b"y" * 32)
    assert ok is False


def test_sign_diploma_empty_secret_raises():
    with pytest.raises(RuntimeError, match="DASHBOARD_PROOF_SECRET"):
        sign_diploma("body", secret=b"", student_token="s",
                     cohort_id="c", mention="bien", progress_pct=60,
                     final_score=None, issued_at=ISSUED)


def test_diploma_scheme_distinct_from_proof():
    """A diploma must have SCHEME=diploma.v2, not v1 (proof). Defense
    against a forged challenge proof being repackaged as a diploma."""
    body = _body("A", "C")
    signed = sign_diploma(body, secret=SECRET, student_token="abc",
                          cohort_id="C", mention="bien", progress_pct=60,
                          final_score=75, issued_at=ISSUED)
    assert "SCHEME: diploma.v2" in signed
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
        assert "SCHEME: diploma.v2" in content


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


# --- per-challenge scores (regression : global hint sum) ------------------

def _story(key, solved=True, costs=(), quiz=None, flag=False):
    return {"challenge_key": key, "status": "solved" if solved else "in_progress",
            "hints": [{"cost_pct": c} for c in costs], "hint_cost_total": sum(costs),
            "quiz": {"score": quiz} if quiz is not None else None, "flag_verified": flag}


def test_hint_penalty_is_per_challenge_not_global():
    """Old rule : 100 - sum of ALL hint costs -> 0 as soon as 100 % of hints
    were spent anywhere. Now each challenge is scored on its own hints."""
    from diploma_scores import diploma_figures
    f = diploma_figures([_story("a", costs=(5, 10, 20, 35, 50), quiz=80),
                         _story("b", quiz=90), _story("c", quiz=90)], td_total=3)
    assert f["score_challenge"] == round((0 + 100 + 100) / 3)
    assert f["final_score"] == round((40 + 95 + 95) / 3)


def test_final_score_matches_proof_formula():
    from diploma_scores import challenge_score
    c = challenge_score(_story("a", costs=(5, 10), quiz=70, flag=True))
    assert c == {"challenge_key": "a", "score_challenge": 85, "score_quiz": 70,
                 "bonus_flag": 10, "score_final": 88}
    assert challenge_score(_story("b", quiz=100, flag=True))["score_final"] == 100


def test_quiz_of_unsolved_challenge_is_ignored_and_missing_quiz_counts_zero():
    from diploma_scores import diploma_figures
    f = diploma_figures([_story("a", quiz=None), _story("b", solved=False, quiz=10)], td_total=2)
    assert f["quiz_pct"] is None and f["quiz_missing"] == 1
    assert f["final_score"] == 50 and f["hints_used"] == 0


def test_full_marks_without_quiz_no_longer_blocks_progress_mention():
    """Old rule used quiz avg 0 when no quiz -> at best 'reussite'. Now the
    final score drives it ; 100 % solved without quiz = final 50 -> reussite,
    stated on the diploma ; with quizzes the high mention is reachable."""
    from diploma_scores import diploma_figures
    no_quiz = diploma_figures([_story(k) for k in "abcde"], td_total=5)
    quiz = diploma_figures([_story(k, quiz=60) for k in "abcde"], td_total=5)
    assert (no_quiz["final_score"], no_quiz["mention"]) == (50, "reussite")
    assert (quiz["final_score"], quiz["mention"]) == (80, "tres_bien")


def test_nothing_solved():
    from diploma_scores import diploma_figures
    f = diploma_figures([_story("a", solved=False, costs=(5,))], td_total=13)
    assert f["final_score"] is None and f["mention"] == "participation" and f["hint_penalty"] == 5


def test_signed_footer_fields_and_verifier_output():
    body = _body("Alice", COHORT)
    signed = sign_diploma(body, secret=SECRET, student_token="abc", cohort_id=COHORT,
                          mention="tres_bien", progress_pct=92, final_score=83, issued_at=ISSUED)
    ok, meta = verify(signed, SECRET)
    assert ok and meta["progress_pct"] == "92" and meta["final_score"] == "83"
    assert meta["mention"] == "tres_bien" and meta["cohort"] == COHORT and meta["timestamp"] == ISSUED
    assert "SCORE_PCT" not in signed


# --- registry (regression : new date and signature on every view) ---------

def _diploma_page(client, token):
    r = client.get(f"/admin/diploma/{token}?cohort=" + COHORT, headers=AUTH)
    assert r.status_code == 200
    return r.get_data(as_text=True)


def _signature(html):
    import re
    return re.search(r"SIGNATURE: ([0-9a-f]{64})", html).group(1)


def test_reprint_serves_the_same_signed_diploma(isolated_app):
    _seed_student(isolated_app, token="stud-reg", solve_count=2)
    first = _diploma_page(isolated_app, "stud-reg")
    second = _diploma_page(isolated_app, "stud-reg")
    assert _signature(first) == _signature(second)
    assert 'class="diploma-stale"' not in second


def test_new_results_flag_stale_and_reissue_adds_a_row(isolated_app):
    _seed_student(isolated_app, token="stud-up", solve_count=1)
    before = _signature(_diploma_page(isolated_app, "stud-up"))
    _seed_student(isolated_app, token="stud-up", solve_count=3)
    stale = _diploma_page(isolated_app, "stud-up")
    assert _signature(stale) == before and 'class="diploma-stale"' in stale
    r = isolated_app.post("/api/diplomas/stud-up/reissue?cohort=" + COHORT, headers=AUTH)
    assert r.status_code == 200 and r.get_json()["ok"] is True
    after = _diploma_page(isolated_app, "stud-up")
    assert _signature(after) != before and 'class="diploma-stale"' not in after
    import db
    with db.get_connection() as c:
        assert c.execute("SELECT COUNT(*) FROM diplomas WHERE student_token='stud-up'").fetchone()[0] == 2


def test_reissue_requires_teacher_and_known_student(isolated_app):
    _seed_student(isolated_app, token="stud-x", solve_count=1)
    assert isolated_app.post("/api/diplomas/stud-x/reissue?cohort=" + COHORT).status_code in (401, 403)
    assert isolated_app.post("/api/diplomas/nobody/reissue?cohort=" + COHORT, headers=AUTH).status_code == 404


def test_zip_reuses_the_stored_diploma(isolated_app):
    _seed_student(isolated_app, token="stud-zip", solve_count=13)
    sig = _signature(_diploma_page(isolated_app, "stud-zip"))
    r = isolated_app.get("/api/diplomas.zip?cohort=" + COHORT, headers=AUTH)
    with zipfile.ZipFile(io.BytesIO(r.data)) as zf:
        (name,) = zf.namelist()
        assert sig in zf.read(name).decode()
