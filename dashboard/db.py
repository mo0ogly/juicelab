"""SQLite access layer for the JuiceLab dashboard.

Uses the stdlib sqlite3 module with row_factory set to sqlite3.Row so
that handlers can address columns by name. The database file path is
read from the DASHBOARD_DB env var (default: ./data/dashboard.sqlite).

The connection is opened with check_same_thread=False because Flask's
default development server may dispatch requests across worker threads;
the sqlite3 module is thread-safe at the module level when each cursor
is used in a single thread, which is the case here (one cursor per
request).
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

LOGGER = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "dashboard.sqlite"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_ROSTER_PATH = Path(__file__).parent / "data" / "roster.txt"


def db_path() -> Path:
    """Return the configured database path, creating its parent if needed."""
    raw = os.environ.get("DASHBOARD_DB", str(DEFAULT_DB_PATH))
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def roster_path() -> Path:
    raw = os.environ.get("DASHBOARD_ROSTER", str(DEFAULT_ROSTER_PATH))
    return Path(raw).expanduser().resolve()


def load_roster() -> dict[str, str]:
    """Return token -> display name mapping. Empty dict if file missing.

    Format: one entry per line, `<token>\\s+<name>`. Lines starting with `#`
    and blanks are ignored. The token is the JuiceLab UUID emitted by the
    overlay (events.student_token).
    """
    path = roster_path()
    if not path.is_file():
        return {}
    mapping: dict[str, str] = {}
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            token, name = parts[0].strip(), parts[1].strip()
            if token and name:
                mapping[token] = name
    except OSError as exc:
        LOGGER.warning("roster read failed at %s: %s", path, exc)
        return {}
    return mapping


def init_schema(path: Path | None = None) -> None:
    """Apply schema.sql idempotently on the configured database, then run
    the in-code migrations to bring an existing DB up to the current
    column set (CREATE TABLE IF NOT EXISTS does not add new columns to
    an already-existing table)."""
    target = path or db_path()
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(target) as conn:
        conn.executescript(schema_sql)
        _migrate(conn)
    LOGGER.info("schema initialised at %s", target)


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply additive migrations on existing databases. Safe to run on a
    fresh DB too — every step is guarded against re-application."""
    cur = conn.cursor()
    columns = {row[1] for row in cur.execute("PRAGMA table_info(events)").fetchall()}
    if "award_pushed_at" not in columns:
        LOGGER.info("migrating events: ADD COLUMN award_pushed_at TEXT")
        cur.execute("ALTER TABLE events ADD COLUMN award_pushed_at TEXT")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_award_pending "
        "ON events(event_type, award_pushed_at)"
    )
    # students table : add status workflow columns. Legacy rows (no status
    # column) get 'validated' so existing classrooms keep emitting events
    # without prof re-approval. New rows created by /api/cohort/join start
    # as 'pending' and must be approved by the prof.
    student_cols = {row[1] for row in cur.execute("PRAGMA table_info(students)").fetchall()}
    if student_cols:  # table exists
        if "email" not in student_cols:
            LOGGER.info("migrating students: ADD COLUMN email TEXT")
            cur.execute("ALTER TABLE students ADD COLUMN email TEXT")
        if "status" not in student_cols:
            LOGGER.info("migrating students: ADD COLUMN status TEXT DEFAULT 'validated'")
            # Default 'validated' for the ALTER so legacy rows keep working;
            # the CREATE TABLE schema uses 'pending' for fresh installs which
            # is what new join requests will inherit.
            cur.execute("ALTER TABLE students ADD COLUMN status TEXT NOT NULL DEFAULT 'validated'")
        if "dashboard_url_used" not in student_cols:
            cur.execute("ALTER TABLE students ADD COLUMN dashboard_url_used TEXT")
        if "decided_at" not in student_cols:
            cur.execute("ALTER TABLE students ADD COLUMN decided_at TEXT")
        if "decided_by" not in student_cols:
            cur.execute("ALTER TABLE students ADD COLUMN decided_by TEXT")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_students_status ON students(cohort_id, status)"
        )
    # cohorts table : seed from distinct events.cohort_id so existing data
    # is browsable right after migration. Idempotent (INSERT OR IGNORE).
    has_cohorts = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cohorts'"
    ).fetchone()
    if has_cohorts:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        cur.execute(
            "INSERT OR IGNORE INTO cohorts (cohort_id, label, created_at) "
            "SELECT DISTINCT cohort_id, NULL, ? FROM events WHERE cohort_id IS NOT NULL",
            (now,),
        )

    # students table : seed from roster.txt if present and table empty. This
    # lets a project upgrading from the file-based roster migrate transparently.
    has_students = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='students'"
    ).fetchone()
    if has_students:
        n = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if n == 0:
            roster = load_roster()
            if roster:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc).isoformat()
                cohort = os.environ.get("DASHBOARD_DEFAULT_COHORT") or ""
                if cohort:
                    cur.executemany(
                        "INSERT OR IGNORE INTO students "
                        "(cohort_id, student_token, display_name, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        [(cohort, tok, name, now, now) for tok, name in roster.items()],
                    )
                    LOGGER.info("seeded %d students from roster.txt into cohort %s", len(roster), cohort)
    # Phase 1 — tags + notes + alerts (idempotent)
    for stmt in [
        "CREATE TABLE IF NOT EXISTS student_tag (student_token TEXT NOT NULL, cohort_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'none', updated_at TEXT NOT NULL, PRIMARY KEY (cohort_id, student_token))",
        "CREATE TABLE IF NOT EXISTS student_note (student_token TEXT NOT NULL, cohort_id TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, PRIMARY KEY (cohort_id, student_token))",
        "CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, cohort_id TEXT NOT NULL, student_token TEXT NOT NULL, kind TEXT NOT NULL, challenge_key TEXT, created_at TEXT NOT NULL, ack_at TEXT)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_cohort_unack ON alerts(cohort_id, ack_at)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_recent ON alerts(cohort_id, created_at DESC)",
    ]:
        cur.execute(stmt)
    conn.commit()


