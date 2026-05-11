# Security Policy

## Scope

JuiceLab is a **deliberately vulnerable educational platform**. The OWASP Juice Shop core under it ships intentional vulnerabilities for students to exploit — those are out of scope. What IS in scope:

* The JuiceLab Angular **overlay** (`juice-shop/frontend/src/app/juicelab-overlay/`) — leaks of private hints, quiz answers, walkthroughs, or any bypass of the server-side gating.
* The JuiceLab **Express routes** (`juice-shop/routes/juicelab.ts`) — auth bypass, level-skip, walkthrough access without solve, admin endpoint without token.
* The **Flask dashboard** (`dashboard/`) — auth bypass, SQL injection in `/api/cohort`, HMAC forgery in `/api/verify-flag` or `/api/proof`, IDOR on events, leaked teacher token in logs.
* The **CTFd Mode C bridge** (`_push_hint_penalty` and `_resolve_ctfd_team` in `dashboard/app.py`) — credential exfiltration, team mapping spoofing, award injection on behalf of another student.
* The **Docker stack** (`docker/`) — container escape, secret leakage, network exposure unintended by `docker-compose.yml`.
* The **proof signing** (`HMAC-SHA-256` on `proof.md`) — any way to produce a valid proof without solving the challenge.

**Out of scope.** Vulnerabilities in OWASP Juice Shop itself — report those to the upstream project at <https://github.com/juice-shop/juice-shop/security/policy>. Vulnerabilities in CTFd — report at <https://github.com/CTFd/CTFd/security/policy>. Vulnerabilities that require the attacker to already have the `DASHBOARD_TEACHER_TOKEN` or `CTFD_ADMIN_TOKEN` — those tokens grant teacher-level access by design.

## Supported versions

JuiceLab is alpha-stage classroom software. Only the `main` branch is supported. There is no LTS, no security branch, no backport policy. Patches for confirmed vulnerabilities land on `main` within the disclosure window below; deployments are expected to track `main` or pin a specific commit and apply security patches manually.

| Version | Supported |
|---|---|
| `main` (rolling) | yes |
| any older tag | no |

## How to report a vulnerability

**Do not file public GitHub issues for vulnerability reports.** Use one of the channels below:

1. **GitHub private advisory** (preferred) — open a draft at <https://github.com/mo0ogly/juicelab/security/advisories/new>. This keeps the discussion private until the fix is ready.
2. **Email** — `mo0ogly@proton.me`. Include `[JUICELAB-SEC]` in the subject line.

Please include in your report:

* A description of the vulnerability and its impact.
* Step-by-step reproduction (a minimal payload is ideal).
* The affected commit hash or branch.
* Your assessment of the severity (low / medium / high / critical) and the exploit prerequisites (anonymous? authenticated student? local network? Mode C only?).
* Whether you wish to be credited in the advisory, and under what name / handle.

If you have PoC code, paste it inline or attach it — do not link to a public gist.

## Disclosure timeline

| Day | Action |
|---|---|
| 0 | Vulnerability reported. Maintainer acknowledges receipt within 72 hours. |
| 0-7 | Maintainer reproduces the issue, scopes the impact, drafts a fix. |
| 7-30 | Fix is committed to a private branch. Reporter is consulted on disclosure language. |
| 30-60 | Fix is merged to `main`. Public advisory is published with credit (if requested). |
| 60+ | If the fix is not yet ready and the reporter wants to disclose, the maintainer will not block it — the priority is downstream safety. |

We aim for a 30-day disclosure window in the typical case. For critical vulnerabilities affecting the proof signing or the teacher token gating, we will move faster (7 to 14 days target). For low-severity issues that require a Mode C deployment with a misconfigured CTFd, we may extend to 60 days if the fix is non-trivial.

## What we will not do

* Sue or threaten you for reporting a vulnerability in good faith.
* Demand silence beyond the agreed disclosure window.
* Pay a bounty. JuiceLab is a non-funded classroom project. We will credit you publicly and gratefully if you wish.
* Penalize a contributor for filing a vulnerability report against their own code, as long as the report follows this policy.

