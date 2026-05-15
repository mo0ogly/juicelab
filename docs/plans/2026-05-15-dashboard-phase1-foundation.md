# Dashboard Phase 1 — Foundation (SSE + Tags/Notes) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remplacer le polling `/api/cohort` toutes 5s par un flux SSE persistant, et installer le schema `student_tag` + `student_note` + `alerts` qui sera exploite en Phase 2 (signal-to-noise).

**Architecture:** Pub/sub thread-safe en memoire (`collections.defaultdict[str, list[Queue]]` indexe par cohort_id). `sync_routes.py` publie apres insert SQLite. `sse_routes.py` expose `/api/cohort/stream` (Flask `stream_with_context`, mimetype `text/event-stream`) qui souscrit, replay snapshot initial, puis stream events delta. Frontend swap `setInterval` pour `EventSource` natif.

**Tech Stack:** Flask 3, SQLite (existant), pytest (existant), vanilla JS (existant), zero nouvelle dependance externe. CSP unchanged (`connect-src 'self'` autorise deja SSE same-origin).

**Reference design :** `docs/plans/2026-05-15-dashboard-monitor-sse-modes-design.md`

**Tests cible :** +16 pytest (objectif >= +10 atteint), zero regression sur 199 existants.

**Decomposition fichiers :**
- Ce fichier : Tasks 1-4 (schema, DB helpers, pubsub primitive, SSE endpoint)
- `2026-05-15-dashboard-phase1-foundation-pt2.md` : Tasks 5-9 (sync broadcast, tags HTTP, frontend EventSource, e2e, final gate)

---

## Task 1 — Schema migration : student_tag + student_note + alerts

**Files:**
- Modify: `dashboard/schema.sql`
- Modify: `dashboard/db.py` (additions dans `_migrate()`)
- Test: `dashboard/tests/test_schema_phase1.py` (NEW)

**Step 1 — Write failing test :**

Create `dashboard/tests/test_schema_phase1.py`:

```python
"""Schema migration smoke tests for Phase 1."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    import importlib, sys
    if "db" in sys.modules: del sys.modules["db"]
    import db
    importlib.reload(db)
    db.init_schema()
    return tmp_path / "d.sqlite"


def _cols(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as c:
        return {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}


def test_student_tag_table_exists(fresh_db):
    cols = _cols(fresh_db, "student_tag")
    assert {"student_token", "cohort_id", "status", "updated_at"} <= cols


def test_student_note_table_exists(fresh_db):
    cols = _cols(fresh_db, "student_note")
    assert {"student_token", "cohort_id", "body", "updated_at"} <= cols


def test_alerts_table_exists(fresh_db):
    cols = _cols(fresh_db, "alerts")
    assert {"id", "cohort_id", "student_token", "kind", "challenge_key", "created_at", "ack_at"} <= cols
```

**Step 2 — Run to verify FAIL :**

```bash
cd /home/fpizzi/juice/dashboard
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! python3 -m pytest tests/test_schema_phase1.py -v
```

Expected : 3 FAIL "no such table".

**Step 3 — Append to `dashboard/schema.sql` :**

```sql
CREATE TABLE IF NOT EXISTS student_tag (
    student_token TEXT NOT NULL,
    cohort_id     TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'none',
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (student_token, cohort_id)
);
CREATE TABLE IF NOT EXISTS student_note (
    student_token TEXT NOT NULL,
    cohort_id     TEXT NOT NULL,
    body          TEXT NOT NULL DEFAULT '',
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (student_token, cohort_id)
);
CREATE TABLE IF NOT EXISTS alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cohort_id     TEXT NOT NULL,
    student_token TEXT NOT NULL,
    kind          TEXT NOT NULL,
    challenge_key TEXT,
    created_at    TEXT NOT NULL,
    ack_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_cohort_unack ON alerts(cohort_id, ack_at);
CREATE INDEX IF NOT EXISTS idx_alerts_recent ON alerts(cohort_id, created_at DESC);
```

**Step 4 — Append migrations to `dashboard/db.py` `_migrate()` (just before final commit) :**

