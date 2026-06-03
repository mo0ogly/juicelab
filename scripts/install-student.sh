#!/usr/bin/env bash
# JuiceLab — installateur eleve / smoke test enseignant.
#
# Usage :
#   ./scripts/install-student.sh                       # solo local : dashboard + juice-shop sur la meme machine
#   ./scripts/install-student.sh -c M2-IA-2026         # cohort_id en argument
#   ./scripts/install-student.sh -c X -y               # non interactif, accepte tous les defauts
#   ./scripts/install-student.sh --reset               # docker compose down -v + reinstall propre
#
# Scenario 4 (Juice Shop chez l'eleve, dashboard consolide chez le prof) :
#   Cote eleve :
#     ./scripts/install-student.sh -d 192.168.1.10 -l amelie -c M2-IA-2026
#       -> lance UNIQUEMENT juice-shop, configure pour pousser ses events
#          vers le dashboard du prof (http://192.168.1.10:<DASHBOARD_PORT>).
#   Cote prof :
#     ./scripts/install-student.sh --server -c M2-IA-2026
#       -> lance UNIQUEMENT le dashboard, accessible sur le LAN, et affiche
#          l'IP a distribuer aux eleves.
#
# Modes de lancement :
#   (defaut)   solo local  : services dashboard + juicelab-demo
#   -d HOST    eleve scen.4 : juicelab-demo seul, dashboard_url -> HOST
#   --server   prof scen.4  : dashboard seul, joignable sur le LAN
#
# Ce script :
#   1. verifie docker / docker compose / openssl
#   2. genere TEACHER_ADMIN_TOKEN + DASHBOARD_TEACHER_TOKEN (32 chars random)
#      a partir de openssl rand si absent dans docker/.env
#   3. ecrit / met a jour docker/.env (les valeurs existantes ne sont PAS ecrasees)
#   4. lance les services docker compose adaptes au mode choisi
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
DASHBOARD_HOST=""      # -d : IP/host du dashboard prof (scenario 4 cote eleve)
INSTANCE_LABEL=""      # -l : nom unique de l'instance eleve dans la matrice prof
SERVER_ONLY=0          # --server : lance uniquement le dashboard (scenario 4 cote prof)

# ---- args ------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--cohort)    COHORT_ID="$2"; shift 2 ;;
        -d|--dashboard) DASHBOARD_HOST="$2"; shift 2 ;;
        -l|--label)     INSTANCE_LABEL="$2"; shift 2 ;;
        --server)       SERVER_ONLY=1; shift ;;
        -y|--yes)       ASSUME_YES=1; shift ;;
        --reset)        RESET=1; shift ;;
        -h|--help)
            sed -n '2,38p' "$0"
            exit 0
            ;;
        *) echo "Argument inconnu : $1" >&2; exit 2 ;;
    esac
done

# -d et --server sont mutuellement exclusifs (eleve distant vs prof serveur).
if [[ -n "${DASHBOARD_HOST}" && "${SERVER_ONLY}" -eq 1 ]]; then
    echo "Erreur : -d/--dashboard (eleve) et --server (prof) sont exclusifs." >&2
    exit 2
fi

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
    # Reecriture portable : `sed -i` differe entre GNU (Linux) et BSD (macOS,
    # qui exige `sed -i ''`). On passe par un fichier temporaire pour eviter
    # toute divergence.
    local key="$1" val="$2" tmp
    if [[ -f "${ENV_FILE}" ]] && grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
        tmp="$(mktemp "${ENV_FILE}.XXXXXX")"
        sed "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}" > "${tmp}" && mv "${tmp}" "${ENV_FILE}"
    else
        printf '%s=%s\n' "${key}" "${val}" >> "${ENV_FILE}"
    fi
}

# Detection de l'IP LAN, portable Linux + macOS.
#   Linux : hostname -I
#   macOS : ipconfig getifaddr enX (pas de hostname -I), fallback ifconfig.
detect_lan_ip() {
    local ip iface
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    if [[ -z "${ip}" ]] && command -v ipconfig >/dev/null 2>&1; then
        for iface in en0 en1 en2 en3; do
            ip="$(ipconfig getifaddr "${iface}" 2>/dev/null)"
            [[ -n "${ip}" ]] && break
        done
    fi
    if [[ -z "${ip}" ]] && command -v ifconfig >/dev/null 2>&1; then
        ip="$(ifconfig 2>/dev/null | awk '/inet /{ if ($2 != "127.0.0.1") { print $2; exit } }')"
    fi
    echo "${ip}"
}

# Liste les PIDs qui ECOUTENT sur un port TCP (Linux ss, fallback macOS lsof).
# Le `|| true` final neutralise le grep sans match (exit 1) sous set -o pipefail.
port_listeners() {
    local port="$1"
    {
        if command -v ss >/dev/null 2>&1; then
            ss -ltnpH "sport = :${port}" 2>/dev/null \
                | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u | tr '\n' ' '
        elif command -v lsof >/dev/null 2>&1; then
            lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null | sort -u | tr '\n' ' '
        fi
    } || true
}

