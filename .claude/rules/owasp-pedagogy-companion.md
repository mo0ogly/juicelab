# Rule — OWASP Juice Shop Pedagogy Companion

Production rigoureuse d'un pack pédagogique trilingue (briefing + hints
gradués + quiz QCM) pour les **111 challenges natifs OWASP Juice Shop**,
en vue d'une contribution upstream sous forme d'extension officielle
"Juice Shop Pedagogy Companion".

## Why this rule exists

Le user a explicitement demandé (2026-05-09) :

> "j'aimerai que tu fasses ça pour tous les challenges de la plateforme
> comme ça je pourrai les renvoyer à OWASP. Sois detaillé, je préfère
> la qualité. Pas d'invention, pas de précipitation."

Trois conséquences directes :

1. **Pas d'invention** = chaque pack DOIT être ancré sur des sources
   factuelles vérifiables (description OWASP, code source de la vuln,
   tutorial natif s'il existe, hint upstream s'il existe).
2. **Qualité > volume** = il vaut mieux 5 packs irréprochables par session
   que 30 packs creux. Pas de copier-coller cosmétique entre challenges
   similaires : chaque mécanique a ses propres concepts.
3. **Tracking auditable** = chaque production doit être reproductible et
   vérifiable a posteriori (quelles sources ont été lues, par qui,
   quand). Le tracker partagé est l'unique source de vérité du progrès.

Cette rule s'applique en plus de — pas en remplacement de — la skill
`juicelab-add-challenge`. Elle prolonge le scope autorisé aux 98
challenges hors parcours TD, **uniquement** pour la production du pack
upstream.

## Hard rules (BLOQUANT)

| # | Rule | Enforcement |
|---|---|---|
| 1 | **Pre-flight obligatoire** : avant d'écrire UN SEUL caractère de briefing/hints/quiz pour un challenge, marquer la case `sources_read` du tracker ET citer dans le pack au moins une source factuelle (description OWASP officielle, ligne de code de la vuln, ou tutorial natif). | Refus de la production si `sources_read = -` dans le tracker. |
| 2 | **Pas de copier-coller inter-challenge** : deux challenges qui partagent une catégorie (ex. plusieurs Reset Password) DOIVENT avoir des concepts distincts qui reflètent la mécanique propre à chacun. | Audit par diff : si deux pack briefing ont >40% de phrases identiques, refus. |
| 3 | **Pas de challenge marqué BLOCKED traité** : les challenges dépréciés (csrfChallenge avec FIXME upstream, par exemple) restent en statut BLOCKED, NE sont PAS produits. | Lire le commentaire à côté du `key:` dans `data/static/challenges.yml` avant chaque production. |
| 4 | **Bilingue strict** : chaque `*_fr` a son `*_en`, chaque `options_fr` a `options_en` de même longueur, chaque `explanation_fr` a `explanation_en`. | grep `_fr\|_en` dans le yaml = nombre pair. |
| 5 | **File size < 800 lignes** par yaml. | Hook `file_size_check.cjs` (déjà actif). |
| 6 | **Tracker mis à jour DANS la même session** que la production. Pas de drift entre fichiers produits et statut tracker. | Audit hebdomadaire par diff `ls briefing/ vs tracker DONE`. |

## Sources factuelles obligatoires (par challenge)

Avant d'écrire le pack pour un challenge `<key>`, lire et citer mentalement :

1. **`juice-shop/data/static/challenges.yml`** — entrée du challenge avec
   `name`, `category`, `description`, `difficulty`, `tags`, et tout
   commentaire FIXME. Description = source primaire de la mission.
2. **`juice-shop/frontend/src/hacking-instructor/challenges/<key>.ts`** — si
   présent, contient le tutorial natif OWASP avec étapes guidées,
   payloads exacts, sélecteurs CSS. Source primaire pour les hints
   gradués et l'écriture de la mission.
3. **`juice-shop/data/static/codefixes/<key>/`** — si présent, contient le
   code vulnérable + le fix. Source primaire pour le concept "défense
   canonique".
