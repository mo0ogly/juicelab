---
name: apex
description: Methodologie structuree APEX (Analyze-Plan-Execute-eXamine) pour implementer des features de facon systematique dans le projet juice (OWASP Juice Shop + JuiceLab overlay + Dashboard pedagogique). 10 etapes autonomes, validation, review adversariale, tests, et creation de PR. Mode Integration (-i) pour porter du code externe (overlay, patches, packs OWASP) avec tracker exhaustif. Mode Recette (-rc) PDCA-C avec swarm 6 agents adapte au stack juicelab (Angular + Flask + YAML packs). Utiliser quand une tache touche plusieurs fichiers, presente des risques, ou integre du code externe. Se declenche sur "apex", "plan d'attaque", "implemente cette feature", "workflow structure", "integre ce repo", "porte ce code", "ajoute un challenge", "audit pack pedagogique".
---

# APEX - Analyze, Plan, Execute, eXamine - juice project edition

Pipeline systematique en 10 etapes pour toute tache non-triviale dans `/home/fpizzi/juice`
(OWASP Juice Shop + JuiceLab overlay TD M2 + Dashboard Flask pedagogique).

Inspire de Codelynx APEX, Explore-Plan-Execute (Upsun), Everything-Claude-Code, Trail of Bits.

### Stack juice

| Composant | Tech | Port | Process mgmt |
|---|---|---|---|
| Juice Shop | Angular 17 + Node.js (TypeScript) | 3000 | `./juice.sh shop` |
| Dashboard pedagogique | Flask + SQLite | 5050 | `./juice.sh dash` |
| JuiceLab overlay | Angular components + assets/juicelab/ | (dans shop) | `./juice.sh build` |
| Packs pedagogiques | YAML v2 (briefing/hints/quiz) | n/a | lint script |

### Model Policy

| Agent / Etape | Model | Justification |
|---|---|---|
| ETAPE 01 (ANALYZE) — Explore agent | **haiku** | Lecture seule, Glob/Grep/Read |
| ETAPE 05 (EXAMINE) — review adversariale | **sonnet** | Analyse critique, OWASP, pedagogie |
| Mode `-rc` — 6 agents recette (C-01 a C-65) | **haiku** | grep, lint, comptages |
| Mode `-rc` — aggregation scorecard | **sonnet** | Consolidation, scoring |
| Subagents custom (pack-writer, source-checker) | **sonnet** | Production pedagogique |

## Syntaxe

```
/apex [flags] <description de la tache>
```

## Flags

| Flag | Description |
|------|-------------|
| `-a` / `--auto` | Skip confirmations, auto-approve plans |
| `-x` / `--examine` | Active la review adversariale (etape 05) |
| `-s` / `--save` | Sauvegarde chaque etape dans `.claude/output/apex/{task-id}/` |
| `-t` / `--test` | Inclut creation + execution de tests (etapes 07-08) |
| `-b` / `--branch` | Verifie qu'on n'est pas sur main, cree une branche si besoin |
| `-pr` / `--pull-request` | Cree une PR a la fin (active -b automatiquement) |
| `-e` / `--economy` | Pas de subagents, economise les tokens |
| `-r <id>` / `--resume <id>` | Reprend depuis une tache precedente |
| `-i` / `--integrate` | Mode Integration : tracker exhaustif, inventaire source, recovery |
| `-rc` / `--recette` | Mode Recette : remplace ETAPE 04 par cycle PDCA-C complet (65 checks, swarm 6 agents) |
| `-p` / `--pedagogy` | Mode Pack pedagogique : enforce schemas YAML v2, bilingue strict, sources OWASP obligatoires |

**Par defaut (sans flags) :** confirmation a chaque etape, pas de tests, pas de PR.

## Les 10 etapes

### ETAPE 00 : INIT
- Parser les flags et la description
- Creer le dossier output si `-s` (`.claude/output/apex/{task-id}/`)
- Verifier l'etat git (branche, uncommitted changes)
- Si `-b` : verifier qu'on n'est pas sur main/master, creer branche `feat/{task-slug}`

### ETAPE 00b : PRE-FLIGHT CHECK (BLOQUANT)

Avant toute analyse, verifier que l'environnement juicelab est operationnel :

```bash
# Process mgmt — juice.sh health (statut services)
./juice.sh health
# -> shop up + dash up = OK | autres etats = STOP, fixer d'abord
# Acceptation : services peuvent etre DOWN si tache est de fixer une config statique

# Juice Shop reachable (si tache touche overlay/frontend/routes)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# -> 200 = OK | autre = warning (si shop down, ne pas tester l'UI)

# Dashboard reachable (si tache touche dashboard/)
curl -s -o /dev/null -w "%{http_code}" http://localhost:5050/api/health
# -> 200 = OK | autre = warning

# Angular build (si tache touche juice-shop/frontend/)
cd /home/fpizzi/juice/juice-shop && timeout 600 npx ng build --configuration production 2>&1 | tail -3
# -> "Application bundle generation complete" = OK | erreurs = STOP

# Dashboard syntax (si tache touche dashboard/)
python -m py_compile /home/fpizzi/juice/dashboard/app.py /home/fpizzi/juice/dashboard/db.py
# -> exit 0 = OK | sinon = STOP

# Pedagogy lint (si tache touche packs briefing/hints/quiz)
python /home/fpizzi/juice/.claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py 2>&1 | tail -5
# -> 0 issues = OK | issues listees = noter mais pas bloquant pour analyse

# Hook file_size_check actif (si tache cree des fichiers)
ls /home/fpizzi/juice/.claude/hooks/file_size_check.cjs
# -> present = OK | absent = STOP, hook manquant
```

**Si un pre-flight echoue :**
1. Informer l'utilisateur du blocage
2. Proposer de fixer le pre-requis d'abord
3. NE PAS continuer sur une base cassee

**Exception :** si la tache EST de fixer le pre-requis qui echoue, continuer.

### ETAPE 01 : ANALYZE (comprendre, pas coder)

Exploration pure du code existant. ZERO ligne de code produite.

