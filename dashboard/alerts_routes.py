"""Alerts CRUD HTTP API (Phase 2 Task 3).

Exposes :
- GET  /api/alerts?cohort=<id>[&unack=true]
- POST /api/alerts/<id>/ack    (idempotent)

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

from db import ack_alert, get_connection, recent_alerts


def register_alerts_routes(app: Flask, check_teacher_auth: Callable) -> None:
    """Register the /api/alerts endpoints on the given Flask app."""

    @app.get("/api/alerts")
    def list_alerts() -> Response:
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        cohort = request.args.get("cohort", "").strip()
        if not cohort:
            return jsonify({"error": "missing cohort"}), 400  # type: ignore[return-value]
        unack_only = request.args.get("unack", "").strip().lower() in ("1", "true", "yes")
        with get_connection() as conn:
            rows = recent_alerts(conn, cohort, limit=500)
        result = []
        for r in rows:
            if unack_only and r["ack_at"] is not None:
                continue
            result.append({
                "id": r["id"],
                "cohort_id": r["cohort_id"],
                "student_token": r["student_token"],
                "kind": r["kind"],
                "challenge_key": r["challenge_key"],
                "created_at": r["created_at"],
                "ack_at": r["ack_at"],
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
