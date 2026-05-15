# A — IMPROVEMENTS pour cycle 002

## Nouveaux checks a ajouter au SCORING_CONFIG

| Check | Domaine | Justification |
|-------|---------|---------------|
| PERF-01 | performance | `grep "@import.*googleapis\|@import.*gstatic" static/*.css` → bloquant si trouve |
| PERF-02 | performance | `grep "preconnect.*fonts" templates/*.html` → score si present |
| SEC-SRI | security_csp | Verifier que _compute_css_sri couvre TOUS les .css du dossier static/ (not just main) |
| A11Y-CONTRAST | accessibility | Lancer un script Python WCAG sur tous les pairs `--text-*` / `--bg-*` du fichier CSS, fail si ratio < 4.5:1 sur body text |
| MARKUP-DEAD | markup_consistency | grep auto chaque classe declaree dans CSS contre usages templates → liste orphelines |
| VISUAL-RECETTE | visual | Bloquante si pas executee : playwright/puppeteer screenshot par page |

## Checks a retirer / poids a ajuster

- Aucun retire au cycle 1.
- Augmenter poids performance de 12 → 15 (signal clair) au cycle 2.
- Reduire poids file_size_hygiene de 5 → 3 (deja bien geree, faible variance).

## Pipeline improvements

1. **Visual recette via playwright headless** : ajouter step C.1b avec headless browser, screenshots stocks dans `pdca/.../cycle_NNN/screenshots/`
2. **Agent prompts** : ajouter section explicite "SCOPE = DELTA introduit par les modifs git status, PAS l'etat global". Reduire faux positifs scope drift.
3. **Verifie contrastes en parallele des agents** : script Python WCAG canonique systematique avant scoring accessibility.
4. **Token diff tracking** : enrichir D_INVENTORY.json avec git diff stats (insertions/deletions par fichier).

## Pre-flight P.0 pour juicelab dashboard (specifique)

Adapter le P.0 du skill audit-pdca (qui cible LIA-SEC) pour juicelab dashboard :
```bash
# Flask boot
DASHBOARD_TEACHER_TOKEN=... python3 -c "from app import create_app; create_app()"
# CSS endpoints
curl -s http://localhost:5050/static/dashboard.css -o /dev/null -w "%{http_code}"
# Tests
DASHBOARD_TEACHER_TOKEN=... python3 -m pytest tests/ -q
```

## Objectif cycle 002

- Score global : 84 → 92 (+8 pts)
- Closing : HAUTE H1 + H2 (auto-gain ~7 pts performance + ~4 pts security)
- Visual recette executee = unlocks 100% certitude design

## Prompts agents a iterer

- Toutes les `prompt brainstorm` doivent inclure :
  - "Verifier scope = DELTA fournis dans `D_INVENTORY.json files_modified` UNIQUEMENT"
  - "Pour chaque finding, separer `INTRODUIT_PAR_CYCLE` vs `PRE_EXISTANT`"
  - "Calculer contrastes WCAG avec formule canonique : linearization gamma C ≤ 0.03928 ? C/12.92 : ((C+0.055)/1.055)^2.4"