1. **Lire les fichiers concernes** : Glob + Grep + Read
2. **Cartographier les dependances** : qui appelle quoi, imports, routes API
3. **Triage d'usage (OBLIGATOIRE pour fichiers existants)** :
   ```bash
   # Pour chaque symbole public, chercher cross-language (TS Angular + Python Flask + YAML)
   grep -rn "SymbolName\|/api/route-correspondante" \
     --include="*.ts" --include="*.tsx" --include="*.py" --include="*.yaml" --include="*.yml" \
     /home/fpizzi/juice/ \
     | grep -v node_modules | grep -v le_fichier_lui_meme

   # 0 resultats = DEAD CODE -> proposer suppression, NE PAS corriger
   # N resultats = ACTIF -> corriger/activer
   ```
   Classer : **ACTIF** / **DEAD** / **PROTOTYPE**.
4. **Identifier les patterns existants** : conventions, nommage, architecture
5. **Consulter la documentation** :
   - `CLAUDE.md` racine projet
   - `.claude/rules/owasp-pedagogy-companion.md` (regles packs)
   - `.claude/rules/programming.md` (regles code)
   - `CONTEXTE-JuiceLab.md`, `ARCHITECTURE.md`
   - Skill `juicelab-add-challenge` si tache touche un pack
6. **Verifier les contraintes juicelab** :
   - **ZERO emoticon** dans le code, commentaires, strings UI
   - **ZERO placeholder** (`TODO`, `coming soon`, setTimeout simule, donnees mock)
   - **ZERO hardcoding** :
     - Strings UI → catalogue i18n `frontend/src/app/juicelab-overlay/models/juicelab-i18n.ts` (FR/EN/BR)
     - URLs/ports → `assets/juicelab/config.json` ou variables d'environnement
     - JAMAIS de `'http://localhost:5050'`, `'admin@juice-sh.op'`, `'Connecte-toi'` en dur
   - **800 lignes max par fichier** (hook `.claude/hooks/file_size_check.cjs` enforce)
   - **Trilingue strict FR/EN/BR** pour tout texte visible
   - **Schemas YAML v2** pour packs pedagogiques (briefing/hints/quiz)
   - **Cohorte hints fixe** : 5 / 10 / 20 / 35 / 50 (devier = casser `HINT_COST_BY_LEVEL`)
   - **Quiz** : 3 QCM, 4 options exactement, `correct` index 0-3, bilingue
   - **NE JAMAIS LIRE le contenu complet** de fichiers sensibles (challenges.yml en bulk, scenarios.py si present) — travailler via metadonnees

Output (si `-s`) : `01-analyze.md`
```
FICHIERS CONCERNES : [liste avec lignes]
DEPENDANCES : [qui appelle quoi]
PATTERNS EXISTANTS : [conventions detectees]
CONTRAINTES : [i18n FR/EN/BR, schemas v2, hint cohort, file size 800]
RISQUES : [ce qui peut casser, hooks bloquants, parcours TD]
```

Gate : presenter l'analyse a l'utilisateur. Attendre validation sauf si `-a`.

### ETAPE 02 : PLAN (architecturer avant d'implementer)

Strategie fichier par fichier avec ordre d'implementation.

1. **Decomposer en etapes atomiques** : 1 etape = 1 fichier ou 1 fonction
2. **Ordonner par dependance** : ce qui doit exister avant le reste
3. **Identifier les gates entre etapes** : compilation, lint pedagogy, schema check
4. **Estimer le blast radius** : composants Angular, routes Flask, packs YAML
5. **Definir le rollback** : `git stash` / `git checkout -- <fichiers>`
6. **Si tache pedagogie** : verifier que la decision respecte la regle `.claude/rules/owasp-pedagogy-companion.md` (sources lues, schema v2, bilingue strict, parcours TD intact)

Format du plan :
```
ETAPE 1 : [action] -> [fichier:ligne] -> [gate: ng build / py_compile / lint pedagogy]
ETAPE 2 : [action] -> [fichier:ligne] -> [gate: ...]
ROLLBACK : git stash / git checkout -- [fichiers]
CRITERES DE SUCCES : [quand c'est "done"]
```

Output (si `-s`) : `02-plan.md`

Gate : presenter le plan a l'utilisateur. Attendre validation sauf si `-a`.

### ETAPE 03 : EXECUTE (implementer avec discipline)

Implementation guidee par le plan. Chaque changement est tracke.

Regles :
1. **1 etape a la fois** : pas de multi-fichier sans validation
2. **Gate apres chaque etape** : build, lint, syntax check
3. **Pas de drift** : si un probleme emerge, revenir au PLAN. Si 2+ etapes echouent : STOP, replanifier
4. **Logger les decisions** : ecrire dans `.claude/output/apex/{task-id}/decision_log.jsonl` (JSONL strict)

   Format obligatoire :
   ```jsonl
   {"ts":"{YYYY-MM-DDTHH:MM:SS}","phase":"EXECUTE","step":N,"action":"{verbe}","file":"{fichier:ligne}","decision":"{pourquoi}","gate":"{PASS|FAIL|N/A}","status":"{success|partial|failure}"}
   ```

5. **Silent Drift Detection** : verifier que l'objectif n'a pas derive vs description originale `/apex`. Si oui : STOP, signaler, reprendre depuis PLAN. Logger `"drift_detected": true`.

6. **Conventions juicelab strictes** :
   - TypeScript/Angular : `t('key')` via react-i18next ou equivalent ngx-translate ; pas de string hardcodee
   - Python/Flask : `logging` module, pas `print()` ; type hints sur fonctions publiques
   - YAML packs : schema_version `juicelab.briefing.v2`, `juicelab.hints.v2`, `juicelab.quiz.v2`
   - JuiceLab i18n : `frontend/src/app/juicelab-overlay/models/juicelab-i18n.ts` (FR/EN/BR)
   - Config : `juice-shop/frontend/src/assets/juicelab/config.json`
   - Zero emoji, zero TODO, zero placeholder, zero mock

