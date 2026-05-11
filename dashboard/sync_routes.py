"""Public POST /api/sync endpoint with student status gate.

Extracted from app.py to keep the main file under the 800-line limit
enforced by .claude/hooks/file_size_check.cjs (project rule). The handler
preserves the legacy behaviour : events are validated, inserted, and
logged. The gate added here rejects events from students whose join
request is still 'pending' or was 'rejected' (status workflow introduced
by /api/cohort/join).

Legacy classrooms keep working : ensure_student() in db.py auto-creates
unknown (cohort, token) pairs as 'validated' so events arriving without
a prior /api/cohort/join are accepted on first sight. Only rows that the
prof actively moved to 'pending' or 'rejected' are blocked.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from flask import Flask, Response, jsonify, request

from db import get_connection, get_student_status

LOGGER = logging.getLogger(__name__)


ValidateFn = Callable[[dict[str, Any]], "tuple[bool, str]"]
InsertFn = Callable[[dict[str, Any], "str | None"], int]


def register_sync_routes(
    app: Flask,
    validate_event: ValidateFn,
    insert_event: InsertFn,
) -> None:

    @app.post("/api/sync")
    def sync_event() -> Response:
        if not request.is_json:
            return jsonify({"error": "expected application/json body"}), 400  # type: ignore[return-value]
        payload = request.get_json(silent=True) or {}
        ok, msg = validate_event(payload)
        if not ok:
            return jsonify({"error": msg}), 400  # type: ignore[return-value]

        cohort = str(payload["cohort_id"]).strip()
        token = str(payload["student_token"]).strip()
        with get_connection() as conn:
            status_row = get_student_status(conn, token, cohort)
        if status_row is not None and status_row[0] not in ("validated",):
            LOGGER.info(
                "sync gate: blocked event from student=%s cohort=%s status=%s",
                token[:8] + "...", cohort, status_row[0],
            )
            return jsonify({
                "error": "join not approved",
                "status": status_row[0],
                "cohort_id": cohort,
            }), 403  # type: ignore[return-value]

        instance_label = request.headers.get("X-Instance-Label") or None
        new_id = insert_event(payload, instance_label)
        LOGGER.info(
            "ingested event id=%s student=%s cohort=%s type=%s challenge=%s",
            new_id,
            token[:8] + "...",
            cohort,
            payload["event_type"],
            payload.get("challenge_key") or "-",
        )
        return jsonify({"ok": True, "id": new_id}), 201  # type: ignore[return-value]
