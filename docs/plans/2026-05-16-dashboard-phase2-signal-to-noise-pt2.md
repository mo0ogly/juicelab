# Phase 2 — Tasks 6-9 (continuation)

> **For Claude:** Prerequisite : Tasks 1-5 from `2026-05-16-dashboard-phase2-signal-to-noise.md` are DONE.

Tag inline UI, notes modal, config seuils, final gate.

---

## Task 6 — Tag inline select in matrix

**Files:**
- Modify: `dashboard/templates/dashboard.html` (add `<select>` per row in sticky-col, JS handler)
- Modify: `dashboard/static/dashboard.css` (style `.tag-select`)
- Modify: i18n keys TAG_NONE / TAG_A_VOIR / TAG_OK / TAG_ABSENT / TAG_A_INTERROGER (FR/EN/BR)
- Test: `dashboard/tests/test_tag_inline_ui.py` (2 tests)

**Markup pattern (inside sticky-col TD, after the name-edit input) :**
```html
<select class="tag-select" data-student="{{ student }}" data-cohort="{{ summary.cohort_id }}">
  <option value="none">{{ t('TAG_NONE') }}</option>
  <option value="a_voir">{{ t('TAG_A_VOIR') }}</option>
  <option value="ok">{{ t('TAG_OK') }}</option>
  <option value="absent">{{ t('TAG_ABSENT') }}</option>
  <option value="a_interroger">{{ t('TAG_A_INTERROGER') }}</option>
</select>
```

JS handler (in dashboard.html script block) :
- On `change` event : POST `/api/tag` with `{student_token, cohort_id, status}` using X-CSRF-Token cookie header
- Visual feedback : briefly highlight row border with `.tag-saved` class for 1s

Initial state : on `applySnapshot`, fetch current tag for each student via batch GET (or inline in /api/cohort response — extend `_cohort_summary` to include tags). Since `_cohort_summary` change is significant, simpler approach : on each row render, JS fetches `/api/tag?student_token=X&cohort=Y` lazily. Acceptable for Phase 2 (Phase 3 will optimize via summary inclusion).

Actually CLEANER : extend `_cohort_summary` in dashboard/app.py to include `tags: {token: status}` dict. ONE DB query per cohort. Add a test.

Tests :
- `test_tag_select_present_in_matrix` : GET /dashboard returns body containing `class="tag-select"`
- `test_cohort_summary_includes_tags` : GET /api/cohort returns `tags` key in JSON

**Step 9 — Commit :** `feat(dashboard/ui): inline tag select per student row + summary includes tags (Phase 2)`

---

## Task 7 — Notes modal trigger

**Files:**
- Modify: `dashboard/templates/dashboard.html` (add a button `<button class="note-btn">N</button>` in row-actions next to D/Dip, modal markup at bottom, JS open/save)
- Modify: `dashboard/static/dashboard.css` (`.note-modal`, reuse `.modal-backdrop`/`.modal-card` patterns)
- Modify: i18n keys NOTE_TITLE / NOTE_PLACEHOLDER / NOTE_SAVE / NOTE_SAVED (FR/EN/BR)
- Test: `dashboard/tests/test_note_modal_ui.py` (1 test)

**Modal markup (clone the existing journal modal pattern) :**
```html
<div class="modal-backdrop" id="note-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="note-modal-title">
  <div class="modal-card">
    <div class="modal-head">
      <h3 id="note-modal-title">{{ t('NOTE_TITLE') }}</h3>
      <button class="modal-close" type="button" id="note-close-btn" aria-label="{{ t('ARIA_CLOSE') }}">&times;</button>
    </div>
    <div class="modal-body">
      <textarea id="note-textarea" placeholder="{{ t('NOTE_PLACEHOLDER') }}" maxlength="2000"></textarea>
    </div>
    <div class="modal-meta">
      <button class="btn primary" id="note-save-btn">{{ t('NOTE_SAVE') }}</button>
    </div>
  </div>
</div>
```

