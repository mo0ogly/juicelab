"""Alerts storage helpers (Phase 1 CRUD + Phase 2 auto-resolution).

Moved out of db.py so the alerts table contract lives in one small module.
Every function takes an open sqlite3.Connection and — unless stated
otherwise — the caller is responsible for committing. db.py re-exports
these names so `db.insert_alert(...)`-style call sites keep working.

Terminology: an alert is ACTIVE when ack_at IS NULL AND resolved_at IS NULL.
resolved_at (Phase 2) stamps when a state alert was closed automatically by
the monitor; ack_at stamps a manual teacher acknowledgement.
"""
import sqlite3


def insert_alert(conn: sqlite3.Connection, cohort_id: str, student_token: str,
                 kind: str, challenge_key: str | None, now: str) -> int:
    """Insert one alert row.

    Inputs: open connection, cohort id, student token, alert kind, optional
    challenge key (None for cohort- or student-wide kinds) and the creation
    timestamp as ISO text. Output: the new row id (0 if the driver gives no
    lastrowid). Side effect: one INSERT, no commit — the caller commits.
    """
    cur = conn.execute(
        "INSERT INTO alerts (cohort_id, student_token, kind, challenge_key, created_at) VALUES (?, ?, ?, ?, ?)",
        (cohort_id, student_token, kind, challenge_key, now),
    )
    return cur.lastrowid or 0


def recent_alerts(conn: sqlite3.Connection, cohort_id: str, limit: int = 100) -> list[sqlite3.Row]:
    """Latest `limit` alerts of `cohort_id`, newest insertion first.

    Columns: id, cohort_id, student_token, kind, challenge_key, created_at,
    ack_at, resolved_at. Returns every alert whatever its ack/resolution
    state ; filtering (unack-only, excluding resolved) is the caller's job.
    Read-only ; sets conn.row_factory to sqlite3.Row so callers can address
    columns by name.
    """
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT id, cohort_id, student_token, kind, challenge_key, created_at, ack_at, resolved_at "
        "FROM alerts WHERE cohort_id=? ORDER BY id DESC LIMIT ?",
        (cohort_id, limit),
    ).fetchall()


def unacked_alert_groups(conn: sqlite3.Connection, cohort_id: str) -> list[sqlite3.Row]:
    """ACTIVE alerts of `cohort_id`, one row per (student_token, kind,
    challenge_key), most recently raised group first. ACTIVE means
    ack_at IS NULL AND resolved_at IS NULL : acknowledged and auto-resolved
    alerts leave the grouped listing. Columns: id (latest alert of the
    group, usable with ack_alert_group), student_token, kind, challenge_key,
    n (alerts in the group), first_at, last_at. Read-only.
    """
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT MAX(id) AS id, student_token, kind, challenge_key, COUNT(*) AS n, "
        "MIN(created_at) AS first_at, MAX(created_at) AS last_at "
        "FROM alerts WHERE cohort_id=? AND ack_at IS NULL AND resolved_at IS NULL "
        "GROUP BY student_token, kind, challenge_key ORDER BY MAX(id) DESC",
        (cohort_id,),
    ).fetchall()


def ack_alert(conn: sqlite3.Connection, alert_id: int, now: str) -> int:
    """Stamp ack_at on a single alert if not already acked. Returns rowcount
    (0 if alert missing or already acked, 1 on success). Caller commits."""
    cur = conn.execute(
        "UPDATE alerts SET ack_at=? WHERE id=? AND ack_at IS NULL",
        (now, alert_id),
    )
    return cur.rowcount


def ack_alert_group(conn: sqlite3.Connection, alert_id: int, now: str) -> int | None:
    """Stamp ack_at on every ACTIVE alert sharing (cohort_id, student_token,
    kind, challenge_key) with alert `alert_id`, that alert included.

    Only ACTIVE alerts (ack_at IS NULL AND resolved_at IS NULL) are
    acknowledged : an auto-resolved alert is already closed and needs no
    ack. Returns the number of rows acknowledged (0 when the whole group
    was already acked or resolved), or None when `alert_id` does not exist.
    `IS` compares challenge_key so a NULL key matches NULL. Caller commits."""
    ref = conn.execute(
        "SELECT cohort_id, student_token, kind, challenge_key FROM alerts WHERE id=?",
        (alert_id,),
    ).fetchone()
    if ref is None:
        return None
    cur = conn.execute(
        "UPDATE alerts SET ack_at=? WHERE cohort_id=? AND student_token=? AND kind=? "
        "AND challenge_key IS ? AND ack_at IS NULL AND resolved_at IS NULL",
        (now, ref[0], ref[1], ref[2], ref[3]),
    )
    return cur.rowcount


def resolve_alert_group(conn: sqlite3.Connection, cohort_id: str, student_token: str,
                        kind: str, challenge_key: str | None, now: str) -> int:
    """Stamp resolved_at=`now` on every ACTIVE alert matching the
    (cohort_id, student_token, kind, challenge_key) tuple.

    Used by the monitor to auto-close state alerts (blocked, stuck, idle,
    absent) whose condition ended. `IS` compares challenge_key so a None key
    matches SQL NULL. Returns the number of rows resolved (0 when the group
    has no ACTIVE alert left). Caller commits.
    """
    cur = conn.execute(
        "UPDATE alerts SET resolved_at=? WHERE cohort_id=? AND student_token=? AND kind=? "
        "AND challenge_key IS ? AND ack_at IS NULL AND resolved_at IS NULL",
        (now, cohort_id, student_token, kind, challenge_key),
    )
    return cur.rowcount


def active_alert_keys(conn: sqlite3.Connection, cohort_id: str) -> list[tuple[str, str, str | None]]:
    """Distinct (student_token, kind, challenge_key) triples of the ACTIVE
    alerts (ack_at IS NULL AND resolved_at IS NULL) of `cohort_id`.

    Used by the monitor tick to know which state alerts still stand in the
    database before auto-resolving the stale ones. Read-only; row order is
    unspecified.
    """
    rows = conn.execute(
        "SELECT DISTINCT student_token, kind, challenge_key FROM alerts "
        "WHERE cohort_id=? AND ack_at IS NULL AND resolved_at IS NULL",
        (cohort_id,),
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def student_display_names(conn: sqlite3.Connection, cohort_id: str) -> dict[str, str]:
    """Map student_token -> display_name for the students of `cohort_id` that
    have a non-empty name. Tokens without a roster row or a name are absent.
    Read-only."""
    rows = conn.execute(
        "SELECT student_token, display_name FROM students "
        "WHERE cohort_id=? AND display_name IS NOT NULL AND display_name != ''",
        (cohort_id,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}
