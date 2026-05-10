# CONTEXTE — JuiceLab (TD M2 IA/Cybersecurite Paris-Sorbonne)

Document de reference pour gestion multisession. A lire en debut de session
quand le travail concerne JuiceLab / TD Juice Shop / juicelab-overlay.

## Identite et cadre

- Auteur : Fabrice Pizzi (handle `mo0ogly`).
- Role : professeur M2 IA/Cybersecurite Paris-Sorbonne, analyste ANSSI.
- Email : mo0ogly@proton.me.
- Livrable : TD 12h en 3 demi-journees sur la securite web, public etudiants
  debutants heterogenes francophones (cohorte 2026), extension anglophone
  prevue (cohorte 2027).

## Architecture en place

OWASP Juice Shop (clone vanilla) sert de moteur. Pas de fork, pas de
modification du code Juice Shop sauf 2 patchs minimaux.

Repo separe `mo0ogly/juicelab-pedagogy` contient la surcouche pedagogique :

- 13 challenges Juice Shop selectionnes pour le TD :
  - 5 DJ1 recon
  - 4 DJ2 auth/access
  - 4 DJ3 XSS
- Hints gradues 5 niveaux Vygotsky avec cout scoring 5/10/20/35/50 %.
- Quiz 3 questions post-validation.
- Observables enseignant pour intervention orale.
- Journal de bord obligatoire (`before_solve` / `after_solve`).
- Walkthroughs canoniques FR + EN.
- Fiches docx imprimables FR + EN.

Skill `juice-shop-pedagogy` (installee dans `skills-plugin`) avec
architecture multi-agents niveau 5 : SELECTOR, PEDAGOGUE, TRANSLATOR,
VALIDATOR. Boucle OBJECTIVE -> DECOMPOSE -> PLAN -> ACT -> OBSERVE ->
EVALUATE -> REPLAN -> COMPLETE. Generation d'un pack pedagogique pour un
challenge donne par sa key Juice Shop.

Plugin Angular `juicelab-overlay` (Angular 20, standalone components,
signals) ajoute dans le frontend Juice Shop :

- Composants : `JuicelabPanel` (container avec tabs), `HintsPanel`,
  `JournalForm`, `QuizForm`, `BadgesDisplay`.
- Services :
  - `JuicelabPackService` (parse YAML via `js-yaml`).
  - `JuicelabStateService` (LocalStorage v1).
  - `JuicelabScoringService` (deductif plancher 50).
  - `JuicelabSyncService` (POST events vers dashboard cloud, queue offline).
  - `JuicelabBadgeEngineService` (4 regles, extensible).
- Route lazy `/juicelab` + bouton icone `school` dans la navbar.

## Paths