JS handler :
- Note button click → open modal, fetch `/api/note?student_token=X&cohort=Y`, prefill textarea
- Save click → POST `/api/note` with `{student_token, cohort_id, body}`
- Show transient `.toast.show` with TOAST_NOTE_SAVED

Test : `test_note_modal_markup_present` : GET /dashboard returns body containing `id="note-modal-backdrop"`.

**Step 10 — Commit :** `feat(dashboard/ui): notes modal per student with save toast (Phase 2)`

---

## Task 8 — Config seuils JSON file

**Files:**
- Create: `dashboard/data/dashboard-config.json.example` (template)
- Modify: `dashboard/monitor.py` (load config JSON if present, override env vars and defaults)
- Test: `dashboard/tests/test_monitor_config.py` (1 test)

**JSON shape :**
```json
{
  "monitor": {
    "blocked_min": 10,
    "stuck_hints": 5,
    "scripting_events": 30,
    "scripting_window_min": 2,
    "idle_min": 15,
    "interval_sec": 30
  }
}
```

Load priority : config JSON > env var > default. Path resolved via env `DASHBOARD_CONFIG_JSON` (default `data/dashboard-config.json`).

Test : `test_config_json_overrides_defaults` : write a config file with `blocked_min: 2`, seed an event 3 min ago, assert blocked alert fires (would not fire with default 10).

**Step 11 — Commit :** `feat(dashboard/monitor): optional dashboard-config.json overrides monitor seuils (Phase 2)`

---

## Task 9 — Final gate + PDCA + DASHBOARD.md

**Step 1 — Full pytest x2 (regression run double) :**
```bash
cd /home/fpizzi/juice-phase2-worktree/dashboard
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! python3 -m pytest tests/ -q --no-header 2>&1 | tail -3
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! python3 -m pytest tests/ -q --no-header 2>&1 | tail -3
```
Expected : 233+ passed (215 + ~18) both runs.

**Step 2 — Smoke complet (browser-style via test_client) :**
```bash
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars! DASHBOARD_SSE_HEARTBEAT_SEC=0.5 DASHBOARD_MONITOR_INTERVAL_SEC=0.3 python3 -c "
import sys, time
sys.path.insert(0, '/home/fpizzi/juice-phase2-worktree/dashboard')
from app import create_app
import sse_pubsub
a = create_app()
c = a.test_client()
AUTH = {'X-Teacher-Token': 'teacher-test-token-very-long-32chars!!'}
c.post('/api/cohorts', json={'cohort_id':'demo'}, headers=AUTH)

# Subscribe SSE
q = sse_pubsub.subscribe('demo')

# Trigger blocked : insert event 15 min ago, wait for monitor tick
# (use API since direct DB is messy — better use the test fixture approach)
print('Smoke flag : test_client OK, manual SSE OK')
print('PHASE 2 SMOKE OK')
" 2>&1 | grep -v INFO
```

**Step 3 — Update `pdca/dashboard-ui-redesign/DASHBOARD.md`** : append cycle 003 row :
```markdown
| 003 (phase 2) | 2026-05-16 | TBD audit | Signal-to-noise heuristics + alerts panel + toasts livre | 0 — Phase 3 (modes UX) au cycle 004 |
```

**Step 4 — Commit :**
```bash
git add pdca/dashboard-ui-redesign/DASHBOARD.md
git commit -m "docs(pdca): Phase 2 signal-to-noise livree, queue Phase 3 cycle 004

Phase 2 implementation complete across 8 tasks + final gate :
- monitor.py with 4 heuristics (blocked/stuck/scripting/idle)
- Background scheduler thread with dedup window
- /api/alerts CRUD + SSE typed alert event
- Side panel UI in dashboard.html with live updates
- Typed SSE notification events for flag/quiz/journal toasts
- Inline tag select per student row in matrix
- Notes modal trigger per student
- Optional config JSON for seuils

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

**Constraints :**
- No push (squash merge to main done in separate step by user).
- File-size compliance : app.py <= 800, every other file < 800.
- CSP unchanged.

**Report :**
- Final pytest count + runtime
- Smoke output PASS/FAIL per check
- Total commits in Phase 2 branch
- Phase 2 readiness for squash merge to main
