"""CRUD endpoints for cohorts (table cohorts).

Endpoints registered :
  GET    /api/cohorts                       list with counts
  POST   /api/cohorts                       create/rename (upsert label)
  POST   /api/cohorts/<cid>/reset           wipe events + students (row stays)
  DELETE /api/cohorts/<cid>                 drop cohort row + cascade events + students
  GET    /admin/cohorts                     HTML admin page (token-gated)

All endpoints are token-gated via auth_check_json / auth_check_html passed
by the app factory. The HTML page is the UX surface bound to the JSON
endpoints — no orphan route policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from flask import Flask, Response, jsonify, render_template, request

from db import (
    delete_cohort as db_delete_cohort,
    get_connection,
    list_cohorts,
    reset_cohort as db_reset_cohort,
    upsert_cohort,
)


AuthFn = Callable[[], "tuple[bool, Any]"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_id(raw: str) -> str:
    """Cohort IDs are short identifiers reused in URL paths so we keep them
    URL-safe and short. Allow only alnum, dash, underscore, dot."""
    s = (raw or "").strip()
    if not s or len(s) > 64:
        return ""
    for ch in s:
        if not (ch.isalnum() or ch in "-_."):
            return ""
    return s


def register_cohorts_routes(
    app: Flask,
    auth_check_json: AuthFn,
    auth_check_html: AuthFn,
) -> None:

    @app.get("/admin/cohorts")
    def cohorts_admin_page() -> Response:
        ok, err = auth_check_html()
        if not ok:
            return err  # type: ignore[return-value]
        return render_template("cohorts.html")  # type: ignore[return-value]

    @app.get("/api/cohorts")
    def list_cohorts_api() -> Response:
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        with get_connection() as conn:
            rows = list_cohorts(conn)
        return jsonify({
            "cohorts": [
                {
                    "cohort_id": r["cohort_id"],
                    "label": r["label"],
                    "created_at": r["created_at"],
                    "event_count": int(r["event_count"] or 0),
                    "student_count": int(r["student_count"] or 0),
                }
                for r in rows
            ]
        })

    @app.post("/api/cohorts")
    def upsert_cohort_api() -> Response:
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        if not request.is_json:
            return jsonify({"error": "expected application/json body"}), 400  # type: ignore[return-value]
        payload = request.get_json(silent=True) or {}
        cid = _clean_id(payload.get("cohort_id") or "")
        if not cid:
            return jsonify({"error": "cohort_id required, alnum + - _ . only, <= 64 chars"}), 400  # type: ignore[return-value]
        label = payload.get("label")
        if label is not None:
            label = str(label).strip()
            if label == "":
                label = None
            elif len(label) > 100:
                return jsonify({"error": "label must be <= 100 chars"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            upsert_cohort(conn, cid, label, _now())
        return jsonify({"ok": True, "cohort_id": cid, "label": label})

    @app.post("/api/cohorts/<cid>/reset")
    def reset_cohort_api(cid: str) -> Response:
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        cid = _clean_id(cid)
        if not cid:
            return jsonify({"error": "invalid cohort_id"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            counts = db_reset_cohort(conn, cid)
        return jsonify({"ok": True, "cohort_id": cid, **counts})

    @app.delete("/api/cohorts/<cid>")
    def delete_cohort_api(cid: str) -> Response:
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        cid = _clean_id(cid)
        if not cid:
            return jsonify({"error": "invalid cohort_id"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            counts = db_delete_cohort(conn, cid)
        return jsonify({"ok": True, "cohort_id": cid, **counts})