```python
# Phase 1 — tags + notes + alerts (idempotent)
for stmt in [
    "CREATE TABLE IF NOT EXISTS student_tag (student_token TEXT NOT NULL, cohort_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'none', updated_at TEXT NOT NULL, PRIMARY KEY (student_token, cohort_id))",
    "CREATE TABLE IF NOT EXISTS student_note (student_token TEXT NOT NULL, cohort_id TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, PRIMARY KEY (student_token, cohort_id))",
    "CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, cohort_id TEXT NOT NULL, student_token TEXT NOT NULL, kind TEXT NOT NULL, challenge_key TEXT, created_at TEXT NOT NULL, ack_at TEXT)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_cohort_unack ON alerts(cohort_id, ack_at)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_recent ON alerts(cohort_id, created_at DESC)",
]:
    cur.execute(stmt)
```

**Step 5 — Run tests + regression :**

```bash
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! python3 -m pytest tests/test_schema_phase1.py tests/ -v 2>&1 | tail -10
```

Expected : 3 PASS phase1 + 199 existants = 202.

**Step 6 — Commit :**

```bash
git add dashboard/schema.sql dashboard/db.py dashboard/tests/test_schema_phase1.py
git commit -m "feat(dashboard/db): student_tag, student_note, alerts tables (Phase 1)"
```

---

## Task 2 — DB helpers : set/get tag, note, alert

**Files:**
- Modify: `dashboard/db.py` (append helpers ~ligne 540)
- Test: `dashboard/tests/test_db_helpers_phase1.py` (NEW)

**Step 1 — Write failing test :**

Create `dashboard/tests/test_db_helpers_phase1.py`:

```python
"""DB helpers for tags, notes, alerts (Phase 1)."""
from __future__ import annotations
import pytest, sys, importlib
from datetime import datetime, timezone


@pytest.fixture
def db_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    if "db" in sys.modules: del sys.modules["db"]
    import db
    importlib.reload(db)
    db.init_schema()
    return db


def test_set_and_get_tag(db_module):
    now = datetime.now(timezone.utc).isoformat()
    with db_module.get_connection() as c:
        db_module.set_tag(c, "tok123", "M2-IA-2026", "a_voir", now)
        c.commit()
        result = db_module.get_tag(c, "tok123", "M2-IA-2026")
    assert result == "a_voir"


def test_get_tag_default_none(db_module):
    with db_module.get_connection() as c:
        result = db_module.get_tag(c, "missing", "M2-IA-2026")
    assert result is None


def test_set_and_get_note(db_module):
    now = datetime.now(timezone.utc).isoformat()
    with db_module.get_connection() as c:
        db_module.set_note(c, "tok123", "M2-IA-2026", "rusee sur XSS", now)
        c.commit()
        result = db_module.get_note(c, "tok123", "M2-IA-2026")
    assert result == "rusee sur XSS"


def test_insert_and_recent_alerts(db_module):
    now = datetime.now(timezone.utc).isoformat()
    with db_module.get_connection() as c:
        db_module.insert_alert(c, "M2-IA-2026", "tok123", "blocked", "xss-stored", now)
        db_module.insert_alert(c, "M2-IA-2026", "tok456", "stuck", "sql-inject", now)
        c.commit()
        rows = db_module.recent_alerts(c, "M2-IA-2026", limit=10)
    kinds = {r["kind"] for r in rows}
    assert kinds == {"blocked", "stuck"}
```

**Step 2 — Run FAIL :**

```bash
python3 -m pytest tests/test_db_helpers_phase1.py -v
```

Expected : 4 FAIL `AttributeError`.

**Step 3 — Append helpers to `dashboard/db.py` :**