port_in_use() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -ltnH "sport = :${port}" 2>/dev/null | grep -q .
    elif command -v lsof >/dev/null 2>&1; then
        lsof -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    else
        return 1   # pas d'outil : on suppose libre, docker tranchera
    fi
}

# Libere un port hote avant le lancement docker. Strategie graduee :
#   1. (si demande) stoppe le service systemd user juicelab-dashboard ;
#   2. tue les process restants qui ecoutent (TERM puis KILL) ;
#   3. abandonne avec un message clair si toujours occupe.
free_port() {
    local port="$1" stop_service="${2:-}" pids
    port_in_use "${port}" || return 0   # deja libre

    if [[ "${stop_service}" == "service" ]] && command -v systemctl >/dev/null 2>&1; then
        if systemctl --user is-active --quiet juicelab-dashboard.service 2>/dev/null; then
            warn "Port ${port} : arret du service juicelab-dashboard.service (systemd user)"
            systemctl --user stop juicelab-dashboard.service 2>/dev/null || true
            sleep 1
        fi
    fi

    pids="$(port_listeners "${port}")"
    if [[ -n "${pids// /}" ]]; then
        warn "Port ${port} occupe (PID ${pids}) — arret force"
        kill ${pids} 2>/dev/null || true
        sleep 2
        pids="$(port_listeners "${port}")"
        if [[ -n "${pids// /}" ]]; then
            kill -9 ${pids} 2>/dev/null || true
            sleep 1
        fi
    fi

    if port_in_use "${port}"; then
        die "Port ${port} toujours occupe apres tentative de liberation. Le liberer manuellement puis relancer."
    fi
    ok "Port ${port} libere"
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

# Secret de signature des preuves (mode solo : active /api/proof et le diplome).
# Inoffensif a generer en mode cohorte : le dashboard prof a le sien.
CURRENT_PROOF="$(env_get DASHBOARD_PROOF_SECRET || true)"
if is_token_valid "${CURRENT_PROOF}"; then
    ok "DASHBOARD_PROOF_SECRET deja configure (preserve)"
else
    NEW="$(gen_token)"
    env_set DASHBOARD_PROOF_SECRET "${NEW}"
    ok "DASHBOARD_PROOF_SECRET genere"
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

# ---- Step 2b : cablage scenario 4 (eleve distant) --------------------------

if [[ -n "${DASHBOARD_HOST}" ]]; then
    env_set DASHBOARD_PUBLIC_HOST "${DASHBOARD_HOST}"
    ok "DASHBOARD_PUBLIC_HOST = ${DASHBOARD_HOST} (events pousses vers le dashboard prof)"

    # Label unique de l'instance dans la matrice prof. Defaut : nom de session.
    if [[ -z "${INSTANCE_LABEL}" ]]; then
        INSTANCE_LABEL="$(id -un 2>/dev/null || echo eleve)"
    fi
    env_set JUICELAB_INSTANCE_LABEL "${INSTANCE_LABEL}"
    ok "JUICELAB_INSTANCE_LABEL = ${INSTANCE_LABEL}"
elif [[ -n "${INSTANCE_LABEL}" ]]; then
    env_set JUICELAB_INSTANCE_LABEL "${INSTANCE_LABEL}"
    ok "JUICELAB_INSTANCE_LABEL = ${INSTANCE_LABEL}"
fi

# ---- Step 3 : build + up ---------------------------------------------------

# Selection des services selon le mode :
#   --server         -> dashboard seul (prof, scenario 4)
#   -d HOST          -> juicelab-demo seul (eleve, scenario 4)
#   (defaut)         -> dashboard + juicelab-demo (solo local)
if [[ "${SERVER_ONLY}" -eq 1 ]]; then
    COMPOSE_SERVICES=(dashboard)
    say "Mode prof (--server) : build + lancement du dashboard seul"
elif [[ -n "${DASHBOARD_HOST}" ]]; then
    COMPOSE_SERVICES=(juicelab-demo)
    say "Mode eleve (-d ${DASHBOARD_HOST}) : build + lancement de juice-shop seul"
else
    COMPOSE_SERVICES=(dashboard juicelab-demo)
    say "Mode solo local : build + lancement dashboard + juice-shop"
fi

# Ports hote a binder selon le mode (defaut .env : dashboard 5050, demo 3000).
DASHBOARD_PORT="$(env_get DASHBOARD_PORT)"; DASHBOARD_PORT="${DASHBOARD_PORT:-5050}"
DEMO_PORT="$(env_get JUICELAB_DEMO_PORT)"; DEMO_PORT="${DEMO_PORT:-3000}"

# Retire d'abord nos propres conteneurs/reseau stale (idempotent, garde les volumes).
(cd "${DOCKER_DIR}" && "${DC[@]}" --env-file .env down >/dev/null 2>&1 || true)

# Libere les ports que ce mode va utiliser : service systemd juicelab + process tiers.
if [[ "${SERVER_ONLY}" -eq 1 ]]; then
    free_port "${DASHBOARD_PORT}" service
elif [[ -n "${DASHBOARD_HOST}" ]]; then
    free_port "${DEMO_PORT}"
else
    free_port "${DASHBOARD_PORT}" service
    free_port "${DEMO_PORT}"
fi

say "docker compose up -d --build (premier build : 5-8 min, builds suivants : 10s)"
(cd "${DOCKER_DIR}" && "${DC[@]}" --env-file .env up -d --build "${COMPOSE_SERVICES[@]}")
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

DASHBOARD_PORT="$(env_get DASHBOARD_PORT)"; DASHBOARD_PORT="${DASHBOARD_PORT:-5050}"

if [[ "${SERVER_ONLY}" -eq 1 ]]; then
    wait_http "http://127.0.0.1:${DASHBOARD_PORT}/api/health" "Dashboard /api/health"
elif [[ -n "${DASHBOARD_HOST}" ]]; then
    wait_http "http://127.0.0.1:3000/" "Juice Shop"
    # Dashboard distant : verification best-effort (le LAN/firewall peut bloquer).
    if curl -fsS --max-time 3 "http://${DASHBOARD_HOST}:${DASHBOARD_PORT}/api/health" >/dev/null 2>&1; then
        ok "Dashboard prof joignable : http://${DASHBOARD_HOST}:${DASHBOARD_PORT}/api/health"
    else
        warn "Dashboard prof http://${DASHBOARD_HOST}:${DASHBOARD_PORT} injoignable depuis ici."
        warn "Verifier que le prof a lance --server, que le LAN est plat, et le firewall (port ${DASHBOARD_PORT})."
    fi
else
    wait_http "http://127.0.0.1:3000/" "Juice Shop"
    wait_http "http://127.0.0.1:${DASHBOARD_PORT}/api/health" "Dashboard /api/health"
fi

# ---- Step 5 : recap --------------------------------------------------------

echo
echo "========================================================================"
printf "${C_OK}Installation OK${C_OFF}\n\n"

if [[ "${SERVER_ONLY}" -eq 1 ]]; then
    LAN_IP="$(detect_lan_ip)"; LAN_IP="${LAN_IP:-<ip-de-cette-machine>}"
    cat <<EOF
  Mode prof (--server) : dashboard de consolidation lance.

  Prof   -> http://127.0.0.1:${DASHBOARD_PORT}/login            (token ci-dessous)
  Prof   -> http://127.0.0.1:${DASHBOARD_PORT}/dashboard?cohort=${COHORT_ID}

  A DISTRIBUER AUX ELEVES (scenario 4) :
    Cohorte   : ${COHORT_ID}
    Dashboard : ${LAN_IP}     (commande eleve : ./scripts/install-student.sh -d ${LAN_IP} -c ${COHORT_ID} -l <prenom>)

  CORS : verifier que DASHBOARD_CORS_ORIGINS autorise l'origine des eleves.
         Si tous les eleves ouvrent http://127.0.0.1:3000, valeur actuelle OK :
         $(env_get DASHBOARD_CORS_ORIGINS)

  DASHBOARD_TEACHER_TOKEN = $(env_get DASHBOARD_TEACHER_TOKEN)
EOF
elif [[ -n "${DASHBOARD_HOST}" ]]; then
    cat <<EOF
  Mode eleve (scenario 4) : juice-shop lance, events pousses vers le prof.

  Eleve  -> http://127.0.0.1:3000/#/juicelab           (parcours TD)
  Eleve  -> http://127.0.0.1:3000/#/score-board        (challenges OWASP)

  Cohorte           : ${COHORT_ID}
  Instance (label)  : $(env_get JUICELAB_INSTANCE_LABEL)
  Dashboard prof    : http://${DASHBOARD_HOST}:${DASHBOARD_PORT}
EOF
else
    cat <<EOF
  Mode solo local : dashboard + juice-shop sur cette machine.

  Eleve  -> http://127.0.0.1:3000/#/juicelab           (parcours TD)
  Eleve  -> http://127.0.0.1:3000/#/score-board        (challenges OWASP)
  Prof   -> http://127.0.0.1:${DASHBOARD_PORT}/login            (token ci-dessous)
  Prof   -> http://127.0.0.1:${DASHBOARD_PORT}/dashboard?cohort=${COHORT_ID}

  DASHBOARD_TEACHER_TOKEN = $(env_get DASHBOARD_TEACHER_TOKEN)
  TEACHER_ADMIN_TOKEN     = $(env_get TEACHER_ADMIN_TOKEN)
EOF
fi

cat <<EOF

  Stop  : (cd docker && ${DC[*]} --env-file .env down)
  Wipe  : (cd docker && ${DC[*]} --env-file .env down -v)
  Logs  : (cd docker && ${DC[*]} --env-file .env logs -f)
========================================================================
EOF
