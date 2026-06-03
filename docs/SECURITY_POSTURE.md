# JuiceLab Dashboard - Security Posture

> French version: [SECURITY_POSTURE-FR.md](./SECURITY_POSTURE-FR.md).

Snapshot of the hardening achieved through 17 PDCA cycles on the
`dashboard/` scope. This document is the single-page summary intended
for OWASP review, audit reports, and procurement questionnaires. The
authoritative cycle-by-cycle log is in [`SECURITY.md`](../SECURITY.md).

## Scope

This posture applies to the JuiceLab Flask teacher dashboard
(`dashboard/`, served on port 5050). The OWASP Juice Shop core that
runs underneath remains deliberately vulnerable for student
exploitation - that is its educational purpose and is out of scope
here.

## Controls in place

### Application security (SAST)

| Tool | What it catches | Status |
|---|---|---|
| bandit | Python security anti-patterns | HIGH=0 ; MEDIUM=1 baseline-pinned |
| ruff S-rules | Python linter security subset | 0 findings |
| semgrep | OWASP Top 10 + Python + Flask rule packs | 0 findings |
| CodeQL | GitHub-native semantic SAST + CWE taint flow | runs on every push/PR + weekly cron |

### Dependency security (SCA)

| Tool | What it catches | Status |
|---|---|---|
| pip-audit | CVE in pinned Python deps | 0 known CVE |
| safety | Independent CVE database (second opinion) | 0 known CVE |
| Dependabot | Auto-PR on CVE patch / minor bump | weekly Mon 04:30 Europe/Paris |
| pip-licenses (SEC-13) | GPL / AGPL / LGPL refusal | 18/18 OK (BSD/MIT/Apache/MPL) |
| requirements.lock.txt | Hash-pinned deps, `--require-hashes` install | 18 packages, sha256 attested |

### Secrets management

| Tool | What it catches | Status |
|---|---|---|
| gitleaks | Hardcoded secrets in source | 0 leaks in `dashboard/` (tests allowlisted) |
| `.bandit-baseline.json` | Pinned acceptable findings, regression guard | baseline + 0 deviation |
| HMAC chains | Teacher token + proof secret | timing-safe `hmac.compare_digest` everywhere |
| Audit log JSONL | Login attempts, CSRF fails, sync blocks, decisions | privacy-by-design (token prefix + email domain) |

### Network security

