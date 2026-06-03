# Plan de rebranding — JuiceLab -> Pedagogy Companion

> Version anglaise : [REBRAND_PLAN.md](./REBRAND_PLAN.md).

Statut : **DIFFÉRÉ**. À exécuter uniquement si la Discussion OWASP Phase 0
revient positive ET qu'un mainteneur accepte le chemin du plugin Pedagogy
Companion. En attendant, le code interne conserve le nom `JuiceLab`
(évite du travail inutile).

## Pourquoi différé

Un renommage complet touche une surface importante :

| Couche | Jeton | Nombre |
|---|---|---|
| Clés i18n | `JUICELAB_*` | 140+ entrées (FR / EN / BR) |
| Sélecteurs Angular | `juicelab-overlay`, `juicelab-panel`, ... | 12 composants |
| Classes TypeScript | `JuicelabSyncService`, `JuicelabStateService`, ... | 7 services |
| Routes et chemins | `/juicelab`, `/assets/juicelab/`, `/data/juicelab-private/` | 4 racines de chemin |
| Clés LocalStorage | `juicelab_state_v1`, `juicelab_join_v1`, `juicelab_sync_queue_v1` | 3 clés (migration nécessaire) |
| Classes CSS | à portée overlay, risque faible | < 20 |
| Dépôt Dashboard | nom de marque, titres de pages, clés i18n | côté prof complet |
| Documentation | fichiers README (FR/EN/BR), texte de la modale d'aide | 3 langues x N pages |
| Tests | URL de mock, fichiers de fixture | 5 fichiers |

Estimation au moment de l'exécution : **2 à 3 jours** avec la portée actuelle
(110 packs déjà organisés). Le risque n'est pas technique — c'est un effort
gaspillé si OWASP décide de conserver les choses en externe (Plan B dans la
règle `.claude/rules/owasp-pedagogy-companion.md`).

## Renommage public (déjà effectué)

Pour la Discussion en amont et le README du fork, le nom visible
extérieurement est **"Pedagogy Companion for OWASP Juice Shop"**.
En interne, le code dit toujours JuiceLab. Cette séparation est intentionnelle :
les mainteneurs évaluent la proposition sous un nom neutre sans que j'aie à
payer le coût du rebranding à l'avance.

## Quand déclencher

Déclencher ce plan lorsque L'UNE de ces conditions est remplie :

1. Un mainteneur OWASP commente positivement la Discussion ET
   demande une première PR (mini contribution Phase 1).
2. Nous décidons de publier un paquet npm / git public
   `juice-shop-pedagogy-companion` indépendamment du merge en amont.
3. Plusieurs utilisateurs académiques adoptent le fork et demandent
   une identité publique claire.

## Étapes lors du déclenchement

1. **Clés i18n** : sed `s/JUICELAB_/PEDAGOGY_/g` sur les 3 fichiers JSON
   i18n. Régénérer FR / EN / BR en réexécutant le linter i18n pour
   assurer la parité.
2. **Sélecteurs Angular** : sed sur `juicelab-overlay` -> `pedagogy-overlay`,
   `juicelab-panel` -> `pedagogy-panel`, etc. Mettre à jour les fichiers
   de template, les fichiers spec, les imports parents.
3. **Classes TS** : renommer `JuicelabXxxService` en `PedagogyXxxService`.
   Lancer `npx ng build --configuration production` pour détecter les
   imports cassés.
4. **Chemins** : déplacer `frontend/src/app/juicelab-overlay/` vers
   `frontend/src/app/pedagogy-overlay/`. Déplacer
   `frontend/src/assets/juicelab/` vers
   `frontend/src/assets/pedagogy/`. Mettre à jour les références à
   `frontend/src/assets/juicelab/config.json` côté dashboard.
5. **Migration LocalStorage** : ajouter un pont one-shot dans le service
   d'état qui lit les clés legacy `juicelab_*` et les écrit sous
   `pedagogy_*`, puis supprime le legacy. Conserver pendant 2 versions,
   puis supprimer.
6. **Dashboard** : session séparée. Renommer `dashboard/i18n/`,
   les templates, le catalogue JS. Les clés i18n restent (le catalogue
   FR/EN est déjà neutre), il s'agit donc surtout d'un remplacement
   textuel.
7. **Tests** : mettre à jour les `test_*.sh` et `*.spec.ts` qui
   référencent les clés `JUICELAB_*` ou les sélecteurs `juicelab-*`.
8. **Documentation** : régénérer le README dans les 3 langues.
9. **Tracker** : rafraîchir `.claude/output/owasp-pedagogy-companion/TRACKER.md`
   pour refléter les nouveaux noms de schéma (`pedagogy.briefing.v2`, etc.).

## Filet de sécurité

Avant le renommage :

```bash
# Tag the pre-rebrand state so we can compare diffs / revert if needed.
git tag pre-rebrand-pedagogy
git push juicelab pre-rebrand-pedagogy
```

Après le renommage :

```bash
# Regression gate.
cd juice-shop/frontend && node node_modules/typescript/bin/tsc --noEmit -p src/tsconfig.app.json
cd ../.. && bash dashboard/tests/test_join_api.sh
bash dashboard/tests/test_cohorts_api.sh
bash dashboard/tests/test_students_api.sh
bash dashboard/tests/test_i18n_api.sh
python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py
```

Si l'une des portes échoue, lancer `git reset --hard pre-rebrand-pedagogy` et
investiguer avant de réessayer.
