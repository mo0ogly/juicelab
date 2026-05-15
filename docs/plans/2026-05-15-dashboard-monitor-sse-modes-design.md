# Dashboard JuiceLab — Monitor + SSE + Modes UX — Design

**Date :** 2026-05-15
**Statut :** design approuvé via /brainstorming, à transformer en plan implémentation détaillé via /writing-plans
**Cycle PDCA antérieur :** 001 (redesign UI cyber-pédagogique sombre, 84/100)
**Scope :** 3 axes (A signal-to-noise + B SSE temps réel + C modes UX), 3 phases livrables indépendamment

## Contexte

Le dashboard professeur JuiceLab (Flask + Jinja, port 5000/5050) est utilisé en live pendant les TDs cybersécurité M2 pour suivre 20-30 étudiants travaillant sur OWASP Juice Shop. Le redesign visuel (cycle PDCA 001) est terminé. Restent trois gaps fonctionnels majeurs :

1. **Signal-to-noise faible** : prof scanne la matrice visuellement → latence détection problèmes (étudiant bloqué, scripting, abandon)
2. **Temps réel laggy** : polling `/api/cohort` toutes 5s, 30 students = 6 req/s + 5s de latence visible avant maj
3. **Single mode dense** : le même rendu sert pour live projetté et analyse post-TD, sans optimisation pour aucun

## Architecture

```
sync POST event ─► SQLite insert ─► SSE broadcast queue
                                          │
                                          ▼
                              frontend EventSource
                                          │
                                          ▼
                          render matrix + alerts panel + toast
                                          ▲
                                          │
                    monitor.py heuristiques (blocked/stuck/scripting/idle)
                          tick toutes 30s, broadcast alert events
```

