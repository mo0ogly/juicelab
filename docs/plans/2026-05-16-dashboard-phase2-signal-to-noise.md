# Dashboard Phase 2 — Signal-to-noise Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Detecter automatiquement les etudiants en difficulte (blocked/stuck) ou avec comportement suspect (scripting/idle), surfacer dans un side panel d'alertes en live + toasts contextuels, et permettre au prof de tagger/noter inline pour reagir vite.

**Architecture:** Module `monitor.py` avec 4 heuristiques. Thread background tick toutes 30s, insert dans `alerts` table (deja livree Phase 1), broadcast SSE event `alert`. Frontend ajoute un side panel + toasts.

**Tech Stack:** Flask + SQLite + `threading.Thread` (PAS APScheduler — zero dep externe). EventSource consomme deja le stream Phase 1.

**Reference design :** `docs/plans/2026-05-15-dashboard-monitor-sse-modes-design.md` Phase 2 section.

**Tests cible :** +18 pytest, zero regression sur 215 existants.

**Decomposition :**
- Ce fichier : Tasks 1-5 (heuristiques, scheduler, alerts API, alerts panel, typed SSE events)
- `2026-05-16-dashboard-phase2-signal-to-noise-pt2.md` : Tasks 6-9 (tag inline UI, notes modal, config, final gate)

---

## Task 1 — monitor.py with 4 heuristiques

**Files:**
- Create: `dashboard/monitor.py`
- Create: `dashboard/tests/test_monitor.py`

