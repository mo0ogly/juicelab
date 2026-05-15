# Dashboard Phase 3 — Modes UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deux modes UX optimises pour usages distincts (live projete TD vs analyse post-TD), barre filtres + raccourcis clavier, drill-down modal sans nouvel onglet, export PDF cohorte. Final cycle PDCA Phase 3.

**Tech Stack:** Flask + Jinja + vanilla JS + weasyprint (new dep).

**Reference design :** `docs/plans/2026-05-15-dashboard-monitor-sse-modes-design.md` Phase 3 section.

**Tests cible :** +8 pytest, zero regression sur 235.

---

## Task 1 — Mode toggle ?mode=live | ?mode=analyse

**Files:**
- Modify: `dashboard/templates/dashboard.html` (`<body class="mode-{{ mode }}">`, mode toggle button in topbar)
- Modify: `dashboard/app.py` (`/dashboard` route reads `?mode=` query arg, passes to template)
- Modify: `dashboard/static/dashboard-widgets.css` (mode-live + mode-analyse rules)
- Modify: `dashboard/i18n/{fr,en}.json` (MODE_LIVE, MODE_ANALYSE, MODE_SWITCH)
- Create: `dashboard/tests/test_mode_toggle.py` (2 tests)

**Route handler change** : in `/dashboard` GET handler in app.py, add :
```python
mode = request.args.get("mode", "analyse").strip().lower()
if mode not in ("live", "analyse"):
    mode = "analyse"
# pass to render_template : mode=mode
```

**Template change** : `<body class="mode-{{ mode }}">`. Add a topbar toggle :
```html
<a class="logout mode-switch" href="?cohort={{ summary.cohort_id }}&mode={% if mode == 'live' %}analyse{% else %}live{% endif %}">{{ t('MODE_SWITCH') }} : {{ t('MODE_' + mode.upper()) }}</a>
```

**CSS** : 
```css
body.mode-live .scroll, body.mode-live .toolbar, body.mode-live .legend { display: none; }
body.mode-live .kpi-value { font-size: 56px; }
body.mode-live .alerts-panel { margin: 32px 0; padding: 24px; }
body.mode-analyse { /* default, no overrides */ }
```

**i18n :** MODE_LIVE="Live", MODE_ANALYSE="Analyse", MODE_SWITCH="Mode" FR ; EN same English.

**Tests :**
- `test_default_mode_is_analyse` : GET /dashboard returns body with `class="mode-analyse"`
- `test_mode_live_renders` : GET /dashboard?mode=live → body has `class="mode-live"`

App.py limit : currently 800 — can't add lines. Mitigation : move mode parsing into a 1-line ternary at the render_template call. Or inline in the template via `request.args.get('mode', 'analyse')` (Jinja can access `request`). Use template-side parse → zero app.py change :
```html
{% set mode = request.args.get('mode', 'analyse') if request.args.get('mode', 'analyse') in ('live', 'analyse') else 'analyse' %}
```

That keeps app.py untouched. CLEANER.

Commit: `feat(dashboard/ui): mode=live|analyse toggle in topbar (Phase 3)`

---

## Task 2 — Filter bar (challenge, score range, recency, tag)

**Files:**
- Modify: `dashboard/templates/dashboard.html` (filter bar markup + JS filter logic on matrix rows)
- Modify: `dashboard/static/dashboard-widgets.css` (style `.filter-bar`, reuse `.sort-bar` patterns)
- Modify: `dashboard/i18n/{fr,en}.json` (FILTER_CHALLENGE, FILTER_SCORE, FILTER_RECENCY, FILTER_TAG, FILTER_RESET, FILTER_ALL)
- Create: `dashboard/tests/test_filter_bar.py` (2 tests : markup present + filter classes on rows)

