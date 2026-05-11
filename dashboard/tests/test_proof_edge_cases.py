"""Coverage : remaining edge cases in proof_routes + sync_routes.

Targets specifically the un-covered branches identified by coverage:
- proof_routes lines 137-155, 170-176 (quiz submitted path with scores).
- proof_routes lines 76-86, 90 (rare event-type branches in scoring loop).
- sync_routes lines 53-58 (sync gate blocked-by-status branch).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from proof_routes import build_proof_markdown

TOKEN = "teacher-test-token-very-long-32chars!!"
AUTH = {"X-Teacher-Token": TOKEN}
COHORT = "M2-IA-2026"


def _ev(t, data, ts="2026-05-11T08:00:00Z"):
    return {"event_type": t, "data": data, "client_ts": ts, "server_ts": ts, "level_id": 1}


# --- build_proof_markdown : quiz submitted with full score breakdown ---

def test_build_proof_with_quiz_submitted_full():
    events = [
        _ev("hint_revealed", {"level": 1, "cost_pct": 10}, "2026-05-11T08:01Z"),
        _ev("hint_revealed", {"level": 2, "cost_pct": 20}, "2026-05-11T08:02Z"),
        _ev("quiz_completed", {
            "score": 75,
            "answers": {"Q1": "A", "Q2": "C", "Q3": "B"},
            "q1_score": 25, "q2_score": 25, "q3_score": 25,
        }, "2026-05-11T08:30:00Z"),
        _ev("flag_verified", {}, "2026-05-11T08:35Z"),
        _ev("challenge_solved", {}, "2026-05-11T08:36Z"),
    ]
    body = build_proof_markdown(
        student_token="abc", student_name="Bob", cohort_id=COHORT,
        challenge_key="k", challenge_name="N", challenge_category="C",
        challenge_difficulty=2, challenge_description="d", events=events,
    )
    assert "Score quiz : **75/100**" in body
    assert "Q1" in body and "Q2" in body and "Q3" in body
    # score_challenge = 100 - 30 = 70; quiz=75; avg = round(72.5) = 72 (banker's); +10 = 82
    assert "Score final : **82/100**" in body
    assert "flag CTF verifie" in body


def test_build_proof_with_quiz_no_score():
    events = [_ev("quiz_completed", {"answers": {}}, "2026-05-11T08:30Z")]
    body = build_proof_markdown(
        student_token="abc", student_name="N", cohort_id=COHORT,
        challenge_key="k", challenge_name="N", challenge_category="C",
        challenge_difficulty=2, challenge_description="d", events=events,
    )
    # Branch: quiz_data exists but score key absent -> "-/100"
    assert "Score quiz : **-/100**" in body


def test_build_proof_with_flag_only_no_solve():
    events = [_ev("flag_verified", {}, "2026-05-11T08:35Z")]
    body = build_proof_markdown(
        student_token="abc", student_name="N", cohort_id=COHORT,
        challenge_key="k", challenge_name="N", challenge_category="C",
        challenge_difficulty=2, challenge_description="d", events=events,
    )
    assert "+10 flag CTF verifie" in body


def test_build_proof_hints_over_100():
    # cost_pct sum > 100 must clamp score_challenge to 0
    events = [
        _ev("hint_revealed", {"level": 1, "cost_pct": 50}, "2026-05-11T08:01Z"),
        _ev("hint_revealed", {"level": 2, "cost_pct": 60}, "2026-05-11T08:02Z"),
        _ev("challenge_solved", {}, "2026-05-11T08:36Z"),
    ]
    body = build_proof_markdown(
        student_token="abc", student_name="N", cohort_id=COHORT,
        challenge_key="k", challenge_name="N", challenge_category="C",
        challenge_difficulty=2, challenge_description="d", events=events,
    )
    assert "**0/100**" in body


# --- sync_routes : gated by student status ------------------------------

@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "dashboard.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    for mod in ("app", "db", "sync_routes", "join_routes", "students_routes"):
        if mod in sys.modules:
            del sys.modules[mod]
    import app as app_mod
    flask_app = app_mod.create_app()
    flask_app.testing = True
    return flask_app.test_client()


def _ev_payload(token="uuid-sync-1"):
    return {
        "student_token": token,
        "cohort_id": COHORT,
        "event_type": "hint_revealed",
        "challenge_key": "loginAdminChallenge",
        "data": {"level": "N1", "cost_pct": 5},
        "client_timestamp": "2026-05-11T08:00:00Z",
    }


def test_sync_blocked_when_pending(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": COHORT, "label": "Sync"})
    isolated_app.post("/api/cohort/join", json={
        "cohort_id": COHORT, "student_token": "uuid-sync-pend", "email": "p@e.com",
    })
    r = isolated_app.post("/api/sync", json=_ev_payload("uuid-sync-pend"))
    assert r.status_code == 403
    body = r.get_json()
    assert body["status"] == "pending"
    assert body["cohort_id"] == COHORT


def test_sync_blocked_when_rejected(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": COHORT, "label": "Sync"})
    isolated_app.post("/api/cohort/join", json={
        "cohort_id": COHORT, "student_token": "uuid-sync-rej", "email": "r@e.com",
    })
    isolated_app.post("/api/students/uuid-sync-rej/reject", headers=AUTH,
                      json={"cohort_id": COHORT})
    r = isolated_app.post("/api/sync", json=_ev_payload("uuid-sync-rej"))
    assert r.status_code == 403
    assert r.get_json()["status"] == "rejected"


def test_sync_allowed_when_validated(isolated_app):
    isolated_app.post("/api/cohorts", headers=AUTH,
                      json={"cohort_id": COHORT, "label": "Sync"})
    isolated_app.post("/api/cohort/join", json={
        "cohort_id": COHORT, "student_token": "uuid-sync-ok", "email": "o@e.com",
    })
    isolated_app.post("/api/students/uuid-sync-ok/approve", headers=AUTH,
                      json={"cohort_id": COHORT})
    r = isolated_app.post("/api/sync", json=_ev_payload("uuid-sync-ok"))
    assert r.status_code in (200, 201)
