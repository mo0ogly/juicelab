# PDCA Cycle 005 — Gap Report (audit Phases 1+2+3)

**Date :** 2026-05-16
**Scope :** main HEAD `c6fe1ad` apres squash merge des 3 phases.
**Baseline :** 242 pytest pass, 5.9s, file-size 800 cap respecte.

## Synthese

| Domaine | Score | Findings |
|---------|-------|----------|
| architecture_coherence | 78/100 | 1 CRITICAL (CSP frame-ancestors casse drill-down), 1 HAUTE (race persist+SSE), 3 MOYENNE |
| security_csp | 74/100 | 1 CRITICAL (idem), 2 HAUTE (style-src unsafe-inline, JS sans SRI), 2 MOYENNE |
| performance | 72/100 | 2 CRITICAL (monitor full-scan, frontend re-fetch every event), 2 MOYENNE, 1 BASSE |
| code_quality | 72/100 | 1 CRITICAL (800-line saturation app.py+dashboard.html), 1 HAUTE (BR i18n debt), 3 MOYENNE/BASSE |
| i18n_a11y_tests | 91/100 | 1 HAUTE (BR claim mismatch), 4 MOYENNE/BASSE (focus mgmt, contrast idle, playwright deferred) |

**Score global pondere : 77/100** (objectif >=80 manque legerement, bloque par 1 vrai CRITICAL non detecte par tests)

## Findings CRITICAL (verification independante effectuee)

### F1 — CSP `frame-ancestors 'none'` casse le drill-down Phase 3 (CONFIRME)

**Severite :** CRITICAL (feature shipped Phase 3 ne fonctionne pas en browser reel)

**Verification :** 
```
$ curl /admin/student/X → Content-Security-Policy: ... frame-ancestors 'none'
```
Le drill-down ouvre `<iframe src="/admin/student/X">`. Le navigateur applique CSP de la PAGE EMBARQUEE (student detail). `frame-ancestors 'none'` interdit l'embed → iframe vide.

Tests existants verifient SEULEMENT la presence du markup `id="drilldown-backdrop"`, jamais le rendu effectif de l'iframe. Gap de test.

**Fix :** `dashboard/app.py:621` :
```python
# Avant
"connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
# Apres
"connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'"
```
`'self'` autorise meme-origine (dashboard embedant son propre student detail) sans ouvrir vers d'autres origines. Effort : 1 char. Test playwright en cycle 006 pour eviter regression.

## Findings HAUTE

### F2 — Monitor compute_alerts full-table scan (perf)
**Fichier :** `dashboard/monitor.py:93-97` — `SELECT * FROM events WHERE cohort_id=? ORDER BY id`. 10k events × 30s tick = 333k rows/heure.
**Fix :** ajouter `AND client_ts > datetime('now', '-1 hour')`. 99% reduction.

### F3 — SSE event triggers full /api/cohort re-fetch (perf)
**Fichier :** `dashboard/templates/dashboard.html:~648` — 30 events × 5/min = 150 fetches/min wasteful. Phase 2 deferred to Phase 3, Phase 3 didn't address.
**Fix immediat :** debounce 2s. **Fix propre :** delta patching protocol (cycle 006).

### F4 — File-size saturation app.py + dashboard.html (blocking future)
**Files :** `app.py` 800 / `dashboard.html` 800 = hook empeche tout add. Phase 4 ne peut pas shipper sans refactor prealable.
**Fix :** extraire `_cohort_summary` / `_validate_event` / CTFd dans modules helpers ; decomposer dashboard.html en partials.

### F5 — BR i18n claim vs reality
**Files :** `CLAUDE.md` declare trilingual FR/EN/BR, `dashboard/i18n_helpers.py:28` `SUPPORTED = ("fr", "en")`. Tests `HELP_S2_BODY` mentionne BR.
**Fix :** soit retirer mention BR de CLAUDE.md, soit creer `i18n/br.json` + ajouter "br" au tuple. Decision produit.

### F6 — `style-src 'unsafe-inline'` permet inline `<style>`
**File :** `app.py:618` — pre-existant, pas introduit par Phases 1-3. Inline `<style>` blocs dans login.html / diploma.html / cohorts.html. Backlog refactor cycle 006.