| Header | Value | Cycle |
|---|---|---|
| `Content-Security-Policy` | `'self' nonce-XXX 'strict-dynamic'` (no `unsafe-inline`) | 8 |
| `X-Content-Type-Options` | `nosniff` | 3 |
| `X-Frame-Options` | `DENY` | 3 |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | 3 |
| `Permissions-Policy` | `interest-cohort=()` | 3 |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` (HTTPS only) | 17 |
| `Cache-Control` | `no-store` global | 7 |
| `Server` | masked from Werkzeug version leak | 7 |

### Anti-tampering

| Defense | Mechanism | Cycle |
|---|---|---|
| CSRF protection | Double-submit cookie, API client (`X-Teacher-Token`) exempt | 3 |
| SRI on stylesheet | `integrity="sha384-<hash>"` computed at boot | 9 |
| Per-request CSP nonce | `secrets.token_urlsafe(16)` per request | 8 |
| Proof signing | HMAC-SHA256, tamper-evident `proof.md` | upstream |
| Flag verification | HMAC-SHA1 (OWASP CTF compat), timing-safe | upstream |

### Operations

| Control | What it does | Cycle |
|---|---|---|
| Per-IP rate limiting | sliding window on public endpoints | 1 |
| CORS allowlist | only Juice Shop origin (configurable) | initial |
| Cohort gate | `/api/sync` returns 403 until teacher approves student | 0 |
| Login redirect | `/dashboard` -> `/login` when unauthenticated | 0 |
| Audit log | JSONL append-only, 6 event types | 4 |

### Dynamic security (DAST)

| Tool | Coverage | Status |
|---|---|---|
| OWASP ZAP baseline | Passive crawl, 66 rules | FAIL=0, PASS=66, WARN=1 (no-store on 404, intended) |

### Testing

| Metric | Value | Cycle |
|---|---|---|
| pytest suite | 177 tests | 17 |
| Code coverage | 96% on `dashboard/` | 15 |
| Bash recettes | 71 functional tests | initial |
| Security recette | 14/14 gates | 16 |
| Crypto invariants | 11 mutation-style tests on `verify`, `sign_proof`, `check_csrf` | 14 |

### Supply chain

| Artifact | Format | Cycle |
|---|---|---|
| SBOM | CycloneDX 1.6 JSON, 18 components with pURL | 13 |
| Lockfile | `--require-hashes` pip-compile output | 12 |
| License manifest | `dashboard/LICENSES.md` auto-generated | 16 |
| Generator | `scripts/gen_licenses.sh` reproducible | 16 |

### CI/CD

| Workflow | Runs | Cycle |
|---|---|---|
| `dashboard-tests` (`ci.yml`) | pytest + schema migration | initial |
| `legacy-db-migration` (`ci.yml`) | migration on legacy SQLite | initial |
| `dashboard-security-recette` (`ci.yml`) | full 14-gate SAST/SCA/secrets/coverage/SBOM/licenses | 11 |
| `docker-compose-validate` (`ci.yml`) | compose config parse | initial |
| `codeql.yml` | Python + JS/TS semantic SAST | 12 |
| `yaml-lint` | pedagogical pack YAML parse | initial |
| `shellcheck` | docker entrypoint linting | initial |

Branch protection (documented in [`BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md)) :
8 required status checks, `enforce_admins: true`, `required_signatures: true`,
`required_linear_history: true`, `allow_force_pushes: false`.

## Trajectory (17 PDCA cycles)

```
72.75 -> 83.25 -> 87.50 -> 94.00 -> 95.65 ->
96.55 -> 97.50 -> 98.40 -> 99.20 -> 99.65 ->
99.85 -> 99.92 -> 99.95 -> 99.97 -> 99.98 ->
99.99 -> 99.99 (plateau)
```

Practical saturation reached at cycle 16. Further marginal gains come
from infrastructure-side controls (HSTS preload submission, SLSA
provenance, reverse-proxy hardening) that live outside the application
codebase.

## Known residual risks

| Risk | Mitigation | Severity |
|---|---|---|
| Compromised `DASHBOARD_TEACHER_TOKEN` | Out of scope - holder is teacher | by design |
| Student spoofing another `student_token` | JWT email cross-check in Mode B/C | medium, documented in threat model |
| Compromised CTFd (Mode C) | Dashboard consumes only `id`+`email`, no code injection | medium |
| Reverse-proxy compromise | SRI on `dashboard.css`, no JS SRI yet (inline only) | low |
| Coverage `proof_routes.py` 93%, `students_routes.py` 93%, `app.py` 91% | edge cases / template render variants | low |

## How to verify

```bash
# Full local validation (10s + ZAP via docker ~30s):
bash dashboard/tests/test_security_scan.sh

# Skip DAST (no docker):
SKIP_DAST=1 bash dashboard/tests/test_security_scan.sh

# Regenerate SBOM:
cyclonedx-py requirements dashboard/requirements.lock.txt \
  --output-format JSON --output-file /tmp/sbom.cdx.json

# Regenerate LICENSES.md:
bash scripts/gen_licenses.sh

# Run the full pytest suite under coverage:
coverage run --source=dashboard -m pytest dashboard/tests/test_*.py
coverage report
```

## Reporting a vulnerability

See [`SECURITY.md`](../SECURITY.md) section "How to report a
vulnerability". Private advisory via GitHub or email to
`mo0ogly@proton.me` with `[JUICELAB-SEC]` in the subject.