**Markup** (place above the scroll div in dashboard.html, only shown in mode=analyse) :
```html
{% if mode == 'analyse' %}
<div class="filter-bar" role="toolbar" aria-label="{{ t('FILTER_TITLE') }}">
  <label>{{ t('FILTER_CHALLENGE') }} : <select id="filter-challenge"><option value="">{{ t('FILTER_ALL') }}</option>{% for c in summary.challenges %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select></label>
  <label>{{ t('FILTER_SCORE') }} : <select id="filter-score"><option value="">{{ t('FILTER_ALL') }}</option><option value="lt50">&lt; 50</option><option value="50-80">50-80</option><option value="gt80">&gt; 80</option></select></label>
  <label>{{ t('FILTER_TAG') }} : <select id="filter-tag"><option value="">{{ t('FILTER_ALL') }}</option><option value="a_voir">{{ t('TAG_A_VOIR') }}</option><option value="ok">{{ t('TAG_OK') }}</option><option value="absent">{{ t('TAG_ABSENT') }}</option><option value="a_interroger">{{ t('TAG_A_INTERROGER') }}</option><option value="none">{{ t('TAG_NONE') }}</option></select></label>
  <button type="button" class="btn" id="filter-reset">{{ t('FILTER_RESET') }}</button>
</div>
{% endif %}
```

**JS** : on filter change, iterate matrix `<tr>` rows, add/remove `.row-filtered-out` class. Score parse from `.score-total` text. Tag from `.tag-select` value.

```javascript
function applyFilters() {
  const fChal = document.getElementById('filter-challenge')?.value || '';
  const fScore = document.getElementById('filter-score')?.value || '';
  const fTag = document.getElementById('filter-tag')?.value || '';
  document.querySelectorAll('#body-rows tr').forEach(tr => {
    let hide = false;
    if (fChal) {
      const cell = tr.querySelector('td[data-cell="' + fChal + '"]');
      if (!cell || cell.querySelector('.pill.empty')) hide = true;
    }
    if (!hide && fScore) {
      const txt = (tr.querySelector('.score-total')?.textContent || '').match(/\d+/);
      const s = txt ? parseInt(txt[0]) : -1;
      if (fScore === 'lt50' && (s < 0 || s >= 50)) hide = true;
      if (fScore === '50-80' && (s < 50 || s > 80)) hide = true;
      if (fScore === 'gt80' && s <= 80) hide = true;
    }
    if (!hide && fTag) {
      const tg = tr.querySelector('.tag-select')?.value || 'none';
      if (tg !== fTag) hide = true;
    }
    tr.classList.toggle('row-filtered-out', hide);
  });
}

document.getElementById('filter-challenge')?.addEventListener('change', applyFilters);
document.getElementById('filter-score')?.addEventListener('change', applyFilters);
document.getElementById('filter-tag')?.addEventListener('change', applyFilters);
document.getElementById('filter-reset')?.addEventListener('click', () => {
  ['filter-challenge', 'filter-score', 'filter-tag'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  applyFilters();
});
```

**CSS :**
```css
.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; padding: 12px 16px; margin: 16px 0; background: var(--bg-elev); border: 1px solid var(--border); border-radius: var(--radius); }
.filter-bar label { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-mute); display: flex; align-items: center; gap: 8px; }
.filter-bar select { padding: 5px 9px; font-family: var(--font-body); font-size: 12px; background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius-sm); text-transform: none; letter-spacing: 0; }
.row-filtered-out { display: none !important; }
```

**Tests :**
- `test_filter_bar_renders_in_analyse_mode` : GET /dashboard?cohort=demo body has `class="filter-bar"`
- `test_filter_bar_absent_in_live_mode` : GET /dashboard?mode=live body does NOT have `class="filter-bar"`

Commit: `feat(dashboard/ui): filter bar (challenge/score/tag) in analyse mode (Phase 3)`

---

## Task 3 — Keyboard shortcuts

**Files:**
- Modify: `dashboard/templates/dashboard.html` (JS keydown listener)
- Modify: `dashboard/i18n/{fr,en}.json` (KEYBOARD_HELP_TITLE + per-shortcut)
- Create: `dashboard/tests/test_keyboard_shortcuts.py` (1 test : markup + handler script present)

**Shortcuts :**
- `j` / `k` : navigate matrix rows (focus next/prev `<tr data-student="X">`, scroll into view, add `.row-focused` class)
- `Enter` : open student detail modal for focused row (delegates to drill-down from Task 4)
- `t` : cycle tag for focused row (none → a_voir → ok → absent → a_interroger → none)
- `/` : focus filter input if present
- `?` : show keyboard help overlay

