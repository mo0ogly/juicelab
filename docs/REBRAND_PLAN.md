# Rebrand plan — JuiceLab -> Pedagogy Companion

Status : **DEFERRED**. To be executed only if the OWASP Phase 0
Discussion comes back positive AND a maintainer accepts the Pedagogy
Companion plugin path. Until then the internal code keeps the
`JuiceLab` name (avoids wasted churn).

## Why deferred

A full rename touches a large surface :

| Layer | Token | Count |
|---|---|---|
| i18n keys | `JUICELAB_*` | 140+ entries (FR / EN / BR) |
| Angular selectors | `juicelab-overlay`, `juicelab-panel`, ... | 12 components |
| TypeScript classes | `JuicelabSyncService`, `JuicelabStateService`, ... | 7 services |
| Routes & paths | `/juicelab`, `/assets/juicelab/`, `/data/juicelab-private/` | 4 path roots |
| LocalStorage keys | `juicelab_state_v1`, `juicelab_join_v1`, `juicelab_sync_queue_v1` | 3 keys (need migration) |
| CSS classes | overlay-scoped, low risk | < 20 |
| Dashboard repo | brand name, page titles, i18n keys | full prof side |
| Documentation | README files (FR/EN/BR), help modal text | 3 langs x N pages |
| Tests | mock URLs, fixture files | 5 files |

Estimate at execution time : **2-3 days** with current scope (110
packs already curated). The risk is not technical — it is wasted
effort if OWASP decides to keep things external (Plan B in the rule
`.claude/rules/owasp-pedagogy-companion.md`).

## Public-facing rename (already done)

For the upstream Discussion and the fork README, the externally
visible name is **"Pedagogy Companion for OWASP Juice Shop"**.
Internally the code still says JuiceLab. This split is intentional :
maintainers evaluate the proposal under a neutral name without me
having to pay the rebrand cost upfront.

## When to trigger

Trigger this plan when ANY of these conditions is met :

1. An OWASP maintainer comments positively on the Discussion AND
   asks for a first PR (Phase 1 mini contribution).
2. We decide to publish a public `juice-shop-pedagogy-companion`
   npm / git package independently of upstream merge.
3. Multiple academic users adopt the fork and ask for a clean public
   identity.

## Steps when triggered

1. **i18n keys** : sed `s/JUICELAB_/PEDAGOGY_/g` on the 3 i18n JSON
   files. Regenerate FR / EN / BR by re-running the i18n linter to
   ensure parity.
2. **Angular selectors** : sed on `juicelab-overlay` -> `pedagogy-overlay`,
   `juicelab-panel` -> `pedagogy-panel`, etc. Update template files,
   spec files, parent imports.
3. **TS classes** : rename `JuicelabXxxService` to `PedagogyXxxService`.
   Run `npx ng build --configuration production` to catch broken
   imports.
4. **Paths** : move `frontend/src/app/juicelab-overlay/` to
   `frontend/src/app/pedagogy-overlay/`. Move
   `frontend/src/assets/juicelab/` to
   `frontend/src/assets/pedagogy/`. Update
   `frontend/src/assets/juicelab/config.json` references in the
   dashboard side.
5. **LocalStorage migration** : add a one-shot bridge in the state
   service that reads legacy `juicelab_*` keys and writes them under
   `pedagogy_*`, then deletes the legacy. Keep for 2 releases then
   drop.
6. **Dashboard** : separate session. Rename `dashboard/i18n/`,
   templates, JS catalog. i18n keys stay (FR/EN catalog already keyed
   neutrally), so this is mostly text find-replace.
7. **Tests** : update test_*.sh and *.spec.ts that reference
   JUICELAB_* keys or `juicelab-*` selectors.
8. **Documentation** : regenerate README in 3 langs.
9. **Tracker** : refresh `.claude/output/owasp-pedagogy-companion/TRACKER.md`
   to reflect new schema names (`pedagogy.briefing.v2` etc).

## Safety net

Before the rename :

```bash
# Tag the pre-rebrand state so we can compare diffs / revert if needed.
git tag pre-rebrand-pedagogy
git push juicelab pre-rebrand-pedagogy
```

After the rename :

```bash
# Regression gate.
cd juice-shop/frontend && node node_modules/typescript/bin/tsc --noEmit -p src/tsconfig.app.json
cd ../.. && bash dashboard/tests/test_join_api.sh
bash dashboard/tests/test_cohorts_api.sh
bash dashboard/tests/test_students_api.sh
bash dashboard/tests/test_i18n_api.sh
python .claude/output/owasp-pedagogy-companion/lint_juicelab_pedagogy.py
```

If any gate fails, `git reset --hard pre-rebrand-pedagogy` and
investigate before retrying.
