"""Phase 2 Task 5 : typed SSE notification events.

Not safe under pytest-xdist parallel — module reload pattern.
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
    monkeypatch.setenv("DASHBOARD_MONITOR_ENABLED", "0")
    for m in ["app", "db", "sse_pubsub", "sync_routes"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    return create_app()


def _post_event(client, event_type, challenge_key="xss"):
    return client.post("/api/sync", json={
        "cohort_id": "demo",
        "student_token": "tok-notif",
        "event_type": event_type,
        "challenge_key": challenge_key,
        "client_ts": "2026-05-16T10:00:00Z",
        "data": {},
    })


def test_flag_verified_triggers_notification(app):
    import sse_pubsub
    q = sse_pubsub.subscribe("demo")
    try:
        client = app.test_client()
        r = _post_event(client, "flag_verified")
        assert r.status_code == 201
        # First event is the plain `event` payload (no kind), then the notification.
        seen_kinds = []
        for _ in range(2):
            try:
                ev = q.get(timeout=1.0)
                seen_kinds.append(ev.get("kind") or "event")
                if ev.get("kind") == "notification":
                    assert ev.get("subtype") == "flag"
                    return  # success
            except Exception:
                break
        pytest.fail(f"notification event never delivered, saw {seen_kinds}")
    finally:
        sse_pubsub.unsubscribe("demo", q)


def test_quiz_completed_triggers_notification(app):
    import sse_pubsub
    q = sse_pubsub.subscribe("demo")
    try:
        client = app.test_client()
        r = _post_event(client, "quiz_completed")
        assert r.status_code == 201
        for _ in range(2):
            try:
                ev = q.get(timeout=1.0)
                if ev.get("kind") == "notification":
                    assert ev.get("subtype") == "quiz"
                    return
            except Exception:
                break
        pytest.fail("quiz notification not delivered")
    finally:
        sse_pubsub.unsubscribe("demo", q)


def test_journal_filled_triggers_notification(app):
    import sse_pubsub
    q = sse_pubsub.subscribe("demo")
    try:
        client = app.test_client()
        r = _post_event(client, "journal_filled")
        assert r.status_code == 201
        for _ in range(2):
            try:
                ev = q.get(timeout=1.0)
                if ev.get("kind") == "notification":
                    assert ev.get("subtype") == "journal"
                    return
            except Exception:
                break
        pytest.fail("journal notification not delivered")
    finally:
        sse_pubsub.unsubscribe("demo", q)
