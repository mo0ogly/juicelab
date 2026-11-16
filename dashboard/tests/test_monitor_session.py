"""monitor.py : session horizon, absent students, auto-resolution.

State alerts (blocked, stuck, idle, absent) describe a situation, so they
only make sense while the student is in the current session and they close
by themselves when the situation ends. Same module-reload caveat as
tests/test_monitor.py : run serially.
"""
from __future__ import annotations

import importlib
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

COHORT = "c1"


@pytest.fixture
def db_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    for name in ("DASHBOARD_CONFIG_JSON", "DASHBOARD_MONITOR_SESSION_MIN", "DASHBOARD_MONITOR_IDLE_MIN"):
        monkeypatch.delenv(name, raising=False)
    for m in ["db", "db_alerts", "monitor"]:
        if m in sys.modules:
            del sys.modules[m]
    import db
    importlib.reload(db)
    db.init_schema()
    return db


def _ago(minutes: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _event(db_mod, token, event_type="hint_revealed", key="xss", minutes_ago=0.0):
    ts = _ago(minutes_ago)
    with db_mod.get_connection() as c:
        c.execute(
            "INSERT INTO events (cohort_id, student_token, event_type, challenge_key, "
            "client_ts, server_ts, data_json, instance_label) VALUES (?, ?, ?, ?, ?, ?, '{}', '')",
            (COHORT, token, event_type, key, ts, ts),
        )
        c.commit()


def _roster(db_mod, token, status="validated"):
    now = _ago(0)
    with db_mod.get_connection() as c:
        c.execute(
            "INSERT INTO students (cohort_id, student_token, display_name, status, created_at, updated_at) "
            "VALUES (?, ?, NULL, ?, ?, ?)",
            (COHORT, token, status, now, now),
        )
        c.commit()


def _alert(db_mod, token, kind, key=None, minutes_ago=0.0, ack=False):
    ts = _ago(minutes_ago)
    with db_mod.get_connection() as c:
        new_id = db_mod.insert_alert(c, COHORT, token, kind, key, ts)
        if ack:
            db_mod.ack_alert(c, new_id, ts)
        c.commit()
    return new_id


def _kinds(alerts, token):
    return {a["kind"] for a in alerts if a["student_token"] == token}


def _row(db_mod, alert_id):
    with db_mod.get_connection() as c:
        c.row_factory = sqlite3.Row
        return c.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()


# --- session horizon ------------------------------------------------------

def test_in_session_student_still_gets_state_alerts(db_mod):
    """Control : 20 min of silence is inside the session, alerts fire as before."""
    import monitor
    _event(db_mod, "tok-in", minutes_ago=20)
    assert {"idle", "blocked"} <= _kinds(monitor.compute_alerts(db_mod, COHORT), "tok-in")


def test_student_out_of_session_gets_no_state_alert(db_mod):
    """A student whose last event is older than the session is not 'idle' or 'blocked'."""
    import monitor
    for _ in range(5):
        _event(db_mod, "tok-old", minutes_ago=300)
    assert _kinds(monitor.compute_alerts(db_mod, COHORT), "tok-old") == set()


def test_session_length_is_configurable(db_mod, monkeypatch):
    import monitor
    monkeypatch.setenv("DASHBOARD_MONITOR_SESSION_MIN", "600")
    _event(db_mod, "tok-old", minutes_ago=300)
    assert "idle" in _kinds(monitor.compute_alerts(db_mod, COHORT), "tok-old")


# --- absent ---------------------------------------------------------------

def test_absent_roster_student_flagged_while_cohort_is_active(db_mod):
    import monitor
    _event(db_mod, "tok-here", minutes_ago=1)
    _roster(db_mod, "tok-missing")
    alerts = monitor.compute_alerts(db_mod, COHORT)
    assert _kinds(alerts, "tok-missing") == {"absent"}
    assert "absent" not in _kinds(alerts, "tok-here")


def test_no_absent_alert_when_nobody_is_working(db_mod):
    """No session in progress : an empty classroom raises no absence."""
    import monitor
    _event(db_mod, "tok-here", minutes_ago=300)
    _roster(db_mod, "tok-missing")
    assert _kinds(monitor.compute_alerts(db_mod, COHORT), "tok-missing") == set()


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_not_validated_student_is_never_absent(db_mod, status):
    import monitor
    _event(db_mod, "tok-here", minutes_ago=1)
    _roster(db_mod, "tok-other", status=status)
    assert _kinds(monitor.compute_alerts(db_mod, COHORT), "tok-other") == set()


def test_student_seen_earlier_but_not_today_is_absent(db_mod):
    import monitor
    _event(db_mod, "tok-here", minutes_ago=1)
    _roster(db_mod, "tok-last-week")
    _event(db_mod, "tok-last-week", minutes_ago=60 * 24 * 7)
    assert _kinds(monitor.compute_alerts(db_mod, COHORT), "tok-last-week") == {"absent"}


# --- auto-resolution ------------------------------------------------------

def test_state_alert_resolves_when_condition_ends(db_mod):
    import monitor
    stale = _alert(db_mod, "tok-a", "idle", minutes_ago=30)
    _event(db_mod, "tok-a", minutes_ago=0)  # the student is back : no longer idle
    resolved = []
    monitor.run_tick(db_mod, COHORT, on_alert=lambda a: None, on_resolved=resolved.append)
    row = _row(db_mod, stale)
    assert row["resolved_at"] is not None and row["ack_at"] is None
    assert [(r["student_token"], r["kind"]) for r in resolved] == [("tok-a", "idle")]


def test_state_alert_stays_while_condition_holds(db_mod):
    """Control : the tick must not close an alert that is still true."""
    import monitor
    _event(db_mod, "tok-a", minutes_ago=20)
    live = _alert(db_mod, "tok-a", "idle", minutes_ago=5)
    monitor.run_tick(db_mod, COHORT, on_alert=lambda a: None, on_resolved=lambda a: None)
    assert _row(db_mod, live)["resolved_at"] is None


def test_scripting_alert_is_never_auto_resolved(db_mod):
    """Scripting is an incident to review, not a state : only the teacher closes it."""
    import monitor
    incident = _alert(db_mod, "tok-a", "scripting", minutes_ago=30)
    _event(db_mod, "tok-a", minutes_ago=0)
    monitor.run_tick(db_mod, COHORT, on_alert=lambda a: None, on_resolved=lambda a: None)
    assert _row(db_mod, incident)["resolved_at"] is None


def test_acked_alert_is_not_touched_by_auto_resolution(db_mod):
    import monitor
    acked = _alert(db_mod, "tok-a", "idle", minutes_ago=30, ack=True)
    _event(db_mod, "tok-a", minutes_ago=0)
    monitor.run_tick(db_mod, COHORT, on_alert=lambda a: None, on_resolved=lambda a: None)
    assert _row(db_mod, acked)["resolved_at"] is None


def test_tick_inserts_new_alert_once(db_mod):
    import monitor
    _event(db_mod, "tok-a", minutes_ago=20)
    raised = []
    for _ in range(3):
        monitor.run_tick(db_mod, COHORT,
                         on_alert=lambda a: (raised.append(a["kind"]), monitor.persist_alert(db_mod, a)),
                         on_resolved=lambda a: None)
    assert sorted(raised) == ["blocked", "idle"]


# --- dedup after resolution ----------------------------------------------

IDLE = {"cohort_id": COHORT, "student_token": "tok-a", "kind": "idle", "challenge_key": None}


def test_auto_resolved_alert_does_not_block_a_new_one(db_mod):
    """Blocked, unblocked, blocked again 10 min later : the second one must show."""
    import monitor
    first = _alert(db_mod, "tok-a", "idle", minutes_ago=10)
    with db_mod.get_connection() as c:
        db_mod.resolve_alert_group(c, COHORT, "tok-a", "idle", None, _ago(5))
        c.commit()
    assert _row(db_mod, first)["resolved_at"] is not None
    assert monitor._is_duplicate(db_mod, IDLE) is False


def test_recently_acked_alert_still_blocks_a_new_one(db_mod):
    """Control : the teacher's acknowledgement keeps silencing for the window."""
    import monitor
    _alert(db_mod, "tok-a", "idle", minutes_ago=10, ack=True)
    assert monitor._is_duplicate(db_mod, IDLE) is True


# --- storage --------------------------------------------------------------

def test_resolved_alerts_leave_the_grouped_listing(db_mod):
    _alert(db_mod, "tok-a", "idle", minutes_ago=10)
    _alert(db_mod, "tok-b", "idle", minutes_ago=10)
    with db_mod.get_connection() as c:
        db_mod.resolve_alert_group(c, COHORT, "tok-a", "idle", None, _ago(0))
        c.commit()
        tokens = [g["student_token"] for g in db_mod.unacked_alert_groups(c, COHORT)]
    assert tokens == ["tok-b"]


def test_migration_adds_resolved_at_to_an_existing_database(tmp_path, monkeypatch):
    """A database created before this column existed keeps its rows and gains it."""
    path = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, cohort_id TEXT NOT NULL, "
        "student_token TEXT NOT NULL, kind TEXT NOT NULL, challenge_key TEXT, "
        "created_at TEXT NOT NULL, ack_at TEXT)"
    )
    conn.execute("INSERT INTO alerts (cohort_id, student_token, kind, created_at) VALUES ('c1','t','idle','2026-01-01')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DASHBOARD_DB", str(path))
    for m in ["db", "db_alerts"]:
        if m in sys.modules:
            del sys.modules[m]
    import db
    importlib.reload(db)
    db.init_schema()
    with db.get_connection() as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(alerts)").fetchall()}
        rows = c.execute("SELECT kind, resolved_at FROM alerts").fetchall()
    assert "resolved_at" in cols
    assert [tuple(r) for r in rows] == [("idle", None)]