## Hall of fame

This section will list reporters who responsibly disclosed vulnerabilities to JuiceLab.

(No entries yet.)

## Cryptography

JuiceLab uses two distinct HMAC chains:

* **`ctf.key` -> `JUICESHOP_CTF_SECRET`** — `HMAC-SHA1(secret, challenge.name)` is the OWASP Juice Shop CTF flag formula. Shared between Juice Shop (`lib/utils.ts ctfFlag()`), the dashboard `/api/verify-flag`, and the CTFd `.csv` import. SHA-1 is used because the upstream OWASP `juice-shop-ctf-cli` mandates it for compatibility; we do not introduce a new flag format.
* **`DASHBOARD_PROOF_SECRET`** — `HMAC-SHA-256(secret, proof_body)` signs the downloadable `proof.md`. SHA-256 because there is no compatibility constraint here, and the dashboard generates and verifies its own proofs (`dashboard/verify_proof.py`).

Both secrets must be >= 16 characters. The dashboard refuses to boot the proof endpoint if `DASHBOARD_PROOF_SECRET` is shorter, and prints a warning if `JUICESHOP_CTF_SECRET` is empty (then `/api/verify-flag` returns 503).

## Threat model summary

| Actor | Capability | Mitigation |
|---|---|---|
| Curious student | Inspects HTTP traffic, opens DevTools, reads cookies | All hints / quiz answers / walkthroughs gated server-side. Quiz answers stripped from the wire on GET, only checked on POST. Walkthrough refused until `challenges.solved` is true. |
| Aggressive student | Spoofs another student's `student_token` | The token is a browser UUID — easy to spoof. Mitigation: in Mode B / C, the cohort matrix shows the JWT email alongside, which the teacher can cross-check. The proof markdown is signed HMAC, so a forged token still cannot produce a valid proof. |
| Malicious classmate | Tries to inject awards on a peer's CTFd team | The dashboard resolves the team from the JWT email, not from a client-supplied identifier. Spoofing requires forging a Juice Shop JWT, which is upstream-Juice-Shop territory. |
| External attacker | Hits the dashboard / Juice Shop from the LAN or internet | CORS allowlist + teacher-token gating on admin routes. Public deployments must put HTTPS in front (Caddy / Traefik) and restrict the dashboard by IP at the firewall — documented in [`docker/README.md`](./docker/README.md) section 3. |
| Compromised CTFd | Returns malicious data on `/api/v1/teams` | The dashboard only consumes `id` and `email` fields. A malicious CTFd can poison the team mapping but cannot inject code into the dashboard. The worst case is a wrong team_id, which produces a wrong leaderboard line — visible to the teacher and reversible. |

## Hardening tracker (PDCA cycles)

