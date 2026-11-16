"""Phase 2 signal-to-noise heuristics + session horizon & auto-resolution.

compute_alerts reads the events table and returns the alerts currently true
for one cohort : blocked / stuck / scripting / idle, plus absent for
validated roster students while the cohort is in session. The kinds listed
in STATE_KINDS describe a *situation* : run_tick auto-resolves them when the
condition ends. "scripting" is an incident : only the teacher closes it.
start_monitor schedules run_tick per cohort and publishes new alerts and
`alert_resolved` events over SSE.
Threshold env vars : DASHBOARD_MONITOR_BLOCKED_MIN, _STUCK_HINTS,
_SCRIPTING_EVENTS, _SCRIPTING_WINDOW_MIN, _IDLE_MIN, _SESSION_MIN."""

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

# Kinds that describe a situation and are auto-resolved by run_tick once the
# condition is no longer true. "scripting" is an incident to review : only a
# teacher ack closes it, the monitor never does.
STATE_KINDS = frozenset({"blocked", "stuck", "idle", "absent"})


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
    """Compute thresholds : JSON config > env var > default.

    "session_min" is operator policy : it bounds how long a student counts
    as "in session" after their last event (default 240 minutes). Operators
    set it with the env var DASHBOARD_MONITOR_SESSION_MIN or the JSON key
    monitor.session_min ; past that horizon a student is handled by the
    "absent" kind instead of "idle".
    """
    return {
        "blocked_min":      _config_override("blocked_min")          or _env_int("DASHBOARD_MONITOR_BLOCKED_MIN", 10),
        "stuck_hints":      _config_override("stuck_hints")          or _env_int("DASHBOARD_MONITOR_STUCK_HINTS", 5),
        "scripting_events": _config_override("scripting_events")     or _env_int("DASHBOARD_MONITOR_SCRIPTING_EVENTS", 30),
        "scripting_window": _config_override("scripting_window_min") or _env_int("DASHBOARD_MONITOR_SCRIPTING_WINDOW_MIN", 2),
        "idle_min":         _config_override("idle_min")             or _env_int("DASHBOARD_MONITOR_IDLE_MIN", 15),
        "session_min":      _config_override("session_min")          or _env_int("DASHBOARD_MONITOR_SESSION_MIN", 240),
    }


def _config_reset_cache() -> None:
    """Test helper to clear the config cache between tests."""
    global _CONFIG_CACHE, _CONFIG_PATH_CACHE
    _CONFIG_CACHE = None
    _CONFIG_PATH_CACHE = None


