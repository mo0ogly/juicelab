# JuiceLab Dashboard - Posture de sécurité

> Version anglaise : [SECURITY_POSTURE.md](./SECURITY_POSTURE.md).

Instantané du durcissement obtenu au fil de 17 cycles PDCA sur le
périmètre `dashboard/`. Ce document est le résumé en une page destiné
aux revues OWASP, aux rapports d'audit et aux questionnaires d'appel
d'offres. Le journal cycle par cycle faisant foi est dans [`SECURITY.md`](../SECURITY.md).

## Périmètre

Cette posture s'applique au tableau de bord enseignant JuiceLab (Flask)
(`dashboard/`, servi sur le port 5050). Le cœur OWASP Juice Shop qui
s'exécute en dessous reste délibérément vulnérable pour les exercices
d'exploitation des étudiants — c'est son objectif pédagogique et il est
hors périmètre ici.

## Contrôles en place

### Sécurité applicative (SAST)

| Outil | Ce qu'il détecte | État |
|---|---|---|
| bandit | Anti-patterns de sécurité Python | HIGH=0 ; MEDIUM=1 ancré en baseline |
| ruff règles S | Sous-ensemble de sécurité du linter Python | 0 findings |
| semgrep | OWASP Top 10 + packs de règles Python + Flask | 0 findings |
| CodeQL | SAST sémantique natif GitHub + analyse de flux CWE | exécuté à chaque push/PR + cron hebdomadaire |

### Sécurité des dépendances (SCA)

| Outil | Ce qu'il détecte | État |
|---|---|---|
| pip-audit | CVE dans les dépendances Python épinglées | 0 CVE connu |
| safety | Base CVE indépendante (second avis) | 0 CVE connu |
| Dependabot | PR automatique sur correctif CVE / montée mineure | hebdomadaire lun. 04 h 30 Europe/Paris |
| pip-licenses (SEC-13) | Refus GPL / AGPL / LGPL | 18/18 OK (BSD/MIT/Apache/MPL) |
| requirements.lock.txt | Dépendances épinglées par hachage, installation `--require-hashes` | 18 paquets, sha256 attesté |

### Gestion des secrets

| Outil | Ce qu'il détecte | État |
|---|---|---|
| gitleaks | Secrets codés en dur dans les sources | 0 fuite dans `dashboard/` (tests en liste blanche) |
| `.bandit-baseline.json` | Findings acceptables épinglés, garde de régression | baseline + 0 écart |
| Chaînes HMAC | Token enseignant + secret de preuve | `hmac.compare_digest` temporellement sûr partout |
| Journal d'audit JSONL | Tentatives de connexion, échecs CSRF, blocages sync, décisions | vie privée by design (préfixe de token + domaine e-mail) |

### Sécurité réseau

