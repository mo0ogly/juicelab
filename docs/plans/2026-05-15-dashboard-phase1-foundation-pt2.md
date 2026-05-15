# Dashboard Phase 1 Foundation — Part 2 (Tasks 5-9)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. **Prerequisite:** Tasks 1-4 in `2026-05-15-dashboard-phase1-foundation.md` are DONE.

Continuation : sync broadcast hook, tags HTTP routes, frontend EventSource swap, e2e test, final gate.

---

## Task 5 — Broadcast hook in sync_routes.py

**Files:**
- Modify: `dashboard/sync_routes.py`
- Test: `dashboard/tests/test_sync_broadcasts.py` (NEW)

**Step 1 — Failing test :**

Create `dashboard/tests/test_sync_broadcasts.py`:

```python
"""sync POST event triggers sse_pubsub.publish (Phase 1)."""
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
    for m in ["app", "db", "sse_pubsub", "sse_routes", "sync_routes"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    return create_app()


def test_sync_publishes_to_pubsub(app):
    import sse_pubsub
    client = app.test_client()
    q = sse_pubsub.subscribe("M2-IA-2026")
    try:
        r = client.post("/api/sync", json={
            "cohort_id": "M2-IA-2026",
            "student_token": "tok123",
            "event_type": "solved",
            "challenge_key": "xss-stored",
            "client_ts": "2026-05-15T10:00:00Z",
            "data": {},
        })
        assert r.status_code == 201
        ev = q.get(timeout=1.0)
        assert ev["event_type"] == "solved"
        assert ev["student_token"] == "tok123"
    finally:
        sse_pubsub.unsubscribe("M2-IA-2026", q)
```

**Step 2 — Run FAIL :**

```bash
python3 -m pytest tests/test_sync_broadcasts.py -v
```

Expected : timeout queue.get (publish jamais appele).

**Step 3 — Modify `dashboard/sync_routes.py` :**

Add import at top :

```python
import sse_pubsub
```

Just before the final `return jsonify({"ok": True, "id": new_id}), 201` line :

```python
        try:
            sse_pubsub.publish(cohort, {
                "id": new_id,
                "cohort_id": cohort,
                "student_token": token,
                "event_type": payload["event_type"],
                "challenge_key": payload.get("challenge_key"),
                "client_ts": payload.get("client_ts"),
            })
        except Exception as exc:
            LOGGER.warning("sse publish failed for event=%s: %s", new_id, exc)
```

**Step 4 — Run PASS + regression :**

```bash
python3 -m pytest tests/test_sync_broadcasts.py tests/ -v 2>&1 | tail -10
```

Expected : 1 PASS + zero regression.

**Step 5 — Commit :**

```bash
git add dashboard/sync_routes.py dashboard/tests/test_sync_broadcasts.py
git commit -m "feat(dashboard/sync): broadcast each /api/sync event to SSE pubsub"
```

---

## Task 6 — Tags + notes HTTP API (CRUD)

**Files:**
- Create: `dashboard/tags_routes.py`
- Modify: `dashboard/app.py`
- Test: `dashboard/tests/test_tags_routes.py` (NEW)

**Step 1 — Failing test :**

Create `dashboard/tests/test_tags_routes.py`:

```python
"""HTTP CRUD for student_tag + student_note (Phase 1)."""
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
    for m in ["app", "db", "tags_routes"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    return create_app()


def _auth(app):
    c = app.test_client()
    c.set_cookie("teacher_session", "teacher-test-token-very-long-32chars!!")
    return c


def test_set_tag_requires_auth(app):
    c = app.test_client()
    r = c.post("/api/tag", json={"student_token": "x", "cohort_id": "c", "status": "a_voir"})
    assert r.status_code in (401, 403)


def test_set_then_get_tag(app):
    c = _auth(app)
    r1 = c.post("/api/tag", json={"student_token": "tok", "cohort_id": "M2-IA-2026", "status": "a_voir"})
    assert r1.status_code == 200
    r2 = c.get("/api/tag?student_token=tok&cohort=M2-IA-2026")
    assert r2.status_code == 200
    assert r2.json["status"] == "a_voir"
```

**Step 2 — Run FAIL :**

