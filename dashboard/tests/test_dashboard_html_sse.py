"""Dashboard HTML body must use EventSource, not setInterval polling (Phase 1).

Note: this test reloads the `app` module from scratch to bind to the
test-controlled env vars. It is NOT safe under pytest-xdist parallel
workers (shared `sys.modules` state). The project runs tests serially;
if -n is ever added, refactor to a session-scoped fixture.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOKEN = "teacher-test-token-very-long-32chars!!"
AUTH = {"X-Teacher-Token": TOKEN}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    monkeypatch.setenv("DASHBOARD_SSE_HEARTBEAT_SEC", "0.5")
    for m in ("app", "db", "sse_pubsub", "sse_routes"):
        if m in sys.modules:
            del sys.modules[m]
    from app import create_app
    a = create_app()
    a.testing = True
    return a.test_client()


def test_dashboard_html_uses_eventsource_not_polling(client):
    # Cohort must exist before the HTML page can render the matrix.
    r = client.post(
        "/api/cohorts",
        json={"cohort_id": "M2-IA-2026", "label": "M2 IA 2026"},
        headers=AUTH,
    )
    assert r.status_code in (200, 201), r.data

    # /dashboard accepts X-Teacher-Token header (see _check_teacher_auth_html).
    r = client.get("/dashboard?cohort=M2-IA-2026", headers=AUTH)
    assert r.status_code == 200, r.data
    body = r.data.decode("utf-8")

    # NEW: EventSource live updates via /api/cohort/stream.
    assert "EventSource" in body, "expected EventSource client wiring in dashboard.html"
    assert "/api/cohort/stream" in body, "expected SSE stream URL in dashboard.html"

    # OLD: the setInterval polling loop must be gone.
    assert "setInterval(tick" not in body, (
        "legacy setInterval(tick, REFRESH_MS) polling must be removed"
    )
