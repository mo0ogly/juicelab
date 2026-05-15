"""sync POST event triggers sse_pubsub.publish (Phase 1).

Note: this test uses module-level reload (importlib.reload) which is
NOT safe under pytest-xdist parallel workers. The project runs tests
serially; if -n is ever added, refactor to a fixture-scope='session'
pattern.
"""
from __future__ import annotations
import sys, pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", "teacher-test-token-very-long-32chars!!")
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    monkeypatch.setenv("DASHBOARD_SSE_HEARTBEAT_SEC", "0.5")
    for m in ["app", "db", "sse_pubsub", "sse_routes", "sync_routes"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    return create_app()


def test_sync_publishes_to_pubsub(app):
    import sse_pubsub
    client = app.test_client()
    q = sse_pubsub.subscribe("M2-IA-2026")
    try:
        r = client.post("/api/sync", json={
            "cohort_id": "M2-IA-2026",
            "student_token": "tok123",
            "event_type": "challenge_solved",
            "challenge_key": "xss-stored",
            "client_ts": "2026-05-15T10:00:00Z",
            "data": {},
        })
        assert r.status_code == 201
        ev = q.get(timeout=1.0)
        assert ev["event_type"] == "challenge_solved"
        assert ev["student_token"] == "tok123"
    finally:
        sse_pubsub.unsubscribe("M2-IA-2026", q)
