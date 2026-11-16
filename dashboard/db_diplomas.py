"""Registry of issued diplomas (table ``diplomas``, see schema.sql).

A diploma is issued once and then served as stored, so a reprint carries
the same date and the same signature. Re-issuing adds a new row ; nothing
is updated or deleted here.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any


def latest_diploma(conn: sqlite3.Connection, cohort_id: str,
                   student_token: str) -> dict[str, Any] | None:
    """Latest issued diploma of the student in the cohort, or None.
    ``figures`` is the decoded figures_json."""
    row = conn.execute(
        "SELECT id, issued_at, mention, progress_pct, final_score, figures_json, "
        "       signed_body, body_sha256 "
        "  FROM diplomas WHERE cohort_id = ? AND student_token = ? "
        " ORDER BY id DESC LIMIT 1",
        (cohort_id, student_token),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0], "issued_at": row[1], "mention": row[2],
        "progress_pct": row[3], "final_score": row[4],
        "figures": json.loads(row[5]), "signed_body": row[6], "body_sha256": row[7],
    }


def count_issuances(conn: sqlite3.Connection, cohort_id: str, student_token: str) -> int:
    """How many times the diploma of this student was issued (0 = never)."""
    return conn.execute(
        "SELECT COUNT(*) FROM diplomas WHERE cohort_id = ? AND student_token = ?",
        (cohort_id, student_token),
    ).fetchone()[0]


def insert_diploma(conn: sqlite3.Connection, *, cohort_id: str, student_token: str,
                   issued_at: str, figures: dict[str, Any], signed_body: str) -> int:
    """Record one issuance and return its id. The caller commits."""
    cur = conn.execute(
        "INSERT INTO diplomas (cohort_id, student_token, issued_at, mention, progress_pct, "
        "                      final_score, figures_json, signed_body, body_sha256) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (cohort_id, student_token, issued_at, figures["mention"], figures["progress_pct"],
         figures["final_score"], json.dumps(figures, sort_keys=True), signed_body,
         hashlib.sha256(signed_body.encode("utf-8")).hexdigest()),
    )
    return int(cur.lastrowid)
