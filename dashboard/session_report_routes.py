"""GET /admin/session-report : printable end-of-session report (teacher).

Query : ``cohort`` (required) and ``session`` (1-based index, default the
latest session). Content built by session_report.build_session_report.
"""
from __future__ import annotations

from typing import Callable

from flask import Flask, Response, render_template, request

from db import get_connection
from session_report import build_session_report


def register_session_report_routes(app: Flask, auth_check_html: Callable) -> None:
    """Register the report page. ``auth_check_html`` returns (ok, response)."""

    @app.get("/admin/session-report")
    def session_report_page() -> Response:
        """Render the report ; 400 without cohort or with a non-numeric
        session, 404-free empty state when the cohort has no activity or the
        index is out of range (the page says so and lists sessions)."""
        ok, err = auth_check_html()
        if not ok:
            return err  # type: ignore[return-value]
        cohort = (request.args.get("cohort") or "").strip()
        if not cohort:
            return Response("missing cohort", status=400)
        raw = (request.args.get("session") or "").strip()
        if raw and not raw.isdigit():
            return Response("session must be a positive integer", status=400)
        with get_connection() as conn:
            report = build_session_report(conn, cohort, int(raw) if raw else None)
        return render_template("session_report.html", cohort_id=cohort, report=report)  # type: ignore[return-value]