Pivots :
- Polling 5s `/api/cohort` → SSE persistent stream `/api/cohort/stream`
- Nouveau module `dashboard/monitor.py` (heuristiques d'alerte)
- 2 tables nouvelles : `student_tag` (status + cohort) + `student_note` (texte libre)
- Frontend : `EventSource` natif (zero polling)
- CSP : zero changement (`connect-src 'self'` autorise déjà SSE same-origin)

## Phasage

Trois phases indépendantes livrables, chacune en commit/PR séparé. Possible pause/re-prioritisation entre phases.

### Phase 1 — Foundation (~1 jour)

Objectif : remplacer polling par SSE + ajouter schema tags/notes (sans encore les exploiter).

Livrables :
- Migration schema : tables `student_tag (token, cohort_id, status, updated_at)` + `student_note (token, cohort_id, body, updated_at)` dans `db.py`
- Nouveau blueprint `dashboard/sse_routes.py` exposant `/api/cohort/stream` (mimetype `text/event-stream`, `stream_with_context`)
- `dashboard/sync_routes.py` modifié : broadcast event au pool SSE après chaque insert DB
- Frontend `dashboard.html` : remove `setInterval(tick, REFRESH_MS)`, ajouter `EventSource('/api/cohort/stream')` avec handlers `message`, `error`, `open`. Reconnect auto via `Last-Event-Id`.
- Blueprint `dashboard/tags_routes.py` (CRUD tags + notes)
- `+10 tests pytest` : SSE stream emit, reconnect, tag CRUD, note CRUD

### Phase 2 — Signal-to-noise (~2 jours)

Objectif : transformer rôle prof de "scanner visuel" à "réagir aux alertes".

Livrables :
- Module `dashboard/monitor.py` : 4 heuristiques
  - `blocked` : 0 events 10 min sur même `challenge_key` actif
  - `stuck` : 5/5 hints utilisés sur un challenge sans `solved` event
  - `scripting` : >30 events / 2 min ratio anormal
  - `idle` : 0 events 15 min cohort-wide
- Heuristiques scheduled : `APScheduler` tick 30s, écrit alertes dans `alerts` table puis broadcast SSE
- Seuils dans `dashboard/config.json` (ajustables sans redeploy)
- Partial `templates/_alerts_panel.html` : side panel rose pulse, clic ouvre modal détail étudiant
- Toast push : événements SSE typés `event: flag_posted`, `event: quiz_done`, `event: journal_saved`. Toast 4s en bas-droite
- Tag inline UI : `<select>` per row matrix avec statuses (à voir / OK / absent / à interroger / —), persist via POST tags
- Notes modal : textarea per student, save/load via tags_routes
- `+15 tests pytest` : mock DB states per heuristique, alert lifecycle, tag/note persistence

### Phase 3 — Modes UX (~1.5 jour)

Objectif : 2 modes optimisés pour usages distincts (live projetté vs analyse post-TD).

Livrables :
- Query param `?mode=live` : KPI géants 4×N, alerts panel pinned, matrix masquée (mode TV/projecteur)
- `?mode=analyse` (default) : matrix dense + barre filtres
- Filter bar : par challenge, par score range, par activity recency, par tag
- Keyboard shortcuts (vanilla JS) :
  - `j`/`k` : navigate row matrice
  - `Enter` : open detail modal
  - `t` : cycle tag status
  - `/` : focus filter search
  - `?` : show shortcuts overlay
- Drill-down modal (remplace `target="_blank"` student detail) — overlay full-screen avec back arrow
- Export PDF cohorte report via `weasyprint` : top/bottom 5 students, distribution scores histogramme, stats moyennes
- `+8 tests pytest` (rendu modes, filter logic, PDF generation byte signature)
- Visual recette playwright headless : screenshot par mode + state critique

## Data flow SSE détaillé

Server side (Flask `stream_with_context`) :
```python
@bp.get("/api/cohort/stream")
def stream():
    def gen():
        q = subscribe(cohort_id)  # collections.deque maxlen=100
        try:
            yield f"retry: 5000\n\n"
            yield f"id: {last_id}\nevent: snapshot\ndata: {initial_state_json}\n\n"
            while True:
                ev = q.get(timeout=15)
                if ev is None:
                    yield ": heartbeat\n\n"
                else:
                    yield format_sse(ev)
        finally:
            unsubscribe(q)
    headers = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    return Response(stream_with_context(gen()), mimetype="text/event-stream", headers=headers)
```

Client side (vanilla JS) :
```js
const es = new EventSource('/api/cohort/stream?cohort=' + COHORT);
es.addEventListener('snapshot', e => renderFull(JSON.parse(e.data)));
es.addEventListener('event', e => applyDelta(JSON.parse(e.data)));
es.addEventListener('alert', e => showAlertPanel(JSON.parse(e.data)));
es.addEventListener('toast', e => showToast(JSON.parse(e.data)));
es.onerror = () => { /* EventSource auto-reconnects with Last-Event-Id */ };
```

Reconnect strategy : EventSource natif gère reconnect + Last-Event-Id. Server side maintain ring buffer 100 events par cohort_id pour replay.

Backpressure : queue par client (`collections.deque(maxlen=100)`), drop oldest si client lent.

## Out of scope (cycles suivants)

- Replay session timeline scrollable per student
- Cohort percentile rank visualization
- ML-based anomaly detection (cluster scripting patterns)
- Playwright visual recette pour Phase 1+2 (gardé dans Phase 3 uniquement)

## Risks & mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| SSE coupé par reverse proxy non-configuré | HAUTE | doc déploiement + heartbeat 15s côté serveur + warning frontend si `es.readyState === CLOSED` |
| Heuristiques faux positifs (étudiant en pause toilette tagged `blocked`) | MOYENNE | seuils ajustables via `dashboard/config.json`, alertes informatives pas blockers, prof acquittement clic |
| Schema migration SQLite live (cohorte en cours pendant deploy) | MOYENNE | migrations idempotentes (`CREATE TABLE IF NOT EXISTS`), backup auto avant ALTER |
| Scope creep Phase 3 | MOYENNE | timebox 1.5 jour strict, reportés cycle suivant |
| 199 pytest existants doivent rester verts | HAUTE | run pytest après chaque commit, blocker CI si fail |
| APScheduler conflict avec gunicorn multi-worker | MOYENNE | lock fichier ou Redis lock pour single-leader monitoring (ou doc single-worker recommended) |

## Tests strategy

- **Phase 1** : pytest TDD pour endpoints SSE + tags CRUD
- **Phase 2** : pytest mock DB per heuristique state (factories `make_events_for_blocked_state`)
- **Phase 3** : pytest mode rendering + filter logic + PDF byte signature (weasyprint deterministic header)
- **Cross-cutting** : zero régression sur 199 tests existants (run after every commit)
- **Visual recette** : playwright headless Phase 3 livrable (screenshot + assert no Error/Loading permanent par page/mode)

## Success criteria par phase

| Phase | Mesurable |
|-------|-----------|
| 1 | Polling supprimé, SSE stream actif, +10 tests, 199+10 pytest verts |
| 2 | 4 heuristiques détectent leur cas réel, alerts panel + toast fonctionnels, +15 tests |
| 3 | 2 modes URL togglable, filtres opérationnels, PDF exportable, +8 tests, playwright OK |

## Fichiers touchés (estimation Phase 1)

Nouveaux :
- `dashboard/monitor.py` (Phase 2)
- `dashboard/sse_routes.py`
- `dashboard/tags_routes.py`
- `dashboard/templates/_alerts_panel.html` (Phase 2)
- `dashboard/static/dashboard-sse.js`
- `dashboard/config.json` (seuils heuristiques, Phase 2)
- ~30 nouvelles clés i18n FR/EN/BR
- `docs/plans/2026-05-15-dashboard-monitor-sse-modes-design.md` (ce fichier)

Modifiés :
- `dashboard/app.py` (register blueprints SSE + tags, monitor scheduler bootstrap)
- `dashboard/sync_routes.py` (broadcast après insert)
- `dashboard/db.py` (schema migration tags + notes + alerts)
- `dashboard/templates/dashboard.html` (remove polling, add EventSource + alerts panel mount + mode toggle)
- `dashboard/static/dashboard.css` ou widgets.css (style alerts panel, toasts, modes live/analyse)
- `dashboard/i18n/{fr,en,br}.json` (nouvelles clés)

## Décision finale d'approbation

Sections 1 (architecture) + 2 (phasage) + 3 (data flow) + 4 (out of scope) + 5 (risks) approuvées par user (2026-05-15).

Prochaine étape : invoquer `/writing-plans` pour produire spec implémentation Phase 1 step-by-step (commençant par migration schema + endpoint SSE simple).
