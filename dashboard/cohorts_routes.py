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

    @app.get("/api/cohort/export.csv")
    def export_cohort_csv() -> Response:
        """CSV export of the cohort roster + aggregated stats for the
        teacher to drop into Excel / a report. UTF-8 BOM prefix so
        Excel auto-detects the encoding instead of mangling accents.
        """
        from io import StringIO
        import csv
        from db import per_student_stats, list_students
        ok, err = auth_check_json()
        if not ok:
            return err  # type: ignore[return-value]
        cohort = (request.args.get("cohort") or "").strip()
        if not cohort:
            return jsonify({"error": "cohort required"}), 400  # type: ignore[return-value]
        with get_connection() as conn:
            students = list_students(conn, cohort)
            stats = {r["student_token"]: r for r in per_student_stats(conn, cohort)}
        buf = StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow([
            "student_token", "display_name", "email", "status",
            "challenges_solved", "hints_used", "hint_penalty_pct",
            "score_challenge", "quizzes_done", "quiz_avg_score",
            "flags_verified", "journals_written", "journal_word_total",
            "last_event_ts", "created_at", "decided_by",
        ])
        for s in students:
            st = stats.get(s["student_token"])
            cs = int(st["challenges_solved"] or 0) if st else 0
            hp = int(st["hint_penalty_sum"] or 0) if st else 0
            qavg = st["quiz_avg_score"] if st else None
            w.writerow([
                s["student_token"], s["display_name"] or "",
                (s["email"] if "email" in s.keys() else "") or "",
                (s["status"] if "status" in s.keys() else "validated") or "",
                cs, int(st["hints_used"] or 0) if st else 0, hp,
                max(0, 100 - hp), int(st["quizzes_done"] or 0) if st else 0,
                int(round(qavg)) if qavg is not None else "",
                int(st["flags_verified"] or 0) if st else 0,
                int(st["journals_written"] or 0) if st else 0,
                int(st["journal_word_total"] or 0) if st else 0,
                (st["last_event_ts"] if st else "") or "",
                s["created_at"] or "",
                (s["decided_by"] if "decided_by" in s.keys() else "") or "",
            ])
        body = "\ufeff" + buf.getvalue()  # UTF-8 BOM for Excel
        filename = f"cohort_{cohort}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
        return Response(
            body, content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
