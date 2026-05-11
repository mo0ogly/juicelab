#!/usr/bin/env bash
# JuiceLab — installateur eleve / smoke test enseignant.
#
# Usage :
#   ./scripts/install-student.sh                # installation interactive (cohort_id demande)
#   ./scripts/install-student.sh -c M2-IA-2026  # cohort_id en argument
#   ./scripts/install-student.sh -c X -y        # non interactif, accepte tous les defauts
#   ./scripts/install-student.sh --reset        # docker compose down -v + reinstall propre
#
# Ce script :
#   1. verifie docker / docker compose / openssl
#   2. genere TEACHER_ADMIN_TOKEN + DASHBOARD_TEACHER_TOKEN (32 chars random)
#      a partir de openssl rand si absent dans docker/.env
#   3. ecrit / met a jour docker/.env (les valeurs existantes ne sont PAS ecrasees)
#   4. lance docker compose --env-file .env up -d --build
#   5. attend la disponibilite des endpoints / health-check
#   6. affiche les URLs eleve / prof
#
# Idempotent : re-executer le script ne genere pas de nouveaux tokens si
# docker/.env contient deja des valeurs valides (>= 16 chars).

set -euo pipefail

JUICELAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${JUICELAB_ROOT}/docker"
ENV_FILE="${DOCKER_DIR}/.env"
ENV_EXAMPLE="${DOCKER_DIR}/.env.example"

COHORT_ID=""
ASSUME_YES=0
RESET=0

# ---- args ------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--cohort) COHORT_ID="$2"; shift 2 ;;
        -y|--yes)    ASSUME_YES=1; shift ;;
        --reset)     RESET=1; shift ;;
        -h|--help)
            sed -n '2,18p' "$0"
            exit 0
            ;;
        *) echo "Argument inconnu : $1" >&2; exit 2 ;;
    esac
done

# ---- helpers ---------------------------------------------------------------

C_INFO='\033[1;36m'; C_OK='\033[1;32m'; C_WARN='\033[1;33m'; C_ERR='\033[1;31m'; C_OFF='\033[0m'
say()  { printf "${C_INFO}==>${C_OFF} %s\n" "$*"; }
ok()   { printf "${C_OK}OK${C_OFF}  %s\n" "$*"; }
warn() { printf "${C_WARN}!!! ${C_OFF}%s\n" "$*"; }
die()  { printf "${C_ERR}!!! ${C_OFF}%s\n" "$*" >&2; exit 1; }

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Outil manquant : $1. Installe-le avant de relancer."
}

prompt() {
    local question="$1" default="${2:-}" reply
    if [[ "${ASSUME_YES}" -eq 1 ]]; then
        echo "${default}"; return
    fi
    if [[ -n "${default}" ]]; then
        read -r -p "${question} [${default}] : " reply
        echo "${reply:-${default}}"
    else
        read -r -p "${question} : " reply
        echo "${reply}"
    fi
}

gen_token() {
    openssl rand -hex 16   # 32 chars, satisfait l'exigence >= 16
}

env_get() {
    local key="$1"
    [[ -f "${ENV_FILE}" ]] || { echo ""; return; }
    awk -F= -v k="${key}" '$1==k { sub(/^[^=]*=/,""); print; exit }' "${ENV_FILE}"
}

env_set() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
    else
        printf '%s=%s\n' "${key}" "${val}" >> "${ENV_FILE}"
    fi
}