@contextmanager
def get_connection(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a sqlite3 Connection with Row row_factory and proper closing."""
    target = path or db_path()
    conn = sqlite3.connect(target, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---- Team mapping helpers -------------------------------------------------

def get_team_mapping(
    conn: sqlite3.Connection, student_token: str
) -> tuple[int | None, int | None] | None:
    """Look up the cached CTFd identity for a student. Returns
    (team_id, user_id) tuple — either may be None if the lookup found
    only one of them — or None if no row exists yet."""
    row = conn.execute(
        "SELECT ctfd_team_id, ctfd_user_id FROM student_team_mapping "
        "WHERE student_token = ?",
        (student_token,),
    ).fetchone()
    if row is None:
        return None
    return (row["ctfd_team_id"], row["ctfd_user_id"])


def set_team_mapping(
    conn: sqlite3.Connection,
    student_token: str,
    team_id: int | None,
    user_id: int | None,
    synced_at: str,
) -> None:
    """Upsert the CTFd identity cache for a student. Called after a
    successful resolution against the CTFd /api/v1/teams or /api/v1/users
    endpoint."""
    conn.execute(
        "INSERT INTO student_team_mapping "
        "(student_token, ctfd_team_id, ctfd_user_id, last_synced_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(student_token) DO UPDATE SET "
        "ctfd_team_id = excluded.ctfd_team_id, "
        "ctfd_user_id = excluded.ctfd_user_id, "
        "last_synced_at = excluded.last_synced_at",
        (student_token, team_id, user_id, synced_at),
    )
    conn.commit()


def count_team_mappings(conn: sqlite3.Connection) -> int:
    """Number of students with a non-null CTFd team_id. Used by the
    /api/admin/ctfd-status endpoint."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM student_team_mapping "
        "WHERE ctfd_team_id IS NOT NULL"
    ).fetchone()
    return int(row["n"]) if row else 0


# ---- Award push helpers ---------------------------------------------------

def mark_award_pushed(conn: sqlite3.Connection, event_id: int, ts: str) -> None:
    """Stamp the events row so a subsequent reconcile-awards run skips it.
    Called by _push_hint_penalty on a successful POST to CTFd."""
    conn.execute(
        "UPDATE events SET award_pushed_at = ? WHERE id = ?",
        (ts, event_id),
    )
    conn.commit()