7. **Policy gates (BLOQUANT, verifier AVANT d'ecrire du code)** :
   - **NO STUB** : JAMAIS de handlers Flask retournant 501/placeholder. Si une dependance manque, l'implementer ou prevenir l'utilisateur.
   - **NO MOCK** : JAMAIS de donnees fictives, hardcodees ou inventees. Tout pack DOIT citer une source factuelle (challenges.yml, hacking-instructor/, codefixes/).
   - **NO INVENTION** : la regle owasp-pedagogy-companion impose pre-flight sources lues AVANT ecriture. Refus si `sources_read = -` dans tracker.
   - **NO DUP** : pas de copier-coller inter-challenge (>40% phrases identiques = refus).
   - **NO DISABLE** : JAMAIS commenter un fichier entier sans accord explicite.
   - **NO TD BREAK** : les 13 challenges du parcours TD (M2 Sorbonne) sont intouchables sans autorisation explicite. Liste : `juice-shop/frontend/src/assets/juicelab/selected_challenges.yml`.

Gates obligatoires selon contexte :

| Contexte | Gate |
|----------|------|
| Angular frontend | `cd juice-shop && npx ng build --configuration production` (zero TS errors) |
| Flask backend | `python -m py_compile dashboard/app.py dashboard/db.py` + `python -c "import sys; sys.path.insert(0,'dashboard'); import app"` |
| Packs pedagogiques | `python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py` (schemas v2, bilingue, cohort) |
| Overlay (assets/juicelab/) | yaml.safe_load OK + lint + ng build |
| Hooks | `node .claude/hooks/file_size_check.cjs <fichier>` (800 lignes max) |
| Tracker pedagogie | grep cohorte status + diff vs DONE files |

Output (si `-s`) : `03-execute.md`

### VERIFICATION GATE (BLOQUANT)

Apres chaque modification, AVANT de declarer "termine" :

1. **BUILD GATE** :
   - Angular : `cd juice-shop && npx ng build --configuration production` (exit 0)
   - Flask : `python -m py_compile dashboard/app.py dashboard/db.py` (exit 0)
2. **TEST GATE** :
   - JS : `cd juice-shop && npm test -- --watch=false` (si touche tests)
   - Python : `cd dashboard && python -m pytest -x -q` (si tests existent)
3. **LINT GATE** :
   - Packs : `python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py` (0 issues sur les fichiers modifies)
   - JS/TS : `cd juice-shop && npm run lint` (si dispo, peut etre long)
4. **HOOK GATE** : file size, secret scanner s'executent automatiquement via PreToolUse
5. **REGRESSION GATE** : code modifie n'introduit pas de regressions sur l'existant
6. **SMOKE TEST** :
   - Shop : `curl -s http://localhost:3000 | head -1 | grep -i "<!doctype"`
   - Dashboard : `curl -s http://localhost:5050/api/health | grep -q "ok"`
   - Pack modifie : verifier rendu dans l'UI overlay si applicable

Si une gate echoue : STOP, corriger, re-gate. JAMAIS declarer "termine" sans les 6 gates vertes.

**Re-verification apres agents :** si un subagent modifie des fichiers, re-executer les 6 gates AVANT de continuer.

### ETAPE 04 : VALIDATE (auto-verification)

Verification automatique de la qualite :

1. **Diff complet** : `git diff` — relire TOUT ce qui a change
2. **Anti-patterns juicelab** :
   - Zero emoticon dans code/commentaires/strings
   - Zero `TODO` / `placeholder` / `coming soon` / `setTimeout` simule
   - Zero hardcoding URL/port/host (passer par `config.json` ou env)
   - Zero string UI hardcodee (passer par i18n catalogue FR/EN/BR)
   - Trilingue : grep `_fr|_en|_br` retourne nombre divisible par 3 sur les packs
   - Cohorte hints : 5/10/20/35/50 exact
   - Quiz : 4 options exactement, `correct` index 0-3
   - File size < 800 lignes par fichier (sauf exceptions documentees)
3. **Compilation/build** : tout doit passer
4. **Securite OWASP** : SQL injection, XSS, command injection, path traversal, hardcoded secrets (Flask token / proof secret)
5. **Tracker sync** (si tache pedagogie) : `.claude/output/owasp-pedagogy-companion/TRACKER.md` reflete les fichiers produits

Output (si `-s`) : `04-validate.md`

### ETAPE 05 : EXAMINE (review adversariale, optionnelle avec `-x`)

Review critique comme si le code etait ecrit par quelqu'un d'autre :

1. **Analyse critique** : qu'est-ce qui pourrait mal tourner en classe (etudiants M2 en TD) ?
2. **Review securite** : OWASP top 10, secrets dans repo, CORS, XSS, CSRF dans dashboard
3. **Review pedagogique** (si pack) :
   - Briefing : sources citees ? concepts ancres (CWE/OWASP) ? bilingue parfait ?
   - Hints : graduation cognitive (reflex → localize → narrow → syntax → solution) ? `pedagogical_intent` non creux ?
   - Quiz : distracteurs plausibles ? `explanation` justifiee ? pas de trick questions ?
4. **Review performance** : N+1 queries, boucles, pagination dashboard
5. **Review maintenabilite** : SRP, DRY, nommage, complexite, taille fichier
6. **Verdict** : PASS / ISSUES_FOUND

Si ISSUES_FOUND → ETAPE 06 (Resolve).

Output (si `-s`) : `05-examine.md`

### ETAPE 06 : RESOLVE (corriger les issues, si etape 05 en a trouve)

1. Corriger chaque issue identifiee
2. Re-valider (retour ETAPE 04)
3. Documenter les corrections

Output (si `-s`) : `06-resolve.md`

### ETAPE 07 : TESTS (creation, optionnelle avec `-t`)

1. **Analyser** les tests existants pour le code modifie
2. **Creer** les tests manquants :
   - Frontend Angular : `*.spec.ts` a cote du composant
   - Backend Flask : `dashboard/tests/test_*.py`
   - Packs pedagogiques : test via `lint_juicelab_pedagogy.py` + cas regression dans `.claude/output/owasp-pedagogy-companion/`
3. **TDD** : si applicable, tests echouent AVANT l'implementation

Output (si `-s`) : `07-tests.md`

### ETAPE 08 : RUN TESTS (execution, optionnelle avec `-t`)

1. Executer tous les tests concernes :
   - `cd juice-shop && npm test -- --watch=false` (Karma/Jasmine)
   - `cd dashboard && python -m pytest -v` (si pytest setup)
   - `python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py`
2. Si echec : corriger et re-executer (boucle jusqu'a vert)
3. Verifier la couverture si configure

Output (si `-s`) : `08-run-tests.md`

### ETAPE 09 : FINISH (finalisation)

1. **Tracking pedagogie** (si tache touche packs) : mettre a jour `.claude/output/owasp-pedagogy-companion/TRACKER.md` avec :
   - Statut DONE pour briefing/hints/quiz/journal
   - Date YYYY-MM-DD dans `sources_read`
   - Notes pertinentes (BLOCKED reason, parcours TD, etc.)

2. **Plan persistant** : si `-s` actif, finaliser `.claude/output/apex/{task-id}/PLAN.md` :
   ```
   Status: TERMINE
   Date fin: YYYY-MM-DD HH:MM
   Score PDCA: XX/100 (si -rc) | N/A (sinon)
   Gates: BUILD [OK|FAIL] | TEST [OK|FAIL] | LINT [OK|FAIL] | REGRESSION [OK|FAIL] | SMOKE [OK|FAIL]
   ```

3. Si `-pr` : creer la Pull Request avec `gh pr create`
4. Si `-b` sans `-pr` : informer de la branche prete

5. **Scoring Report de session** (obligatoire, produit dans tous les modes) :

```
== APEX SESSION REPORT — {task-id} — {date} ==

Objectif   : {description originale de /apex}
Statut     : ACHIEVED | PARTIALLY_ACHIEVED | FAILED
Duree      : {HH:MM}

Etapes     :
  00 INIT         : OK
  00b PRE-FLIGHT  : OK | SKIP (tache = fix du pre-requis)
  01 ANALYZE      : OK | SKIP
  02 PLAN         : OK | SKIP
  03 EXECUTE      : OK | REPLAN x{N}
  04 VALIDATE     : OK | FAIL + corrections
  05 EXAMINE      : OK | SKIP (pas de -x)
  06 RESOLVE      : OK | SKIP (pas d'issues)
  07 TESTS        : OK | SKIP (pas de -t)
  08 RUN TESTS    : OK | SKIP (pas de -t)
  09 FINISH       : OK

Gates      :
  BUILD         : PASS | FAIL
  TEST          : PASS | FAIL | SKIP
  LINT PEDAGOGY : PASS | FAIL | SKIP
  REGRESSION    : PASS | FAIL
  SMOKE         : PASS | FAIL

Drift      : NONE | DETECTED a etape {N} — {description et correction}
Policy gates:
  NO STUB     : OK | VIOLATION {fichier}
  NO MOCK     : OK | VIOLATION {fichier}
  NO INVENTION: OK | VIOLATION (sources_read manquant)
  NO DUP      : OK | VIOLATION ({key1}<>{key2} >40%)
  NO TD BREAK : OK | VIOLATION (parcours TD touche sans accord)

Score PDCA : {XX/100 si -rc | N/A}
Open items : {liste ou "aucun"}

Auto-evaluation :
  Objectif atteint       : 1/1 ou 0/1
  Zero regression        : 1/1 ou 0/1
  Policy gates respectees: 1/1 ou 0/1
  Journal complet        : 1/1 ou 0/1
  Drift detecte/corrige  : 1/1 ou 0/1
  Total                  : {N}/5
```

Output (si `-s`) : `09-finish.md`

## Mode Resume

```
/apex -r <task-id>
```

1. Localiser le dossier dans `.claude/output/apex/{task-id}/`
2. Lire `00-context.md` pour restaurer la tache, les flags, les criteres
3. Scanner les fichiers d'etapes existants pour determiner la derniere etape completee
4. Reprendre a l'etape suivante

## Mode Economy (`-e`)

Pas de subagents, tout dans le contexte principal. Pour plans token-limites.

## Mode Light (taches simples, 1-2 fichiers)

```
A: "Je modifie X dans Y, dependance Z"
P: "Etape 1: ..., Gate: build / lint"
E: [code]
X: "Diff OK, anti-patterns OK, build OK"
```

## Mode Pedagogy (`-p`)

Quand la tache consiste a produire ou modifier un pack pedagogique (briefing/hints/quiz)
pour un challenge OWASP Juice Shop.

```
/apex -p <action> <challenge_key>
# ex: /apex -p audit weakPasswordChallenge
# ex: /apex -p produce ssrfChallenge
```

Le mode `-p` enforce :

1. **Pre-flight sources** (BLOQUANT) — avant d'ecrire UN SEUL caractere :
   - Lire `juice-shop/data/static/challenges.yml` entree `<challenge_key>`
   - Lire `juice-shop/frontend/src/hacking-instructor/challenges/<key>.ts` si present
   - Lire `juice-shop/data/static/codefixes/<key>/` si present
   - Lire route serveur `juice-shop/routes/<key>.ts` ou `juice-shop/lib/` si present
   - Cocher `sources_read = YYYY-MM-DD` dans `.claude/output/owasp-pedagogy-companion/TRACKER.md`
   - Si AUCUNE des 4 sources : marquer challenge `BLOCKED` et stopper

2. **Schemas v2 obligatoires** :
   - Briefing : `assets/juicelab/briefing/<key>.yaml` — `mission_fr|en|br`, `concepts[].title_fr|en|br` + `body_fr|en|br` (3-4 concepts MAX)
   - Hints : `data/juicelab-private/hints/<key>.yaml` — cohorte `cost_pct: [5,10,20,35,50]` exacte, `text_fr|en|br`, `pedagogical_intent`
   - Quiz : `data/juicelab-private/quiz/<key>.yaml` — 3 questions, 4 options exactement, `correct: 0-3`, `explanation_fr|en|br`

3. **Bilingue strict** : grep `_fr|_en|_br` retourne nombre divisible par 3 ; options arrays meme longueur

4. **File size** : chaque yaml < 800 lignes (hook enforce)

5. **Refus** :
   - Copier-coller >40% inter-challenge : refus
   - Pack sans source citee dans concepts : refus
   - Cohorte hints deviante : refus
   - Quiz avec 3 options absurdes + 1 vraie : refus, retravailler distracteurs

6. **Cross-validation** : apres production, `python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py` doit retourner 0 issues sur les fichiers modifies

7. **Tracker MAJ** : mettre a jour le tracker DANS la meme session (briefing/hints/quiz/journal -> DONE + date + notes)

## Mode Batch (audit multi-fichiers)

```
/apex --batch <description>
```

Phase 1 : TRIAGE RAPIDE (5 sec/fichier) — classer ACTIF / PROTOTYPE / DEAD
Phase 2 : ACTION sur ACTIF + PROTOTYPE approuves
Phase 3 : CLEANUP DEAD (apres validation utilisateur)

Note : mode Batch = seule exception a la policy NO DISABLE. Hors batch, ne jamais renommer en `.disabled`.

## Mode Integration (`--integrate` / `-i`)

Quand la tache consiste a integrer du code provenant d'un repo externe (overlay,
patches OWASP upstream, pack pedagogique externe, lib node, etc.) dans juice.

```
/apex -i <description> --source <repo_url_ou_path>
```

### Principes fondamentaux

1. **LIRE AVANT DE CODER** : INTERDICTION absolue d'ecrire du code tant que TOUS les fichiers du repo source n'ont pas ete lus avec `Read`.
2. **Ne pas reinventer la roue** : reprendre la logique exacte du repo source, l'adapter au stack juice.
3. **Tracking exhaustif** : chaque element suivi individuellement.
4. **Renommage systematique** : pas de nom du repo source dans les noms de fichiers/modules cibles.

### ETAPE 01i : INVENTAIRE SOURCE (BLOQUANT)

Avant toute analyse, creer l'inventaire exhaustif :

```markdown
## INVENTAIRE SOURCE — [nom du repo]

### Fichiers
| # | Fichier | Type | Lignes | Description | Portable ? |
|---|---------|------|--------|-------------|------------|

### Symboles
| # | Symbole | Fichier source | Signature | Description | Portable ? |
|---|---------|----------------|-----------|-------------|------------|

### Dependencies
| # | Package | Version source | Equivalent cible | Notes |
|---|---------|----------------|------------------|-------|
```

Presenter l'inventaire. Attendre validation.

### ETAPE 02i : INTEGRATION TRACKER

Creer `.claude/output/apex/{task-id}/INTEGRATION_TRACKER.md` :
- Registre d'etat de chaque element
- Recovery point si session tombe
- Preuve de completude

Voir version originale skill apex pour structure detaillee (legendes, sections A-E).

### ETAPE 03i : EXECUTE avec suivi tracker

1. **1 element a la fois** : porter A1.1, MAJ tracker, puis A1.2
2. **Gate par element** : chaque element compile/fonctionne avant le suivant
3. **Docstrings obligatoires** :
   - Description
   - Reference source (ex: "Ported from OWASP Juice Shop upstream, hacking-instructor/<key>.ts")
   - Ameliorations apportees
4. **Adaptation au stack** : imports Angular, conventions Flask, schemas YAML v2
5. **MAJ tracker** apres chaque element

### ETAPE 04i : VALIDATION COMPLETUDE

```bash
grep -c "\[ \]" .claude/output/apex/{task-id}/INTEGRATION_TRACKER.md
# 0 = COMPLET | N > 0 = STOP, N elements restants
```

Cross-checks :
1. Chaque fichier source a un fichier cible
2. Chaque symbole porte ou explicitement exclu
3. Tests passent
4. Lint pedagogy = 0 issues
5. ng build + py_compile OK

### Mode Resume Integration

```
/apex -r <task-id> -i
```

Lit l'INTEGRATION_TRACKER, trouve la derniere etape completee, reprend.

### Bonnes pratiques Integration

| Pratique | Description |
|----------|-------------|
| **Isolation** | Code porte dans sous-module isole (ex: `overlay/` pour overlay JuiceLab) |
| **Bridge pattern** | Fonctions bridge entre code porte et existant |
| **Tests d'abord** | Ecrire tests AVANT integration |
| **Incremental** | Valider chaque phase avant la suivante |
| **Rollback clair** | Rollback = supprimer le sous-module isole |

## Supervision adaptee au risque

| Risque | Supervision | Exemples |
|--------|-------------|----------|
| Faible | Autonome (`-a`) | UI cosmetic, typo, ajout label i18n |
| Moyen | Guidee | Nouveau pack pedagogique, nouvelle route Flask |
| Eleve | Surveillee (`-x -t`) | Modification overlay, dashboard auth, schema migration |
| Critique | Full pipeline (`-x -t -pr`) | Compliance (CTF), donnees etudiants, deploiement |
| Integration | Tracker obligatoire (`-i`) | Portage upstream OWASP, lib externe |
| Pedagogie | Sources obligatoires (`-p`) | Production pack briefing/hints/quiz |
| Recette complete | Full PDCA-C (`-rc`) | Apres implementation majeure, release classe, audit qualite |

---

## Mode --recette (`-rc`)

Quand `-rc` est actif, **ETAPE 04 (VALIDATE)** est remplacee par un cycle **PDCA-C complet** orchestrant un swarm de 6 agents paralleles sur 65 checks repartis en 6 categories. A la fin, un scorecard /100 est produit et integre dans ETAPE 09 (FINISH).

### Declenchement

```
/apex -rc <description>           # recette seule, pas de PR
/apex -rc -pr <description>       # recette + PR si score >= 70
/apex -rc -x <description>        # recette + review adversariale
/apex -rc -a <description>        # recette autonome (pas de confirmation)
```

### Pipeline modifie avec -rc

```
00 INIT → 01 ANALYZE → 02 PLAN → 03 EXECUTE
                                      ↓
                             04-RC : PDCA-C (65 checks)
                             ├── C.1 : Build & Compile (10 checks)
                             ├── C.2 : API & Dashboard (10 checks)
                             ├── C.3 : Frontend & Overlay (10 checks)
                             ├── C.4 : Security (10 checks)
                             ├── C.5 : Pedagogy Packs (15 checks)
                             └── C.6 : Code Quality (10 checks)
                                      ↓
                             SCORECARD /100 + PDCA verdict
                                      ↓
                             05 EXAMINE (si -x) → 09 FINISH
```

---

### ETAPE 04-RC : RECETTE PDCA-C

#### 04-RC.0 : Pre-flight gate (BLOQUANT)

```bash
# Angular build
cd juice-shop && timeout 600 npx ng build --configuration production 2>&1 | tail -3
# -> "Application bundle generation complete" = GO | erreurs = STOP

# Dashboard syntax
python -m py_compile dashboard/app.py dashboard/db.py
# -> exit 0 = GO | sinon = STOP

# Juice Shop reachable (si running)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# -> 200 = GO | autre = WARNING (checks shop marques N/A)

# Dashboard health (si running)
curl -s -o /dev/null -w "%{http_code}" http://localhost:5050/api/health
# -> 200 = GO | autre = WARNING

# Pedagogy lint baseline
python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py 2>&1 | tail -3
# -> noter le baseline (issues count) avant le swarm
```

Si un pre-flight echoue : **corriger et re-EXECUTE avant le swarm**.

#### 04-RC.0b : Swarm Context Sheet (OBLIGATOIRE)

Creer `.claude/output/apex/{task-id}/SWARM_CONTEXT.md` AVANT lancer agents.

```markdown
# SWARM CONTEXT — {task-id}

> Derniere MAJ : {timestamp}
> Phase : 04-RC PDCA-C

## Objectif de la session
{description originale de /apex}

## Etat du projet (snapshot pre-swarm)
- Juice Shop : {ONLINE port 3000 | OFFLINE}
- Dashboard : {ONLINE port 5050 | OFFLINE}
- Angular build : {OK | FAIL — detail}
- Dashboard syntax : {OK | FAIL}
- Pedagogy lint : {N issues | OK}
- Branche : {nom}
- Derniers fichiers modifies : {git diff --name-only HEAD~3, max 15}

## Decisions architecturales en vigueur
{Extraites de ETAPE 02 PLAN — i18n FR/EN/BR, schemas v2, parcours TD, hook 800 lignes}

## Agents actifs
| Agent | Categorie | Checks | Statut | Score | Bloquants trouves |
|-------|-----------|--------|--------|-------|--------------------|
| 1 | Build & Compile | C-01..C-10 | PENDING | -/10 | - |
| 2 | API & Dashboard | C-11..C-20 | PENDING | -/10 | - |
| 3 | Frontend & Overlay | C-21..C-30 | PENDING | -/10 | - |
| 4 | Security | C-31..C-40 | PENDING | -/10 | - |
| 5 | Pedagogy Packs | C-41..C-55 | PENDING | -/15 | - |
| 6 | Code Quality | C-56..C-65 | PENDING | -/10 | - |

## Decouvertes cross-agents
{Zone libre — chaque agent y consigne ce qui peut impacter les autres}

## Fichiers sensibles (ne pas modifier)
- juice-shop/frontend/src/assets/juicelab/selected_challenges.yml (parcours TD M2)
- juice-shop/data/static/challenges.yml (source de verite OWASP — 111 entrees)
- .claude/hooks/*.cjs (hooks bloquants)
```

Regles :
1. Chaque agent recoit le chemin dans son prompt
2. Chaque agent met a jour sa ligne en finissant
3. Decouvertes cross-agents partagees
4. L'orchestrateur relit pour aggregation (04-RC.2)
5. Mode resume (`-r`) : reprendre sans relancer agents termines

---

#### 04-RC.1 : Swarm 6 agents paralleles (UN SEUL MESSAGE, 6 Agent tool calls, model: haiku)

Avant lancement : substituer `<PROJECT_ROOT>` dans chaque prompt :

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
echo "PROJECT_ROOT = $PROJECT_ROOT"
```

Lancer tous les agents avec `run_in_background: true, model: haiku`.

---

**AGENT 1 — Build & Compile** (10 checks)

```
Tu es un agent de recette Build & Compile pour le projet juice (OWASP Juice Shop + JuiceLab overlay + Dashboard pedagogique).
Project root: <PROJECT_ROOT>
Swarm Context: Lis d'abord .claude/output/apex/<TASK_ID>/SWARM_CONTEXT.md pour le contexte global.
En finissant, mets a jour ta ligne (Agent 1) et consigne tes decouvertes cross-agents.
Execute les 10 checks suivants. Pour chaque check : resultat PASS/FAIL, valeur observee, detail si FAIL.

C-01 : cd juice-shop && timeout 600 npx ng build --configuration production termine sans error
C-02 : La sortie de ng build ne contient aucune ligne "ERROR" ou "Error " (warnings autorises)
C-03 : Aucune TypeScript error dans la sortie de ng build (TS_ERROR, TS2xxx, TS6xxx)
C-04 : python -m py_compile sur dashboard/app.py et dashboard/db.py — exit 0
C-05 : python -c "import sys; sys.path.insert(0,'dashboard'); import app" — exit 0
C-06 : Aucun fichier .yaml de pack contient ${ suivi de } (template literal interdit dans YAML)
C-07 : Aucun console.log() actif dans les fichiers .ts modifies recemment (git diff HEAD~5 --name-only sur juice-shop/frontend/src/)
C-08 : Aucun hardcoded "localhost" / "127.0.0.1" hors config.json et fichiers de tests
C-09 : Aucun hardcoded "localhost" / "127.0.0.1" dans dashboard/*.py hors config / commentaires
C-10 : Les hooks .claude/hooks/file_size_check.cjs et secret-scanner.cjs sont presents et executables

Produis un rapport JSON : {"category": "Build", "checks": [{"id":"C-01","result":"PASS"|"FAIL","observed":"...","detail":"..."}], "score": N/10}
```

---

**AGENT 2 — API & Dashboard** (10 checks)

```
Tu es un agent de recette API & Dashboard pour le projet juice.
Project root: <PROJECT_ROOT>
Swarm Context: Lis d'abord .claude/output/apex/<TASK_ID>/SWARM_CONTEXT.md.
En finissant, mets a jour ta ligne (Agent 2) et consigne tes decouvertes cross-agents.
Juice Shop port: 3000, Dashboard port: 5050. Si offline, marquer les checks HTTP comme N/A.

C-11 : GET http://localhost:5050/api/health retourne HTTP 200 et un JSON {"status":"ok"}
C-12 : Le code dashboard/app.py declare une route POST /api/sync (handler defini)
C-13 : Le code dashboard/app.py declare une route GET /api/cohort gated par DASHBOARD_TEACHER_TOKEN
C-14 : Le code dashboard/app.py declare une route GET /api/proof si DASHBOARD_PROOF_SECRET present
C-15 : GET / sur Juice Shop port 3000 retourne HTTP 200 et un HTML contenant "Juice Shop"
C-16 : Aucun endpoint dans dashboard/app.py retourne directement status_code=501 (stub interdit)
C-17 : Aucune route ne retourne de donnees mockees hardcodees (verifier les routes GET listes)
C-18 : Le SyncEvent TypeScript dans frontend/src/app/juicelab-overlay/models/juicelab.types.ts est synchronise avec ce que dashboard/db.py accepte (memes champs core)
C-19 : CORS est configure avec une allow-list (pas "*") dans dashboard/app.py
C-20 : Le HMAC secret (DASHBOARD_PROOF_SECRET) a une longueur minimale de 16 chars enforced dans le code (raise/exit si < 16)

Produis un rapport JSON : {"category": "API", "checks": [...], "score": N/10, "shop_online": true|false, "dash_online": true|false}
```

---

**AGENT 3 — Frontend & Overlay** (10 checks)

```
Tu es un agent de recette Frontend & Overlay pour le projet juice (Angular 17 + JuiceLab overlay).
Project root: <PROJECT_ROOT>
Swarm Context: Lis d'abord .claude/output/apex/<TASK_ID>/SWARM_CONTEXT.md.
En finissant, mets a jour ta ligne (Agent 3) et consigne tes decouvertes cross-agents.

C-21 : juice-shop/frontend/src/app/juicelab-overlay/models/juicelab-i18n.ts existe et contient au moins fr, en, br comme locales
C-22 : Aucun .ts dans frontend/src/app/juicelab-overlay/ contient une string UI hardcodee francaise (pattern: ' [A-Z][a-z]+\\? ' hors commentaire) — utiliser le catalogue i18n
C-23 : juice-shop/frontend/src/assets/juicelab/config.json est valide JSON et contient les cles backend/dashboard ports
C-24 : juice-shop/frontend/src/assets/juicelab/selected_challenges.yml contient les 13 challenges du parcours TD M2 (count == 13)
C-25 : Aucun composant Angular du juicelab-overlay ne fait fetch('http://localhost:5050' + ...) en dur (passer par config service)
C-26 : Chaque fichier briefing/<key>.yaml dans assets/juicelab/briefing/ a schema_version == "juicelab.briefing.v2"
C-27 : Tous les composants du juicelab-overlay (frontend/src/app/juicelab-overlay/) ont leurs strings UI passees par le catalogue i18n (pas de hardcode)
C-28 : juice-shop/frontend/src/assets/juicelab/login-helper.html existe (helper TD)
C-29 : La taille du bundle de production (juice-shop/frontend/dist/) ne depasse pas 10 MB (chunk principal main-*.js)
C-30 : Aucun import manquant dans les fichiers .ts modifies recemment (git diff --name-only HEAD~3 sur juice-shop/frontend/)

Produis un rapport JSON : {"category": "Frontend", "checks": [...], "score": N/10}
```

---

**AGENT 4 — Security** (10 checks)

```
Tu es un agent de recette Security pour le projet juice (OWASP defenders side).
Project root: <PROJECT_ROOT>
Swarm Context: Lis d'abord .claude/output/apex/<TASK_ID>/SWARM_CONTEXT.md.
En finissant, mets a jour ta ligne (Agent 4) et consigne tes decouvertes cross-agents.

C-31 : Aucun pattern d'injection SQL dans dashboard/*.py (f-string avec input user dans une query — chercher cur.execute(f"...{ ... }..."))
C-32 : Aucun eval() ou exec() avec input non valide dans dashboard/*.py
C-33 : Aucun pickle.loads() sans controle de source dans dashboard/*.py
C-34 : Aucune cle API, password, ou secret hardcode dans le code versionne (grep "api_key|password|secret" hors tests/docs ; ignorer DEFAULT_TEACHER_TOKEN dans juice.sh qui est commente comme placeholder)
C-35 : DEBUG=False ou absent dans la config de production (dashboard/app.py — pas app.run(debug=True))
C-36 : Le hook .claude/hooks/secret-scanner.cjs existe, est executable, et a un pattern pour AWS_, BEARER, eyJ, sk-
C-37 : CORS_ORIGINS dans dashboard/app.py est une allow-list precise (pas "*" sans condition)
C-38 : Aucun subprocess.run() avec shell=True et input utilisateur non sanitise dans dashboard/*.py
C-39 : Le hook .claude/hooks/process_guard.sh existe, est executable, et bloque les lancements directs hors juice.sh
C-40 : .gitignore inclut .env, .run/, .logs/, ctf.key, encryptionkeys/, node_modules

Produis un rapport JSON : {"category": "Security", "checks": [...], "score": N/10}
```

---

**AGENT 5 — Pedagogy Packs** (15 checks)

```
Tu es un agent de recette Pedagogy Packs pour le projet juice (OWASP Juice Shop Pedagogy Companion).
Project root: <PROJECT_ROOT>
Swarm Context: Lis d'abord .claude/output/apex/<TASK_ID>/SWARM_CONTEXT.md.
En finissant, mets a jour ta ligne (Agent 5) et consigne tes decouvertes cross-agents.

Tu peux executer le linter directement :
python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py
python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py --show-issues
python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py --source-audit

C-41 : lint_juicelab_pedagogy.py retourne 0 issues globales (schema, bilingue, cohorte)
C-42 : Tous les briefing/<key>.yaml dans juice-shop/frontend/src/assets/juicelab/briefing/ ont schema_version == "juicelab.briefing.v2"
C-43 : Tous les hints/<key>.yaml dans juice-shop/data/juicelab-private/hints/ ont les niveaux N1..N5 avec cost_pct exact 5/10/20/35/50
C-44 : Tous les quiz/<key>.yaml dans juice-shop/data/juicelab-private/quiz/ ont exactement 3 questions (Q1, Q2, Q3)
C-45 : Chaque quiz a 4 options exactement par question (options_fr.length == options_en.length == options_br.length == 4)
C-46 : Chaque quiz a un champ correct entre 0 et 3 inclus
C-47 : Chaque briefing a 3-4 concepts MAX (concepts array length entre 3 et 4)
C-48 : Bilingue strict : chaque _fr a son _en, chaque _en a son _br (grep _fr|_en|_br retourne un count divisible par 3 sur chaque fichier pack)
C-49 : Chaque briefing concept cite au moins une source factuelle (mention OWASP, CWE, RFC, ou reference papier dans body_*)
C-50 : Chaque hint a un champ pedagogical_intent non vide et non generique ("give the student a hint" = FAIL)
C-51 : Le TRACKER.md (.claude/output/owasp-pedagogy-companion/TRACKER.md) est sync avec les fichiers DONE (count fichiers briefing/ == count statut DONE briefing)
C-52 : Aucun pack ne touche un des 13 challenges du parcours TD M2 sans accord explicite (verifier git diff vs selected_challenges.yml)
C-53 : Aucun fichier yaml de pack ne depasse 800 lignes (hook file_size_check.cjs)
C-54 : Le linter lance avec --source-audit ne reporte pas plus de SOURCE-THIN que la baseline pre-swarm (regression check)
C-55 : Les BLOCKED dans TRACKER.md ont tous une raison documentee (colonne notes commence par "BLOCKED:")

Produis un rapport JSON : {"category": "Pedagogy", "checks": [...], "score": N/15, "lint_baseline": "<count avant swarm>", "lint_after": "<count apres>"}
```

---

**AGENT 6 — Code Quality** (10 checks)

```
Tu es un agent de recette Code Quality pour le projet juice.
Project root: <PROJECT_ROOT>
Swarm Context: Lis d'abord .claude/output/apex/<TASK_ID>/SWARM_CONTEXT.md.
En finissant, mets a jour ta ligne (Agent 6) et consigne tes decouvertes cross-agents.

C-56 : Aucun fichier source > 800 lignes (find juice-shop/frontend/src dashboard/ overlay/ -name "*.ts" -o -name "*.py" -o -name "*.yaml" | xargs wc -l | awk '$1 > 800 && $2 != "total"')
C-57 : Aucun emoji dans le code (grep emoji range dans juice-shop/frontend/src/, dashboard/*.py, overlay/, .claude/skills/, hors fichiers .md docs)
C-58 : CLAUDE.md a une section "ZERO PLACEHOLDER / ZERO DECORATIVE / ZERO HARDCODING"
C-59 : Aucun TODO / FIXME / placeholder / coming soon dans les fichiers modifies recemment (git diff HEAD~5)
C-60 : Aucun setTimeout simulant une reponse async dans juice-shop/frontend/src/app/juicelab-overlay/ (pattern: setTimeout(.+, [0-9]+ms)) hors animations legitimes
C-61 : Tous les fichiers .yaml de packs parsent sans erreur (python -c "import yaml; yaml.safe_load(open(f))" sur tous les yaml)
C-62 : Les fichiers modifies par la tache courante (git diff --name-only HEAD) ne contiennent pas de chaines hardcodees non-i18n (regex grossiere)
C-63 : git status ne liste aucun fichier .env, ctf.key, ou credentials dans "Untracked files" ni "Modified"
C-64 : Le tracker .claude/output/owasp-pedagogy-companion/TRACKER.md affiche le pourcentage DONE en temps reel (pas de chiffre stale)
C-65 : python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py --update-tracker s'execute sans erreur

Produis un rapport JSON : {"category": "Quality", "checks": [...], "score": N/10}
```

---

#### 04-RC.2 : Aggregation + Scorecard PDCA

Apres completion des 6 agents, consolider :

```
PDCA SCORECARD
══════════════════════════════════════════════
Category                Score    Weight   Weighted
──────────────────────────────────────────────
C.1 Build & Compile     N/10     15%      X.X
C.2 API & Dashboard     N/10     15%      X.X
C.3 Frontend & Overlay  N/10     15%      X.X
C.4 Security            N/10     20%      X.X
C.5 Pedagogy Packs      N/15     25%      X.X
C.6 Code Quality        N/10     10%      X.X
──────────────────────────────────────────────
TOTAL                            100%     XX/100
══════════════════════════════════════════════

Verdict : PASS (>= 70) | CONDITIONAL (50-69) | FAIL (< 50)

FAILs critiques (bloquants pour PR) :
  - C-01 : ng build cassait                              [Build]
  - C-34 : secret hardcode detecte                       [Security]
  - C-41 : lint pedagogy reporte issues                  [Pedagogy]
  - C-52 : parcours TD touche sans accord                [Pedagogy]
  - C-56 : fichier > 800 lignes                          [Quality]

FAILs non-bloquants (a corriger au prochain cycle) :
  - ...
```

Sauvegarder dans `.claude/output/apex/{task-id}/C_SCORECARD.json` et `C_SCORECARD.md`.

#### 04-RC.3 : Remediation immediate (si FAIL critique)

Pour chaque FAIL critique :
1. Corriger immediatement (retour en EXECUTE)
2. Re-lancer l'agent concerne sur le seul check (pas tout le swarm)
3. MAJ scorecard

Si 3+ aller-retours sans resolution : documenter dans `C_BLOCKERS.md` et continuer avec CONDITIONAL.

#### 04-RC.4 : Integration dans ETAPE 09

Dans ETAPE 09 (FINISH) :
- Score PDCA dans le tracking plan
- Si score < 70 : ouvrir une note "PDCA debt" avec FAILs non-bloquants
- Si `-pr` actif : n'ouvrir la PR que si score >= 70 (sinon CONDITIONAL warning dans corps PR)

---

### Checks par categorie — reference rapide

| ID | Categorie | Check | Bloquant PR |
|----|-----------|-------|-------------|
| C-01 | Build | ng build succeeds | OUI |
| C-04 | Build | py_compile dashboard 0 erreurs | OUI |
| C-06 | Build | No template literals in YAML packs | OUI |
| C-11 | API | /api/health HTTP 200 | NON |
| C-13 | API | /api/cohort gated by token | OUI |
| C-16 | API | No 501 stubs | OUI |
| C-19 | API | CORS allow-list (pas *) | OUI |
| C-20 | API | HMAC secret length >= 16 | OUI |
| C-21 | Frontend | i18n catalogue FR/EN/BR exists | OUI |
| C-22 | Frontend | No hardcoded FR strings in overlay | OUI |
| C-24 | Frontend | Parcours TD count == 13 | OUI |
| C-31 | Security | No SQL injection f-strings | OUI |
| C-34 | Security | No hardcoded secrets | OUI |
| C-36 | Security | secret-scanner hook active | OUI |
| C-39 | Security | process_guard hook active | OUI |
| C-40 | Security | .env/ctf.key/keys gitignored | OUI |
| C-41 | Pedagogy | lint_juicelab_pedagogy 0 issues | OUI |
| C-42 | Pedagogy | briefing schema v2 | OUI |
| C-43 | Pedagogy | hints cohort 5/10/20/35/50 | OUI |
| C-44 | Pedagogy | quiz 3 questions | OUI |
| C-45 | Pedagogy | quiz 4 options bilingual | OUI |
| C-52 | Pedagogy | Parcours TD intact | OUI |
| C-53 | Pedagogy | Pack yaml < 800 lines | OUI |
| C-56 | Quality | All files < 800 lines | OUI |
| C-57 | Quality | No emoji in code | OUI |
| C-65 | Quality | --update-tracker works | NON |

**Regles bloquant PR :** Si 1+ check "bloquant PR" = FAIL, la PR ne peut pas etre ouverte sans accord explicite de l'utilisateur.

---

## Epilogue — memory check

Apres ETAPE 09 (FINISH), si le user a une skill memoire active (auto-memory-bounded, dream),
laisser le hook tourner ; ne pas appeler les skills memoire en plus si non requis.