def compute_alerts(db_mod, cohort_id: str, now: datetime | None = None) -> list[dict[str, Any]]:
    """Scan events table for the given cohort, return one dict per detected alert.

    Returned dicts have shape {cohort_id, student_token, kind, challenge_key, created_at}.

    A student is IN SESSION while their last event is newer than
    now - session_min (operator policy, default 240 minutes, env
    DASHBOARD_MONITOR_SESSION_MIN / JSON monitor.session_min). "blocked",
    "stuck" and "idle" are emitted only for in-session students ; "scripting"
    is unchanged and ignores the session horizon. "absent" (challenge_key
    None) is emitted for roster students (students.status = 'validated')
    whose last event is missing or older than the session horizon, but only
    while the cohort is ACTIVE, i.e. at least one cohort event is newer than
    now - idle_min ; students not validated never get one.

    The caller is responsible for de-duplicating (one alert per (token, kind, key) pair)
    and persisting via db_mod.insert_alert(...).
    """
    now = now or datetime.now(timezone.utc)
    s = _seuils()
    session_cutoff = now - timedelta(minutes=s["session_min"])
    idle_cutoff = now - timedelta(minutes=s["idle_min"])
    out: list[dict[str, Any]] = []
    with db_mod.get_connection() as conn:
        rows = conn.execute(
            "SELECT student_token, event_type, challenge_key, client_ts FROM events "
            "WHERE cohort_id=? ORDER BY id ASC",
            (cohort_id,),
        ).fetchall()
        roster_rows = conn.execute(
            "SELECT student_token FROM students "
            "WHERE cohort_id=? AND status='validated'",
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

    # The cohort is in session while at least one of its events is fresh
    # (anybody still working keeps the room "open" for absences).
    cohort_active = any(
        ts > idle_cutoff for events in by_student.values() for _, _, ts in events
    )

    for token, events in by_student.items():
        last_event = events[-1][2] if events else None
        last_challenge = next((k for _, k, _ in reversed(events) if k), None)
        in_session = last_event is not None and last_event > session_cutoff

        if in_session:
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
        # (unchanged : an incident is raised whatever the session horizon)
        window_start = now - timedelta(minutes=s["scripting_window"])
        recent_count = sum(1 for _, _, ts in events if ts > window_start)
        if recent_count > s["scripting_events"]:
            out.append({"cohort_id": cohort_id, "student_token": token, "kind": "scripting",
                        "challenge_key": None, "created_at": now.isoformat()})

        # idle : no event for idle_min minutes (and at least 1 event in
        # history), only while the student is in session
        if in_session and last_event and last_event < idle_cutoff:
            out.append({"cohort_id": cohort_id, "student_token": token, "kind": "idle",
                        "challenge_key": None, "created_at": now.isoformat()})

    # absent : validated roster students not seen during the current session,
    # raised only while somebody is still working in the cohort
    if cohort_active:
        for row in roster_rows:
            token = row[0]
            events = by_student.get(token)
            last = events[-1][2] if events else None
            if last is None or last < session_cutoff:
                out.append({"cohort_id": cohort_id, "student_token": token, "kind": "absent",
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
    """True if `alert` must not be inserted again.

    A matching alert has the same (cohort_id, student_token, kind,
    challenge_key); challenge_key may be None. It is a duplicate when:
    - a matching alert is ACTIVE (ack_at IS NULL AND resolved_at IS NULL),
      whatever its age : it already stands for the condition, so a persistent
      state (idle for weeks, blocked for good) yields one alert, not one per
      window;
    - or a matching alert has ack_at NOT NULL and was created within the last
      `dedupe_minutes`, so an acknowledged alert is not raised again at once.

    An auto-resolved alert (resolved_at set, ack_at NULL) is NEVER a
    duplicate : the condition ended, a recurrence must be raised again
    immediately. Limit: once acknowledged and past the window, a condition
    that still holds is raised again. Read-only; raises sqlite3.Error on DB
    failure.
    """
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=dedupe_minutes)).isoformat()
    challenge = alert.get("challenge_key")
    with db_mod.get_connection() as conn:
        if challenge is None:
            row = conn.execute(
                "SELECT 1 FROM alerts WHERE cohort_id=? AND student_token=? AND kind=? "
                "AND challenge_key IS NULL AND ("
                "(ack_at IS NULL AND resolved_at IS NULL) "
                "OR (ack_at IS NOT NULL AND created_at > ?)) LIMIT 1",
                (alert["cohort_id"], alert["student_token"], alert["kind"], cutoff),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM alerts WHERE cohort_id=? AND student_token=? AND kind=? "
                "AND challenge_key=? AND ("
                "(ack_at IS NULL AND resolved_at IS NULL) "
                "OR (ack_at IS NOT NULL AND created_at > ?)) LIMIT 1",
                (alert["cohort_id"], alert["student_token"], alert["kind"], challenge, cutoff),
            ).fetchone()
    return row is not None


def persist_alert(db_mod, alert: dict) -> None:
    """Default on_alert callback : insert into alerts table AND broadcast SSE.

    The SSE payload carries kind="alert" so the sse_routes generator
    can dispatch it as a typed `event: alert` frame (see Phase 2 Task 3).
    Original alert classification (blocked / stuck / scripting / idle /
    absent) is preserved under `alert_kind` to avoid clashing with the SSE
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


def run_tick(db_mod, cohort_id: str, on_alert: Callable[[dict], None],
             on_resolved: Callable[[dict], None] | None = None,
             now: datetime | None = None) -> None:
    """One monitor pass for `cohort_id` : raise fresh alerts, then
    auto-resolve the state alerts whose condition ended.

    Inputs: db_mod (module exposing get_connection / active_alert_keys /
    resolve_alert_group — the db module or a test fake), the cohort id, the
    on_alert callback, an optional on_resolved callback, and an optional
    `now` (tests; defaults to UTC now).

    Behaviour: compute_alerts(...) is evaluated; every alert that is not a
    duplicate (see _is_duplicate, 60 min window) is handed to on_alert —
    exceptions from on_alert are logged with LOGGER.warning and do not stop
    the tick. Then every ACTIVE alert key of the cohort in the database
    whose kind is in STATE_KINDS and which is NOT in the freshly computed
    set is closed with db_mod.resolve_alert_group (committed immediately);
    on_resolved receives {cohort_id, student_token, kind, challenge_key,
    resolved_at} per closed group and its exceptions are logged, never
    raised. Alerts belonging to the freshly computed set — duplicates still
    standing in the database as well as alerts persisted by on_alert during
    this same tick — are never resolved. DB errors propagate to the caller
    (start_monitor catches them per cohort).
    """
    now = now or datetime.now(timezone.utc)
    alerts = compute_alerts(db_mod, cohort_id, now=now)
    computed_keys = {
        (a["student_token"], a["kind"], a.get("challenge_key")) for a in alerts
    }
    for alert in alerts:
        if _is_duplicate(db_mod, alert):
            continue
        try:
            on_alert(alert)
        except Exception as exc:
            LOGGER.warning("monitor on_alert failed : %s", exc)

    with db_mod.get_connection() as conn:
        for student_token, kind, challenge_key in db_mod.active_alert_keys(conn, cohort_id):
            if kind not in STATE_KINDS:
                continue  # "scripting" is an incident : never auto-resolved
            if (student_token, kind, challenge_key) in computed_keys:
                continue  # condition still true (or raised) in this tick
            resolved_at = now.isoformat()
            db_mod.resolve_alert_group(conn, cohort_id, student_token, kind, challenge_key, resolved_at)
            conn.commit()
            if on_resolved is not None:
                try:
                    on_resolved({
                        "cohort_id": cohort_id,
                        "student_token": student_token,
                        "kind": kind,
                        "challenge_key": challenge_key,
                        "resolved_at": resolved_at,
                    })
                except Exception as exc:
                    LOGGER.warning("monitor on_resolved failed : %s", exc)


def _publish_resolved(payload: dict) -> None:
    """on_resolved callback used by start_monitor : broadcast an
    `alert_resolved` SSE frame for one auto-resolved alert group.

    sse_pubsub is imported lazily inside the call, as persist_alert does, so
    monitor.py stays usable without the SSE layer (tests, CLI). Publish
    failures are logged (LOGGER.warning) and swallowed : a broken SSE bus
    must not abort the monitor loop. `payload` is the dict built by run_tick.
    """
    try:
        import sse_pubsub
        sse_pubsub.publish(payload["cohort_id"], {
            "kind": "alert_resolved",
            "cohort_id": payload["cohort_id"],
            "student_token": payload["student_token"],
            "alert_kind": payload["kind"],
            "challenge_key": payload["challenge_key"],
            "resolved_at": payload["resolved_at"],
        })
    except Exception as exc:
        LOGGER.warning("monitor sse publish failed for alert_resolved : %s", exc)


def start_monitor(db_mod, on_alert: Callable[[dict], None]) -> threading.Thread:
    """Spawn a daemon thread that ticks every _interval_sec() seconds:
    list cohorts -> run_tick(cohort, on_alert, on_resolved=_publish_resolved)
    for each. run_tick raises fresh alerts through `on_alert` (dedupe over a
    60 min window) and auto-resolves state alerts (STATE_KINDS) whose
    condition ended ; _publish_resolved turns each resolution into an
    `alert_resolved` SSE frame (publish failures logged, never raised).
    Idempotent : a second call while a thread is alive returns the existing
    thread."""
    global _MONITOR_THREAD, _STOP_FLAG

    if _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive():
        return _MONITOR_THREAD

    _STOP_FLAG = threading.Event()
    stop = _STOP_FLAG

    def loop() -> None:
        while not stop.is_set():
            try:
                for cohort_id in _list_cohorts(db_mod):
                    try:
                        run_tick(db_mod, cohort_id, on_alert, on_resolved=_publish_resolved)
                    except Exception as exc:
                        LOGGER.warning("monitor tick failed for cohort %s : %s", cohort_id, exc)
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
