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


def db_path() -> Path:
    """Return the configured database path, creating its parent if needed."""
    raw = os.environ.get("DASHBOARD_DB", str(DEFAULT_DB_PATH))
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
    # Always (re)attempt the index creation : on fresh installs, the column
    # comes from schema.sql but the index was excluded there to keep that
    # script applicable to legacy DBs without the column.
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_award_pending "
        "ON events(event_type, award_pushed_at)"
    )
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