**Heuristiques :**
- `blocked` : 0 events 10 min sur meme challenge_key actif (=dernier touche par l'eleve)
- `stuck` : 5/5 hints utilises sur 1 challenge sans `challenge_solved`
- `scripting` : >30 events / 2 min sur 1 student (eg. >30 hint_revealed consecutifs)
- `idle` : 0 events 15 min cohort-wide pour 1 student

Seuils :
- `BLOCKED_MIN` = 10 (minutes)
- `STUCK_HINTS` = 5
- `SCRIPTING_EVENTS` = 30, `SCRIPTING_WINDOW_MIN` = 2
- `IDLE_MIN` = 15

Tous overridables via env var (DASHBOARD_MONITOR_BLOCKED_MIN, etc.).

**Step 1 — Failing test** `dashboard/tests/test_monitor.py` (5 tests, 1 per heuristic + 1 happy path returning 0 alerts) :

```python
"""monitor.py heuristics (Phase 2).

Note: this test uses module-level reload — not safe under pytest-xdist parallel.
"""
from __future__ import annotations
import sys, pytest, importlib
from datetime import datetime, timezone, timedelta

ROOT_FIX = lambda: None
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def db_mod(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    for m in ["db", "monitor"]:
        if m in sys.modules: del sys.modules[m]
    import db
    importlib.reload(db)
    db.init_schema()
    return db


def _insert_event(db_mod, cohort, token, event_type, key, minutes_ago=0):
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    with db_mod.get_connection() as c:
        c.execute(
            "INSERT INTO events (cohort_id, student_token, event_type, challenge_key, client_ts, server_ts, data, instance_label) "
            "VALUES (?, ?, ?, ?, ?, ?, '{}', '')",
            (cohort, token, event_type, key, ts, ts),
        )
        c.commit()


def test_blocked_detected(db_mod):
    import monitor
    _insert_event(db_mod, "c1", "tok1", "hint_revealed", "xss", minutes_ago=15)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    kinds = {a["kind"] for a in alerts}
    assert "blocked" in kinds


def test_stuck_detected(db_mod):
    import monitor
    for i in range(5):
        _insert_event(db_mod, "c1", "tok2", "hint_revealed", "sqli", minutes_ago=5)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    kinds = {a["kind"] for a in alerts}
    assert "stuck" in kinds


def test_scripting_detected(db_mod):
    import monitor
    for i in range(35):
        _insert_event(db_mod, "c1", "tok3", "hint_revealed", "xss", minutes_ago=1)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    kinds = {a["kind"] for a in alerts}
    assert "scripting" in kinds


def test_idle_detected(db_mod):
    import monitor
    # Old event 20 min ago then nothing
    _insert_event(db_mod, "c1", "tok4", "session_start", None, minutes_ago=20)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    kinds = {a["kind"] for a in alerts}
    assert "idle" in kinds


def test_no_alerts_for_active_student(db_mod):
    import monitor
    _insert_event(db_mod, "c1", "tok5", "session_start", None, minutes_ago=2)
    _insert_event(db_mod, "c1", "tok5", "hint_revealed", "xss", minutes_ago=1)
    alerts = monitor.compute_alerts(db_mod, "c1", now=datetime.now(timezone.utc))
    assert alerts == [] or all(a["student_token"] != "tok5" for a in alerts)
```

**Step 2 — Run FAIL :** `python3 -m pytest tests/test_monitor.py -v`

**Step 3 — Create `dashboard/monitor.py`** :

```python
"""Phase 2 signal-to-noise heuristics.

Reads events table to compute live alerts per cohort. Pure functions
(no scheduling, no broadcast) — caller does the tick + insert + SSE.
Threshold env vars : DASHBOARD_MONITOR_BLOCKED_MIN, _STUCK_HINTS,
_SCRIPTING_EVENTS, _SCRIPTING_WINDOW_MIN, _IDLE_MIN."""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _seuils() -> dict[str, int]:
    return {
        "blocked_min":         _env_int("DASHBOARD_MONITOR_BLOCKED_MIN", 10),
        "stuck_hints":         _env_int("DASHBOARD_MONITOR_STUCK_HINTS", 5),
        "scripting_events":    _env_int("DASHBOARD_MONITOR_SCRIPTING_EVENTS", 30),
        "scripting_window":    _env_int("DASHBOARD_MONITOR_SCRIPTING_WINDOW_MIN", 2),
        "idle_min":            _env_int("DASHBOARD_MONITOR_IDLE_MIN", 15),
    }


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
```

**Step 4 — Run PASS + regression :**

```bash
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! python3 -m pytest tests/test_monitor.py tests/ -q --no-header 2>&1 | tail -5
```

Expected : 5 new + 215 = 220 PASS.

**Step 5 — Commit :**

```bash
git add dashboard/monitor.py dashboard/tests/test_monitor.py
git commit -m "feat(dashboard/monitor): 4 heuristics (blocked/stuck/scripting/idle) (Phase 2)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2 — Scheduler (threading.Thread tick loop)

**Files:**
- Modify: `dashboard/monitor.py` (add `start_monitor` function with thread)
- Modify: `dashboard/app.py` (call `start_monitor` in `create_app`, behind env flag)
- Modify: `dashboard/tests/test_monitor.py` (add 2 tests)

**Add `start_monitor(app, interval_sec, on_alert)`** : spawns a daemon thread that ticks every `interval_sec` (env-overridable `DASHBOARD_MONITOR_INTERVAL_SEC`, default 30, test fixture 0.3), per cohort runs `compute_alerts` + dedup against `alerts` table (skip if same (token, kind, key) already in last hour), calls `on_alert(alert)` for each new alert. The `on_alert` callback is wired to insert into DB + publish SSE.

Test :
- `test_scheduler_inserts_alerts` : start thread with interval 0.3, seed events that trigger blocked, wait 1s, verify `recent_alerts` returns a row.
- `test_scheduler_dedupes_within_window` : same as above, but wait 2 ticks, verify only 1 row inserted (not 2).

**`dashboard/app.py` integration** : after `register_*` blocks, optional `if os.environ.get("DASHBOARD_MONITOR_ENABLED", "1") != "0": start_monitor(app, callback)`. Default ON.

**Critical : keep app.py <= 800 lines.** Use single-line append pattern from Phase 1.

**Step 5 — Commit :** `feat(dashboard/monitor): background scheduler thread with dedup window (Phase 2)`

---

## Task 3 — Alerts CRUD API + SSE typed event

**Files:**
- Create: `dashboard/alerts_routes.py`
- Modify: `dashboard/app.py` (register)
- Modify: `dashboard/monitor.py` `on_alert` callback wires to publish SSE typed `event: alert`
- Modify: `dashboard/sse_routes.py` if needed (events already pass through, but `alert` is a distinct event name vs `event`)
- Test: `dashboard/tests/test_alerts_routes.py` (4 tests)

**Endpoints :**
- `GET /api/alerts?cohort=X&unack=true` : list unack alerts (ack_at IS NULL)
- `POST /api/alerts/<id>/ack` : set ack_at = now
- Auth : teacher only (X-Teacher-Token header)

**SSE delta : when monitor inserts a new alert, publish `{kind: "alert", id, cohort_id, student_token, alert_kind, challenge_key, created_at}` via sse_pubsub. The SSE endpoint already emits `event: event` for everything from pubsub. The frontend will discriminate `alert_kind` field.**

(Alternatively : add a new SSE event type `event: alert`. Cleaner. Modify sse_routes to check if the payload has a `kind=alert` flag and emit a different `event:` line. Choose this approach.)

Tests :
- `test_alerts_requires_auth`
- `test_list_alerts_empty`
- `test_list_alerts_returns_inserted`
- `test_ack_alert_sets_ack_at`

**Step 6 — Commit :** `feat(dashboard/alerts): GET /api/alerts + POST /api/alerts/<id>/ack + SSE event (Phase 2)`

---

## Task 4 — Alerts panel UI + dashboard.html integration

**Files:**
- Create: `dashboard/templates/_alerts_panel.html` (partial)
- Modify: `dashboard/templates/dashboard.html` (mount panel + EventSource listener for `alert` event type)
- Modify: `dashboard/i18n/{fr,en,br}.json` (new keys ALERT_KIND_BLOCKED/STUCK/SCRIPTING/IDLE, ALERT_TITLE, ALERT_ACK, ALERT_EMPTY)
- Modify: `dashboard/static/dashboard.css` (style `.alerts-panel`, `.alert-item`, `.alert-kind-X`)
- Test: `dashboard/tests/test_alerts_panel.py` (2 tests)

**Markup pattern :**
```html
<aside class="alerts-panel" id="alerts-panel" aria-label="{{ t('ALERT_TITLE') }}">
  <h2 class="section-title">{{ t('ALERT_TITLE') }}</h2>
  <ul id="alerts-list"></ul>
</aside>
```

Place after the toolbar, before the scroll matrix. Hide via `.hidden` if no alerts.

**JS in dashboard.html :**
- On `alert` event : prepend an `<li class="alert-item alert-kind-{kind}">...</li>` with student token + challenge_key + button "ack"
- Ack click → POST /api/alerts/<id>/ack + remove from DOM

**i18n keys to add (FR/EN/BR) :** ALERT_TITLE, ALERT_KIND_BLOCKED, ALERT_KIND_STUCK, ALERT_KIND_SCRIPTING, ALERT_KIND_IDLE, ALERT_ACK_BUTTON, ALERT_EMPTY.

Tests :
- `test_dashboard_html_renders_alerts_panel` : GET /dashboard returns body containing `id="alerts-panel"`
- `test_alerts_panel_is_aria_labelled`

**Step 7 — Commit :** `feat(dashboard/ui): alerts panel side widget with SSE live updates (Phase 2)`

---

## Task 5 — Typed SSE events for toasts (flag_posted / quiz_done / journal_saved)

**Files:**
- Modify: `dashboard/sync_routes.py` (after publish, also emit a typed `notification` SSE for flag/quiz/journal events)
- Modify: `dashboard/sse_routes.py` (route `notification` events to a distinct SSE event name)
- Modify: `dashboard/templates/dashboard.html` (JS handler for `notification` SSE → toast in DOM)
- Modify: `dashboard/static/dashboard.css` (toast already styled in Phase 1 redesign — verify, add `.toast.notification` if needed)
- Modify: i18n keys TOAST_FLAG_POSTED, TOAST_QUIZ_DONE, TOAST_JOURNAL_SAVED (FR/EN/BR)
- Test: `dashboard/tests/test_notifications.py` (3 tests)

**Logic :** when event_type matches one of {`flag_verified`, `quiz_completed`, `journal_filled`}, sync_routes publishes a SECOND pubsub message with `{kind: "notification", subtype: "flag" | "quiz" | "journal", student_token, challenge_key, ts}`. SSE endpoint emits this as `event: notification`. Frontend shows 4s toast in bottom-right corner.

Tests :
- `test_flag_verified_triggers_notification`
- `test_quiz_completed_triggers_notification`
- `test_journal_filled_triggers_notification`

**Step 8 — Commit :** `feat(dashboard/notifications): typed SSE event for flag/quiz/journal toasts (Phase 2)`

---

**Continuation : Tasks 6-9 in `2026-05-16-dashboard-phase2-signal-to-noise-pt2.md` (tag inline UI, notes modal, config seuils JSON, final gate).**