4. **`juice-shop/routes/<key>.ts`** ou **`juice-shop/lib/`** — code source
   serveur de la vuln (rarement nécessaire mais utile pour challenges
   d'injection / auth).

Si aucune des 4 sources ci-dessus n'est trouvable pour un challenge :
le challenge est marqué `BLOCKED` (sources insuffisantes pour
production qualité) et le user est informé pour décision manuelle.

## Format de livraison v2 — schémas

### `assets/juicelab/briefing/<key>.yaml`

```yaml
challenge_key: "<key>"
schema_version: "juicelab.briefing.v2"

mission_fr: |
  3-6 lignes, voix imperative, qui repondent a 3 questions :
  - Quel est l'objectif technique exact ?
  - Quelle est la categorie OWASP ?
  - Quelle est la methode recommandee ?
mission_en: |
  Same structure in English.

concepts:
  - title_fr: "<concept name FR>"
    title_en: "<concept name EN>"
    body_fr: |
      3-5 lignes par concept, ancrage technique avec references
      (OWASP top, RFC, CWE quand pertinent).
    body_en: |
      Same in English.
  # 3 ou 4 concepts MAX (skill juicelab-add-challenge fixe la borne)
```

### `data/juicelab-private/hints/<key>.yaml`

```yaml
challenge_key: "<key>"
schema_version: "juicelab.hints.v2"

hints:
  N1: { cost_pct: 5,  text_fr: "...", text_en: "...", pedagogical_intent: "..." }
  N2: { cost_pct: 10, ... pedagogical_intent: "..." }
  N3: { cost_pct: 20, ... pedagogical_intent: "..." }
  N4: { cost_pct: 35, ... pedagogical_intent: "..." }
  N5: { cost_pct: 50, ... pedagogical_intent: "..." }
```

Cohorte de coût FIXE : 5 / 10 / 20 / 35 / 50. Toute déviation casse
`HINT_COST_BY_LEVEL` et `JuicelabScoringService`. Refus.

### `data/juicelab-private/quiz/<key>.yaml`

```yaml
challenge_key: "<key>"
schema_version: "juicelab.quiz.v2"

quiz:
  Q1:
    type: multiple_choice          # impose
    question_fr: "..."
    question_en: "..."
    options_fr: [ ..., ..., ..., ... ]   # exactement 4 options
    options_en: [ ..., ..., ..., ... ]   # meme longueur
    correct: <int 0-3>
    explanation_fr: |
      ...
    explanation_en: |
      ...
  Q2: ...
  Q3: ...
```

Trois questions par challenge. `correct` est un index 0-based.

## Procédure standard par challenge

```
1. Ouvrir le tracker, vérifier que <key> est en TODO (sinon STOP).
2. Pre-flight : lire les 4 sources (challenges.yml, hacking-instructor,
   codefixes, route). Cocher `sources_read` avec date YYYY-MM-DD.
3. Rédiger le briefing yaml en respectant schema v2. Bilingue strict.
4. Rédiger le hints yaml avec cohorte 5/10/20/35/50. Pedagogical_intent
   par niveau.
5. Rédiger le quiz yaml avec 3 QCM 4-options bilingues + explanations
   bilingues.
6. (Optionnel) Rédiger le journal yaml si pertinent (v1 OK, fallback
   briefing accepté sinon).
7. Build gate : `npx ng build --configuration production` doit passer.
8. Mettre à jour le tracker : statut DONE pour les 4 packs, date,
   notes brèves.
```

## Quality gates (post-production par challenge)

| Gate | Critère | Outil |
|---|---|---|
| **Schema** | yaml parse sans erreur, schema_version correct | `python -c "import yaml; yaml.safe_load(open('...'))"` |
| **Bilingue** | grep `_fr|_en` retourne nombre pair, options_fr.len == options_en.len | grep + manual review |
| **Cohorte hints** | 5 / 10 / 20 / 35 / 50 exact | grep cost_pct |
| **Quiz correct** | int 0-3 sur chaque Q, jamais hors bornes | grep correct: |
| **File size** | < 800 lignes par yaml | wc -l |
| **Build** | npx ng build passe | npx ng build |
| **Sources** | au moins 1 source citée dans le briefing concepts | review |

Aucun lot n'est "DONE" tant que les 7 gates ne sont pas vertes.

## Tracking — `.claude/output/owasp-pedagogy-companion/TRACKER.md`

Le tracker est l'unique source de vérité du progrès. Format imposé :

| key | category | difficulty | sources_read | briefing | hints | quiz | journal | notes |

Statuts autorisés par cellule :

- `TODO` — jamais commencé
- `IN_PROGRESS` — production en cours dans la session courante
- `DONE` — pack livré, gates vertes, build OK
- `BLOCKED` — challenge déprécié, source manquante, ou décision manuelle requise
- `-` (tiret) — pack non requis (ex. journal optionnel)

Cellule `sources_read` :

- `-` avant pre-flight
- `YYYY-MM-DD` après lecture des sources

Cellule `notes` :

- `BLOCKED: <raison>` si applicable
- `parcours TD` pour les 13 du M2 Sorbonne
- Sinon vide

## Intégration upstream OWASP

Format de livraison à OWASP Juice Shop :

- **Repo cible** : nouveau repo séparé `owasp-juice-shop-pedagogy-companion` (à créer)
- **Format proposé** : YAML v2 documenté ci-dessus, présenté comme extension
- **Process** : PR sur le repo OWASP avec README expliquant le format,
  exemples, et integration côté Juice Shop core (chargement optionnel
  des yamls v2 via une route opt-in)
- **Plan B** : si OWASP refuse le format, le repo reste utilisable comme
  companion installable via npm/git submodule par les enseignants qui
  utilisent Juice Shop pour des TD

Décision finale du user (2026-05-09) : **option (b)** — proposer le
format riche à OWASP, accepter le risque de refus.

## Source-thin challenges — handling specifique (depuis 2026-05-10)

Apres le sweep des sources sur les 74 TODO restants (Lot 3 RETEX),
58 challenges sont classes "SOURCE-THIN" : aucun codefixes officiel,
aucun hacking-instructor. Seules sources : description + hints
OWASP de `challenges.yml` + cheatsheet OWASP linke en
mitigationUrl.

Pour ces 58 challenges, procedure de production renforcee :

1. **Pre-flight etendu** :
   - Lire la description + tous les hints + mitigationUrl de
     `challenges.yml` (comme d'habitude).
   - Grep `juice-shop/routes/` et `juice-shop/lib/` pour identifier
     la route serveur exacte et le code de la vuln.
   - Grep `juice-shop/server.ts` pour le routing + middleware.
   - Grep `juice-shop/ftp/` (si applicable) pour les artefacts.
   - Cocher `sources_read` avec date dans le tracker.

2. **Etiquetage de confiance dans les concepts** :
   - Si la kill chain est documentee/inferable du code, etiqueter
     `[KILL_CHAIN_DOCUMENTED]`.
   - Si la kill chain est conjecturale apres recon, etiqueter
     `[KILL_CHAIN_PROBABLE]` (cf. videoXssChallenge Lot 3).
   - Si la mecanique reste opaque malgre recherche, etiqueter
     `[KILL_CHAIN_UNCERTAIN]` et signaler explicitement au student
     dans le briefing que le tatonnement est intentionnel par
     design OWASP.

3. **Ne JAMAIS inventer une certitude technique** que la source ne
   permet pas. Mieux vaut un briefing qui dit "le pattern probable
   est X mais ajuste selon la version" qu'un briefing qui prescrit
   un payload faux et frustrant.

4. **Cross-validation automatique** : apres production, lancer
   `python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py`
   pour valider schemas + bilingue + cohorte hints.

## Static analysis tooling

Le script `.claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py`
fournit :

- `--update-tracker` : met a jour le bloc Statut global du TRACKER.md
- `--show-issues` : affiche les issues par challenge (verbose)
- `--source-audit` : liste les TODO par categorie de source
  disponible (RICH, CODEFIXES only, HACKING-INSTRUCTOR only,
  SOURCE-THIN)

A lancer apres CHAQUE lot pour update auto du tracker et detection
auto des bugs (paires bilingues, cohorte hints, etc.).

## Anti-patterns documentés

- **Production sans pre-flight** : écrire un briefing en partant de
  l'intuition sur le nom du challenge. Détecté quand les concepts ne
  citent ni la description OWASP ni le code. Refus + redo.
- **Briefing copier-collé** : deux challenges de la même catégorie qui
  partagent 80% du texte. Détecté par diff. Refus + redo.
- **Skip du tracker** : produire 5 packs sans cocher le tracker. Le
  tracker dérive de la réalité, audit ulterieur impossible. Toute
  session se TERMINE par une mise à jour tracker.
- **`pedagogical_intent` creux** : "give the student a hint" est inutile.
  Doit citer une fonction cognitive précise (activate reflex, localize
  surface, narrow down by lexical clue, give syntactic shape, full
  solution).
- **Quiz à options évidentes** : 3 options absurdes + 1 vraie = QCM mort.
  Les distracteurs DOIVENT être plausibles pour un étudiant qui n'a
  pas lu le pack.

## RETEX

À tenir à jour dans le tracker, section `## Notes de session` après
chaque batch :

```
### YYYY-MM-DD — Batch N (X challenges)

Challenges produits : <liste>
Sources avec source manquante : <liste, BLOCKED>
Temps moyen par challenge : <minutes>
Patterns reusables identifies : <liste>
Decisions de qualite : <liste, ex. "rejete copier-colle entre
loginAdmin et loginBender">
```