```bash
python3 -m pytest tests/test_tags_routes.py -v
```

Expected : 404 (no /api/tag).

**Step 3 — Create `dashboard/tags_routes.py` :**

```python
"""Teacher-only CRUD for per-student tags + free-form notes.

Tags : enum {a_voir, ok, absent, a_interroger, none}.
Notes : free text body <= 2000 chars.
Both keyed by (student_token, cohort_id)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from flask import Flask, Response, jsonify, request

from db import get_connection, set_tag, get_tag, set_note, get_note

ALLOWED_TAGS = {"a_voir", "ok", "absent", "a_interroger", "none"}
NOTE_MAX = 2000


def register_tags_routes(app: Flask, check_teacher_auth: Callable) -> None:

    @app.post("/api/tag")
    def set_student_tag() -> Response:
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        payload = request.get_json(silent=True) or {}
        token = str(payload.get("student_token", "")).strip()
        cohort = str(payload.get("cohort_id", "")).strip()
        status = str(payload.get("status", "")).strip()
        if not token or not cohort or status not in ALLOWED_TAGS:
            return jsonify({"error": "invalid tag payload"}), 400
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            set_tag(conn, token, cohort, status, now)
            conn.commit()
        return jsonify({"ok": True, "status": status}), 200

    @app.get("/api/tag")
    def get_student_tag() -> Response:
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        token = request.args.get("student_token", "").strip()
        cohort = request.args.get("cohort", "").strip()
        with get_connection() as conn:
            status = get_tag(conn, token, cohort) or "none"
        return jsonify({"status": status})

    @app.post("/api/note")
    def set_student_note() -> Response:
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        payload = request.get_json(silent=True) or {}
        token = str(payload.get("student_token", "")).strip()
        cohort = str(payload.get("cohort_id", "")).strip()
        body = str(payload.get("body", ""))[:NOTE_MAX]
        if not token or not cohort:
            return jsonify({"error": "invalid note payload"}), 400
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            set_note(conn, token, cohort, body, now)
            conn.commit()
        return jsonify({"ok": True})

    @app.get("/api/note")
    def get_student_note() -> Response:
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        token = request.args.get("student_token", "").strip()
        cohort = request.args.get("cohort", "").strip()
        with get_connection() as conn:
            body = get_note(conn, token, cohort)
        return jsonify({"body": body})
```

**Step 4 — Register in app.py (~ligne 582) :**

Import at top :

```python
from tags_routes import register_tags_routes
```

In `create_app()` after `register_sse_routes(...)` :

```python
register_tags_routes(app, _check_teacher_auth)
```

**Step 5 — Run PASS + regression :**

```bash
python3 -m pytest tests/test_tags_routes.py tests/ -v 2>&1 | tail -10
```

Expected : 2 PASS + zero regression.

**Step 6 — Commit :**

```bash
git add dashboard/tags_routes.py dashboard/app.py dashboard/tests/test_tags_routes.py
git commit -m "feat(dashboard): /api/tag and /api/note teacher-only CRUD"
```

---

## Task 7 — Frontend EventSource (replace polling)

**Files:**
- Modify: `dashboard/templates/dashboard.html`
- Test: `dashboard/tests/test_dashboard_html_sse.py` (NEW)

**Step 1 — Failing test :**

Create `dashboard/tests/test_dashboard_html_sse.py`:

```python
"""dashboard.html uses EventSource not setInterval polling (Phase 1)."""
from __future__ import annotations
import sys, pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASHBOARD_DB", str(tmp_path / "d.sqlite"))
    monkeypatch.setenv("DASHBOARD_TEACHER_TOKEN", "teacher-test-token-very-long-32chars!!")
    monkeypatch.setenv("DASHBOARD_PROOF_SECRET", "proof-test-token-very-long-32chars!")
    for m in ["app", "db"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    a = create_app()
    c = a.test_client()
    c.set_cookie("teacher_session", "teacher-test-token-very-long-32chars!!")
    c.post("/api/cohorts", json={"cohort_id": "M2-IA-2026", "label": "Test"})
    return c


def test_dashboard_html_uses_eventsource(client):
    r = client.get("/dashboard?cohort=M2-IA-2026")
    assert r.status_code == 200
    body = r.data.decode()
    assert "EventSource" in body
    assert "/api/cohort/stream" in body
    assert "setInterval(tick" not in body
```

