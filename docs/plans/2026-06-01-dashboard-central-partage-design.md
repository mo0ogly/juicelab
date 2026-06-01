# Design — Dashboard prof central partage, deployable seul (sparse pinned)

Date: 2026-06-01
Statut: valide (brainstorming)
Repos concernes: `juicelab` (mo0ogly/juicelab), `PwnzzAI` (mo0ogly/PwnzzAI)

## Probleme

Le dashboard prof (Flask, `dashboard/`) habite dans le mono-repo `juice`, qui
contient aussi la partie eleve (overlay, scripts d'install eleve, juice-shop
clone au build). Consequence: pour deployer le dashboard, on clone tout le repo
`juice` et on traine le baggage eleve.

Besoin (mots du user): **installer PwnzzAI ne doit pas forcer a embarquer la
partie eleve juice.** Et il ne veut **pas dupliquer le serveur** sur les deux
repos.

## Constat technique (audit 2026-06-01)

Le dashboard est **deja decouple au niveau code** — ce n'est PAS un refactor:

- `juice-shop` = 0 fichier tracke dans le repo `juice` (clone au build, pas vendore).
- `dashboard/*.py` a **zero** dependance sur `juice-shop` ou `overlay/`.
- `docker/Dockerfile.dashboard` ne `COPY` que `dashboard/`. L'image prof ne
  contient aucun code eleve.

Le couplage est purement **organisationnel** (le dossier vit dans le repo juice).
C'est donc un probleme de **distribution**, pas d'architecture.

## Decision

Approche **C — clone pinne "sparse", zero infra**. Le code `dashboard/` reste
dans `juice` (source de verite unique). Le *deploiement* ne tire qu'une tranche
`dashboard/` + `docker/` a un commit pinne, via `git sparse-checkout`. Reutilise
l'idiome "commit pinne au build" deja en place (PwnzzAI, Juice Shop).

Topologie runtime: **une seule instance centrale** du dashboard. `juicelab` ET
`PwnzzAI` pointent dessus via `JUICELAB_DASHBOARD_URL`. Aucun deploiement en
double.

Approches ecartees:
- **A (image GHCR prebuild)**: la plus propre a consommer mais exige
  registry + pipeline CI + discipline de versioning. Trop d'infra pour maintenant.
- **B (extraire dashboard dans son repo)**: separation conceptuelle ideale mais
  split d'historique, 2 repos a releaser, friction submodules. Trop lourd.

## Composants

### 1. Set distribuable + compose dashboard-only

- Set distribuable = `dashboard/` + `docker/Dockerfile.dashboard` +
  `docker/.env.example`. Deja autosuffisant.
- **Nouveau** `docker/docker-compose.dashboard.yml`: service `dashboard` SEUL
  (pas de service juice-shop), volume `dashboard_data`, lecture `--env-file`.
  Derive du `docker/docker-compose.yml` actuel en retirant le service juice-shop
  et ses dependances.

### 2. Bootstrap sparse pinne (coeur)

- **Nouveau** `scripts/bootstrap-dashboard.sh` (dans juice), utilisable depuis
  n'importe ou (machine vierge, sans clone juice prealable):

  ```
  git clone --filter=blob:none --sparse <juice-url> <dir>
  git -C <dir> sparse-checkout set dashboard docker
  git -C <dir> checkout <PIN_SHA>
  cd <dir> && docker compose -f docker/docker-compose.dashboard.yml up -d --build
  ```

- Tire SEULEMENT `dashboard/` + `docker/`. Jamais `overlay/`, `juice-shop/`,
  scripts d'install eleve.
- Parametres via env/flags: URL du repo, commit pin, dossier cible, env-file.
- Idempotent: si `<dir>` existe deja, fetch + checkout du pin + recreate (logique
  proche de `scripts/dashboard.sh update`).

### 3. Consommation PwnzzAI

- `.env.example` PwnzzAI: ajouter `JUICELAB_DASHBOARD_COMMIT=<sha>` (pin du
  dashboard) en plus de `JUICELAB_DASHBOARD_URL` existant.
- **Nouveau** `scripts/deploy-dashboard.sh` dans PwnzzAI: wrapper fin (~15-20
  lignes) qui appelle le bootstrap sparse juice@PIN. Installer PwnzzAI =
  recuperer ce script fin, **zero code eleve juice**.
- Le coach pointe ensuite `JUICELAB_DASHBOARD_URL` vers l'instance centrale.

### 4. Topologie + coexistence (doc)

- Doc d'ops: UN dashboard central, deux clients. Anti-pattern explicite: ne pas
  re-deployer un 2e dashboard.
- Coexistence deja supportee cote dashboard:
  - `instance_label` (header `X-Instance-Label`) distingue la source de l'evenement.
  - cohortes namespacees (`PWNZZAI-*` vs `M2-*`).
  - le prof voit l'origine de chaque eleve.
  - A documenter, pas a coder.
- CORS: `DASHBOARD_CORS_ORIGINS` doit lister les origines eleves PwnzzAI si elles
  different de juicelab. Point de configuration, pas de code.

## Criteres de succes

1. Sur une machine vierge: `bootstrap-dashboard.sh` lance le dashboard sans
   jamais telecharger `overlay/` ni `juice-shop/`.
2. `docker compose -f docker-compose.dashboard.yml` ne demarre QUE le dashboard.
3. PwnzzAI: `scripts/deploy-dashboard.sh` deploie le dashboard pinne sans cloner
   le repo juice complet.
4. Une instance, deux clients: juicelab et PwnzzAI eleves remontent dans le meme
   dashboard, distingues par `instance_label`, isoles par cohorte.
5. Aucune regression: `docker/docker-compose.yml` (full, dashboard + juice-shop)
   continue de marcher pour le dev local juice.

## Hors scope

- Pas de registry/CI image (approche A).
- Pas d'extraction de repo (approche B).
- Pas de refactor du code `dashboard/` (deja decouple).
- Pas de changement du flow cohort/join, proof, sync (inchanges).

## Suite

Plan d'implementation detaille via writing-plans. Repos a toucher: `juice`
(compose dashboard-only + bootstrap + doc topologie) et `PwnzzAI` (env pin +
deploy script + doc).