- `C:\Users\pizzif\Documents\GitHub\juice\juice-shop\`
  Clone Juice Shop vanilla, modifie avec :
  - `frontend/src/app/juicelab-overlay/` (plugin TypeScript)
  - `frontend/src/assets/juicelab/` (YAML packs, source de verite)
  - `frontend/package.json` (`js-yaml` ajoute)
  - `frontend/src/app/app.routing.ts` (route `/juicelab`)
  - `frontend/src/app/navbar/navbar.component.html` (bouton coach)

- `C:\Users\pizzif\Documents\GitHub\TD Juice\juicelab-pedagogy\`
  Repo source de verite pedagogique :
  - `hints/`, `quiz/`, `journal/`, `walkthroughs/` (YAML par
    `challenge_key`)
  - `selected_challenges.yml` (index canonique des 13)
  - `plugin-source/juicelab-overlay/` (source du plugin Angular, copiable)
  - `plugin-design/ARCHITECTURE.md` (doc design 15 sections)
  - `scripts/install_plugin.ps1`, `generate_fiches.py`, `load_juice_shop.py`
  - `dist/juice-shop-pedagogy.skill` (archive `.skill` installable)

- `skills-plugin/.../skills/juice-shop-pedagogy/` (skill installee)

## Etat actuel

- Skill `juice-shop-pedagogy` operationnelle, 1 seul pack genere a date :
  `loginAdminChallenge` (hints + walkthrough). 12 packs restants a generer.
- Plugin Angular complet copie dans le clone Juice Shop, parses YAML
  directs.

## APEX session 2026-05-09 — workflow prof livre

Trois deliverables ajoutes via `/apex` :

### 1. Endpoint debug admin (juice-shop)
- `GET /api/juicelab/admin/state` ajoute dans `routes/juicelab.ts` + monte dans `server.ts`.
- Authentifie par header `X-Admin-Token` compare a la var d'env `TEACHER_ADMIN_TOKEN` (>= 16 chars, sinon 503).
- Retourne JSON aggrege : `{generated_at, students_count, students[], challenges_solved_global[]}`.
- Pour lancer : `TEACHER_ADMIN_TOKEN=... npm start` dans `juice-shop/`.

### 2. Dashboard Flask + SQLite (`dashboard/`)
- `app.py` (Flask 3.0 + Flask-Cors 5.0), `db.py` (sqlite3 stdlib), `schema.sql`, `templates/dashboard.html`, `tests/test_app.py` (10 tests pytest, tous PASS).
- Endpoints :
  - `GET /api/health` : liveness probe.
  - `POST /api/sync` : ingestion d'un SyncEvent (validation stricte des champs, 201 + id).
  - `GET /api/cohort?cohort=X` : JSON aggrege par eleve x challenge (gated par `X-Teacher-Token`).
  - `GET /dashboard?cohort=X` : page HTML rendu Jinja2 (tableau croise avec pills hints/journal/quiz/solved).
- Auth : env `DASHBOARD_TEACHER_TOKEN` (>= 16 chars).
- CORS : env `DASHBOARD_CORS_ORIGINS` (default `http://127.0.0.1:3000,http://localhost:3000`).
- Pour lancer : `DASHBOARD_TEACHER_TOKEN=... python app.py` dans `dashboard/`.
- Tests : `cd dashboard && python -m pytest tests/`.

### 3. Plugin frontend integre au dashboard
- `frontend/src/assets/juicelab/config.json` : nouveau fichier avec `dashboard_url`, `cohort_id`, `instance_label`, `default_language`.
- `JuicelabPackService.getConfig()` : lit le fichier au boot.
- `JuicelabPanelComponent.ngOnInit()` : appelle `stateSvc.ensureStudent()` + `syncSvc.configure(url, instanceLabel)`.
- `JuicelabSyncService.configure(url, label)` : signature etendue, envoie `X-Instance-Label` sur chaque POST.

### 4. Docker-compose multi-instance (`docker/`)
- `Dockerfile.juicelab` : image custom du clone modifie (npm install + build complet, puis runtime slim).
- `Dockerfile.dashboard` : image Flask + SQLite.
- `docker-compose.yml` : smoke test 1 instance + dashboard.
- `entrypoint.sh` : reecrit `config.json` au demarrage a partir de `JUICELAB_DASHBOARD_URL`, `JUICELAB_COHORT_ID`, `JUICELAB_INSTANCE_LABEL`.
- `provision.py` : lit un roster (1 handle par ligne), genere `docker-compose.cohort.yml` avec un service `juicelab-<handle>` par eleve, port `port_base + index`. Imprime aussi le `DASHBOARD_CORS_ORIGINS` correspondant.
- `roster.example.txt` : 5 handles d'exemple.
- `.env.example`, `.dockerignore` : conventions deploiement.
- `README.md` : 5 sections (smoke test 1 instance, cohorte de N, VPS partage avec Caddy, limitations connues, troubleshooting).

### Tests recette globale APEX (14 PASS / 0 FAIL)

