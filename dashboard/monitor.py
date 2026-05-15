"""Phase 2 signal-to-noise heuristics.

Reads events table to compute live alerts per cohort. Pure functions
(no scheduling, no broadcast) - caller does the tick + insert + SSE.
Threshold env vars : DASHBOARD_MONITOR_BLOCKED_MIN, _STUCK_HINTS,
_SCRIPTING_EVENTS, _SCRIPTING_WINDOW_MIN, _IDLE_MIN."""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)
_MONITOR_THREAD: threading.Thread | None = None
_STOP_FLAG: threading.Event | None = None

_CONFIG_CACHE: dict | None = None
_CONFIG_PATH_CACHE: str | None = None


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _load_config_json() -> dict:
    """Load the optional dashboard-config.json file. Result cached by path
    so re-reading on every tick is cheap. Returns {} on missing or invalid file."""
    global _CONFIG_CACHE, _CONFIG_PATH_CACHE
    path = os.environ.get("DASHBOARD_CONFIG_JSON", "").strip()
    if not path:
        # Default path : <module_dir>/data/dashboard-config.json
        path = str(Path(__file__).parent / "data" / "dashboard-config.json")
    if _CONFIG_PATH_CACHE == path and _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CONFIG_CACHE = data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _CONFIG_CACHE = {}
    _CONFIG_PATH_CACHE = path
    return _CONFIG_CACHE


def _config_override(key: str) -> int | None:
    """Return monitor.<key> from JSON config, or None if absent."""
    data = _load_config_json()
    mon = data.get("monitor", {}) if isinstance(data, dict) else {}
    val = mon.get(key)
    if isinstance(val, (int, float)) and val > 0:
        return int(val)
    return None


def _seuils() -> dict[str, int]:
    """Compute thresholds : JSON config > env var > default."""
    return {
        "blocked_min":      _config_override("blocked_min")          or _env_int("DASHBOARD_MONITOR_BLOCKED_MIN", 10),
        "stuck_hints":      _config_override("stuck_hints")          or _env_int("DASHBOARD_MONITOR_STUCK_HINTS", 5),
        "scripting_events": _config_override("scripting_events")     or _env_int("DASHBOARD_MONITOR_SCRIPTING_EVENTS", 30),
        "scripting_window": _config_override("scripting_window_min") or _env_int("DASHBOARD_MONITOR_SCRIPTING_WINDOW_MIN", 2),
        "idle_min":         _config_override("idle_min")             or _env_int("DASHBOARD_MONITOR_IDLE_MIN", 15),
    }


def _config_reset_cache() -> None:
    """Test helper to clear the config cache between tests."""
    global _CONFIG_CACHE, _CONFIG_PATH_CACHE
    _CONFIG_CACHE = None
    _CONFIG_PATH_CACHE = None


def compute_alerts(db_mod, cohort_id: str, now: datetime | None = None) -> list[dict[str, Any]]:
    """Scan events table for the given cohort, return one dict per detected alert.

    Returned dicts have shape {cohort_id, student_token, kind, challenge_key, created_at}.
    The caller is responsible for de-duplicating (one alert per (token, kind, key) pair)
    and persisting via db_mod.insert_alert(...).
    """
    now = now or datetime.now(timezone.utc)
    s = _seuils()
    out: list[dict[str, Any]] = []
    with db_mod.get_connection() as conn:
        rows = conn.execute(
            "SELECT student_token, event_type, challenge_key, client_ts FROM events "
            "WHERE cohort_id=? ORDER BY id ASC",
            (cohort_id,),
        ).fetchall()

    by_student: dict[str, list[tuple[str, str | None, datetime]]] = defaultdict(list)
    for r in rows:
        try:
            ts = datetime.fromisoformat(r[3])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        by_student[r[0]].append((r[1], r[2], ts))

    for token, events in by_student.items():
        last_event = events[-1][2] if events else None
        last_challenge = next((k for _, k, _ in reversed(events) if k), None)

        # blocked : 0 events for blocked_min on last touched challenge
        if last_event and last_challenge:
            recent_on_challenge = [e for e in events if e[1] == last_challenge and e[2] > now - timedelta(minutes=s["blocked_min"])]
            solved = any(e[0] == "challenge_solved" and e[1] == last_challenge for e in events)
            if not solved and not recent_on_challenge:
                out.append({"cohort_id": cohort_id, "student_token": token, "kind": "blocked",
                            "challenge_key": last_challenge, "created_at": now.isoformat()})

        # stuck : >= stuck_hints hint_revealed on a challenge, not solved
        hints_per_key: dict[str, int] = defaultdict(int)
        solved_keys: set[str] = set()
        for et, key, _ in events:
            if et == "hint_revealed" and key:
                hints_per_key[key] += 1
            if et == "challenge_solved" and key:
                solved_keys.add(key)
        for key, count in hints_per_key.items():
            if count >= s["stuck_hints"] and key not in solved_keys:
                out.append({"cohort_id": cohort_id, "student_token": token, "kind": "stuck",
                            "challenge_key": key, "created_at": now.isoformat()})

        # scripting : > scripting_events within scripting_window minutes
        window_start = now - timedelta(minutes=s["scripting_window"])
        recent_count = sum(1 for _, _, ts in events if ts > window_start)
        if recent_count > s["scripting_events"]:
            out.append({"cohort_id": cohort_id, "student_token": token, "kind": "scripting",
                        "challenge_key": None, "created_at": now.isoformat()})

        # idle : no event for idle_min minutes (and at least 1 event in history)
        if last_event and last_event < now - timedelta(minutes=s["idle_min"]):
            out.append({"cohort_id": cohort_id, "student_token": token, "kind": "idle",
                        "challenge_key": None, "created_at": now.isoformat()})

    return out