**Step 2 — Run FAIL :**

```bash
python3 -m pytest tests/test_dashboard_html_sse.py -v
```

Expected : assertion error sur EventSource (toujours setInterval).

**Step 3 — Modify `dashboard/templates/dashboard.html` :**

Localiser le bloc autour lignes 395-420 contenant :

```js
function tick() { fetch('/api/cohort?cohort=' + ...) ... }
bindJournalPills();
setInterval(tick, REFRESH_MS);
tick();
```

Remplacer par :

```js
function applySnapshot(summary) {
  renderMatrix(summary);
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const ss = String(now.getSeconds()).padStart(2, '0');
  refreshTag.textContent = T('REFRESH_OK', { time: hh + ':' + mm + ':' + ss });
  autoTag.textContent = T('REFRESH_LIVE_LABEL');
  autoTag.classList.remove('off');
}

bindJournalPills();

const es = new EventSource('/api/cohort/stream?cohort=' + encodeURIComponent(COHORT));
es.addEventListener('snapshot', (e) => { try { applySnapshot(JSON.parse(e.data)); } catch (_) {} });
es.addEventListener('event', (e) => {
  // Phase 1 : on every event, re-fetch full snapshot. Phase 2 = delta application.
  fetch('/api/cohort?cohort=' + encodeURIComponent(COHORT), { credentials: 'include' })
    .then(r => r.json()).then(applySnapshot).catch(() => {});
});
es.onerror = () => {
  refreshTag.textContent = T('REFRESH_KO', { msg: 'SSE disconnected, auto-retry' });
  autoTag.textContent = T('REFRESH_TAG_KO');
  autoTag.classList.add('off');
};
```

Supprimer la ligne `const REFRESH_MS = 5000;` et toute la `function tick() { ... }` definition.

**Step 4 — Run PASS + regression :**

```bash
python3 -m pytest tests/test_dashboard_html_sse.py tests/ -v 2>&1 | tail -10
```

Expected : 1 PASS + zero regression (existing test_app_routes still PASS).

**Step 5 — Smoke manuel SSE round-trip :**

```bash
cd /home/fpizzi/juice/dashboard
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! python3 -c "
from app import create_app
a = create_app()
c = a.test_client()
c.set_cookie('teacher_session', 'teacher-test-token-very-long-32chars!!')
c.post('/api/cohorts', json={'cohort_id':'demo','label':'demo'})
r = c.get('/dashboard?cohort=demo')
assert r.status_code == 200
assert b'EventSource' in r.data
assert b'setInterval(tick' not in r.data
print('SMOKE OK')
"
```

**Step 6 — Commit :**

```bash
git add dashboard/templates/dashboard.html dashboard/tests/test_dashboard_html_sse.py
git commit -m "feat(dashboard/ui): swap polling for EventSource(/api/cohort/stream)"
```

---

## Task 8 — End-to-end pytest (event POST -> SSE deliver)

**Files:**
- Test: `dashboard/tests/test_phase1_e2e.py` (NEW)

**Step 1 — Integration test :**

Create `dashboard/tests/test_phase1_e2e.py`:

```python
"""End-to-end Phase 1 : POST /api/sync triggers SSE pubsub deliver."""
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
    for m in ["app", "db", "sse_pubsub", "sse_routes", "sync_routes"]:
        if m in sys.modules: del sys.modules[m]
    from app import create_app
    return create_app()


def test_post_sync_triggers_sse_event(app):
    import sse_pubsub
    q = sse_pubsub.subscribe("M2-IA-2026")
    try:
        client = app.test_client()
        r = client.post("/api/sync", json={
            "cohort_id": "M2-IA-2026",
            "student_token": "tok-e2e",
            "event_type": "solved",
            "challenge_key": "xss-stored",
            "client_ts": "2026-05-15T10:00:00Z",
            "data": {},
        })
        assert r.status_code == 201
        ev = q.get(timeout=1.0)
        assert ev["student_token"] == "tok-e2e"
        assert ev["event_type"] == "solved"
        assert ev["challenge_key"] == "xss-stored"
    finally:
        sse_pubsub.unsubscribe("M2-IA-2026", q)
```