```python
# ------------------------------------------------------------------
# Phase 1 helpers — tags, notes, alerts
# ------------------------------------------------------------------

def set_tag(conn: sqlite3.Connection, student_token: str, cohort_id: str, status: str, now: str) -> None:
    conn.execute(
        "INSERT INTO student_tag (student_token, cohort_id, status, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(student_token, cohort_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at",
        (student_token, cohort_id, status, now),
    )


def get_tag(conn: sqlite3.Connection, student_token: str, cohort_id: str) -> str | None:
    row = conn.execute(
        "SELECT status FROM student_tag WHERE student_token=? AND cohort_id=?",
        (student_token, cohort_id),
    ).fetchone()
    return row[0] if row else None


def set_note(conn: sqlite3.Connection, student_token: str, cohort_id: str, body: str, now: str) -> None:
    conn.execute(
        "INSERT INTO student_note (student_token, cohort_id, body, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(student_token, cohort_id) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at",
        (student_token, cohort_id, body, now),
    )


def get_note(conn: sqlite3.Connection, student_token: str, cohort_id: str) -> str:
    row = conn.execute(
        "SELECT body FROM student_note WHERE student_token=? AND cohort_id=?",
        (student_token, cohort_id),
    ).fetchone()
    return row[0] if row else ""


def insert_alert(conn: sqlite3.Connection, cohort_id: str, student_token: str, kind: str, challenge_key: str | None, now: str) -> int:
    cur = conn.execute(
        "INSERT INTO alerts (cohort_id, student_token, kind, challenge_key, created_at) VALUES (?, ?, ?, ?, ?)",
        (cohort_id, student_token, kind, challenge_key, now),
    )
    return cur.lastrowid or 0


def recent_alerts(conn: sqlite3.Connection, cohort_id: str, limit: int = 100) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT id, cohort_id, student_token, kind, challenge_key, created_at, ack_at "
        "FROM alerts WHERE cohort_id=? ORDER BY id DESC LIMIT ?",
        (cohort_id, limit),
    ).fetchall()
```

**Step 4 — Run PASS + regression :**

```bash
python3 -m pytest tests/test_db_helpers_phase1.py tests/ -v 2>&1 | tail -10
```

Expected : 4 PASS phase1 + zero regression.

**Step 5 — Commit :**

```bash
git add dashboard/db.py dashboard/tests/test_db_helpers_phase1.py
git commit -m "feat(dashboard/db): tag/note/alert CRUD helpers (Phase 1)"
```

---

## Task 3 — SSE pub/sub primitive (in-memory thread-safe)

**Files:**
- Create: `dashboard/sse_pubsub.py`
- Test: `dashboard/tests/test_sse_pubsub.py` (NEW)

**Step 1 — Write failing test :**

Create `dashboard/tests/test_sse_pubsub.py`:

```python
"""SSE pub/sub primitive tests (Phase 1)."""
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
```

**Step 2 — Run FAIL :**

```bash
python3 -m pytest tests/test_sse_pubsub.py -v
```

Expected : ImportError / 2 FAIL.

**Step 3 — Create `dashboard/sse_pubsub.py` :**

```python
"""In-memory pub/sub hub for SSE broadcasts (cohort-scoped).

Phase 1: simple thread-safe fanout. Each subscriber gets its own
bounded queue; slow consumers drop oldest events instead of blocking
producers. Cohort-keyed so cross-cohort isolation is preserved.

Single-process design. If the dashboard ever runs multi-worker
(gunicorn -w N), this hub must be replaced by Redis pub/sub."""

from __future__ import annotations

from collections import defaultdict
from queue import Queue, Full
from threading import RLock
from typing import Any, Dict, List

_LOCK = RLock()
_SUBSCRIBERS: Dict[str, List[Queue]] = defaultdict(list)


def subscribe(cohort_id: str, maxsize: int = 100) -> Queue:
    q: Queue = Queue(maxsize=maxsize)
    with _LOCK:
        _SUBSCRIBERS[cohort_id].append(q)
    return q


def unsubscribe(cohort_id: str, q: Queue) -> None:
    with _LOCK:
        try:
            _SUBSCRIBERS[cohort_id].remove(q)
        except ValueError:
            pass


def publish(cohort_id: str, event: dict[str, Any]) -> int:
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
    with _LOCK:
        return len(_SUBSCRIBERS.get(cohort_id, ()))
```

**Step 4 — Run PASS :**

```bash
python3 -m pytest tests/test_sse_pubsub.py -v
```

Expected : 2 PASS.

**Step 5 — Commit :**

```bash
git add dashboard/sse_pubsub.py dashboard/tests/test_sse_pubsub.py
git commit -m "feat(dashboard/sse): in-memory pub/sub hub for cohort-scoped fanout"
```

---

## Task 4 — SSE stream endpoint /api/cohort/stream

**Files:**
- Create: `dashboard/sse_routes.py`
- Modify: `dashboard/app.py` (register, ~ligne 582)
- Test: `dashboard/tests/test_sse_stream.py` (NEW)

**Step 1 — Write failing test :**

Create `dashboard/tests/test_sse_stream.py`:

