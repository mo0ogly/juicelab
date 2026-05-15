"""Phase 3 — cohort PDF report via weasyprint (optional dep).

Returns 503 if weasyprint is not installed (it requires native libs
like pango/cairo and is not in requirements.lock.txt; teachers can
opt-in via pip install weasyprint). The 503 keeps the route discoverable
without making the whole dashboard fail to boot."""

from __future__ import annotations

from typing import Callable

from flask import Flask, Response, render_template, request

try:
    from weasyprint import HTML
    WEASYPRINT_OK = True
except (ImportError, OSError):
    HTML = None
    WEASYPRINT_OK = False


def register_pdf_routes(
    app: Flask,
    check_teacher_auth: Callable,
    build_summary: Callable,
) -> None:

    @app.get("/admin/cohort/report.pdf")
    def cohort_report_pdf() -> Response:
        """Render the cohort summary as A4 PDF. Requires weasyprint."""
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        cohort = request.args.get("cohort", "").strip()
        if not cohort:
            return Response("missing cohort", status=400)
        if not WEASYPRINT_OK:
            return Response("weasyprint not installed", status=503,
                            headers={"Content-Type": "text/plain"})
        summary = build_summary(cohort)
        html_str = render_template("cohort_report.html", summary=summary, cohort_id=cohort)
        pdf_bytes = HTML(string=html_str).write_pdf()
        return Response(pdf_bytes, mimetype="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="cohort_{cohort}_report.pdf"',
            "Cache-Control": "no-store",
        })