| En-tête | Valeur | Cycle |
|---|---|---|
| `Content-Security-Policy` | `'self' nonce-XXX 'strict-dynamic'` (pas de `unsafe-inline`) | 8 |
| `X-Content-Type-Options` | `nosniff` | 3 |
| `X-Frame-Options` | `DENY` | 3 |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | 3 |
| `Permissions-Policy` | `interest-cohort=()` | 3 |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` (HTTPS uniquement) | 17 |
| `Cache-Control` | `no-store` global | 7 |
| `Server` | masqué pour éviter la fuite de version Werkzeug | 7 |

### Anti-falsification

| Défense | Mécanisme | Cycle |
|---|---|---|
| Protection CSRF | Cookie double-submit, client API (`X-Teacher-Token`) exempté | 3 |
| SRI sur la feuille de style | `integrity="sha384-<hash>"` calculé au démarrage | 9 |
| Nonce CSP par requête | `secrets.token_urlsafe(16)` par requête | 8 |
| Signature de preuve | HMAC-SHA256, `proof.md` inviolable | upstream |
| Vérification de flag | HMAC-SHA1 (compat. OWASP CTF), temporellement sûr | upstream |

### Opérations

| Contrôle | Rôle | Cycle |
|---|---|---|
| Limitation de débit par IP | fenêtre glissante sur les endpoints publics | 1 |
| Liste blanche CORS | uniquement l'origine Juice Shop (configurable) | initial |
| Passerelle de cohorte | `/api/sync` renvoie 403 tant que l'enseignant n'a pas approuvé l'étudiant | 0 |
| Redirection à la connexion | `/dashboard` -> `/login` si non authentifié | 0 |
| Journal d'audit | JSONL en ajout seul, 6 types d'événements | 4 |

### Sécurité dynamique (DAST)

| Outil | Couverture | État |
|---|---|---|
| OWASP ZAP baseline | Exploration passive, 66 règles | FAIL=0, PASS=66, WARN=1 (no-store sur 404, intentionnel) |

### Tests

| Métrique | Valeur | Cycle |
|---|---|---|
| Suite pytest | 177 tests | 17 |
| Couverture de code | 96 % sur `dashboard/` | 15 |
| Recettes Bash | 71 tests fonctionnels | initial |
| Recette de sécurité | 14/14 portes | 16 |
| Invariants cryptographiques | 11 tests de style mutation sur `verify`, `sign_proof`, `check_csrf` | 14 |

### Chaîne d'approvisionnement

| Artefact | Format | Cycle |
|---|---|---|
| SBOM | CycloneDX 1.6 JSON, 18 composants avec pURL | 13 |
| Lockfile | Sortie pip-compile `--require-hashes` | 12 |
| Manifeste de licences | `dashboard/LICENSES.md` généré automatiquement | 16 |
| Générateur | `scripts/gen_licenses.sh` reproductible | 16 |

### CI/CD

| Workflow | Exécutions | Cycle |
|---|---|---|
| `dashboard-tests` (`ci.yml`) | pytest + migration de schéma | initial |
| `legacy-db-migration` (`ci.yml`) | migration sur SQLite legacy | initial |
| `dashboard-security-recette` (`ci.yml`) | 14 portes complètes SAST/SCA/secrets/couverture/SBOM/licences | 11 |
| `docker-compose-validate` (`ci.yml`) | analyse de la configuration compose | initial |
| `codeql.yml` | SAST sémantique Python + JS/TS | 12 |
| `yaml-lint` | analyse YAML du pack pédagogique | initial |
| `shellcheck` | lint du point d'entrée Docker | initial |

Protection de branche (documentée dans [`BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md)) :
8 vérifications de statut requises, `enforce_admins: true`, `required_signatures: true`,
`required_linear_history: true`, `allow_force_pushes: false`.

## Trajectoire (17 cycles PDCA)

```
72.75 -> 83.25 -> 87.50 -> 94.00 -> 95.65 ->
96.55 -> 97.50 -> 98.40 -> 99.20 -> 99.65 ->
99.85 -> 99.92 -> 99.95 -> 99.97 -> 99.98 ->
99.99 -> 99.99 (plateau)
```

Saturation pratique atteinte au cycle 16. Les gains marginaux supplémentaires
proviennent de contrôles côté infrastructure (soumission de préchargement HSTS,
provenance SLSA, durcissement du proxy inverse) qui se situent en dehors du
code source de l'application.

## Risques résiduels connus

| Risque | Atténuation | Sévérité |
|---|---|---|
| Compromission du `DASHBOARD_TEACHER_TOKEN` | Hors périmètre — le détenteur est l'enseignant | by design |
| Usurpation par un étudiant d'un autre `student_token` | Vérification croisée e-mail JWT en Mode B/C | moyen, documenté dans le modèle de menace |
| Compromission de CTFd (Mode C) | Le tableau de bord ne consomme que `id`+`email`, pas d'injection de code | moyen |
| Compromission du proxy inverse | SRI sur `dashboard.css`, pas encore de SRI JS (inline uniquement) | faible |
| Couverture `proof_routes.py` 93 %, `students_routes.py` 93 %, `app.py` 91 % | cas limites / variantes de rendu de gabarit | faible |

## Comment vérifier

```bash
# Validation locale complète (10 s + ZAP via docker ~30 s) :
bash dashboard/tests/test_security_scan.sh

# Sans DAST (pas de docker) :
SKIP_DAST=1 bash dashboard/tests/test_security_scan.sh

# Régénérer le SBOM :
cyclonedx-py requirements dashboard/requirements.lock.txt \
  --output-format JSON --output-file /tmp/sbom.cdx.json

# Régénérer LICENSES.md :
bash scripts/gen_licenses.sh

# Exécuter la suite pytest complète avec couverture :
coverage run --source=dashboard -m pytest dashboard/tests/test_*.py
coverage report
```

## Signaler une vulnérabilité

Voir [`SECURITY.md`](../SECURITY.md) section "How to report a
vulnerability". Rapport privé via GitHub ou par e-mail à
`mo0ogly@proton.me` avec `[JUICELAB-SEC]` dans l'objet.