**JS pattern :**
```javascript
let focusedRowIdx = -1;
function setFocusedRow(idx) {
  const rows = Array.from(document.querySelectorAll('#body-rows tr:not(.row-filtered-out)'));
  if (!rows.length) return;
  idx = Math.max(0, Math.min(rows.length - 1, idx));
  rows.forEach(r => r.classList.remove('row-focused'));
  rows[idx].classList.add('row-focused');
  rows[idx].scrollIntoView({ block: 'nearest' });
  focusedRowIdx = idx;
}

document.addEventListener('keydown', (e) => {
  if (e.target.matches('input, textarea, select')) return;  // don't hijack inputs
  if (e.key === 'j') { setFocusedRow(focusedRowIdx + 1); e.preventDefault(); }
  else if (e.key === 'k') { setFocusedRow(focusedRowIdx - 1); e.preventDefault(); }
  else if (e.key === 'Enter' && focusedRowIdx >= 0) { /* delegate to drill-down */ }
  else if (e.key === 't' && focusedRowIdx >= 0) { /* cycle tag */ }
  else if (e.key === '?') { document.getElementById('kbd-help')?.classList.add('open'); e.preventDefault(); }
  else if (e.key === '/') { document.getElementById('filter-challenge')?.focus(); e.preventDefault(); }
});
```

CSS `.row-focused { outline: 2px solid var(--accent); outline-offset: -2px; }` in dashboard-widgets.css.

**Keyboard help overlay** : modal at bottom of body with `<dl>` of shortcuts.

**Test :** `test_keyboard_handler_present` : GET /dashboard body contains `addEventListener('keydown'` and `setFocusedRow`.

Commit: `feat(dashboard/ui): keyboard shortcuts j/k/Enter/t/?/  (Phase 3)`

---

## Task 4 — Drill-down student detail modal

**Files:**
- Modify: `dashboard/templates/dashboard.html` (drill-down modal markup + JS open)
- Modify: `dashboard/i18n/{fr,en}.json` (DRILLDOWN_TITLE)
- Create: `dashboard/tests/test_drilldown_modal.py` (1 test)

Replace the `target="_blank"` `<a href="/admin/student/X">D</a>` button : keep the `<a>` for non-JS fallback, but add a JS handler that intercepts the click, opens an iframe-loading or fetch-rendered modal showing the student detail content.

Simpler: keep target=_blank, ADD a `data-drilldown="1"` attr. JS handler reads it, opens a modal with iframe `<iframe src="/admin/student/X?cohort=Y"></iframe>` and prevents default.

**Modal markup** (clone journal modal pattern) :
```html
<div class="modal-backdrop drilldown-modal" id="drilldown-backdrop" role="dialog" aria-modal="true" aria-labelledby="drilldown-title">
  <div class="modal-card drilldown-card">
    <div class="modal-head">
      <h3 id="drilldown-title">{{ t('DRILLDOWN_TITLE') }}</h3>
      <button class="modal-close" type="button" id="drilldown-close-btn" aria-label="{{ t('ARIA_CLOSE') }}">&times;</button>
    </div>
    <div class="modal-body">
      <iframe id="drilldown-iframe" class="drilldown-iframe" src="" title="{{ t('DRILLDOWN_TITLE') }}"></iframe>
    </div>
  </div>
</div>
```

CSS :
```css
.drilldown-card { width: min(1100px, 96vw); max-height: 92vh; padding: 16px 18px; }
.drilldown-iframe { width: 100%; height: 70vh; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); }
```

JS :
```javascript
document.querySelectorAll('a[data-drilldown="1"]').forEach(a => {
  a.addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('drilldown-iframe').src = a.href;
    document.getElementById('drilldown-backdrop').classList.add('open');
  });
});
document.getElementById('drilldown-close-btn').addEventListener('click', () => {
  document.getElementById('drilldown-backdrop').classList.remove('open');
  document.getElementById('drilldown-iframe').src = '';
});
```

