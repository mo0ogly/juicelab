# CLAUDE.md — Project Rules for juicelab

**OWASP Juice Shop + JuiceLab pedagogical overlay + cohort dashboard.**
Used as a pedagogical platform for university TDs (M2 ANSSI, M2-IA, etc.).

## Rules detaillees (fichiers de reference)

| Fichier | Contenu |
|---------|---------|
| `.claude/rules/programming.md` | Regles React, Go, Python, General (zero emoticon, zero placeholder, zero hardcoding) |
| `.claude/rules/owasp-pedagogy-companion.md` | Production rigoureuse du pack pedagogique trilingue (briefing + hints + quiz) pour les 111 challenges natifs OWASP Juice Shop |

## Architecture

```
juice/
├── juice-shop/         OWASP Juice Shop (Angular 20 + Express, port 3000)
│   └── frontend/src/app/juicelab-overlay/   plugin overlay pedagogique (route /juicelab)
├── overlay/            mirror des fichiers pedagogiques copies sur juice-shop au build
│   ├── frontend/                            sources Angular (badges, panels, services)
│   ├── data/juicelab-private/               packs hints/quiz/journal YAML
│   └── routes/                              endpoints Express overlay
├── dashboard/          dashboard prof Flask (port 5000 ou 5050)
│   ├── app.py                               routes + CSP + CSRF + cookie auth
│   ├── sync_routes.py                       POST /api/sync (event ingestion)
│   ├── students_routes.py                   /api/students (CRUD)
│   ├── cohorts_routes.py                    /api/cohorts (CRUD)
│   └── data/dashboard.sqlite                event log
├── docker/             docker-compose.yml + .env.example + Dockerfiles
├── patches/            juicelab-core.patch (patches juice-shop core files)
├── scripts/
│   ├── apply-overlay.{sh,ps1}               merge overlay/ into juice-shop clone
│   ├── install-student.{sh,ps1}             one-shot bootstrap pour eleve / smoke test
│   └── juicelab-dashboard.service           systemd user unit template
├── docs/
│   ├── STUDENT-INSTALL-{FR,EN}.md           guide install eleve
│   ├── TEACHER-DASHBOARD-{FR,EN}.md         guide install dashboard prof
│   ├── COHORT_WORKFLOW.md, CTF-INTEGRATION.md, etc.
└── .claude/skills/                           skills locaux du projet
```

## Source de verite

| Data | Source unique | Notes |
|------|---------------|-------|
| Challenges OWASP selectionnes pour TD | `juice-shop/frontend/src/assets/juicelab/selected_challenges.yml` | NE JAMAIS creer un nouveau challenge OWASP |
| Hints (5 niveaux) | `overlay/data/juicelab-private/hints/<key>.yaml` | cohorte cout fixe : 5/10/20/35/50 |
| Quiz (3 QCM, 4 options) | `overlay/data/juicelab-private/quiz/<key>.yaml` | bilingue FR/EN strict |
| Briefing | `overlay/frontend/src/assets/juicelab/briefing/<key>.yaml` | 3-4 concepts max |
| Config overlay runtime | `overlay/frontend/src/assets/juicelab/config.json` | dashboard_url + cohort_id + instance_label |
| Env Docker | `docker/.env` (depuis `.env.example`) | tokens >= 16 chars sinon dashboard refuse de boot |

## ZERO PLACEHOLDER / ZERO DECORATIVE / ZERO HARDCODING — REGLE ABSOLUE

