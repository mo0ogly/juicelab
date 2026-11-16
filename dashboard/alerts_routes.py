"""Alerts CRUD HTTP API (Phase 2 Task 3).

Exposes :
- GET  /api/alerts?cohort=<id>[&unack=true][&group=true]
      without group=true: latest alerts, each carrying `ack_at` and
      `resolved_at`; `unack=true` keeps only ACTIVE alerts (not acked AND
      not auto-resolved).
      group=true returns unacked alerts only, one entry per (student,
      kind, challenge) with `count` and `first_at`; `id` is the latest.
- POST /api/alerts/<id>/ack    (idempotent)
- POST /api/alerts/<id>/ack-group  (idempotent, acks every identical alert)

Both routes are teacher-auth gated through the shared
`check_teacher_auth` callback registered by app.create_app(). The
header-based auth path (X-Teacher-Token) is CSRF-exempt by design
(see dashboard/csrf.py), so automated recettes and CLI tools can
ack without juggling cookies.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from flask import Flask, Response, jsonify, request

from db import (
    ack_alert, ack_alert_group, get_connection, recent_alerts,
    student_display_names, unacked_alert_groups,
)


def register_alerts_routes(app: Flask, check_teacher_auth: Callable) -> None:
    """Register the /api/alerts endpoints on the given Flask app."""

    @app.get("/api/alerts")
    def list_alerts() -> Response:
        """List the alerts of one cohort for the teacher panel.

        Query params: `cohort` (required), `unack=true` to keep only ACTIVE
        alerts (ack_at IS NULL AND resolved_at IS NULL), `group=true` for
        the per (student, kind, challenge) grouped view. Every non-grouped
        entry carries `ack_at` and `resolved_at` (None while the alert is
        open); resolved alerts stay visible in the full listing.
        """
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        cohort = request.args.get("cohort", "").strip()
        if not cohort:
            return jsonify({"error": "missing cohort"}), 400  # type: ignore[return-value]
        unack_only = request.args.get("unack", "").strip().lower() in ("1", "true", "yes")
        if request.args.get("group", "").strip().lower() in ("1", "true", "yes"):
            with get_connection() as conn:
                groups = unacked_alert_groups(conn, cohort)
                names = student_display_names(conn, cohort)
            return jsonify({"alerts": [{
                "id": g["id"],
                "cohort_id": cohort,
                "student_token": g["student_token"],
                "display_name": names.get(g["student_token"]),
                "kind": g["kind"],
                "challenge_key": g["challenge_key"],
                "count": g["n"],
                "first_at": g["first_at"],
                "created_at": g["last_at"],
                "ack_at": None,
            } for g in groups]})
        with get_connection() as conn:
            rows = recent_alerts(conn, cohort, limit=500)
            names = student_display_names(conn, cohort)
        result = []
        for r in rows:
            if unack_only and (r["ack_at"] is not None or r["resolved_at"] is not None):
                continue
            result.append({
                "id": r["id"],
                "cohort_id": r["cohort_id"],
                "student_token": r["student_token"],
                # None when the student has no roster name: the panel then
                # falls back to a token prefix.
                "display_name": names.get(r["student_token"]),
                "kind": r["kind"],
                "challenge_key": r["challenge_key"],
                "created_at": r["created_at"],
                "ack_at": r["ack_at"],
                "resolved_at": r["resolved_at"],
            })
        return jsonify({"alerts": result})

    @app.post("/api/alerts/<int:alert_id>/ack")
    def ack(alert_id: int) -> Response:
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            changed = ack_alert(conn, alert_id, now)
            conn.commit()
        if changed == 0:
            # Either already acked or no such row — return 200 idempotent.
            return jsonify({"ok": True, "noop": True})
        return jsonify({"ok": True, "ack_at": now})

    @app.post("/api/alerts/<int:alert_id>/ack-group")
    def ack_group(alert_id: int) -> Response:
        """Acknowledge alert `alert_id` and every unacked alert with the same
        cohort, student, kind and challenge. Lets the panel clear a grouped
        row in one request. 404 when the id is unknown; `acked` is 0 when the
        group was already acknowledged (idempotent)."""
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            acked = ack_alert_group(conn, alert_id, now)
            conn.commit()
        if acked is None:
            return jsonify({"error": "alert not found"}), 404  # type: ignore[return-value]
        return jsonify({"ok": True, "acked": acked, "ack_at": now})