```python
"""SSE /api/cohort/stream endpoint tests (Phase 1)."""
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
    for m in ["app", "db", "sse_pubsub", "sse_routes"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    a = create_app()
    a.testing = True
    return a


def test_stream_requires_teacher_auth(app):
    client = app.test_client()
    r = client.get("/api/cohort/stream?cohort=M2-IA-2026")
    assert r.status_code in (401, 403)


def test_stream_emits_initial_chunk(app):
    client = app.test_client()
    client.set_cookie("teacher_session", "teacher-test-token-very-long-32chars!!")
    with client.get("/api/cohort/stream?cohort=M2-IA-2026", buffered=False) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("Content-Type", "")
        chunk = next(r.iter_encoded())
        assert b"retry:" in chunk or b"event:" in chunk or b"data:" in chunk
```

**Step 2 — Run FAIL :**

```bash
python3 -m pytest tests/test_sse_stream.py -v
```

Expected : 404 (endpoint absent).

**Step 3 — Create `dashboard/sse_routes.py` :**

```python
"""Server-Sent Events endpoint for the cohort matrix live stream.

Exposes /api/cohort/stream?cohort=<id> as text/event-stream. Each
subscriber receives:
  - one `event: snapshot` with the initial cohort state on connect
  - `event: event` after every /api/sync insert
  - `: heartbeat` every 15 s

EventSource native gere reconnect. Server emits `retry: 5000` once."""

from __future__ import annotations

import json
from typing import Callable

from flask import Flask, Response, request, stream_with_context

import sse_pubsub

HEARTBEAT_SEC = 15


def register_sse_routes(app: Flask, check_teacher_auth: Callable, build_summary: Callable) -> None:

    @app.get("/api/cohort/stream")
    def stream_cohort():
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        cohort = request.args.get("cohort", "").strip()
        if not cohort:
            return Response("missing cohort", status=400)

        def gen():
            q = sse_pubsub.subscribe(cohort)
            try:
                yield "retry: 5000\n\n"
                try:
                    snap = build_summary(cohort)
                    yield f"event: snapshot\ndata: {json.dumps(snap)}\n\n"
                except Exception:
                    yield "event: snapshot\ndata: {}\n\n"
                while True:
                    try:
                        ev = q.get(timeout=HEARTBEAT_SEC)
                        yield f"event: event\ndata: {json.dumps(ev)}\n\n"
                    except Exception:
                        yield ": heartbeat\n\n"
            finally:
                sse_pubsub.unsubscribe(cohort, q)

        headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        return Response(stream_with_context(gen()), mimetype="text/event-stream", headers=headers)
```

**Step 4 — Register dans `dashboard/app.py` :**

Avant `register_diploma_routes` (~ligne 582), ajouter import en haut :

```python
from sse_routes import register_sse_routes
```

Puis dans `create_app()` apres `register_proof_routes(...)` :

```python
register_sse_routes(app, _check_teacher_auth, _build_cohort_summary)
```

**ATTENTION** : `_build_cohort_summary` est probablement nomme differemment dans app.py. Grep pour la fonction qui sert `/api/cohort` :

```bash
grep -n "def _build\|def _collect\|def _summary\|api_cohort" dashboard/app.py | head -5
```

Et passer la fonction correspondante a `register_sse_routes`. Si la fonction interne n'est pas exposable, refactor : extraire `def _build_cohort_summary(cohort_id: str) -> dict:` du handler `api_cohort` et l'utiliser ici + dans `api_cohort`.

**Step 5 — Verifier app.py < 800 lignes :**

```bash
wc -l dashboard/app.py
```

Si > 800, refactor : extraire la chaine longue de `register_*` lignes ~582 en helper `_register_all_routes(app, ...)`.

**Step 6 — Run PASS + regression :**

```bash
python3 -m pytest tests/test_sse_stream.py tests/ -v 2>&1 | tail -10
```

Expected : 2 PASS + zero regression.

**Step 7 — Commit :**

```bash
git add dashboard/sse_routes.py dashboard/app.py dashboard/tests/test_sse_stream.py
git commit -m "feat(dashboard): /api/cohort/stream SSE endpoint with snapshot+heartbeat"
```

---

**Continuation : voir `2026-05-15-dashboard-phase1-foundation-pt2.md` pour Tasks 5-9 (sync broadcast hook, tags HTTP routes, frontend EventSource swap, e2e test, final gate).**
