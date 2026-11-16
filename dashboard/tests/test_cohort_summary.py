"""cohort_summary.build_cohort_summary : cohort-level view for the teacher.

Covers what the matrix needs beyond per-student cells : enrolled students
with no activity, time spent per challenge, and one stats line per challenge.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

COHORT = "c1"
T0 = datetime(2026, 11, 16, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def summary_of(tmp_path, monkeypatch):
    """Return a callable building the summary of COHORT on an isolated DB."""
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    for m in ["db", "db_alerts", "cohort_summary"]:
        if m in sys.modules:
            del sys.modules[m]
    import db
    db.init_schema()
    import cohort_summary
    return lambda: cohort_summary.build_cohort_summary(COHORT)


def _student(token, status="validated", name=None):
    import db
    now = T0.isoformat()
    with db.get_connection() as c:
        c.execute(
            "INSERT INTO students (cohort_id, student_token, display_name, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (COHORT, token, name, status, now, now),
        )
        c.commit()


def _event(token, event_type, key, minute, data="{}"):
    import db
    ts = (T0 + timedelta(minutes=minute)).isoformat()
    with db.get_connection() as c:
        c.execute(
            "INSERT INTO events (cohort_id, student_token, event_type, challenge_key, "
            "client_ts, server_ts, data_json, instance_label) VALUES (?, ?, ?, ?, ?, ?, ?, '')",
            (COHORT, token, event_type, key, ts, ts, data),
        )
        c.commit()


def _classroom():
    """alice solves xss in 12 min with 2 hints, bob is on xss with 1 hint,
    carol is enrolled and did nothing."""
    _student("alice", name="Alice")
    _student("bob")
    _student("carol")
    _event("alice", "hint_revealed", "xss", 0)
    _event("alice", "hint_revealed", "xss", 5)
    _event("alice", "challenge_solved", "xss", 12)
    _event("alice", "hint_revealed", "sqli", 20)
    _event("bob", "hint_revealed", "xss", 3)


# --- unchanged contract (control) ----------------------------------------

def test_existing_keys_are_still_there(summary_of):
    _classroom()
    s = summary_of()
    for key in ("cohort_id", "students", "challenges", "matrix", "totals",
                "events_total", "event_counts", "names", "tags"):
        assert key in s, key
    assert s["challenges"] == ["sqli", "xss"]
    assert s["matrix"]["alice"]["xss"]["solved"] is True
    assert s["names"] == {"alice": "Alice"}
    assert s["events_total"] == 5


# --- enrolled students without activity ----------------------------------

def test_validated_student_without_event_is_listed(summary_of):
    _classroom()
    s = summary_of()
    assert s["students"] == ["alice", "bob", "carol"]
    assert s["matrix"]["carol"] == {}
    assert s["event_counts"]["carol"] == 0
    assert s["totals"]["carol"]["avg_score"] is None
    assert s["totals"]["carol"]["partial_score"] is None
    assert s["totals"]["carol"]["challenges_touched"] == 0


def test_active_students_counts_only_students_with_events(summary_of):
    _classroom()
    assert summary_of()["active_students"] == 2


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_not_validated_student_without_event_is_not_listed(summary_of, status):
    _classroom()
    _student("dave", status=status)
    assert "dave" not in summary_of()["students"]


def test_empty_cohort(summary_of):
    s = summary_of()
    assert s["students"] == [] and s["active_students"] == 0 and s["challenge_stats"] == {}


# --- time spent per challenge --------------------------------------------

def test_slot_carries_first_ts_and_duration(summary_of):
    _classroom()
    slot = summary_of()["matrix"]["alice"]["xss"]
    assert slot["first_ts"] == T0.isoformat()
    assert slot["duration_sec"] == 12 * 60


def test_single_event_has_zero_duration(summary_of):
    _classroom()
    assert summary_of()["matrix"]["bob"]["xss"]["duration_sec"] == 0


def test_unparseable_timestamp_gives_no_duration(summary_of):
    import db
    _student("eve")
    with db.get_connection() as c:
        c.execute(
            "INSERT INTO events (cohort_id, student_token, event_type, challenge_key, "
            "client_ts, server_ts, data_json, instance_label) VALUES (?, 'eve', 'hint_revealed', 'xss', 'not-a-date', ?, '{}', '')",
            (COHORT, T0.isoformat()),
        )
        c.commit()
    assert summary_of()["matrix"]["eve"]["xss"]["duration_sec"] is None


# --- one stats line per challenge ----------------------------------------

def test_challenge_stats_counts_and_averages(summary_of):
    _classroom()
    stats = summary_of()["challenge_stats"]
    assert set(stats) == {"sqli", "xss"}
    assert stats["xss"] == {
        "solved": 1, "in_progress": 1, "not_started": 1,
        "avg_hints": 1.5, "avg_duration_sec": 360,
    }
    assert stats["sqli"] == {
        "solved": 0, "in_progress": 1, "not_started": 2,
        "avg_hints": 1.0, "avg_duration_sec": 0,
    }


def test_challenge_stats_buckets_add_up_to_listed_students(summary_of):
    _classroom()
    s = summary_of()
    for ch, st in s["challenge_stats"].items():
        assert st["solved"] + st["in_progress"] + st["not_started"] == len(s["students"]), ch


# --- wiring ---------------------------------------------------------------

def test_api_cohort_serves_the_new_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", "teacher-test-token-very-long-32chars!!")
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_MONITOR_ENABLED", "0")
    for m in ["app", "db", "db_alerts", "cohort_summary", "monitor", "sse_pubsub"]:
        if m in sys.modules:
            del sys.modules[m]
    from app import create_app
    client = create_app().test_client()
    _classroom()
    r = client.get(f"/api/cohort?cohort={COHORT}",
                   headers={"X-Teacher-Token": "teacher-test-token-very-long-32chars!!"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["active_students"] == 2 and "carol" in body["students"]
    assert body["challenge_stats"]["xss"]["solved"] == 1
