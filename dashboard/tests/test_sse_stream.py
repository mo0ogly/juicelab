"""SSE /api/cohort/stream endpoint tests (Phase 1)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TOKEN = "teacher-test-token-very-long-32chars!!"
AUTH = {"X-Teacher-Token": TOKEN}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", TOKEN)
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_CORS_ORIGINS", "http://127.0.0.1:3000")
    monkeypatch.setenv("DASHBOARD_SSE_HEARTBEAT_SEC", "0.5")
    for m in ["app", "db", "sse_pubsub", "sse_routes"]:
        if m in sys.modules:
            del sys.modules[m]
    from app import create_app
    a = create_app()
    a.testing = True
    return a


def test_stream_requires_teacher_auth(app):
    client = app.test_client()
    r = client.get("/api/cohort/stream?cohort=M2-IA-2026")
    # No auth headers / cookies -> teacher auth must reject.
    assert r.status_code in (401, 403)


def test_stream_emits_initial_chunk(app):
    client = app.test_client()
    # Use header-based auth (existing project pattern for API clients).
    with client.get(
        "/api/cohort/stream?cohort=M2-IA-2026",
        headers=AUTH,
        buffered=False,
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("Content-Type", "")
        # Drain the first ~256 bytes (snapshot + retry directive). The
        # werkzeug test client streams chunk-by-chunk; stop as soon as
        # we have enough bytes to assert the SSE framing.
        chunks: list[bytes] = []
        total = 0
        for chunk in r.iter_encoded():
            chunks.append(chunk)
            total += len(chunk)
            if total > 200:
                break
        payload = b"".join(chunks)
        assert b"retry:" in payload or b"event:" in payload or b"data:" in payload