### F7 — Pas de SRI sur `dashboard-keyboard.js` + `dashboard-drilldown.js`
**Files :** `dashboard.html` + 2 JS Phase 3. Tradeoff documente : app.py au cap 800, ajouter SRI = depasser. Mitigation : `script-src 'self' + nonce` couvre origin trust.

## Findings MOYENNE

### F8 — monitor.persist_alert non-atomic (insert DB puis publish SSE)
**File :** `dashboard/monitor.py:192-219` — si SSE publish fail apres insert, subscriber SSE rate l'event mais REST /api/alerts le revele. Dedup window protege.
**Fix :** swap ordre (publish d'abord) ou try/finally. <10 min.

### F9 — Aucune garde runtime gunicorn multi-worker
**Files :** `sse_pubsub.py`, `monitor.py` — single-process design documente mais pas enforce. `gunicorn -w 2` casse silencieusement.
**Fix :** boot-time check + log.critical si `gunicorn` detecte avec workers > 1.

### F10 — keyboard `/` raccourci focus filter-challenge meme en mode live
**File :** `dashboard-keyboard.js:59` — `?.focus()` no-op silencieux en live. Comportement accidentel, pas intentionnel.
**Fix :** ajouter check `if (document.body.classList.contains('mode-analyse'))`.

### F11 — Drill-down modal ouverture ne focus pas iframe
**File :** `dashboard-drilldown.js:open()` — pas de programmatic focus. A11y FAIL keyboard trap.
**Fix :** `closeBtn.focus()` apres `bd.classList.add('open')`.

### F12 — Synchronous PDF generation
**File :** `pdf_routes.py:42` — weasyprint blocking. Acceptable production WSGI multi-worker, risk en dev single-thread.

## Findings BASSE

### F13 — Dead CSS `.w-30p` + `.text-mono`
**File :** `dashboard-widgets.css:13,19` — flagged cycle 001, jamais purge.

### F14 — `--text-mute` contraste 4.05:1 sub-AA body 
**File :** `dashboard.css:21` — flagged cycle 001 reste unfixed. Aussi affecte `.alert-kind-idle`.

### F15 — Index events(cohort_id, client_ts DESC) absent
**File :** `dashboard/schema.sql` — `idx_events_cohort` existe mais ne couvre pas time-windowed queries.

### F16 — Visual recette playwright deferree depuis cycle 001
**Backlog persistent.** Tests existants verifient markup presence, pas rendu navigateur effectif. F1 est consequence directe.

## Faux positifs / claims a relativiser

- **Security agent claim "style-src 'unsafe-inline' = XSS vector"** : exagere. Inline `<style>` blocs sont server-rendered Jinja sans interpolation user-data. XSS surface = 0.
- **Tests "no flaky"** : 242/242 mais isolation via `del sys.modules` rend l'execution serielle obligatoire. pytest-xdist casserait. Documente.

## Plan remediation A.1 (priorise)

### Phase IMMEDIATE — hotfix CSP (5 min) — applique dans ce cycle 005

- F1 : `frame-ancestors 'self'` (1-char fix, 1 test playwright SI playwright shipped sinon test manuel)

### Phase 1 backlog cycle 006 — quick wins (~2h)

- F2 : monitor time-window WHERE client_ts > 1h ago
- F3 : debounce frontend re-fetch 2s
- F11 : drill-down modal focus management
- F13 : delete dead CSS
- F8 : monitor publish-then-insert reorder

### Phase 2 backlog cycle 006 — moderate (~1 jour)

- F4 : refactor app.py + dashboard.html sous 700 (decompose helpers/partials)
- F5 : decision BR i18n (suppression vs ajout)
- F9 : gunicorn multi-worker guard
- F10 : explicit mode check keyboard shortcuts
- F15 : index events composite

### Phase 3 backlog cycle 007+ — moderate (~2-3 jours)

- F3 : delta patching protocol propre (vs debounce hack)
- F14 : --text-mute contraste fix + recette
- F16 : playwright visual recette
- F6 : refactor inline `<style>` blocks vers external + remove unsafe-inline
- F7 : SRI sur Phase 3 JS files (apres F4 libere place app.py)
- F12 : PDF generation async (Celery / RQ)
