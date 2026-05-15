"""Server-Sent Events endpoint for the cohort matrix live stream.

Exposes /api/cohort/stream?cohort=<id> as text/event-stream. Each
subscriber receives :
  - one `retry: 5000` directive (EventSource native reconnect backoff)
  - one `event: snapshot` with the initial cohort state on connect
  - `event: event` after every /api/sync insert that publish()es
  - `: heartbeat` every HEARTBEAT_SEC seconds when idle

Single-process design (matches sse_pubsub). For multi-worker
deployments, replace the in-memory hub with Redis pub/sub.

`X-Accel-Buffering: no` disables nginx response buffering on the
proxy path; required for SSE to deliver chunks promptly.
"""

from __future__ import annotations

import json
import os
from queue import Empty
from typing import Callable, Optional

from flask import Flask, Response, request, stream_with_context

import sse_pubsub

DEFAULT_HEARTBEAT_SEC = 15


def _heartbeat_sec() -> float:
    """Read DASHBOARD_SSE_HEARTBEAT_SEC env var (float seconds), default 15.

    Test suites set this to 0.5 so the q.get timeout fires fast on stream end.
    """
    raw = os.environ.get("DASHBOARD_SSE_HEARTBEAT_SEC", "").strip()
    if not raw:
        return DEFAULT_HEARTBEAT_SEC
    try:
        v = float(raw)
        return v if v > 0 else DEFAULT_HEARTBEAT_SEC
    except ValueError:
        return DEFAULT_HEARTBEAT_SEC


def register_sse_routes(
    app: Flask,
    check_teacher_auth: Callable[[], tuple[bool, Optional[Response]]],
    build_summary: Optional[Callable[[str], dict]] = None,
) -> None:
    """Register /api/cohort/stream on the given Flask app."""

    @app.get("/api/cohort/stream")
    def stream_cohort() -> Response:
        """Stream cohort events as SSE; teacher-auth gated."""
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err  # type: ignore[return-value]
        cohort = request.args.get("cohort", "").strip()
        if not cohort:
            return Response("missing cohort", status=400)

        def gen():
            """Yield SSE-framed chunks for this subscriber lifecycle."""
            q = sse_pubsub.subscribe(cohort)
            try:
                yield "retry: 5000\n\n"
                if build_summary is not None:
                    try:
                        snap = build_summary(cohort)
                        yield f"event: snapshot\ndata: {json.dumps(snap)}\n\n"
                    except Exception:
                        yield "event: snapshot\ndata: {}\n\n"
                else:
                    yield "event: snapshot\ndata: {}\n\n"
                while True:
                    try:
                        ev = q.get(timeout=_heartbeat_sec())
                        # Discriminate payload by `kind` to emit typed SSE
                        # event names (event: alert, event: notification...).
                        # Plain Phase 1 sync broadcasts have no `kind` and
                        # keep getting the default `event: event` frame.
                        if isinstance(ev, dict) and "kind" in ev:
                            ev_name = ev["kind"]
                            payload = {k: v for k, v in ev.items() if k != "kind"}
                        else:
                            ev_name = "event"
                            payload = ev
                        yield f"event: {ev_name}\ndata: {json.dumps(payload)}\n\n"
                    except Empty:
                        yield ": heartbeat\n\n"
            finally:
                sse_pubsub.unsubscribe(cohort, q)

        headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        return Response(
            stream_with_context(gen()),
            mimetype="text/event-stream",
            headers=headers,
        )