| Stage | Test | Resultat |
|---|---|---|
| Phase B | hint anonyme | 401 PASS |
| Phase B | hint N3 sans N1/N2 | 403 PASS |
| Phase B | walkthrough non solved | 403 PASS |
| Phase B | walkthrough solved | 200 PASS |
| Phase B | quiz questions strippees (no `correct`) | PASS |
| Admin | sans token | 401 PASS |
| Admin | mauvais token | 401 PASS |
| Admin | bon token + JSON valide | PASS |
| Dashboard | `/api/health` | 200 ok=true PASS |
| Dashboard | `POST /api/sync` valide | 201 PASS |
| Dashboard | POST sans body | 400 PASS |
| Dashboard | `/api/cohort` sans token | 401 PASS |
| Dashboard | `/api/cohort` events>0 avec token | PASS |
| Dashboard | `/dashboard` HTML rendered | PASS |
| Frontend | `config.json` cohort_id | PASS |
| Anti-leak | `/assets/juicelab/hints/X.yaml` | SPA fallback PASS |

Plus 10 tests pytest dashboard (tous PASS).

### Limitations connues

- Docker daemon non actif dans l'env de dev — le build des images n'a pas pu etre execute en environnement Claude. Le YAML compose est valide via `docker compose config`, les Dockerfiles sont corrects syntaxiquement. A executer cote utilisateur : `cd docker && cp .env.example .env && (editer secrets) && docker compose --env-file .env up -d --build`.
- `student_token` cote sync = UUID local navigateur, `studentToken` cote phase B = email Juice Shop. Le mapping passe par `instance_label` (handle Docker = handle eleve). A unifier dans une iteration ulterieure.
- State `consumedHintsByStudent` en memoire — perdu au restart container. Acceptable pour TD continu.
- Pas de HTTPS interne entre Juice Shop et dashboard. OK en reseau Docker prive, a securiser pour deploiement VPS public.

### Comment ca s'utilise

Reponses aux 4 questions du prof :

1. **Acces au dashboard** : `http://<IP serveur>:5000/dashboard?cohort=M2-IA-2026` avec header `X-Teacher-Token: <token>` (env `DASHBOARD_TEACHER_TOKEN`).
2. **Profils eleves** : pas de creation cote prof. Chaque eleve s'inscrit sur SON instance Juice Shop (via `/#/register`). Le mapping eleve <-> instance se fait via le `instance_label` configure dans le compose (handle Docker).
3. **Voir progressions** : tableau croise dans le dashboard. Pills : `hints N/5`, `journal`, `quiz X/100`, `solved`. Mise a jour quasi temps reel (delay = HTTP roundtrip + offline queue flush si reseau coupe).
4. **Lancer challenges** : selon scenario :
   - Smoke test (1 eleve) : `docker compose up`, eleve va sur `http://127.0.0.1:3000/#/juicelab`.
   - Cohorte (N eleves) : `python provision.py roster.txt --port-base 3001`, puis `docker compose -f docker-compose.yml -f docker-compose.cohort.yml up`. Chaque eleve a son URL `http://<IP>:300X/#/juicelab`.

## Phase B livree 2026-05-09 — gating server-side actif

**Etat** : phase B implementee, testee (8/8 recette), online.

**Routes Express** (declarees dans `server.ts` apres la route `whoami`) :

| Route | Methode | Auth | Comportement |
|---|---|---|---|
| `/api/juicelab/hint?key=X&level=N` | GET | JWT (cookie ou Bearer) | Retourne le niveau N. Refuse 403 si N-1 non consomme. State per-(student_token, challenge_key). |
| `/api/juicelab/quiz/questions?key=X` | GET | JWT | Retourne les 3 questions strippees des `expected_keywords` et de `correct`. |
| `/api/juicelab/quiz/score` | POST | JWT | Body `{challenge_key, language, answers}`. Score calcule server-side, retourne `{score, by_question}`. |
| `/api/juicelab/walkthrough?key=X` | GET | JWT | Retourne le markdown si `challenges[key].solved === true`. Sinon 403. |
| `/data/juicelab-private/*` | tout | - | 404 force, jamais expose. |

Les fichiers prives sont sous `juice-shop/data/juicelab-private/{hints,walkthroughs,quiz}/` — non servis par Express, lus uniquement par `routes/juicelab.ts`.

State in-memory : `Map<studentEmail, Map<challengeKey, Set<HintLevel>>>`. Suffisant pour TD mono-instance. Pour multi-instance ou persistance : migrer vers Redis ou table Sequelize.