def _interval_sec() -> float:
    """Tick interval in seconds. Priority : JSON config > env var > default 30s."""
    val = _config_override("interval_sec")
    if val is not None:
        return float(val)
    raw = os.environ.get("DASHBOARD_MONITOR_INTERVAL_SEC", "").strip()
    if not raw:
        return 30.0
    try:
        v = float(raw)
        return v if v > 0 else 30.0
    except ValueError:
        return 30.0


def _list_cohorts(db_mod) -> list[str]:
    with db_mod.get_connection() as conn:
        rows = conn.execute("SELECT cohort_id FROM cohorts").fetchall()
    return [r[0] for r in rows]


def _is_duplicate(db_mod, alert: dict, dedupe_minutes: int = 60) -> bool:
    """True if a matching alert (cohort, token, kind, challenge_key) was
    inserted within the last `dedupe_minutes`. challenge_key may be None."""
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=dedupe_minutes)).isoformat()
    challenge = alert.get("challenge_key")
    with db_mod.get_connection() as conn:
        if challenge is None:
            row = conn.execute(
                "SELECT 1 FROM alerts WHERE cohort_id=? AND student_token=? AND kind=? "
                "AND challenge_key IS NULL AND created_at > ? LIMIT 1",
                (alert["cohort_id"], alert["student_token"], alert["kind"], cutoff),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM alerts WHERE cohort_id=? AND student_token=? AND kind=? "
                "AND challenge_key=? AND created_at > ? LIMIT 1",
                (alert["cohort_id"], alert["student_token"], alert["kind"], challenge, cutoff),
            ).fetchone()
    return row is not None


def persist_alert(db_mod, alert: dict) -> None:
    """Default on_alert callback : insert into alerts table AND broadcast SSE.

    The SSE payload carries kind="alert" so the sse_routes generator
    can dispatch it as a typed `event: alert` frame (see Phase 2 Task 3).
    Original alert classification (blocked / stuck / scripting / idle)
    is preserved under `alert_kind` to avoid clashing with the SSE
    discriminator key.
    """
    with db_mod.get_connection() as conn:
        new_id = db_mod.insert_alert(
            conn, alert["cohort_id"], alert["student_token"],
            alert["kind"], alert.get("challenge_key"), alert["created_at"],
        )
        conn.commit()
    try:
        import sse_pubsub
        sse_pubsub.publish(alert["cohort_id"], {
            "kind": "alert",
            "id": new_id,
            "cohort_id": alert["cohort_id"],
            "student_token": alert["student_token"],
            "alert_kind": alert["kind"],
            "challenge_key": alert.get("challenge_key"),
            "created_at": alert["created_at"],
        })
    except Exception as exc:
        LOGGER.warning("monitor sse publish failed for alert : %s", exc)


def start_monitor(db_mod, on_alert: Callable[[dict], None]) -> threading.Thread:
    """Spawn a daemon thread that ticks every _interval_sec() seconds:
    list cohorts -> compute_alerts -> drop duplicates (60min window) ->
    call on_alert(alert) for every fresh one. Idempotent : a second call
    while a thread is alive returns the existing thread."""
    global _MONITOR_THREAD, _STOP_FLAG

    if _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive():
        return _MONITOR_THREAD

    _STOP_FLAG = threading.Event()
    stop = _STOP_FLAG

    def loop() -> None:
        while not stop.is_set():
            try:
                for cohort_id in _list_cohorts(db_mod):
                    alerts = compute_alerts(db_mod, cohort_id)
                    for alert in alerts:
                        if _is_duplicate(db_mod, alert):
                            continue
                        try:
                            on_alert(alert)
                        except Exception as exc:
                            LOGGER.warning("monitor on_alert failed : %s", exc)
            except Exception as exc:
                LOGGER.warning("monitor tick failed : %s", exc)
            stop.wait(_interval_sec())

    _MONITOR_THREAD = threading.Thread(target=loop, name="juicelab-monitor", daemon=True)
    _MONITOR_THREAD.start()
    return _MONITOR_THREAD


def stop_monitor() -> None:
    """Signal the monitor thread to exit at the next tick boundary."""
    global _STOP_FLAG, _MONITOR_THREAD
    if _STOP_FLAG is not None:
        _STOP_FLAG.set()
    _MONITOR_THREAD = None
    _STOP_FLAG = None
