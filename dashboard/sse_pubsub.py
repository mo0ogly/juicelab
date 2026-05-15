"""In-memory pub/sub hub for SSE broadcasts (cohort-scoped).

Phase 1: simple thread-safe fanout. Each subscriber gets its own
bounded queue; slow consumers drop oldest events instead of blocking
producers. Cohort-keyed so cross-cohort isolation is preserved.

Single-process design. If the dashboard ever runs multi-worker
(gunicorn -w N), this hub must be replaced by Redis pub/sub since
in-memory state is per-process."""

from __future__ import annotations

from collections import defaultdict
from queue import Queue, Full
from threading import RLock
from typing import Any, Dict, List

_LOCK = RLock()
_SUBSCRIBERS: Dict[str, List[Queue]] = defaultdict(list)


def subscribe(cohort_id: str, maxsize: int = 100) -> Queue:
    """Register a new bounded queue subscriber for the given cohort."""
    q: Queue = Queue(maxsize=maxsize)
    with _LOCK:
        _SUBSCRIBERS[cohort_id].append(q)
    return q


def unsubscribe(cohort_id: str, q: Queue) -> None:
    """Remove a subscriber queue; silently no-op if already unsubscribed."""
    with _LOCK:
        try:
            _SUBSCRIBERS[cohort_id].remove(q)
        except ValueError:
            pass


def publish(cohort_id: str, event: dict[str, Any]) -> int:
    """Fan event out to all cohort subscribers; drop oldest on Full, return delivered count."""
    delivered = 0
    with _LOCK:
        subs = list(_SUBSCRIBERS.get(cohort_id, ()))
    for q in subs:
        try:
            q.put_nowait(event)
            delivered += 1
        except Full:
            try:
                q.get_nowait()
                q.put_nowait(event)
                delivered += 1
            except Exception:
                pass
    return delivered


def subscriber_count(cohort_id: str) -> int:
    """Return current number of active subscribers for the cohort."""
    with _LOCK:
        return len(_SUBSCRIBERS.get(cohort_id, ()))
