# Branch protection for `main`

This document captures the GitHub branch-protection settings that
operationalise the CI gates added during the PDCA cycles. The settings
live in GitHub repository configuration, not in source code, so they
have to be applied once via the `gh` CLI or the web UI. This file
documents the required state so a forked / re-deployed instance can
reproduce it.

## Required checks before merge to `main`

The following CI jobs (from `.github/workflows/ci.yml` and
`.github/workflows/codeql.yml`) MUST pass before a pull request can
be merged into `main`:

| Job | Source workflow | What it gates |
|---|---|---|
| `Dashboard pytest + lint` | `ci.yml :: dashboard-tests` | Application code + schema migration |
| `Migration on a legacy SQLite without award_pushed_at` | `ci.yml :: legacy-db-migration` | Schema migration on existing databases |
| `Dashboard security recette (SAST + SCA + secrets + coverage)` | `ci.yml :: dashboard-security-recette` | bandit + ruff + pip-audit + semgrep + gitleaks + safety + pytest 95% coverage + lockfile drift + SBOM |
| `docker compose config validation` | `ci.yml :: docker-compose-validate` | docker stack config integrity |
| `ShellCheck on docker/entrypoint.sh` | `ci.yml :: shellcheck` | shell quality |
| `Lint YAML pedagogical packs` | `ci.yml :: yaml-lint` | YAML parse integrity |
| `CodeQL semantic analysis (python)` | `codeql.yml` | semantic SAST + CWE |
| `CodeQL semantic analysis (javascript-typescript)` | `codeql.yml` | semantic SAST + CWE |

## Apply the protection rule via `gh`

```bash
# Requires admin on the repo. Replace mo0ogly/juicelab with the fork
# path if you are using your own.

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

## Why each setting

* `strict: true` — re-run CI on the latest base before allowing merge,
  catches the case where a previously-green PR was based on a now-stale
  main.
* `enforce_admins: true` — even a repo owner cannot bypass the gates.
  The point of CI is that nobody bypasses it.
* `required_approving_review_count: 1` — at least one human eyeball on
  every PR. Self-merges are blocked.
* `dismiss_stale_reviews: true` — a force-push to the PR branch
  invalidates the previous approval, since the diff has changed.
* `required_signatures: true` — every commit on `main` must be GPG-
  or SSH-signed. The signer's key has to be registered with their
  GitHub account, which is the closest GitHub gives to attesting
  "this commit was authored by the GitHub-listed identity, not by an
  attacker who stole the password".
* `required_linear_history: true` — no merge commits. Either rebase
  or squash. Keeps `git bisect` linear and `git blame` precise.
* `allow_force_pushes: false` + `allow_deletions: false` — `main` is
  append-only. A force-push or branch deletion would rewrite or destroy
  signed history.

## CODEOWNERS (optional but recommended)

Add `.github/CODEOWNERS`:

```
* @mo0ogly
/dashboard/        @mo0ogly
/juice-shop/       @mo0ogly
/.github/workflows/ @mo0ogly
/SECURITY.md       @mo0ogly
```

Combined with `require_code_owner_reviews: true` (if you change the
default), this routes a PR review request to the listed owner
automatically.

## Verification after applying

```bash
gh api "repos/$REPO/branches/main/protection" \
  --jq '{checks: .required_status_checks.checks | map(.context), signatures: .required_signatures.enabled, linear: .required_linear_history.enabled, force: .allow_force_pushes.enabled}'
```

Expected output:

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

## Trade-offs

* **Required signatures + solo maintainer**: if `main` is locked to
  signed commits, a maintainer who hasn't yet configured GPG / SSH
  signing cannot push to `main` at all. Configure signing first:
  `git config --global commit.gpgsign true` + register the key on
  GitHub. See [GitHub's signing docs](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification).

* **Linear history + many small PRs**: rebases instead of merges add
  noise to forks. For a research / classroom project this trade-off is
  acceptable; for a large open-source project with many contributors,
  consider `allow_merge_commit: true` and rely on linearization via
  squash-merge instead.

* **enforce_admins blocking emergencies**: the maintainer can
  temporarily set `enforce_admins: false`, push the hotfix, then
  re-enable. Document this in the commit message: `[bypass-admin] fix
  CVE-XXXX-YYYY`. Reviewing this discipline is part of the post-incident
  retro.