is_token_valid() {
    local v="$1"
    [[ -n "${v}" && "${v}" != replace-me-with-* && ${#v} -ge 16 ]]
}

# ---- Step 0 : prereqs ------------------------------------------------------

say "Verification des prerequis"
need_cmd docker
need_cmd openssl
need_cmd awk
need_cmd sed

if docker compose version >/dev/null 2>&1; then
    DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    DC=(docker-compose)
else
    die "docker compose v2 (ou docker-compose v1) introuvable."
fi
ok "docker, openssl, ${DC[*]} disponibles"

[[ -d "${DOCKER_DIR}" ]] || die "Dossier docker/ introuvable : ${DOCKER_DIR}"
[[ -f "${ENV_EXAMPLE}" ]] || die ".env.example introuvable : ${ENV_EXAMPLE}"

# ---- Step 1 : reset si demande --------------------------------------------

if [[ "${RESET}" -eq 1 ]]; then
    say "--reset : docker compose down -v (efface les volumes)"
    (cd "${DOCKER_DIR}" && "${DC[@]}" --env-file .env down -v 2>/dev/null || true)
    rm -f "${ENV_FILE}"
    ok "Etat precedent supprime"
fi

# ---- Step 2 : .env ---------------------------------------------------------

if [[ ! -f "${ENV_FILE}" ]]; then
    say "Creation de docker/.env a partir de .env.example"
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
fi

CURRENT_TEACHER="$(env_get TEACHER_ADMIN_TOKEN || true)"
CURRENT_DASHBOARD="$(env_get DASHBOARD_TEACHER_TOKEN || true)"
CURRENT_COHORT="$(env_get JUICELAB_COHORT_ID || true)"

if is_token_valid "${CURRENT_TEACHER}"; then
    ok "TEACHER_ADMIN_TOKEN deja configure (preserve)"
else
    NEW="$(gen_token)"
    env_set TEACHER_ADMIN_TOKEN "${NEW}"
    ok "TEACHER_ADMIN_TOKEN genere"
fi

if is_token_valid "${CURRENT_DASHBOARD}"; then
    ok "DASHBOARD_TEACHER_TOKEN deja configure (preserve)"
else
    NEW="$(gen_token)"
    env_set DASHBOARD_TEACHER_TOKEN "${NEW}"
    ok "DASHBOARD_TEACHER_TOKEN genere"
fi

if [[ -z "${COHORT_ID}" ]]; then
    if [[ -n "${CURRENT_COHORT}" && "${CURRENT_COHORT}" != replace-me-with-* ]]; then
        COHORT_ID="${CURRENT_COHORT}"
        ok "JUICELAB_COHORT_ID deja configure : ${COHORT_ID}"
    else
        COHORT_ID="$(prompt 'Identifiant de cohorte (ex M2-IA-2026)' 'M2-IA-2026')"
    fi
fi
env_set JUICELAB_COHORT_ID "${COHORT_ID}"
ok "JUICELAB_COHORT_ID = ${COHORT_ID}"

# ---- Step 3 : build + up ---------------------------------------------------

say "docker compose up -d --build (premier build : 5-8 min, builds suivants : 10s)"
(cd "${DOCKER_DIR}" && "${DC[@]}" --env-file .env up -d --build)
ok "Conteneurs lances"

# ---- Step 4 : health checks ------------------------------------------------

say "Attente des endpoints (timeout 120s par endpoint)"

wait_http() {
    local url="$1" name="$2" timeout="${3:-120}" elapsed=0
    while (( elapsed < timeout )); do
        if curl -fsS --max-time 3 "${url}" >/dev/null 2>&1; then
            ok "${name} : ${url}"
            return 0
        fi
        sleep 3; elapsed=$((elapsed + 3))
    done
    warn "${name} pas encore pret apres ${timeout}s : ${url}"
    return 1
}

DASHBOARD_PORT="$(env_get DASHBOARD_PORT)"; DASHBOARD_PORT="${DASHBOARD_PORT:-5000}"

wait_http "http://127.0.0.1:3000/" "Juice Shop"
wait_http "http://127.0.0.1:${DASHBOARD_PORT}/api/health" "Dashboard /api/health"

# ---- Step 5 : recap --------------------------------------------------------

cat <<EOF

========================================================================
${C_OK}Installation OK${C_OFF}

  Eleve  -> http://127.0.0.1:3000/#/juicelab           (parcours TD)
  Eleve  -> http://127.0.0.1:3000/#/score-board        (challenges OWASP)
  Prof   -> http://127.0.0.1:${DASHBOARD_PORT}/login            (token ci-dessous)
  Prof   -> http://127.0.0.1:${DASHBOARD_PORT}/dashboard?cohort=${COHORT_ID}

  DASHBOARD_TEACHER_TOKEN = $(env_get DASHBOARD_TEACHER_TOKEN)
  TEACHER_ADMIN_TOKEN     = $(env_get TEACHER_ADMIN_TOKEN)

  Stop  : (cd docker && ${DC[*]} --env-file .env down)
  Wipe  : (cd docker && ${DC[*]} --env-file .env down -v)
  Logs  : (cd docker && ${DC[*]} --env-file .env logs -f)
========================================================================
EOF