1. **ZERO placeholder** — chaque element UI connecte a un vrai appel API. Pas de "TODO", "coming soon", `setTimeout` qui simule.
2. **ZERO hardcoding** — toute chaine UI visible passe par i18n (`juicelab-overlay/models/juicelab-i18n.ts`, FR/EN minimum). URL/port via `assets/juicelab/config.json` ou env var. JAMAIS `'http://localhost:5050'` ou `'admin@juice-sh.op'` en dur dans un composant.
3. **ZERO decorative** — pas de Matrix rain, pas de fake "SYSTEM COMPROMISED".
4. **ZERO emoticon** dans le code sauf demande explicite du user.
5. **ZERO schema ASCII** — tout diagramme dans le wiki en fence Mermaid (`flowchart`, `sequenceDiagram`). JAMAIS de box-drawing `┌──┐│└──┘`.

## File size — 800 lines max

Aucun fichier source ne depasse 800 lignes. S'applique a `.py`, `.jsx`, `.js`, `.ts`, `.tsx`, `.go`, `.md`, `.json` (sauf datasets), `.yaml`.

Quand un fichier approche 700 lignes : decomposer en modules logiques par responsabilite. Pour `.tsx` : extraire sub-components + hooks + constants. Pour `.py` : extraire classes + fonctions utilitaires. Pour `.md` : decomposer par section.

Hook `.claude/hooks/file_size_check.cjs` enforce au moment de l'edit (PreToolUse Edit/Write).

## i18n trilingual (FR / EN / BR)

Tout texte visible : `t('key')` via react-i18next (Juice Shop) ou via le catalogue overlay (`juicelab-i18n.ts`). JAMAIS de string hardcodee. Termes techniques restent en anglais.

## Process Management

Pas de commandes directes. Utiliser :
- `juice.ps1` (Windows) / `juice.sh` (Linux) pour build / start / stop / health
- `scripts/install-student.{sh,ps1}` pour bootstrap eleve
- `systemctl --user start juicelab-dashboard.service` pour le dashboard prof persistant

## Dashboard — variables d'env critiques

| Variable | Min | Effet si absent |
|----------|-----|-----------------|
| `DASHBOARD_TEACHER_TOKEN` | 16 chars | dashboard refuse de booter (503) |
| `DASHBOARD_PROOF_SECRET` | 16 chars | flag verification desactivee |
| `DASHBOARD_PORT` | — | default 5000 |
| `DASHBOARD_BIND` | — | default 0.0.0.0 (production VPS = 127.0.0.1 + reverse proxy) |
| `DASHBOARD_CORS_ORIGINS` | — | CORS bloque les eleves si leur origine pas listee |
| `JUICELAB_COHORT_ID` | — | cohorte par defaut overlay |

`docker/.env` n'est lu QUE par `docker compose --env-file`. `python3 app.py` direct ignore ce fichier — l'env doit etre exporte dans le shell appelant ou via systemd `EnvironmentFile=`.

## Skills a utiliser

| Situation | Skill |
|-----------|-------|
| Implementation structuree multi-fichiers | `/apex` (10 etapes) |
| Audit qualite avec benchmark | `/audit-pdca` |
| Modifier un pack pedagogique existant (hints/quiz/journal) | `/juicelab-add-challenge` (refuse de creer un nouveau challenge OWASP) |
| Test/recette d'un module | `/test-driven-development` |
| Debug systematique | `/systematic-debugging` |
| Verification avant marquer "done" | `/verification-before-completion` |

## Git

- Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
- Repo `juice/` push sur `juicelab` remote (mo0ogly/juicelab)
- Repo `juice-shop/` push sur `fork` remote (mo0ogly/juice-shop), JAMAIS sur `origin` (upstream OWASP) sans PR explicite
- Pas de `houyi` dans les noms de fichiers
- Strip CRLF avant commit (`sed -i 's/\r$//' <fichier>`) — plein de fichiers du repo sont en CRLF historique, on ne touche que ceux qu'on a modifies

## Template literal bug

Pas de `${}` dans les fonctions standalone `.jsx`. Utiliser concatenation.

## Content Filter Safety

Eviter de lire en entier : fichiers > 800 lignes (par regle), packs hints/quiz si pas necessaire, gros JSON datasets. Travailler via metadonnees + grep cible quand possible.
