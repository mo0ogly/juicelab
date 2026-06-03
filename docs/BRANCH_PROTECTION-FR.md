# Protection de la branche `main`

> Version anglaise : [BRANCH_PROTECTION.md](./BRANCH_PROTECTION.md).

Ce document consigne les paramètres de protection de branche GitHub qui
opérationnalisent les portails CI ajoutés lors des cycles PDCA. Ces paramètres
résident dans la configuration du dépôt GitHub, et non dans le code source ; ils
doivent donc être appliqués une seule fois via la CLI `gh` ou l'interface web. Ce
fichier documente l'état requis afin qu'une instance dupliquée ou redéployée
puisse le reproduire.

## Vérifications requises avant la fusion dans `main`

Les tâches CI suivantes (issues de `.github/workflows/ci.yml` et
`.github/workflows/codeql.yml`) DOIVENT réussir avant qu'une pull request puisse
être fusionnée dans `main` :

| Tâche | Workflow source | Ce qu'elle contrôle |
|---|---|---|
| `Dashboard pytest + lint` | `ci.yml :: dashboard-tests` | Code applicatif + migration de schéma |
| `Migration on a legacy SQLite without award_pushed_at` | `ci.yml :: legacy-db-migration` | Migration de schéma sur des bases de données existantes |
| `Dashboard security recette (SAST + SCA + secrets + coverage)` | `ci.yml :: dashboard-security-recette` | bandit + ruff + pip-audit + semgrep + gitleaks + safety + pytest 95 % de couverture + dérive du fichier de verrouillage + SBOM |
| `docker compose config validation` | `ci.yml :: docker-compose-validate` | Intégrité de la configuration de la pile Docker |
| `ShellCheck on docker/entrypoint.sh` | `ci.yml :: shellcheck` | Qualité du script shell |
| `Lint YAML pedagogical packs` | `ci.yml :: yaml-lint` | Intégrité de l'analyse syntaxique YAML |
| `CodeQL semantic analysis (python)` | `codeql.yml` | SAST sémantique + CWE |
| `CodeQL semantic analysis (javascript-typescript)` | `codeql.yml` | SAST sémantique + CWE |

## Appliquer la règle de protection via `gh`

```bash
# Nécessite le rôle administrateur sur le dépôt. Remplacer mo0ogly/juicelab
# par le chemin du fork si vous utilisez le vôtre.

REPO="mo0ogly/juicelab"

gh api -X PUT "repos/$REPO/branches/main/protection" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {"context": "Dashboard pytest + lint"},
      {"context": "Migration on a legacy SQLite without award_pushed_at"},
      {"context": "Dashboard security recette (SAST + SCA + secrets + coverage)"},
      {"context": "docker compose config validation"},
      {"context": "ShellCheck on docker/entrypoint.sh"},
      {"context": "Lint YAML pedagogical packs"},
      {"context": "CodeQL semantic analysis (python)"},
      {"context": "CodeQL semantic analysis (javascript-typescript)"}
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "required_signatures": true,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "restrictions": null
}
EOF
```

## Justification de chaque paramètre

* `strict: true` — relance le CI sur la dernière base avant d'autoriser la fusion ;
  détecte le cas où une PR précédemment verte s'appuyait sur un `main` désormais
  périmé.
* `enforce_admins: true` — même le propriétaire du dépôt ne peut pas contourner les
  portails. L'objectif du CI est précisément que personne ne puisse les esquiver.
* `required_approving_review_count: 1` — au moins un regard humain sur chaque PR.
  Les auto-fusions sont bloquées.
* `dismiss_stale_reviews: true` — un force-push sur la branche de la PR invalide
  l'approbation précédente, car le diff a changé.
* `required_signatures: true` — chaque commit sur `main` doit être signé par GPG
  ou SSH. La clé du signataire doit être enregistrée dans son compte GitHub, ce qui
  constitue la garantie la plus proche qu'offre GitHub pour attester que « ce commit
  a été rédigé par l'identité listée sur GitHub, et non par un attaquant qui aurait
  volé le mot de passe ».
* `required_linear_history: true` — aucun commit de fusion. Il faut effectuer un
  rebase ou un squash. Cela maintient `git bisect` linéaire et `git blame` précis.
* `allow_force_pushes: false` + `allow_deletions: false` — `main` est en mode
  ajout-seulement. Un force-push ou la suppression de la branche réécrirait ou
  détruirait l'historique signé.

## CODEOWNERS (facultatif mais recommandé)

Ajouter `.github/CODEOWNERS` :

```
* @mo0ogly
/dashboard/        @mo0ogly
/juice-shop/       @mo0ogly
/.github/workflows/ @mo0ogly
/SECURITY.md       @mo0ogly
```

Combiné avec `require_code_owner_reviews: true` (si vous modifiez la valeur par
défaut), cela achemine automatiquement la demande de revue de PR vers le
propriétaire listé.

## Vérification après application

```bash
gh api "repos/$REPO/branches/main/protection" \
  --jq '{checks: .required_status_checks.checks | map(.context), signatures: .required_signatures.enabled, linear: .required_linear_history.enabled, force: .allow_force_pushes.enabled}'
```

Résultat attendu :

```json
{
  "checks": [
    "Dashboard pytest + lint",
    "Migration on a legacy SQLite without award_pushed_at",
    "Dashboard security recette (SAST + SCA + secrets + coverage)",
    "docker compose config validation",
    "ShellCheck on docker/entrypoint.sh",
    "Lint YAML pedagogical packs",
    "CodeQL semantic analysis (python)",
    "CodeQL semantic analysis (javascript-typescript)"
  ],
  "signatures": true,
  "linear": true,
  "force": false
}
```

## Compromis

* **Signatures requises + mainteneur unique** : si `main` est verrouillé aux commits
  signés, un mainteneur qui n'a pas encore configuré la signature GPG / SSH ne peut
  pas pousser sur `main`. Configurer la signature en premier :
  `git config --global commit.gpgsign true` + enregistrer la clé sur GitHub. Voir
  [la documentation de signature de GitHub](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification).

* **Historique linéaire + nombreuses petites PR** : les rebases à la place des fusions
  ajoutent du bruit dans les forks. Pour un projet de recherche ou de salle de classe,
  ce compromis est acceptable ; pour un grand projet open source avec de nombreux
  contributeurs, envisager `allow_merge_commit: true` et s'appuyer sur la linéarisation
  via le squash-merge à la place.

* **enforce_admins bloquant les urgences** : le mainteneur peut temporairement définir
  `enforce_admins: false`, pousser le correctif urgent, puis réactiver la protection.
  Documenter cela dans le message du commit : `[bypass-admin] fix CVE-XXXX-YYYY`. La
  revue de cette discipline fait partie du bilan post-incident.
