"""monitor.py heuristics (Phase 2).

Note: this test uses module-level reload (importlib.reload(db)) which is
NOT safe under pytest-xdist parallel workers. The project runs tests
serially; if -n is ever added, refactor to a fixture-scope='session'
pattern or a process-local sqlite path that does not require reload.
"""
from __future__ import annotations
import sys, pytest, importlib, time
from datetime import datetime, timezone, timedelta

import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def db_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    for m in ["db", "monitor"]:
        if m in sys.modules: del sys.modules[m]
    import db
    importlib.reload(db)
    db.init_schema()
    return db


def _insert_event(db_mod, cohort, token, event_type, key, minutes_ago=0):
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    with db_mod.get_connection() as c:
        c.execute(
            "INSERT INTO events (cohort_id, student_token, event_type, challenge_key, "
            "client_ts, server_ts, data_json, instance_label) "
            "VALUES (?, ?, ?, ?, ?, ?, '{}', '')",
            (cohort, token, event_type, key, ts, ts),
        )
        c.commit()


def test_blocked_detected(db_mod):
    import monitor
    _insert_event(db_mod, "c1", "tok1", "hint_revealed", "xss", minutes_ago=15)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    kinds = {a["kind"] for a in alerts}
    assert "blocked" in kinds


def test_stuck_detected(db_mod):
    import monitor
    for i in range(5):
        _insert_event(db_mod, "c1", "tok2", "hint_revealed", "sqli", minutes_ago=5)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    kinds = {a["kind"] for a in alerts}
    assert "stuck" in kinds


def test_scripting_detected(db_mod):
    import monitor
    for i in range(35):
        _insert_event(db_mod, "c1", "tok3", "hint_revealed", "xss", minutes_ago=1)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    kinds = {a["kind"] for a in alerts}
    assert "scripting" in kinds


def test_idle_detected(db_mod):
    import monitor
    # Old event 20 min ago then nothing
    _insert_event(db_mod, "c1", "tok4", "session_start", None, minutes_ago=20)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    kinds = {a["kind"] for a in alerts}
    assert "idle" in kinds


def test_no_alerts_for_active_student(db_mod):
    import monitor
    _insert_event(db_mod, "c1", "tok5", "session_start", None, minutes_ago=2)
    _insert_event(db_mod, "c1", "tok5", "hint_revealed", "xss", minutes_ago=1)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    assert alerts == [] or all(a["student_token"] != "tok5" for a in alerts)


def test_scheduler_inserts_alerts(db_mod, monkeypatch):
    """start_monitor() spawns a daemon thread that ticks and persists alerts."""
    monkeypatch.setenv("DASHBOARD_MONITOR_INTERVAL_SEC", "0.2")
    import monitor
    # Seed a cohort + stuck pattern (5 hints, not solved)
    with db_mod.get_connection() as c:
        c.execute(
            "INSERT INTO cohorts (cohort_id, created_at) VALUES (?, ?)",
            ("c1", datetime.now(timezone.utc).isoformat()),
        )
        c.commit()
    for _ in range(5):
        _insert_event(db_mod, "c1", "tok-sched", "hint_revealed", "xss", minutes_ago=1)

    monitor.start_monitor(db_mod, lambda alert: monitor.persist_alert(db_mod, alert))
    time.sleep(0.5)  # let scheduler tick at least once
    monitor.stop_monitor()

    with db_mod.get_connection() as conn:
        rows = db_mod.recent_alerts(conn, "c1")
    kinds = {r["kind"] for r in rows}
    assert "stuck" in kinds


def test_scheduler_dedupes_within_window(db_mod, monkeypatch):
    """Multiple ticks must not duplicate the same (token, kind, key) alert."""
    monkeypatch.setenv("DASHBOARD_MONITOR_INTERVAL_SEC", "0.2")
    import monitor
    with db_mod.get_connection() as c:
        c.execute(
            "INSERT INTO cohorts (cohort_id, created_at) VALUES (?, ?)",
            ("c1", datetime.now(timezone.utc).isoformat()),
        )
        c.commit()
    for _ in range(5):
        _insert_event(db_mod, "c1", "tok-dedup", "hint_revealed", "xss", minutes_ago=1)

    monitor.start_monitor(db_mod, lambda alert: monitor.persist_alert(db_mod, alert))
    time.sleep(0.7)  # let scheduler tick ~3 times
    monitor.stop_monitor()

    with db_mod.get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE cohort_id=? AND student_token=? AND kind='stuck'",
            ("c1", "tok-dedup"),
        ).fetchone()
    # Should be 1 (deduped), not 3+
    assert row[0] == 1


# --- Regression : persistent condition must not re-fire every dedupe window ---
# Observed 2026-11-16 on a real DB : 285 identical unacked alerts per condition,
# one per hour since May, because dedup only looked at the creation window.

def _insert_alert_aged(db_mod, minutes_ago, ack=False):
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    with db_mod.get_connection() as conn:
        new_id = db_mod.insert_alert(conn, "c1", "tok-old", "idle", None, ts)
        if ack:
            db_mod.ack_alert(conn, new_id, ts)
        conn.commit()
    return new_id


ALERT_IDLE = {"cohort_id": "c1", "student_token": "tok-old", "kind": "idle", "challenge_key": None}


def test_recent_alert_is_duplicate_control(db_mod):
    """Control : inside the window the alert is a duplicate (already true before the fix)."""
    import monitor
    _insert_alert_aged(db_mod, minutes_ago=5)
    assert monitor._is_duplicate(db_mod, ALERT_IDLE) is True


def test_old_unacked_alert_is_still_duplicate(db_mod):
    """An unacked alert older than the window still stands for the condition."""
    import monitor
    _insert_alert_aged(db_mod, minutes_ago=180)
    assert monitor._is_duplicate(db_mod, ALERT_IDLE) is True


def test_old_acked_alert_allows_new_one(db_mod):
    """Once acked and out of the window, the condition may be raised again."""
    import monitor
    _insert_alert_aged(db_mod, minutes_ago=180, ack=True)
    assert monitor._is_duplicate(db_mod, ALERT_IDLE) is False


def test_old_unacked_alert_other_challenge_is_not_duplicate(db_mod):
    """The unacked rule is keyed on challenge too : a different key is a new alert."""
    import monitor
    _insert_alert_aged(db_mod, minutes_ago=180)
    other = dict(ALERT_IDLE, kind="stuck", challenge_key="xss")
    assert monitor._is_duplicate(db_mod, other) is False
