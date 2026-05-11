"""In-process rate limiter for Flask public endpoints.

Sliding-window token bucket per remote address. Holds state in process
memory ; resets on dashboard restart. Adequate for single-process
deployments (the M2 lab default). For multi-worker / multi-replica
setups, replace with Flask-Limiter backed by Redis.

Usage :

    from rate_limit import rate_limit, ip_key

    @app.post("/api/cohort/join")
    @rate_limit(ip_key, max_calls=10, window_sec=3600)
    def cohort_join_api(): ...

A 429 JSON response is returned automatically when the bucket is full.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable, Deque

from flask import jsonify, request

_buckets: defaultdict[str, Deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def ip_key() -> str:
    """Default key function : client IP (X-Forwarded-For aware).

    Reads the leftmost entry of X-Forwarded-For when behind a reverse
    proxy, otherwise falls back to request.remote_addr. Strip any
    surrounding whitespace and limit length so a malicious header
    cannot blow the dict.
    """
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        candidate = fwd.split(",")[0].strip()
        if candidate and len(candidate) <= 64:
            return candidate
    return (request.remote_addr or "?")[:64]


def rate_limit(
    key_fn: Callable[[], str],
    max_calls: int,
    window_sec: int,
) -> Callable:
    """Decorator factory : key_fn() -> bucket id, max_calls / window_sec.

    Returns 429 with a JSON body when the bucket overflows.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):
            key = f"{fn.__module__}.{fn.__name__}:{key_fn()}"
            now = time.monotonic()
            with _lock:
                bucket = _buckets[key]
                cutoff = now - window_sec
                while bucket and bucket[0] < cutoff:
                    bucket.popleft()
                if len(bucket) >= max_calls:
                    return jsonify({
                        "error": "rate limit exceeded",
                        "retry_after_sec": int(window_sec - (now - bucket[0])),
                    }), 429
                bucket.append(now)
            return fn(*args, **kwargs)
        return wrapper

    return decorator
