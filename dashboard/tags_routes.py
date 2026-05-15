"""Teacher-only CRUD for per-student tags + free-form notes (Phase 1, Task 6).

Tags : enum {a_voir, ok, absent, a_interroger, none}.
Notes : free text body <= 2000 chars.
Both keyed by (cohort_id, student_token), matching the composite PK
column order from Task 1 and using the set_tag/get_tag/set_note/get_note
helpers from Task 2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from flask import Flask, Response, jsonify, request

from db import get_connection, get_note, get_tag, set_note, set_tag

ALLOWED_TAGS = {"a_voir", "ok", "absent", "a_interroger", "none"}
NOTE_MAX = 2000


def register_tags_routes(app: Flask, check_teacher_auth: Callable) -> None:
    """Wire /api/tag and /api/note endpoints onto the given Flask app."""

    @app.post("/api/tag")
    def set_student_tag() -> Response:
        """Upsert the triage status for a (cohort_id, student_token) pair."""
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err  # type: ignore[return-value]
        payload = request.get_json(silent=True) or {}
        token = str(payload.get("student_token", "")).strip()
        cohort = str(payload.get("cohort_id", "")).strip()
        status = str(payload.get("status", "")).strip()
        if not token or not cohort or status not in ALLOWED_TAGS:
            return jsonify({"error": "invalid tag payload"}), 400  # type: ignore[return-value]
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            set_tag(conn, token, cohort, status, now)
            conn.commit()
        return jsonify({"ok": True, "status": status}), 200  # type: ignore[return-value]

    @app.get("/api/tag")
    def get_student_tag() -> Response:
        """Return the current triage status, defaulting to "none" if unset."""
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err  # type: ignore[return-value]
        token = request.args.get("student_token", "").strip()
        cohort = request.args.get("cohort", "").strip()
        with get_connection() as conn:
            status = get_tag(conn, token, cohort) or "none"
        return jsonify({"status": status})

    @app.post("/api/note")
    def set_student_note() -> Response:
        """Upsert the free-form note body, clamped to NOTE_MAX chars."""
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err  # type: ignore[return-value]
        payload = request.get_json(silent=True) or {}
        token = str(payload.get("student_token", "")).strip()
        cohort = str(payload.get("cohort_id", "")).strip()
        body = str(payload.get("body", ""))[:NOTE_MAX]
        if not token or not cohort:
            return jsonify({"error": "invalid note payload"}), 400  # type: ignore[return-value]
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            set_note(conn, token, cohort, body, now)
            conn.commit()
        return jsonify({"ok": True})

    @app.get("/api/note")
    def get_student_note() -> Response:
        """Return the current note body, defaulting to "" if unset."""
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err  # type: ignore[return-value]
        token = request.args.get("student_token", "").strip()
        cohort = request.args.get("cohort", "").strip()
        with get_connection() as conn:
            body = get_note(conn, token, cohort)
        return jsonify({"body": body})
