"""Public endpoints for cohort join workflow (no teacher token required).

Students enter their cohort code + email in the JuiceLab overlay modal and
land here. The prof then approves or rejects them through the gated
endpoints in students_routes.py. The sync gate in app.py rejects events
from any student whose status is not 'validated'.

Endpoints registered :
  GET  /api/cohort/exists?cohort_id=<id>          public, cohort_id existence check
  POST /api/cohort/join                           public, create/refresh a pending request
  GET  /api/student/status?student_token=<t>&cohort=<c>
                                                  public, poll join workflow status

The endpoints are designed to be UI-driven only (cohort-join-dialog in the
overlay polls /api/student/status every minute). No route is orphan : each
maps to a visible UX surface on the Juice Shop side or the dashboard side.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, request

from db import (
    cohort_exists,
    create_join_request,
    get_connection,
    get_student_status,
)
from rate_limit import ip_key, rate_limit


_TOKEN_RE = re.compile(r"^[A-Za-z0-9._:\-]{8,128}$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_COHORT_RE = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")
_URL_RE = re.compile(r"^https?://[^\s]{1,256}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_join_routes(app: Flask) -> None:

    @app.get("/api/cohort/exists")
    @rate_limit(ip_key, max_calls=30, window_sec=60)
    def cohort_exists_api() -> Response:
        cid = (request.args.get("cohort_id") or "").strip()
        if not cid or not _COHORT_RE.match(cid):
            return jsonify({"exists": False, "error": "invalid cohort_id"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            present = cohort_exists(conn, cid)
        return jsonify({"cohort_id": cid, "exists": bool(present)})

    @app.post("/api/cohort/join")
    @rate_limit(ip_key, max_calls=10, window_sec=3600)
    def cohort_join_api() -> Response:
        if not request.is_json:
            return jsonify({"error": "expected application/json body"}), 400  # type: ignore[return-value]
        payload = request.get_json(silent=True) or {}
        cid = str(payload.get("cohort_id") or "").strip()
        token = str(payload.get("student_token") or "").strip()
        email = str(payload.get("email") or "").strip().lower()
        dashboard_url = str(payload.get("dashboard_url") or "").strip()

        if not cid or not _COHORT_RE.match(cid):
            return jsonify({"error": "invalid cohort_id"}), 400  # type: ignore[return-value]
        if not token or not _TOKEN_RE.match(token):
            return jsonify({"error": "invalid student_token (8-128 chars, [A-Za-z0-9._:-])"}), 400  # type: ignore[return-value]
        if not email or not _EMAIL_RE.match(email) or len(email) > 254:
            return jsonify({"error": "invalid email"}), 400  # type: ignore[return-value]
        if dashboard_url and not _URL_RE.match(dashboard_url):
            return jsonify({"error": "invalid dashboard_url"}), 400  # type: ignore[return-value]

        with get_connection() as conn:
            if not cohort_exists(conn, cid):
                # Force the prof to create the cohort first. We refuse to
                # silently create a cohort row from a public endpoint to
                # avoid letting students spam arbitrary cohort identifiers.
                return jsonify({"error": "unknown cohort_id, ask the teacher to create it first"}), 404  # type: ignore[return-value]
            status = create_join_request(conn, cid, token, email, dashboard_url, _now())
        return jsonify({
            "ok": True,
            "cohort_id": cid,
            "student_token": token,
            "status": status,
        }), 202  # type: ignore[return-value]

    @app.get("/api/student/status")
    @rate_limit(ip_key, max_calls=120, window_sec=60)
    def student_status_api() -> Response:
        token = (request.args.get("student_token") or "").strip()
        cohort = (request.args.get("cohort") or "").strip() or None
        if not token or not _TOKEN_RE.match(token):
            return jsonify({"error": "invalid student_token"}), 400  # type: ignore[return-value]
        if cohort and not _COHORT_RE.match(cohort):
            return jsonify({"error": "invalid cohort"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            result = get_student_status(conn, token, cohort)
        if result is None:
            return jsonify({"student_token": token, "status": "unknown"})
        status, found_cohort = result
        return jsonify({
            "student_token": token,
            "cohort_id": found_cohort,
            "status": status,
        })