**Step 2 — Run :**

```bash
python3 -m pytest tests/test_phase1_e2e.py tests/ -v 2>&1 | tail -10
```

Expected : 1 PASS + zero regression. Total ~215 tests.

**Step 3 — Commit :**

```bash
git add dashboard/tests/test_phase1_e2e.py
git commit -m "test(dashboard): e2e POST /api/sync triggers SSE pubsub broadcast"
```

---

## Task 9 — Final gate + doc update

**Step 1 — Full pytest :**

```bash
cd /home/fpizzi/juice/dashboard
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! python3 -m pytest tests/ -q --no-header 2>&1 | tail -5
```

Expected : 215+ passed, zero failed.

**Step 2 — Smoke complet :**

```bash
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! python3 -c "
from app import create_app
a = create_app()
c = a.test_client()
c.set_cookie('teacher_session', 'teacher-test-token-very-long-32chars!!')
c.post('/api/cohorts', json={'cohort_id':'demo','label':'demo'})
print('dashboard:', c.get('/dashboard?cohort=demo').status_code)
print('stream:', c.get('/api/cohort/stream?cohort=demo', buffered=False).status_code)
print('tag set:', c.post('/api/tag', json={'student_token':'t1','cohort_id':'demo','status':'ok'}).status_code)
print('tag get:', c.get('/api/tag?student_token=t1&cohort=demo').json)
print('Phase 1 SMOKE OK')
" 2>&1 | grep -v INFO
```

**Step 3 — Update PDCA DASHBOARD.md :**

Append to `pdca/dashboard-ui-redesign/DASHBOARD.md` Cycles table :

```markdown
| 002 (phase 1) | 2026-05-15 | TBD audit | Foundation SSE+tags livree | 0 — Phase 2 (signal-to-noise) au cycle 003 |
```

**Step 4 — Commit :**

```bash
git add pdca/dashboard-ui-redesign/DASHBOARD.md
git commit -m "docs(pdca): Phase 1 foundation livree, queue Phase 2 cycle 003"
```

---

## Summary

| Task | Tests added | Notes |
|------|-------------|-------|
| 1 | 3 | schema migration tags+notes+alerts |
| 2 | 4 | DB helpers CRUD |
| 3 | 2 | pubsub primitive |
| 4 | 2 | SSE endpoint |
| 5 | 1 | sync broadcast hook |
| 6 | 2 | tags HTTP routes |
| 7 | 1 | frontend EventSource |
| 8 | 1 | e2e integration |
| 9 | 0 | doc update only |

**Total : 16 tests Phase 1** (objectif >= +10 atteint).

**File-size compliance checks :**
- `db.py` actuellement 563 → +50 lignes (helpers Phase 1) → 613. OK.
- `app.py` actuellement 800 → Task 4+6 ajoutent 2 imports + 2 register lines. Si depasse 800, refactor : extraire la chaine `register_*_routes` (~ligne 582) en `_register_all_routes(app, ...)` helper.
- Nouveaux fichiers : tous < 200 lignes.

**CSP unchanged check :** `connect-src 'self'` autorise deja SSE same-origin. Zero CSP change.

**FCP unchanged check :** SSE = connexion persistante, pas asset render-blocking. Zero impact FCP.

**Risks recap :**
- app.py boundary 800 lignes — refactor helper en backup
- Single-worker assumption (in-memory pubsub) — documenter dans README dashboard pour deploy
- Test concurrency : `sse_pubsub` est module-level, isole entre tests via `del sys.modules` dans fixture

---

Plan complete and saved to `docs/plans/2026-05-15-dashboard-phase1-foundation.md` + `2026-05-15-dashboard-phase1-foundation-pt2.md`. Two execution options :

**1. Subagent-Driven (this session)** — Je dispatch un subagent frais par task, review entre tasks, iteration rapide. REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`.

**2. Parallel Session (separate)** — Tu ouvres une nouvelle session avec `superpowers:executing-plans`, batch execution avec checkpoints, je reste libre pour autre chose.

Which approach?