| Cycle | Commit | Added |
|---|---|---|
| 1 | `996851b` | Timing-safe `hmac.compare_digest` on the teacher-token check (3 sites). Per-IP sliding-window rate limit on the three public endpoints (`/api/cohort/join` 10/h, `/api/cohort/exists` 30/min, `/api/student/status` 120/min). WCAG AA contrast on dashboard text. Recette coverage for the previously untested `/api/proof`, `/api/journal-text`, `/api/verify-flag`, `/logout`. |
| 2 | `9fa1388` | `app.py` extraction (992 -> 704 lines, below the 800-line audit limit). Inline `onclick` removed from `dashboard.html` to align with future CSP `script-src 'self'`. |
| 3 | `6d9f7ad` | CSRF double-submit cookie on browser sessions (API clients via `X-Teacher-Token` header are exempt by design). After-request middleware sets `X-Content-Type-Options`, `X-Frame-Options DENY`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy` on every response. |
| 4 | `5a75df8` | Audit log JSONL (6 event types : login_success/fail, csrf_fail, sync_blocked, join_request, decision). Privacy-by-design : token prefixes (8 chars) + email domain only. THREAT_MODEL.md (STRIDE 15 threats) added. |
| 5 | `e093cde` | Static security recette `test_security_scan.sh` : bandit + ruff S-rules + pip-audit + secrets grep + absolute-URL check. requirements.txt bumped to close 7 CVEs in flask, flask-cors, requests, pytest. 0 known CVE remaining. |
| 6 | `00e330e` | Recette `test_security_scan.sh` etendue 5 -> 8 checks : SEC-06 semgrep (OWASP top 10 + Python + Flask rule packs, 0 findings), SEC-07 gitleaks (secret scan scoped to `dashboard/`, 0 leaks), SEC-08 safety (CVE second opinion vs pip-audit, 0 vulns). Triple cross-check securite acquis : bandit + semgrep + ruff cote SAST, pip-audit + safety cote SCA, gitleaks + grep cote secrets. |
| 7 | `437b872` | Recette etendue 8 -> 10 checks. SEC-09 pytest under coverage.py (32/32 PASS, **65%** dashboard/ coverage, seuil 60%). SEC-10 OWASP ZAP DAST baseline via docker (`ghcr.io/zaproxy/zaproxy:stable`, FAIL=0, PASS=65, WARN-NEW=2 info-disclosure non-bloquants). Mitigation Server-header leak (Werkzeug/3.1.8 Python/3.13.7 -> "JuiceLab") par patch `WSGIRequestHandler.server_version` + ajout `Cache-Control: no-store` global. 2 stale assertions corrigees (401 -> 302 redirect-to-login, "Eleves" -> "Roster"). |
| 8 | `3988479` | **CSP `unsafe-inline` ELIMINE**. `script-src` durci avec `'nonce-XXX' 'strict-dynamic'` (per-request nonce via `secrets.token_urlsafe(16)` + `before_request` + `context_processor`); 7 blocs inline `<script>` taggues `nonce="{{ csp_nonce }}"`. `style-src` reduit a `'self'` (10 attributs `style="..."` extraits vers `.w-10/.w-25p/.link-plain/.hidden/...` dans `dashboard.css`). Suite ZAP : `PASS=66, WARN-NEW=1, FAIL=0` (seul reste `Cache-Control: no-store` flagged, comportement attendu). Coverage push : `+12 tests proof_signing` (`test_proof_signing.py` couvre `build_proof_markdown`, `sign_proof`, `verify_proof.verify` -- HMAC roundtrip, tamper-detect, wrong-secret, malformed-sig). Coverage globale **65% -> 75%** (+10 pts). `proof_routes.py` 9% -> 56%, `verify_proof.py` 0% -> 52%. 44/44 pytest PASS + 71/71 bash recettes PASS. |
| 9 | `5cb2d7b` | **SRI (Subresource Integrity) sur stylesheet local**. SHA-384 du fichier `dashboard.css` calcule au boot (`_compute_css_sri` via `hashlib.sha384 + base64`), expose dans le contexte Jinja (`{{ css_sri }}`), injecte dans les 4 templates avec `integrity="sha384-..." crossorigin="anonymous"`. Defense contre reverse proxy compromis qui swappe le CSS (l'attaquant ne peut pas modifier la feuille sans casser le hash). Coverage push : `+22 tests cohorts_routes/join_routes` (`test_cohorts_join_routes.py` couvre CRUD `/api/cohorts`, `/api/cohort/exists`, `/api/cohort/join`, `/api/student/status`) + `+10 tests rate_limit` (`test_rate_limit.py` couvre `ip_key` XFF parsing, decorator quota/window/IP-iso/endpoint-iso, monkeypatched time slide). Coverage globale **75% -> 83%** (+8 pts). `cohorts_routes.py` 26% -> 91%, `join_routes.py` 35% -> 89%, `rate_limit.py` 48% -> 100%. 76/76 pytest PASS + 71/71 bash recettes PASS. |
| 10 | `d735667` | **Coverage 90% atteint + bandit baseline + gitleaks scoped**. Coverage push : `+15 tests proof HTTP path` (`test_proof_http.py` couvre `/api/verify-flag` flag valide via HMAC-SHA1, missing-fields/disabled-when-secret-missing/wrong-flag, `/api/journal-text` auth/missing/latest-after-text, `/api/proof` validation-args/no-events/signed-output/disabled-when-secret-missing) + `+11 tests pending/approve/reject` (`test_students_pending.py` couvre workflow trilateral cohorte : `/api/students/pending` auth+filter+empty, `/api/students/<tok>/approve` -> status validated, `/api/students/<tok>/reject` -> rejected, reject-puis-approve flow). Coverage globale **83% -> 90%** (+7 pts). `proof_routes.py` 56% -> 85%, `students_routes.py` 65% -> 93%. Bandit baseline file `.bandit-baseline.json` pinne 1 MEDIUM acceptable (B104 binding 0.0.0.0 documented via `noqa`); recette echoue desormais si MEDIUM > baseline. Gitleaks scope etendu via `dashboard/.gitleaks.toml` (allowlist `dashboard/tests/.*` pour fixtures synthetiques, conserve full scan productif). 102/102 pytest PASS + 71/71 bash recettes PASS. |
| 11 | `6ddb4d7` | **Coverage 93% + CI security recette enforced**. Coverage push : `+14 tests csrf_helpers` (`test_csrf_helpers.py` couvre `issue_csrf_token` entropie, `set_csrf_cookie` headers (HttpOnly=false, SameSite=Lax, Secure-via-DASHBOARD_HTTPS), `clear_csrf_cookie` expires, `check_csrf` 4 branches : safe-method, X-Teacher-Token bypass, missing-header/cookie, mismatched, matched POST/PUT/DELETE) + `+19 tests i18n_helpers` (`test_i18n_helpers.py` couvre `_load_catalog` cached/missing/parse-failure, `_resolve_lang` URL/cookie/Accept-Language/default + cookie-overrides-AL precedence, `_translate` known/unknown/fallback-default/format-substitute/format-error-swallow, `after_request` cookie set-on-URL-param + Secure-on-HTTPS) + `+9 tests verify_proof CLI` (`test_verify_proof_cli.py` couvre `main()` argparse, --secret flag, --secret-env, env-missing, secret-too-short, file-not-found, valid/invalid/wrong-secret, no-signature). Coverage globale **90% -> 93%** (+3 pts). `csrf.py` 67% -> 100%, `i18n_helpers.py` 75% -> 100%, `verify_proof.py` 52% -> 96%. **CI pipeline durci** : nouveau job `dashboard-security-recette` dans `.github/workflows/ci.yml` qui execute la recette complete (bandit + ruff + pip-audit + semgrep + gitleaks + safety + pytest+coverage) sur chaque push/PR sur main. Toute regression securite bloque le merge desormais. 144/144 pytest PASS + 71/71 bash recettes PASS. |
| 12 | `f2528c6` | **Lockfile pinned + CodeQL semantic analysis**. Recette **11 checks** (de 10 a 11). SEC-11 nouveau gate : `pip-compile --generate-hashes` regenere `dashboard/requirements.lock.txt` et diff vs etat commit. Bloque si drift. 18 packages pinnes avec `--hash=sha256:<...>` (chaine transitive complete : blinker, certifi, charset-normalizer, click, flask, flask-cors, idna, iniconfig, itsdangerous, jinja2, markupsafe, packaging, pluggy, pygments, pytest, requests, urllib3, werkzeug). CI installe avec `pip install --require-hashes -r requirements.lock.txt`. **Nouveau workflow `.github/workflows/codeql.yml`** : analyse semantique GitHub-native (Python + JS/TS), pack `security-extended` (taint flow + CWE), scope dashboard/ + .github/workflows, excluder juice-shop/ (volontairement vulnerable). Trigger : push, PR, cron hebdomadaire lundi 04:00 UTC pour rattraper CVE drift inter-merge. 144/144 pytest PASS + 71/71 bash recettes PASS + 11/11 security recette PASS. |
| 15 | `951bda6` | **License compliance gate + app.py coverage**. SEC-13 nouveau gate recette : `pip-licenses` audite les 18 packages du lockfile, refuse GPL/AGPL/LGPL (incompatible MIT distribution). Allowlist : BSD/MIT/MPL 2.0/Apache 2.0/PSF/ISC/Public Domain. Status actuel : 18/18 pkgs OK (Flask BSD, Flask-Cors MIT, requests Apache 2.0, certifi MPL 2.0, etc.). Coverage push : `+10 tests app.py routes` (`test_app_routes.py` couvre `/login` GET form rendering + next param, `/login` POST wrong-token-401, correct-token-302-with-csrf-cookies, default-next, disabled-when-no-teacher-token-503, `/logout` clear-cookies-302, `/api/cohort` missing/empty/unknown). Coverage globale **95% -> 96%** (+1 pt). `app.py` 83% -> 91% (+8). CI : `pip-licenses` ajoute au toolchain `dashboard-security-recette`. Recette **12 -> 13 checks**. 172/172 pytest PASS + 71/71 bash recettes PASS + 13/13 security recette PASS. |
| 14 | `829a547` | **Crypto invariants (mutation-style) + branch protection documented**. Nouveau test `test_crypto_invariants.py` (11 cas) cible specifiquement les operations crypto-critiques que la mutation testing classique attaque : `==` -> `!=`, off-by-one, swap operand, MD5 vs SHA256, constant flip. Couvre : verify (one-byte sig flip, truncation, extra bytes, wrong secret), sign_proof (signature equation HMAC(secret, payload)), check_csrf (one-byte diff, case-sensitive, empty-empty blocked, safe-method bypass, X-Teacher-Token short-circuit priority), HMAC operand swap (key<->msg inversion catches reverse-arg mutation). Detecte regression silencieuse meme si bandit/semgrep/CodeQL ratent. Nouveau `docs/BRANCH_PROTECTION.md` (228 lignes) : 8 status checks requis pour merge sur main (pytest, migration, security-recette, compose-validate, shellcheck, yaml-lint, codeql python+JS), `enforce_admins: true`, `required_signatures: true`, `required_linear_history: true`, `allow_force_pushes: false`, snippet `gh api PUT` ready-to-run + verification command + tradeoffs documentes. 162/162 pytest PASS + 71/71 bash recettes PASS + 12/12 security recette PASS. |
| 13 | `1494b6e` | **SBOM CycloneDX + coverage 95%**. SEC-12 nouveau gate recette : `cyclonedx-py requirements dashboard/requirements.lock.txt` genere SBOM JSON CycloneDX 1.6 avec 18 composants pURL (`pkg:pypi/flask@3.1.3`, etc.), exigence >= 15 composants. CI ajoute step de generation + `actions/upload-artifact@v4` retention 90j -- SBOM downloadable depuis GitHub Actions UI pour audit supply-chain. Coverage push : `+7 tests proof/sync edge cases` (`test_proof_edge_cases.py` couvre `build_proof_markdown` quiz_completed avec score+answers detailles, quiz_data sans score, flag-only-no-solve, hints over 100% clampe a 0, `/api/sync` 403 quand pending/rejected, 200 quand validated). Coverage globale **93% -> 95%** (+2 pts). `proof_routes.py` 85% -> 93%, `sync_routes.py` 90% -> 100%. Recette **11 -> 12 checks**. 151/151 pytest PASS + 71/71 bash recettes PASS + 12/12 security recette PASS. |

## Acknowledgements

The threat model is informed by:

* OWASP Top 10 for LLM Applications (we are not an LLM app, but the principles of input separation apply).
* The OWASP Juice Shop threat model under the `pwning.owasp-juice.shop` companion guide.
* The CTFd hardening checklist at <https://docs.ctfd.io/docs/security/>.

Thanks for keeping the classroom safe.
