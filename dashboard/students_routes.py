"""CRUD endpoints for the dashboard roster (table students).

Extracted from app.py to keep the main file under the 800-line limit
enforced by .claude/hooks/file_size_check.cjs (project rule).

Endpoints registered :
  GET    /api/students?cohort=<id>                 list roster + event counts
  POST   /api/students                              upsert display_name
  DELETE /api/students/<token>?cohort=<id>          clear row
  GET    /admin/students?cohort=<id>                HTML CRUD page (token-gated)
  GET    /api/students/pending?cohort=<id>          list pending join requests
  POST   /api/students/<token>/approve              flip status to validated
  POST   /api/students/<token>/reject               flip status to rejected

All endpoints reuse the teacher-token auth helpers from app.py via the
auth_check_json / auth_check_html callables passed to register_routes().
The approve/reject endpoints are bound to buttons in cohorts.html and
students.html — no orphan route policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from flask import Flask, Response, jsonify, render_template, request

from audit_log import log_event
from db import (
    delete_student,
    events_by_day,
    events_by_type,
    get_connection,
    list_pending_students,
    list_students,
    per_student_stats,
    set_student_decision,
    upsert_student_name,
)


AuthFn = Callable[[], "tuple[bool, Any]"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_cohort() -> str:
    import os
    return os.environ.get("DASHBOARD_DEFAULT_COHORT", "") or ""


def _decide(token: str, decision: str, auth_check_json: AuthFn) -> Response:
    """Shared body for approve/reject endpoints. decision must already be
    validated by the caller (only 'validated' or 'rejected' are reachable
    here through the wired routes)."""
    ok, err = auth_check_json()
    if not ok:
        return err  # type: ignore[return-value]
    if decision not in ("validated", "rejected"):
        return jsonify({"error": "invalid decision"}), 400  # type: ignore[return-value]
    if not request.is_json:
        return jsonify({"error": "expected application/json body"}), 400  # type: ignore[return-value]
    payload = request.get_json(silent=True) or {}
    cohort = (payload.get("cohort_id") or _default_cohort()).strip()
    token = (token or "").strip()
    decided_by = str(payload.get("decided_by") or "").strip()[:64]
    if not cohort or not token:
        return jsonify({"error": "cohort_id and student_token required"}), 400  # type: ignore[return-value]
    with get_connection() as conn:
        n = set_student_decision(conn, cohort, token, decision, decided_by, _now())
    if n == 0:
        return jsonify({"error": "student not found", "cohort_id": cohort, "student_token": token}), 404  # type: ignore[return-value]
    log_event("decision", cohort=cohort, student_prefix=token[:8], decision=decision, decided_by=decided_by)
    return jsonify({"ok": True, "cohort_id": cohort, "student_token": token, "status": decision})


def register_students_routes(
    app: Flask,
    auth_check_json: AuthFn,
    auth_check_html: AuthFn,
) -> None:
    """Mount the 4 routes on the Flask app. Called once from create_app()."""

    @app.get("/api/students")
    def list_students_api() -> Response:
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        cohort = (request.args.get("cohort") or _default_cohort()).strip()
        if not cohort:
            return jsonify({"error": "cohort required"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            rows = list_students(conn, cohort)
        students = [
            {
                "cohort_id": r["cohort_id"],
                "student_token": r["student_token"],
                "display_name": r["display_name"],
                "email": r["email"] if "email" in r.keys() else None,
                "status": r["status"] if "status" in r.keys() else "validated",
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "event_count": int(r["event_count"] or 0),
            }
            for r in rows
        ]
        return jsonify({"cohort_id": cohort, "students": students})

    @app.get("/api/students/stats")
    def students_stats_api() -> Response:
        """Per-student progression + cohort-level histograms.

        Wired to /admin/students for the prof-side progression view :
          per_student[]   {token, challenges_solved, hints_used, quizzes_done,
                           flags_verified, last_event_ts, progress_pct}
          events_by_type[]{event_type, n}
          events_by_day[] {day, n}  -- last 7 days

        progress_pct uses TD_TOTAL_CHALLENGES as denominator (default 13,
        matches frontend/src/assets/juicelab/selected_challenges.yml).
        """
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        cohort = (request.args.get("cohort") or _default_cohort()).strip()
        if not cohort:
            return jsonify({"error": "cohort required"}), 400  # type: ignore[return-value]
        td_total = max(1, int(request.args.get("td_total", "13")))
        with get_connection() as conn:
            per = per_student_stats(conn, cohort)
            by_type = events_by_type(conn, cohort)
            by_day = events_by_day(conn, cohort, days=7)
        students = [
            {
                "student_token": r["student_token"],
                "challenges_solved": int(r["challenges_solved"] or 0),
                "hints_used": int(r["hints_used"] or 0),
                "quizzes_done": int(r["quizzes_done"] or 0),
                "flags_verified": int(r["flags_verified"] or 0),
                "last_event_ts": r["last_event_ts"],
                "progress_pct": min(100, round(100 * (int(r["challenges_solved"] or 0)) / td_total)),
            }
            for r in per
        ]
        return jsonify({
            "cohort_id": cohort,
            "td_total": td_total,
            "students": students,
            "events_by_type": [{"event_type": r["event_type"], "n": int(r["n"])} for r in by_type],
            "events_by_day": [{"day": r["day"], "n": int(r["n"])} for r in by_day],
        })

    @app.get("/api/students/pending")
    def list_pending_students_api() -> Response:
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        cohort = (request.args.get("cohort") or _default_cohort()).strip()
        if not cohort:
            return jsonify({"error": "cohort required"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            rows = list_pending_students(conn, cohort)
        pending = [
            {
                "cohort_id": r["cohort_id"],
                "student_token": r["student_token"],
                "display_name": r["display_name"],
                "email": r["email"],
                "dashboard_url_used": r["dashboard_url_used"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
        return jsonify({"cohort_id": cohort, "pending": pending})

    @app.post("/api/students/<token>/approve")
    def approve_student_api(token: str) -> Response:
        return _decide(token, "validated", auth_check_json)

    @app.post("/api/students/<token>/reject")
    def reject_student_api(token: str) -> Response:
        return _decide(token, "rejected", auth_check_json)

    @app.post("/api/students")
    def upsert_student_api() -> Response:
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        if not request.is_json:
            return jsonify({"error": "expected application/json body"}), 400  # type: ignore[return-value]
        payload = request.get_json(silent=True) or {}
        token = (payload.get("student_token") or "").strip()
        cohort = (payload.get("cohort_id") or _default_cohort()).strip()
        name = payload.get("display_name")
        if name is not None:
            name = str(name).strip()
            if name == "":
                name = None
            elif len(name) > 100:
                return jsonify({"error": "display_name must be <= 100 chars"}), 400  # type: ignore[return-value]
        if not token:
            return jsonify({"error": "student_token required"}), 400  # type: ignore[return-value]
        if not cohort:
            return jsonify({"error": "cohort_id required"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            upsert_student_name(conn, cohort, token, name, _now())
        return jsonify({"ok": True, "cohort_id": cohort, "student_token": token, "display_name": name})

    @app.delete("/api/students/<token>")
    def delete_student_api(token: str) -> Response:
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        cohort = (request.args.get("cohort") or _default_cohort()).strip()
        token = (token or "").strip()
        if not cohort or not token:
            return jsonify({"error": "cohort and token required"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            n = delete_student(conn, cohort, token)
        return jsonify({"ok": True, "deleted": n})

    @app.get("/admin/students")
    def students_admin_page() -> Response:
        ok, err = auth_check_html()
        if not ok:
            return err  # type: ignore[return-value]
        cohort = (request.args.get("cohort") or _default_cohort()).strip()
        return render_template("students.html", cohort_id=cohort)  # type: ignore[return-value]