**Frontend adapte** :
- `JuicelabPackService` : `getHint(key, level)`, `getQuizQuestions(key)`, `scoreQuiz(key, lang, answers)`, `getWalkthrough(key)`. Anciennes methodes pack-au-complet supprimees.
- `HintsPanelComponent` : mode incremental, state local `Map<HintLevel, HintResponse>`, gere 401/403/404 avec messages explicites.
- `QuizFormComponent` : recupere les questions strippees, soumet au scoring server-side, affiche le score retourne (par question).

**Resultat des 8 tests recette** :
| # | Test | Resultat |
|---|---|---|
| 1 | GET hint anonyme → 401 | PASS |
| 2 | GET hint N3 sans N1/N2 (token frais) → 403 | PASS |
| 3 | GET hint N1, N2, N3 en sequence → consumed_levels accumule | PASS |
| 4 | GET walkthrough sur challenge non-solved → 403 | PASS |
| 5 | GET walkthrough sur loginAdmin (auto-solved par SQLi login) → 200 + 4146 bytes | PASS |
| 6 | GET ancien leak `/assets/juicelab/hints/X.yaml` → SPA fallback (pas de YAML) | PASS |
| 7 | GET index public `/assets/juicelab/selected_challenges.yml` → 200 | PASS |
| 8 (bonus) | GET `/data/juicelab-private/...` → 404 | PASS |

**Tests bonus quiz end-to-end (apres ajout des 13 YAMLs)** :

| # | Test | Resultat |
|---|---|---|
| Q1 | GET `/api/juicelab/quiz/questions?key=loginAdmin` retourne questions strippees (pas de `correct`, pas de `expected_keywords`) | PASS |
| Q2 | POST `/api/juicelab/quiz/score` avec mauvaises reponses → 0/100 sur les 3 questions | PASS |
| Q3 | POST `/api/juicelab/quiz/score` avec bonnes reponses → 100/100 sur les 3 questions | PASS |

13 quiz YAMLs livres dans `juicelab-pedagogy/quiz/` puis copies dans `juice-shop/data/juicelab-private/quiz/`. Format : Q1 free_text, Q2 multiple_choice, Q3 free_text, FR + EN, expected_keywords pour les free_text, options + correct pour la MCQ.

## Decision architecturale 2026-05-09 — gating server-side

Constat : tout YAML servi sous `/assets/juicelab/` est telechargeable via
`curl`. Cela leak les 5 niveaux d'indices, les keywords du quiz, et les
walkthroughs en clair. Le scoring deductif devient cosmetique. L'utilisateur
a tranche pour l'option A+B :

