"""End-of-session report : who finished what, who to see again, which
challenges to rework.

The session is one of ``learning_story.split_sessions`` over the cohort log
(default : the latest). Thresholds reuse the monitor policy so the report
and the live alerts agree : a student is "stuck" on a challenge left
unsolved after ``monitor.stuck_hints`` hints (default 5). A challenge is
"to rework" when most of the students who tried it in the session did not
solve it (strictly fewer solvers than half of the attempters).
"""
from __future__ import annotations

import sqlite3
from typing import Any

import monitor
from learning_story import in_session, split_sessions


def cohort_events(conn: sqlite3.Connection, cohort_id: str) -> list[sqlite3.Row]:
    """Every event of the cohort (columns used by learning_story), by id."""
    return conn.execute(
        "SELECT student_token, event_type, challenge_key, data_json, client_ts, server_ts "
        "  FROM events WHERE cohort_id = ? ORDER BY id ASC",
        (cohort_id,),
    ).fetchall()


def cohort_sessions(conn: sqlite3.Connection, cohort_id: str) -> list[dict[str, Any]]:
    """Sessions of the cohort, oldest first (see learning_story.split_sessions)."""
    return split_sessions(cohort_events(conn, cohort_id))


def _roster(conn: sqlite3.Connection, cohort_id: str) -> dict[str, str | None]:
    """Validated students of the cohort : token -> display name."""
    rows = conn.execute(
        "SELECT student_token, display_name FROM students "
        " WHERE cohort_id = ? AND COALESCE(status, 'validated') = 'validated'",
        (cohort_id,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def build_session_report(conn: sqlite3.Connection, cohort_id: str,
                         index: int | None = None) -> dict[str, Any] | None:
    """Report of session ``index`` (1-based ; None = latest).

    Returns None when the cohort has no session or ``index`` is out of
    range. Otherwise : ``session`` (see split_sessions), ``sessions`` (all,
    for navigation), ``students`` (attendees, sorted by name) each with
    ``token``, ``name``, ``solved`` and ``in_progress`` (sorted keys),
    ``hints``, ``reasons`` (subset of "no_solve", "stuck" ; empty = fine),
    ``stuck_on`` ; ``absent`` [{token, name}] (validated, no event in the
    session) ; ``challenges`` [{key, attempted, solved, avg_hints, rework}]
    sorted by solve rate then key ; ``to_review`` (count of attendees with
    a reason plus absents).
    """
    events = cohort_events(conn, cohort_id)
    sessions = split_sessions(events)
    if not sessions:
        return None
    if index is None:
        index = len(sessions)
    if not 1 <= index <= len(sessions):
        return None
    session = sessions[index - 1]
    stuck_hints = monitor._seuils()["stuck_hints"]
    roster = _roster(conn, cohort_id)

    per: dict[str, dict[str, dict[str, Any]]] = {}
    for ev in events:
        if not in_session(ev, session):
            continue
        per.setdefault(ev["student_token"], {})
        key = ev["challenge_key"]
        if not key:
            continue
        c = per[ev["student_token"]].setdefault(key, {"solved": False, "hints": 0})
        if ev["event_type"] == "challenge_solved":
            c["solved"] = True
        elif ev["event_type"] == "hint_revealed":
            c["hints"] += 1

    students = []
    for token, chals in per.items():
        solved = sorted(k for k, c in chals.items() if c["solved"])
        pending = sorted(k for k, c in chals.items() if not c["solved"])
        stuck_on = sorted(k for k in pending if chals[k]["hints"] >= stuck_hints)
        reasons = (["no_solve"] if not solved else []) + (["stuck"] if stuck_on else [])
        students.append({
            "token": token, "name": roster.get(token),
            "solved": solved, "in_progress": pending,
            "hints": sum(c["hints"] for c in chals.values()),
            "reasons": reasons, "stuck_on": stuck_on,
        })
    students.sort(key=lambda s: ((s["name"] or s["token"]).lower(), s["token"]))
    absent = sorted(({"token": t, "name": n} for t, n in roster.items() if t not in per),
                    key=lambda s: ((s["name"] or s["token"]).lower(), s["token"]))

    stats: dict[str, dict[str, Any]] = {}
    for chals in per.values():
        for key, c in chals.items():
            s = stats.setdefault(key, {"key": key, "attempted": 0, "solved": 0, "_hints": 0})
            s["attempted"] += 1
            s["solved"] += int(c["solved"])
            s["_hints"] += c["hints"]
    challenges = []
    for s in stats.values():
        challenges.append({
            "key": s["key"], "attempted": s["attempted"], "solved": s["solved"],
            "avg_hints": round(s["_hints"] / s["attempted"], 1),
            "rework": s["solved"] * 2 < s["attempted"],
        })
    challenges.sort(key=lambda c: (c["solved"] / c["attempted"], c["key"]))

    return {
        "cohort_id": cohort_id, "session": session, "sessions": sessions,
        "students": students, "absent": absent, "challenges": challenges,
        "stuck_hints": stuck_hints,
        "to_review": sum(1 for s in students if s["reasons"]) + len(absent),
    }
