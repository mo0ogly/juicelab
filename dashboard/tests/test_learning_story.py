"""Lot 3 : per-challenge story, sessions, student history, session report.

Scenario : two sessions (TDs) a week apart.
  TD1 : alice solves xss (2 hints, quiz 80, journal), bob takes 5 hints on
        sqli without solving, carol enrolled but absent.
  TD2 : alice solves sqli, bob solves xss ; carol still absent.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

COHORT = "c1"
TD1 = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)
TD2 = TD1 + timedelta(days=7)
TEACHER = "teacher-test-token-very-long-32chars!!"


@pytest.fixture
def db_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    for name in ("DASHBOARD_CONFIG_JSON", "DASHBOARD_MONITOR_SESSION_MIN", "DASHBOARD_MONITOR_STUCK_HINTS"):
        monkeypatch.delenv(name, raising=False)
    for m in ["db", "db_alerts", "monitor", "learning_story", "session_report"]:
        sys.modules.pop(m, None)
    import db
    db.init_schema()
    return db


def _student(db, token, name=None, status="validated"):
    with db.get_connection() as c:
        c.execute("INSERT INTO students (cohort_id, student_token, display_name, status, created_at, updated_at) "
                  "VALUES (?, ?, ?, ?, '2026-11-01', '2026-11-01')", (COHORT, token, name, status))
        c.commit()


def _ev(db, token, et, key, at, minute, data=None):
    ts = (at + timedelta(minutes=minute)).isoformat()
    with db.get_connection() as c:
        c.execute("INSERT INTO events (cohort_id, student_token, event_type, challenge_key, client_ts, server_ts, "
                  "data_json, instance_label) VALUES (?, ?, ?, ?, ?, ?, ?, '')",
                  (COHORT, token, et, key, ts, ts, json.dumps(data or {})))
        c.commit()


@pytest.fixture
def classroom(db_mod):
    db = db_mod
    _student(db, "alice", "Alice"); _student(db, "bob", "Bob"); _student(db, "carol", "Carol")
    _student(db, "dave", "Dave", status="rejected")
    _ev(db, "alice", "session_start", None, TD1, 0)
    _ev(db, "alice", "hint_revealed", "xss", TD1, 1, {"level": 1, "cost_pct": 5})
    _ev(db, "alice", "hint_revealed", "xss", TD1, 4, {"level": 2, "cost_pct": 10})
    _ev(db, "alice", "challenge_solved", "xss", TD1, 13)
    _ev(db, "alice", "quiz_completed", "xss", TD1, 15, {"score": 80})
    _ev(db, "alice", "journal_filled", "xss", TD1, 20, {"phase": "after", "text": "ok", "word_count": 42})
    for i in range(5):
        _ev(db, "bob", "hint_revealed", "sqli", TD1, 2 + i, {"level": i + 1, "cost_pct": 5})
    _ev(db, "alice", "challenge_solved", "sqli", TD2, 30)
    _ev(db, "bob", "hint_revealed", "xss", TD2, 5, {"level": 1, "cost_pct": 5})
    _ev(db, "bob", "challenge_solved", "xss", TD2, 25)
    return db


def _events(db, token):
    with db.get_connection() as c:
        return db.events_for_student(c, token, COHORT)


# --- story ----------------------------------------------------------------

def test_story_of_a_solved_challenge(classroom):
    import learning_story
    st = {s["challenge_key"]: s for s in learning_story.challenge_stories(_events(classroom, "alice"))}
    xss = st["xss"]
    assert xss["status"] == "solved" and xss["duration_sec"] == 12 * 60
    assert [s["kind"] for s in xss["steps"]] == ["start", "hint", "hint", "solved", "quiz", "journal"]
    assert xss["hint_cost_total"] == 15 and xss["quiz"]["score"] == 80 and xss["journal_words"] == 42
    assert list(st) == ["xss", "sqli"], "stories in the order the student started them"


def test_story_of_an_unsolved_challenge(classroom):
    import learning_story
    (sqli,) = learning_story.challenge_stories(_events(classroom, "bob"))[:1]
    assert sqli["status"] == "in_progress" and sqli["solved_at"] is None
    assert sqli["duration_sec"] == 4 * 60 and len(sqli["hints"]) == 5


def test_story_ignores_events_without_challenge_and_bad_payload():
    import learning_story
    rows = [
        {"event_type": "session_start", "challenge_key": None, "data_json": "{}", "client_ts": "x", "server_ts": "x"},
        {"event_type": "hint_revealed", "challenge_key": "k", "data_json": "not json", "client_ts": "bad", "server_ts": "bad"},
    ]
    (st,) = learning_story.challenge_stories(rows)
    assert st["hints"] == [{"level": None, "cost_pct": 0, "ts": "bad"}] and st["duration_sec"] is None


# --- sessions -------------------------------------------------------------

def test_split_sessions_on_silence(classroom):
    import session_report
    with classroom.get_connection() as c:
        sessions = session_report.cohort_sessions(c, COHORT)
    assert [s["index"] for s in sessions] == [1, 2]
    assert sessions[0]["students"] == ["alice", "bob"] and sessions[0]["events"] == 11
    assert sessions[1]["start"].startswith("2026-11-16")


def test_session_gap_follows_monitor_horizon(classroom, monkeypatch):
    import learning_story, session_report
    monkeypatch.setenv("DASHBOARD_MONITOR_SESSION_MIN", str(60 * 24 * 8))
    assert learning_story.session_gap_minutes() == 60 * 24 * 8
    with classroom.get_connection() as c:
        assert len(session_report.cohort_sessions(c, COHORT)) == 1


def test_student_history_across_sessions(classroom):
    import learning_story, session_report
    with classroom.get_connection() as c:
        sessions = session_report.cohort_sessions(c, COHORT)
    alice = learning_story.student_sessions(_events(classroom, "alice"), sessions)
    assert [(h["solved_new"], h["solved_total"], h["quiz_avg"]) for h in alice] == [(["xss"], 1, 80), (["sqli"], 2, None)]
    carol = learning_story.student_sessions(_events(classroom, "carol"), sessions)
    assert [h["attended"] for h in carol] == [False, False] and carol[-1]["solved_total"] == 0


# --- session report -------------------------------------------------------

def _report(db, index=None):
    import session_report
    with db.get_connection() as c:
        return session_report.build_session_report(c, COHORT, index)


def test_report_first_session(classroom):
    r = _report(classroom, 1)
    by = {s["token"]: s for s in r["students"]}
    assert by["alice"]["solved"] == ["xss"] and by["alice"]["reasons"] == []
    assert by["bob"]["reasons"] == ["no_solve", "stuck"] and by["bob"]["stuck_on"] == ["sqli"]
    assert [a["token"] for a in r["absent"]] == ["carol"], "rejected dave is never absent"
    assert r["to_review"] == 2
    ch = {c["key"]: c for c in r["challenges"]}
    assert ch["sqli"] == {"key": "sqli", "attempted": 1, "solved": 0, "avg_hints": 5.0, "rework": True}
    assert ch["xss"]["rework"] is False
    assert [c["key"] for c in r["challenges"]] == ["sqli", "xss"], "lowest solve rate first"


def test_report_defaults_to_latest_session(classroom):
    r = _report(classroom)
    assert r["session"]["index"] == 2
    assert {s["token"]: s["solved"] for s in r["students"]} == {"alice": ["sqli"], "bob": ["xss"]}


def test_report_none_when_out_of_range_or_empty(db_mod, classroom):
    assert _report(classroom, 3) is None and _report(classroom, 0) is None


def test_report_none_for_cohort_without_events(db_mod):
    assert _report(db_mod) is None


def test_rework_needs_strict_minority_of_solvers(classroom):
    """Session 2 : xss tried by bob (solved) and nobody else -> fine ; add a
    failing attempter : 1 solver out of 2 is still not 'to rework'."""
    _ev(classroom, "carol", "hint_revealed", "xss", TD2, 10, {"level": 1, "cost_pct": 5})
    ch = {c["key"]: c for c in _report(classroom, 2)["challenges"]}
    assert (ch["xss"]["attempted"], ch["xss"]["solved"], ch["xss"]["rework"]) == (2, 1, False)


# --- routes ---------------------------------------------------------------

@pytest.fixture
def client(classroom, monkeypatch):
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TEACHER)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_MONITOR_ENABLED", "0")
    for m in ["app", "cohort_summary", "sse_pubsub", "students_routes", "session_report_routes"]:
        sys.modules.pop(m, None)
    from app import create_app
    return create_app().test_client()


def test_detail_api_serves_stories_and_history(client):
    r = client.get(f"/api/students/bob/detail?cohort={COHORT}", headers={"X-Teacher-Token": TEACHER})
    body = r.get_json()
    assert r.status_code == 200
    assert [s["challenge_key"] for s in body["stories"]] == ["sqli", "xss"]
    assert [h["solved_new"] for h in body["history"]] == [[], ["xss"]]
    assert body["timeline"] and body["per_challenge"], "previous fields kept"


def test_report_page_renders(client):
    r = client.get(f"/admin/session-report?cohort={COHORT}&session=1", headers={"X-Teacher-Token": TEACHER})
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Bob" in html and "Carol" in html and "sqli" in html
    assert "REPORT_" not in html, "every label is translated"


@pytest.mark.parametrize("qs,status", [("", 400), (f"cohort={COHORT}&session=abc", 400)])
def test_report_page_rejects_bad_query(client, qs, status):
    assert client.get("/admin/session-report?" + qs, headers={"X-Teacher-Token": TEACHER}).status_code == status


def test_report_page_requires_teacher(client):
    r = client.get(f"/admin/session-report?cohort={COHORT}")
    assert r.status_code in (302, 401, 403)