def pending_award_events(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """List the hint_revealed events that have not been pushed to CTFd yet
    (CTFd was unreachable, or feature was disabled at the time). The
    /api/admin/reconcile-awards endpoint iterates over this list to retry
    pushes on demand."""
    return conn.execute(
        "SELECT id, student_token, cohort_id, challenge_key, data_json "
        "FROM events "
        "WHERE event_type = 'hint_revealed' AND award_pushed_at IS NULL "
        "ORDER BY id ASC"
    ).fetchall()


def count_pending_award_events(conn: sqlite3.Connection) -> int:
    """How many hint_revealed events are waiting for a CTFd push. Used by
    /api/admin/ctfd-status."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM events "
        "WHERE event_type = 'hint_revealed' AND award_pushed_at IS NULL"
    ).fetchone()
    return int(row["n"]) if row else 0


# ---- Students roster helpers ----------------------------------------------

def ensure_student(conn: sqlite3.Connection, cohort_id: str, student_token: str, now: str) -> None:
    """Idempotent upsert: register a (cohort, token) pair on first sighting.
    display_name stays NULL so the prof can fill it via /admin/students.
    status='validated' for the legacy auto-discovery path (events arriving
    without a prior /api/cohort/join). ON CONFLICT DO NOTHING preserves
    any decision the prof already made on an existing row (pending,
    rejected, or validated)."""
    conn.execute(
        "INSERT INTO students (cohort_id, student_token, display_name, status, created_at, updated_at) "
        "VALUES (?, ?, NULL, 'validated', ?, ?) "
        "ON CONFLICT(cohort_id, student_token) DO NOTHING",
        (cohort_id, student_token, now, now),
    )


def list_students(conn: sqlite3.Connection, cohort_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT s.cohort_id, s.student_token, s.display_name, s.email, s.status, "
        "       s.dashboard_url_used, s.decided_at, s.decided_by, s.created_at, s.updated_at, "
        "       (SELECT COUNT(*) FROM events e "
        "          WHERE e.cohort_id = s.cohort_id AND e.student_token = s.student_token) AS event_count "
        "  FROM students s "
        " WHERE s.cohort_id = ? "
        " ORDER BY COALESCE(s.display_name, s.student_token) COLLATE NOCASE ASC",
        (cohort_id,),
    ).fetchall()


def per_student_stats(conn: sqlite3.Connection, cohort_id: str) -> list[sqlite3.Row]:
    """Per-student aggregated stats for the teacher dashboard.

    Returns one row per student in the cohort with counts of distinct
    challenges solved / hints consumed / quizzes completed / flags
    verified, plus the last event timestamp. Used by /api/students/stats
    to render progression bars + last-activity columns.
    """
    # Note: hint cost_pct and quiz score are stored inside data_json. SQLite's
    # json_extract() lets us aggregate them server-side instead of fetching
    # every event row into Python.
    return conn.execute(
        "SELECT s.student_token,"
        "  (SELECT COUNT(DISTINCT challenge_key) FROM events e"
        "     WHERE e.cohort_id = s.cohort_id AND e.student_token = s.student_token"
        "       AND e.event_type = 'challenge_solved') AS challenges_solved,"
        "  (SELECT COUNT(*) FROM events e"
        "     WHERE e.cohort_id = s.cohort_id AND e.student_token = s.student_token"
        "       AND e.event_type = 'hint_revealed') AS hints_used,"
        "  (SELECT COALESCE(SUM(CAST(json_extract(data_json, '$.cost_pct') AS INTEGER)), 0)"
        "     FROM events e WHERE e.cohort_id = s.cohort_id"
        "       AND e.student_token = s.student_token"
        "       AND e.event_type = 'hint_revealed') AS hint_penalty_sum,"
        "  (SELECT COUNT(DISTINCT challenge_key) FROM events e"
        "     WHERE e.cohort_id = s.cohort_id AND e.student_token = s.student_token"
        "       AND e.event_type = 'quiz_completed') AS quizzes_done,"
        "  (SELECT AVG(CAST(json_extract(data_json, '$.score') AS REAL))"
        "     FROM events e WHERE e.cohort_id = s.cohort_id"
        "       AND e.student_token = s.student_token"
        "       AND e.event_type = 'quiz_completed'"
        "       AND json_extract(data_json, '$.score') IS NOT NULL) AS quiz_avg_score,"
        "  (SELECT COUNT(*) FROM events e"
        "     WHERE e.cohort_id = s.cohort_id AND e.student_token = s.student_token"
        "       AND e.event_type = 'flag_verified') AS flags_verified,"
        "  (SELECT COUNT(*) FROM events e"
        "     WHERE e.cohort_id = s.cohort_id AND e.student_token = s.student_token"
        "       AND e.event_type = 'journal_filled'"
        "       AND json_extract(data_json, '$.phase') = 'after'"
        "       AND length(COALESCE(json_extract(data_json, '$.text'), '')) > 0)"
        "    AS journals_written,"
        "  (SELECT COALESCE(SUM(CAST(json_extract(data_json, '$.word_count') AS INTEGER)), 0)"
        "     FROM events e WHERE e.cohort_id = s.cohort_id"
        "       AND e.student_token = s.student_token"
        "       AND e.event_type = 'journal_filled'"
        "       AND json_extract(data_json, '$.phase') = 'after') AS journal_word_total,"
        "  (SELECT MAX(client_ts) FROM events e"
        "     WHERE e.cohort_id = s.cohort_id AND e.student_token = s.student_token) AS last_event_ts"
        "  FROM students s WHERE s.cohort_id = ?",
        (cohort_id,),
    ).fetchall()


def events_for_student(conn: sqlite3.Connection, student_token: str,
                        cohort_id: str) -> list[sqlite3.Row]:
    """Full event timeline for one student across the whole cohort.

    Ordered ascending by insertion id. Returns every column the teacher
    detail view needs : type, challenge, payload, both timestamps,
    instance label. Power source for /admin/student/<token>.
    """
    return conn.execute(
        "SELECT id, event_type, challenge_key, data_json, client_ts, server_ts, "
        "       instance_label, award_pushed_at "
        "  FROM events "
        " WHERE student_token = ? AND cohort_id = ? "
        " ORDER BY id ASC",
        (student_token, cohort_id),
    ).fetchall()


def events_by_type(conn: sqlite3.Connection, cohort_id: str) -> list[sqlite3.Row]:
    """Histogram : count of events grouped by event_type for a cohort."""
    return conn.execute(
        "SELECT event_type, COUNT(*) AS n FROM events "
        "  WHERE cohort_id = ? GROUP BY event_type ORDER BY n DESC",
        (cohort_id,),
    ).fetchall()


def events_by_day(conn: sqlite3.Connection, cohort_id: str, days: int = 7) -> list[sqlite3.Row]:
    """Daily activity for the last N days. ISO date in 'day', count in 'n'."""
    return conn.execute(
        "SELECT substr(client_ts, 1, 10) AS day, COUNT(*) AS n FROM events "
        "  WHERE cohort_id = ? AND client_ts >= date('now', ?) "
        "  GROUP BY day ORDER BY day ASC",
        (cohort_id, f"-{int(days)} days"),
    ).fetchall()


def list_pending_students(conn: sqlite3.Connection, cohort_id: str) -> list[sqlite3.Row]:
    """Pending join requests for a cohort. Empty list if cohort_id unknown."""
    return conn.execute(
        "SELECT cohort_id, student_token, display_name, email, dashboard_url_used, "
        "       created_at, updated_at "
        "  FROM students "
        " WHERE cohort_id = ? AND status = 'pending' "
        " ORDER BY created_at ASC",
        (cohort_id,),
    ).fetchall()


def create_join_request(
    conn: sqlite3.Connection,
    cohort_id: str,
    student_token: str,
    email: str,
    dashboard_url: str,
    now: str,
) -> str:
    """Upsert a join request for a (cohort, token) pair.

    Returns the current status after the upsert: 'pending' on fresh row or
    on re-submit while still pending, 'validated' if the prof already
    approved (re-emission is then idempotent), 'rejected' if already
    refused (the student would see the rejected banner again).
    """
    row = conn.execute(
        "SELECT status FROM students WHERE cohort_id = ? AND student_token = ?",
        (cohort_id, student_token),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO students (cohort_id, student_token, display_name, email, status, "
            "                      dashboard_url_used, created_at, updated_at) "
            "VALUES (?, ?, NULL, ?, 'pending', ?, ?, ?)",
            (cohort_id, student_token, email or None, dashboard_url or None, now, now),
        )
        return "pending"
    conn.execute(
        "UPDATE students SET email = COALESCE(?, email), "
        "                    dashboard_url_used = COALESCE(?, dashboard_url_used), "
        "                    updated_at = ? "
        " WHERE cohort_id = ? AND student_token = ?",
        (email or None, dashboard_url or None, now, cohort_id, student_token),
    )
    return str(row["status"])


def get_student_status(
    conn: sqlite3.Connection, student_token: str, cohort_id: str | None = None
) -> tuple[str, str] | None:
    """Return (status, cohort_id) for a student_token. If cohort_id given,
    scope the lookup ; otherwise return the first match (a token is a UUID
    so collisions across cohorts are not expected). None if unknown."""
    if cohort_id:
        row = conn.execute(
            "SELECT status, cohort_id FROM students WHERE cohort_id = ? AND student_token = ?",
            (cohort_id, student_token),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT status, cohort_id FROM students WHERE student_token = ? LIMIT 1",
            (student_token,),
        ).fetchone()
    if row is None:
        return None
    return (str(row["status"]), str(row["cohort_id"]))


def set_student_decision(
    conn: sqlite3.Connection,
    cohort_id: str,
    student_token: str,
    decision: str,
    decided_by: str,
    now: str,
) -> int:
    """Set status to 'validated' or 'rejected'. Returns rowcount (0 if row
    not found, 1 on success). Caller must validate `decision`."""
    cur = conn.execute(
        "UPDATE students SET status = ?, decided_at = ?, decided_by = ?, updated_at = ? "
        " WHERE cohort_id = ? AND student_token = ?",
        (decision, now, decided_by or None, now, cohort_id, student_token),
    )
    return cur.rowcount


def cohort_exists(conn: sqlite3.Connection, cohort_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM cohorts WHERE cohort_id = ?", (cohort_id,)
    ).fetchone()
    return row is not None


def upsert_student_name(
    conn: sqlite3.Connection, cohort_id: str, student_token: str, name: str | None, now: str
) -> None:
    """Set or clear display_name. Creates the row if missing (manual add by prof)."""
    conn.execute(
        "INSERT INTO students (cohort_id, student_token, display_name, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(cohort_id, student_token) DO UPDATE SET "
        "display_name = excluded.display_name, updated_at = excluded.updated_at",
        (cohort_id, student_token, name, now, now),
    )


def delete_student(conn: sqlite3.Connection, cohort_id: str, student_token: str) -> int:
    """Hard delete the roster row. Events are kept (historical record)."""
    cur = conn.execute(
        "DELETE FROM students WHERE cohort_id = ? AND student_token = ?",
        (cohort_id, student_token),
    )
    return cur.rowcount


def purge_orphan_events(conn: sqlite3.Connection, cohort_id: str) -> int:
    """Drop events whose student_token has no row in students(cohort_id).

    Cleans up the trail left by /api/students DELETE (which keeps events
    for audit) or by test recettes that emit events under throwaway
    tokens. Returns the number of rows removed.
    """
    cur = conn.execute(
        "DELETE FROM events WHERE cohort_id = ? "
        "  AND student_token NOT IN (SELECT student_token FROM students WHERE cohort_id = ?)",
        (cohort_id, cohort_id),
    )
    return cur.rowcount


# ---- Cohorts registry helpers ---------------------------------------------

def ensure_cohort(conn: sqlite3.Connection, cohort_id: str, now: str) -> None:
    """Idempotent registration. Called from _insert_event on every sync."""
    conn.execute(
        "INSERT INTO cohorts (cohort_id, label, created_at) VALUES (?, NULL, ?) "
        "ON CONFLICT(cohort_id) DO NOTHING",
        (cohort_id, now),
    )


def list_cohorts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return cohorts with counts (events + students). Sorted by label/id."""
    return conn.execute(
        "SELECT c.cohort_id, c.label, c.created_at, "
        "       (SELECT COUNT(*) FROM events e WHERE e.cohort_id = c.cohort_id) AS event_count, "
        "       (SELECT COUNT(*) FROM students s WHERE s.cohort_id = c.cohort_id) AS student_count "
        "  FROM cohorts c "
        " ORDER BY COALESCE(c.label, c.cohort_id) COLLATE NOCASE ASC"
    ).fetchall()


def upsert_cohort(conn: sqlite3.Connection, cohort_id: str, label: str | None, now: str) -> None:
    conn.execute(
        "INSERT INTO cohorts (cohort_id, label, created_at) VALUES (?, ?, ?) "
        "ON CONFLICT(cohort_id) DO UPDATE SET label = excluded.label",
        (cohort_id, label, now),
    )


def reset_cohort(conn: sqlite3.Connection, cohort_id: str) -> dict[str, int]:
    """Wipe events + students for the cohort. Cohort row stays."""
    e = conn.execute("DELETE FROM events WHERE cohort_id = ?", (cohort_id,)).rowcount
    s = conn.execute("DELETE FROM students WHERE cohort_id = ?", (cohort_id,)).rowcount
    return {"events_deleted": e, "students_deleted": s}


def delete_cohort(conn: sqlite3.Connection, cohort_id: str) -> dict[str, int]:
    """Drop cohort row + events + students. Hard delete."""
    out = reset_cohort(conn, cohort_id)
    c = conn.execute("DELETE FROM cohorts WHERE cohort_id = ?", (cohort_id,)).rowcount
    out["cohorts_deleted"] = c
    return out


def names_for_cohort(conn: sqlite3.Connection, cohort_id: str) -> dict[str, str]:
    """token -> human label map. Uses display_name, falling back to email
    when the prof has not renamed the student inline. Students enrolled via
    the cohort-join flow carry only an email (display_name stays NULL), so
    without this fallback they surface in the matrix as opaque tokens. Rows
    with neither a name nor an email are skipped."""
    rows = conn.execute(
        "SELECT student_token, "
        "       COALESCE(NULLIF(display_name, ''), email) AS label "
        "  FROM students "
        " WHERE cohort_id = ? "
        "   AND COALESCE(NULLIF(display_name, ''), email) IS NOT NULL",
        (cohort_id,),
    ).fetchall()
    return {r["student_token"]: r["label"] for r in rows}


# ------------------------------------------------------------------
# Phase 1 helpers — tags, notes, alerts
# ------------------------------------------------------------------
# ON CONFLICT target uses (cohort_id, student_token) to match the
# composite PRIMARY KEY declaration order in schema.sql (cohort_id
# first, aligned with the students table convention from Task 1 fix).
# SQLite accepts either column order on the conflict target, but
# matching the PK keeps things defensive and grep-friendly.

def set_tag(conn: sqlite3.Connection, student_token: str, cohort_id: str, status: str, now: str) -> None:
    conn.execute(
        "INSERT INTO student_tag (student_token, cohort_id, status, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(cohort_id, student_token) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at",
        (student_token, cohort_id, status, now),
    )


def get_tag(conn: sqlite3.Connection, student_token: str, cohort_id: str) -> str | None:
    row = conn.execute(
        "SELECT status FROM student_tag WHERE student_token=? AND cohort_id=?",
        (student_token, cohort_id),
    ).fetchone()
    return row[0] if row else None


def tags_for_cohort(conn: sqlite3.Connection, cohort_id: str) -> dict[str, str]:
    """Return {student_token: status} for all tagged students in the cohort."""
    rows = conn.execute(
        "SELECT student_token, status FROM student_tag WHERE cohort_id=?",
        (cohort_id,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def set_note(conn: sqlite3.Connection, student_token: str, cohort_id: str, body: str, now: str) -> None:
    conn.execute(
        "INSERT INTO student_note (student_token, cohort_id, body, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(cohort_id, student_token) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at",
        (student_token, cohort_id, body, now),
    )


def get_note(conn: sqlite3.Connection, student_token: str, cohort_id: str) -> str:
    row = conn.execute(
        "SELECT body FROM student_note WHERE student_token=? AND cohort_id=?",
        (student_token, cohort_id),
    ).fetchone()
    return row[0] if row else ""


def insert_alert(conn: sqlite3.Connection, cohort_id: str, student_token: str, kind: str, challenge_key: str | None, now: str) -> int:
    cur = conn.execute(
        "INSERT INTO alerts (cohort_id, student_token, kind, challenge_key, created_at) VALUES (?, ?, ?, ?, ?)",
        (cohort_id, student_token, kind, challenge_key, now),
    )
    return cur.lastrowid or 0


def recent_alerts(conn: sqlite3.Connection, cohort_id: str, limit: int = 100) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT id, cohort_id, student_token, kind, challenge_key, created_at, ack_at "
        "FROM alerts WHERE cohort_id=? ORDER BY id DESC LIMIT ?",
        (cohort_id, limit),
    ).fetchall()


def ack_alert(conn: sqlite3.Connection, alert_id: int, now: str) -> int:
    """Stamp ack_at on a single alert if not already acked. Returns rowcount
    (0 if alert missing or already acked, 1 on success). Caller commits."""
    cur = conn.execute(
        "UPDATE alerts SET ack_at=? WHERE id=? AND ack_at IS NULL",
        (now, alert_id),
    )
    return cur.rowcount
