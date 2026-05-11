"""Structured audit log for security-relevant events.

Writes one JSON line per event to the file pointed at by
``DASHBOARD_AUDIT_LOG`` (defaults to ``./data/audit.jsonl`` so it
survives container restarts in the standard deployment). Each event
carries a timestamp, an event type, the requesting IP (X-Forwarded-For
aware), and any additional context fields the caller passes in.

The audit trail is append-only and meant for forensic / compliance
review. It is intentionally separate from the application logs so an
operator can ship it to a SIEM (Splunk / Wazuh / Loki) without piping
verbose Flask noise.

Event types emitted by the dashboard :
  login_success   teacher successfully authenticated via /login
  login_fail      bad teacher token on /login
  csrf_fail       cookie-authenticated request without matching CSRF token
  sync_blocked    /api/sync rejected because the student is pending/rejected
  join_request    new POST /api/cohort/join landed
  decision        teacher approved or rejected a student

Adding a new event type is free : just call ``log_event("name", ...)``.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import has_request_context, request

LOGGER = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).parent / "data" / "audit.jsonl"


def _audit_path() -> Path:
    raw = os.environ.get("DASHBOARD_AUDIT_LOG", str(DEFAULT_PATH))
    return Path(raw).expanduser()


def _client_ip() -> str:
    if not has_request_context():
        return ""
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        candidate = fwd.split(",")[0].strip()
        if candidate and len(candidate) <= 64:
            return candidate
    return (request.remote_addr or "")[:64]


def log_event(event_type: str, **fields: Any) -> None:
    """Append one JSONL line. Failure is logged but never raised — the
    audit log is a best-effort sink and must not crash the request."""
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "ip": _client_ip(),
    }
    if has_request_context():
        record["method"] = request.method
        record["path"] = request.path
    record.update(fields)
    try:
        path = _audit_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError as exc:
        LOGGER.warning("audit log write failed (event=%s): %s", event_type, exc)