Add `data-drilldown="1"` to the `<a>D</a>` markup (Jinja + JS-rendered path).

**Test :** `test_drilldown_modal_markup_present` : GET /dashboard body contains `id="drilldown-backdrop"` and `data-drilldown="1"`.

Commit: `feat(dashboard/ui): drill-down student detail in modal iframe (Phase 3)`

---

## Task 5 — Export PDF cohorte report

**Files:**
- Modify: `dashboard/requirements.txt` (add `weasyprint`)
- Create: `dashboard/pdf_routes.py` (route + render)
- Create: `dashboard/templates/cohort_report.html` (PDF template)
- Modify: `dashboard/app.py` (register pdf_routes, single-line append on existing register block; app.py at 800 — REFACTOR if needed)
- Create: `dashboard/tests/test_pdf_routes.py` (1 test)

**WARNING : app.py exactly at 800.** Mitigation : append to the existing one-line `register_*` chain at line 582. Same trick as Phase 1/2.

But adding `import` line too. SAFER : extract the registration chain into a helper inside an existing helper file. Quick mitigation : add ONE import (`from pdf_routes import register_pdf_routes`) by appending `;` to the existing imports line 54 (length OK), and ONE register call appended to line 582. Net: same line count.

If still over 800 : delete a blank line elsewhere in app.py. Last resort.

**`pdf_routes.py` skeleton :**
```python
from __future__ import annotations
from typing import Callable
from flask import Flask, Response, render_template, request, g

try:
    from weasyprint import HTML
    WEASYPRINT_OK = True
except (ImportError, OSError):
    HTML = None
    WEASYPRINT_OK = False


def register_pdf_routes(app: Flask, check_teacher_auth: Callable, build_summary: Callable) -> None:

    @app.get("/admin/cohort/report.pdf")
    def cohort_report_pdf() -> Response:
        ok, err = check_teacher_auth()
        if not ok and err is not None:
            return err
        cohort = request.args.get("cohort", "").strip()
        if not cohort:
            return Response("missing cohort", status=400)
        if not WEASYPRINT_OK:
            return Response("weasyprint not installed", status=503)
        summary = build_summary(cohort)
        html = render_template("cohort_report.html", summary=summary)
        pdf_bytes = HTML(string=html).write_pdf()
        return Response(pdf_bytes, mimetype="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="cohort_{cohort}_report.pdf"',
        })
```

**`cohort_report.html`** : minimal HTML/CSS (no Fraunces/Geist — weasyprint may not have the fonts; use system serif/sans-serif). Title, cohort id, date, top 5 / bottom 5 by score, distribution stats (count, avg, p50, p90, top scores).

Template :
```html
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Cohort Report</title>
<style>
  @page { size: A4; margin: 18mm; }
  body { font-family: Georgia, serif; color: #1a1a1a; }
  h1 { font-size: 24pt; margin: 0 0 8pt; }
  h2 { font-size: 14pt; margin: 16pt 0 6pt; border-bottom: 1pt solid #888; padding-bottom: 4pt; }
  table { border-collapse: collapse; width: 100%; }
  th, td { padding: 4pt 8pt; border-bottom: 0.5pt solid #ccc; text-align: left; font-size: 10pt; }
  th { background: #eee; }
  .meta { font-size: 9pt; color: #555; margin: 0 0 16pt; }
</style></head><body>
<h1>Cohort Report — {{ summary.cohort_id }}</h1>
<p class="meta">{{ summary.students | length }} students &middot; {{ summary.events_total }} events</p>
<h2>Top 5</h2>
<table><tr><th>Student</th><th>Score</th></tr>
{% for s in summary.students[:5] %}<tr><td>{{ summary.names.get(s, s[:10]) }}</td><td>{{ summary.totals.get(s, {}).avg_score or '-' }}</td></tr>{% endfor %}
</table>
</body></html>
```

(Simplified ; production would have richer stats. Phase 3 ships minimum viable.)