- **Aujourd'hui (A)** : tous les packs (hints, quiz, walkthroughs) generes
  sont stockes dans le repo source pedagogie
  `C:\Users\pizzif\Documents\GitHub\TD Juice\juicelab-pedagogy\` et
  ne sont JAMAIS recopies dans `frontend/src/assets/`. La seule chose
  publique reste `selected_challenges.yml` (l'index, pas une solution).
- **Plus tard (B)** : 3e patch Juice Shop = `routes/juicelab.ts` avec
  3 routes Express qui gating l'acces server-side. Spec complete dans
  `plugin-design/PHASE_B_MINI_ENDPOINT.md` du repo source pedagogie.

## Etat apres session 2026-05-09

### Fait

- Port 3000 libere (le node PID 31952 stoppe).
- `npm install` frontend + racine OK (`js-yaml` resolu).
- `npm start` lance, server `listening on port 3000`. Asset
  `/assets/juicelab/selected_challenges.yml` repond 200.
- 3 bugs Angular corriges dans le plugin :
  - `quiz-form.component.ts`, `journal-form.component.ts`,
    `hints-panel.component.ts` lisaient `this.challengeKey()` dans un
    initialisateur de propriete (NG8118). Fix : `toObservable(...)
    .pipe(switchMap(...))`.
  - `hints-panel.component.ts` lisait `state().cohort` qui n'existe pas
    sur `LocalState` (cohort est sous `state.student.cohort`).
- Pack `loginAdminChallenge.yaml` retire de
  `frontend/src/assets/juicelab/hints/` (la version canonique reste dans
  le repo source pedagogie). Dossiers `hints/`, `quiz/`, `journal/` vides
  supprimes des assets.
- `juicelab-pack.service.ts` : header de comment etoffe pour expliquer
  que les routes `getHints/getQuiz/getJournal` 404 jusqu'a phase B.
- 12 packs hints YAML generes dans
  `juicelab-pedagogy/hints/` :
  - DJ1 (5) : scoreBoard, privacyPolicy, directoryListing,
    exposedCredentials, passwordHashLeak
  - DJ2 (3) : adminSection, basketAccess, feedback
  - DJ3 (4) : localXss, reflectedXss, xssBonus, bullyChatbot
  Chaque pack suit le pattern Vygotsky (N1 5%, N2 10%, N3 20%, N4 35%,
  N5 50%) en FR + EN avec `pedagogical_intent`.
- 12 walkthroughs FR generes dans `juicelab-pedagogy/walkthroughs/` :
  meme liste que ci-dessus, structure 11 sections (contexte,
  vulnerabilite OWASP/MITRE/CWE, etapes, validation, concept enseigne,
  prevention, variantes avancees).
- Index `selected_challenges.yml` mis a jour cote source (avec
  `pack_status` complet) et cote assets (version publique, sans
  pack_status).
- Spec mini-endpoint phase B redigee :
  `juicelab-pedagogy/plugin-design/PHASE_B_MINI_ENDPOINT.md`.
  3 routes Express (`/api/juicelab/hint`, `/api/juicelab/quiz/score`,
  `/api/juicelab/walkthrough`), state in-memory par
  (student_token, challenge_key), gating progressif des hints + check
  `challenge.solved` avant walkthrough.

### Reste a faire

1. **Implementer la phase B** d'apres la spec (~4-6h dev).
   - Creer `juice-shop/data/juicelab-private/{hints,quiz,walkthroughs}/`.
   - Copier les YAML/MD du repo source.
   - Coder `routes/juicelab.ts` selon le squelette fourni.
   - Brancher dans `server.ts`.
   - Adapter `juicelab-pack.service.ts` (passer de pack-d'un-coup a
     niveau-par-niveau).
   - Adapter `HintsPanelComponent` pour le mode incremental.
   - Executer les 7 tests recette listes dans la spec.

2. **Generer les 13 quiz YAML** (incluant `loginAdminChallenge`).
   Pattern : 3 questions (Q1 free text, Q2 multiple choice, Q3 free
   text), expected_keywords FR/EN, options FR/EN si MC. Stockes
   exclusivement dans `juicelab-pedagogy/quiz/` (jamais dans assets).

3. **Generer les 13 journal YAML** : prompts before_solve / after_solve
   en FR/EN. Ceux-ci PEUVENT rester publics car ce sont des questions
   de relance, pas des solutions. A decider apres phase B.

4. **Phase C dashboard cloud enseignant** : Flask + DB + auth token.
   Recoit les events POST emis par `JuicelabSyncService`. Permet la vue
   prof temps reel d'une cohorte. Plan dans le projet original.

5. **i18n du plugin Angular** : tous les libelles inline dans les
   templates (`Coach pedagogique JuiceLab`, `Indices gradues`, etc.) a
   passer dans `i18n/fr.json` + EN/BR via `@ngx-translate/core` (deja
   en deps).

6. **Fiches docx FR/EN** des 13 challenges, generees par `scripts/
   generate_fiches.py` du repo source pedagogie.

### Fichiers modifies dans le clone Juice Shop cette session

`C:\Users\pizzif\Documents\GitHub\juice\juice-shop\` :

- `frontend\src\app\juicelab-overlay\` (cree, 13 fichiers TS du plugin)
- `frontend\src\app\juicelab-overlay\quiz-form\quiz-form.component.ts`
  (fix toObservable+switchMap)
- `frontend\src\app\juicelab-overlay\journal-form\journal-form.component.ts`
  (fix toObservable+switchMap)
- `frontend\src\app\juicelab-overlay\hints-panel\hints-panel.component.ts`
  (fix toObservable+switchMap, fix `state().cohort`)
- `frontend\src\app\juicelab-overlay\services\juicelab-pack.service.ts`
  (header de comment phase B)
- `frontend\src\assets\juicelab\selected_challenges.yml` (version
  publique strippee)
- `frontend\src\assets\juicelab\hints\loginAdminChallenge.yaml` SUPPRIME
  (anti-leak)
- `frontend\package.json` (`js-yaml` ajoute, deja present)
- `frontend\src\app\app.routing.ts` (route `/juicelab` ligne 62-67)
- `frontend\src\app\navbar\navbar.component.html` (bouton `school`
  ligne 115)

### Fichiers crees dans le repo source pedagogie

`C:\Users\pizzif\Documents\GitHub\TD Juice\juicelab-pedagogy\` :

- `hints/` : 12 nouveaux YAML (loginAdmin existant + 12 nouveaux = 13)
- `walkthroughs/` : 12 nouveaux MD (loginAdmin existant + 12 nouveaux = 13)
- `selected_challenges.yml` mis a jour avec `pack_status`
- `plugin-design/PHASE_B_MINI_ENDPOINT.md` (spec complete du 3e patch)

### Points de vigilance

- L'app Juice Shop tourne en background. Pour la stopper :
  `Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process -Force`
- Tant que phase B n'est pas livree, le panel Coach affichera des
  "Chargement des indices..." indefini (les requetes 404). C'est attendu.
- LocalStorage state cle `juicelab_state_v1`. Pour reset pendant les
  tests : `localStorage.removeItem('juicelab_state_v1')` dans la console
  DevTools.
- Cookies/JWT Juice Shop : la phase B utilisera le JWT existant pour
  identifier l'etudiant (`security.authenticatedUsers.get(req.cookies.token)`).
  Pas de nouveau systeme d'auth.

## Ce qui reste a faire (vision globale)

1. Faire tourner Juice Shop en local (`npm install` puis `npm start`) et
   valider que `/juicelab` affiche le panel Coach avec le challenge
   `loginAdmin`.
2. Generer les 12 autres packs pedagogiques via la skill (cf. liste ci-dessus).
3. Phase C : design et implementation du dashboard cloud enseignant (Flask
   + DB + auth par token), reception des events POST par le plugin.
4. Polish : i18n complet du plugin (labels via `@ngx-translate`), tests
   Karma, etendre les badges, gerer le mode offline.

## Standards

- Phrases naturelles longueur variable, pas de formules ultra-courtes
  robotiques.
- Pas d'emojis, em dash, fleches Unicode, smart quotes.
- Code Python : typage strict, docstrings anglaises, logging multi-niveaux,
  pas de hardcoding.
- Code TypeScript : standalone components Angular 20, `inject()`, signals,
  RxJS classique.
- Pour frameworks et normes, citer les versions exactes (ISO 27001:2022,
  NIST CSF 2.0, OWASP Top 10 2021, etc.).
- Si non sur d'un point, le dire ou verifier sur internet, ne pas inventer.

## Instruction de demarrage (a executer en debut de session)

1. Lire `C:\Users\pizzif\Documents\GitHub\TD Juice\juicelab-pedagogy\README.md`.
2. Lire `plugin-design\ARCHITECTURE.md` du meme repo.
3. Demander a l'utilisateur ce qu'il veut faire ensuite (debug build,
   generer les 12 packs restants, attaquer la phase C dashboard cloud,
   autre chose).

## Note sur le repo courant

Le repo `C:\Users\pizzif\Documents\GitHub\juice\` etait initialement le
projet AEGIS (these doctorale). Il accueille maintenant le clone Juice Shop
modifie pour JuiceLab. Le `CLAUDE.md` AEGIS reste present et continue de
s'appliquer pour tout travail sur AEGIS, mais pour JuiceLab, ce document
prime.
