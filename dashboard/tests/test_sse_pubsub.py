"""SSE pub/sub primitive tests (Phase 1)."""
# Note: this test uses module-level reload (importlib.reload(sse_pubsub)) which
# is NOT safe under pytest-xdist parallel workers. The project runs tests
# serially; if -n is ever added, refactor to a fixture-scope='session'
# pattern or a process-local module that does not require reload.
from __future__ import annotations
import pytest, sys, importlib


@pytest.fixture
def hub(monkeypatch):
    if "sse_pubsub" in sys.modules: del sys.modules["sse_pubsub"]
    import sse_pubsub
    importlib.reload(sse_pubsub)
    return sse_pubsub


def test_publish_then_receive(hub):
    q = hub.subscribe("M2-IA-2026")
    try:
        hub.publish("M2-IA-2026", {"event_type": "solved", "challenge_key": "xss"})
        ev = q.get(timeout=1.0)
        assert ev["event_type"] == "solved"
    finally:
        hub.unsubscribe("M2-IA-2026", q)


def test_publish_to_other_cohort_not_delivered(hub):
    q = hub.subscribe("M2-IA-2026")
    try:
        hub.publish("M2-DIFFERENT", {"event_type": "solved"})
        with pytest.raises(Exception):
            q.get(timeout=0.2)
    finally:
        hub.unsubscribe("M2-IA-2026", q)