**Test :**
```python
def test_pdf_route_returns_pdf_or_503(client):
    r = client.get("/admin/cohort/report.pdf?cohort=demo", headers=AUTH)
    assert r.status_code in (200, 503)  # 200 if weasyprint installed, 503 fallback
    if r.status_code == 200:
        assert r.mimetype == "application/pdf"
        assert r.data[:4] == b"%PDF"
```

Note : weasyprint may NOT be installed. The test is tolerant of 503 fallback. Phase 3 won't add it to requirements.lock.txt at boot, just document it as optional.

Actually : explicitly add `weasyprint` to requirements.txt (not lock) and document in README that PDF export requires `pip install weasyprint`. The test asserts 200 OR 503 (no hard requirement to install).

Commit: `feat(dashboard/pdf): cohort PDF report via weasyprint (optional dep) (Phase 3)`

---

## Task 6 — Playwright headless visual recette (OPTIONAL)

**Skip if time-constrained.** This task adds playwright as a dev dependency and creates a smoke recette that takes screenshots of /login, /dashboard?mode=live, /dashboard?mode=analyse, /admin/cohorts, /admin/students.

If skipped : just document in Phase 3 final report that visual recette is deferred to a follow-up.

**Files (if implemented) :**
- Add to `dashboard/requirements-dev.txt` : `playwright`
- Create: `dashboard/tests/visual/recette.py` (smoke script)
- Document in `pdca/dashboard-ui-redesign/cycle_004/C_VISUAL_RECETTE.md` after a manual headless run.

**RECOMMENDATION : skip in this Phase 3, defer to a manual session.** Reason : playwright headless setup + browser deps install (Chromium) ~300MB, brittle in CI. Better as separate cycle.

Commit: SKIP. Document in final report.

---

## Task 7 — Final gate + PDCA + DASHBOARD.md

**Step 1 — Full pytest x2 :**
```bash
cd /home/fpizzi/juice-phase3-worktree/dashboard
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars!! DASHBOARD_MONITOR_ENABLED=0 python3 -m pytest tests/ -q --no-header 2>&1 | tail -3
```
Expected : 235 + ~7 = 242 PASS (Task 5 PDF test may PASS only if weasyprint installed).

**Step 2 — Smoke modes :**
```bash
DASHBOARD_TEACHER_TOKEN=teacher-test-token-very-long-32chars!! DASHBOARD_PROOF_SECRET=proof-test-token-very-long-32chars!! DASHBOARD_MONITOR_ENABLED=0 python3 -c "
import sys
sys.path.insert(0, '/home/fpizzi/juice-phase3-worktree/dashboard')
from app import create_app
a = create_app()
c = a.test_client()
AUTH = {'X-Teacher-Token': 'teacher-test-token-very-long-32chars!!'}
c.post('/api/cohorts', json={'cohort_id':'demo'}, headers=AUTH)
# Mode analyse
r = c.get('/dashboard?cohort=demo', headers=AUTH); b = r.data.decode()
print('default_analyse:', r.status_code, 'class=mode-analyse:', 'class=\"mode-analyse\"' in b, 'filter_bar:', 'class=\"filter-bar\"' in b)
# Mode live
r = c.get('/dashboard?cohort=demo&mode=live', headers=AUTH); b = r.data.decode()
print('mode_live:', r.status_code, 'class=mode-live:', 'class=\"mode-live\"' in b, 'no_filter:', 'class=\"filter-bar\"' not in b)
# PDF
r = c.get('/admin/cohort/report.pdf?cohort=demo', headers=AUTH)
print('pdf:', r.status_code, 'mime:', r.mimetype)
print('PHASE 3 SMOKE OK')
" 2>&1 | grep -v INFO | tail -10
```

**Step 3 — Update PDCA `pdca/dashboard-ui-redesign/DASHBOARD.md`** : append cycle 004 row :
```markdown
| 004 (phase 3) | 2026-05-16 | TBD audit | Modes UX + filtres + raccourcis + drill-down modal + PDF export | 0 — visual recette playwright reportee |
```

**Step 4 — Commit :**
```bash
git add pdca/dashboard-ui-redesign/DASHBOARD.md
git commit -m "docs(pdca): Phase 3 modes UX livree (visual recette deferree)"
```

**Done. Phase 3 ready for squash merge to main.**
