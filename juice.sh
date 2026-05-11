#!/usr/bin/env bash
# juice.sh - Launcher JuiceLab (Juice Shop + Dashboard pedagogique) - Linux/macOS
#
# Usage:
#   ./juice.sh start   [shop|dash|all]   (defaut: all)
#   ./juice.sh stop    [shop|dash|all]
#   ./juice.sh restart [shop|dash|all]
#   ./juice.sh status
#   ./juice.sh logs    [shop|dash]
#   ./juice.sh health
#   ./juice.sh build
#   ./juice.sh help
#
# Ports : Juice Shop = 3000, Dashboard Flask = 5050
# PIDs  : .run/<svc>.pid       Logs : .logs/<svc>.log

set -u

# ---- Constantes -----------------------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHOP_DIR="$ROOT/juice-shop"
DASH_DIR="$ROOT/dashboard"
RUN_DIR="$ROOT/.run"
LOG_DIR="$ROOT/.logs"

SHOP_PORT=3000
DASH_PORT=5050

SHOP_PID_FILE="$RUN_DIR/shop.pid"
DASH_PID_FILE="$RUN_DIR/dash.pid"
SHOP_LOG="$LOG_DIR/shop.log"
DASH_LOG="$LOG_DIR/dash.log"
SHOP_ERR="$LOG_DIR/shop.err.log"
DASH_ERR="$LOG_DIR/dash.err.log"

DEFAULT_TEACHER_TOKEN='change-me-please-1234567890'
DEFAULT_PROOF_SECRET='change-me-proof-secret-1234567890'
CTF_KEY_FILE="$ROOT/juice-shop/ctf.key"
CONFIG_JSON="$ROOT/juice-shop/frontend/src/assets/juicelab/config.json"

mkdir -p "$RUN_DIR" "$LOG_DIR"

# ---- Couleurs --------------------------------------------------------------
if [ -t 1 ]; then
  C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YEL=$'\033[33m'; C_RED=$'\033[31m'; C_RST=$'\033[0m'
else
  C_CYAN=''; C_GREEN=''; C_YEL=''; C_RED=''; C_RST=''
fi
say()  { printf "%s%s%s\n" "$C_CYAN"  "$*" "$C_RST"; }
ok()   { printf "%s%s%s\n" "$C_GREEN" "$*" "$C_RST"; }
warn() { printf "%s%s%s\n" "$C_YEL"   "$*" "$C_RST"; }
errp() { printf "%s%s%s\n" "$C_RED"   "$*" "$C_RST" >&2; }

# ---- Helpers ---------------------------------------------------------------
port_listening() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :$port )" 2>/dev/null | awk 'NR>1{found=1} END{exit !found}'
  elif command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -P -n >/dev/null 2>&1
  else
    (echo > /dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1
  fi
}

pid_from_file() {
  local path="$1"
  [ -f "$path" ] || return 1
  local raw
  raw="$(tr -d ' \t\r\n' < "$path" 2>/dev/null)"
  [ -n "$raw" ] || return 1
  case "$raw" in
    ''|*[!0-9]*) return 1 ;;
    *) printf '%s' "$raw" ;;
  esac
}

pid_alive() {
  local pid="$1"
  [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null && kill -0 "$pid" 2>/dev/null
}

resolve_python() {
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1; then
      command -v "$c"
      return 0
    fi
  done
  return 1
}

stop_pid_tree() {
  local pid="$1" label="$2"
  if [ -z "$pid" ] || [ "$pid" -le 0 ] 2>/dev/null; then return; fi
  if ! pid_alive "$pid"; then
    warn "  $label PID=$pid deja eteint"
    return
  fi
  local pgid=""
  pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')"
  if [ -n "$pgid" ] && [ "$pgid" != "0" ]; then
    kill -TERM -"$pgid" 2>/dev/null || true
    sleep 1
    if pid_alive "$pid"; then kill -KILL -"$pgid" 2>/dev/null || true; fi
  else
    kill -TERM "$pid" 2>/dev/null || true
    sleep 1
    if pid_alive "$pid"; then kill -KILL "$pid" 2>/dev/null || true; fi
  fi
  if pid_alive "$pid"; then
    errp "  $label PID=$pid arret impossible"
  else
    ok "  $label PID=$pid arrete"
  fi
}

stop_by_port() {
  local port="$1" label="$2" pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ')"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser -n tcp "$port" 2>/dev/null | tr -s ' ')"
  fi
  pids="$(echo "$pids" | xargs)"
  [ -z "$pids" ] && return 1
  local p
  for p in $pids; do
    warn "  $label orphelin PID=$p sur port $port -> kill"
    stop_pid_tree "$p" "$label"
  done
  return 0
}

# ---- Start / Stop : Juice Shop --------------------------------------------
start_shop() {
  local existing=""
  existing="$(pid_from_file "$SHOP_PID_FILE" 2>/dev/null || true)"
  if [ -n "$existing" ] && pid_alive "$existing"; then
    warn "Juice Shop deja en cours (PID=$existing)"
    return
  fi
  if port_listening "$SHOP_PORT"; then
    errp "Port $SHOP_PORT deja utilise par un autre process. Tape 'ss -ltnp | grep :$SHOP_PORT' pour voir."
    return
  fi
  if [ ! -f "$SHOP_DIR/package.json" ]; then
    errp "package.json introuvable dans $SHOP_DIR"
    return
  fi
  if ! command -v npm >/dev/null 2>&1; then
    errp "npm introuvable dans le PATH"
    return
  fi

  # NODE_ENV=juicelab loads config/juicelab.yml overlay on top of
  # config/default.yml. The overlay clears authorizedRedirects so the
  # "Login with Google" button stays hidden in local-loopback labs (the
  # upstream Google demo clientId does not accept 127.0.0.1 origins).
  : "${JUICELAB_NODE_ENV:=juicelab}"
  say "demarrage Juice Shop (npm start, port $SHOP_PORT, NODE_ENV=$JUICELAB_NODE_ENV)"
  (
    cd "$SHOP_DIR" || exit 1
    NODE_ENV="$JUICELAB_NODE_ENV" setsid nohup npm start >"$SHOP_LOG" 2>"$SHOP_ERR" </dev/null &
    echo $! > "$SHOP_PID_FILE"
  )
  local pid
  pid="$(pid_from_file "$SHOP_PID_FILE" 2>/dev/null || true)"
  ok "  PID=$pid  log=$SHOP_LOG"
}

stop_shop() {
  local existing=""
  existing="$(pid_from_file "$SHOP_PID_FILE" 2>/dev/null || true)"
  if [ -n "$existing" ]; then
    stop_pid_tree "$existing" 'Juice Shop'
    rm -f "$SHOP_PID_FILE"
  else
    warn 'Pas de PID Juice Shop enregistre, recherche par port...'
  fi
  stop_by_port "$SHOP_PORT" 'Juice Shop' || true
}

# ---- Start / Stop : Dashboard ---------------------------------------------
start_dash() {
  local existing=""
  existing="$(pid_from_file "$DASH_PID_FILE" 2>/dev/null || true)"
  if [ -n "$existing" ] && pid_alive "$existing"; then
    warn "Dashboard deja en cours (PID=$existing)"
    return
  fi
  if port_listening "$DASH_PORT"; then
    errp "Port $DASH_PORT deja utilise par un autre process."
    return
  fi
  if [ ! -f "$DASH_DIR/app.py" ]; then
    errp "app.py introuvable dans $DASH_DIR"
    return
  fi

  local py
  py="$(resolve_python || true)"
  if [ -z "$py" ]; then errp "python3/python introuvable dans le PATH"; return; fi

  export DASHBOARD_PORT="$DASH_PORT"

  if [ -z "${DASHBOARD_TEACHER_TOKEN:-}" ] || [ "${#DASHBOARD_TEACHER_TOKEN}" -lt 16 ]; then
    export DASHBOARD_TEACHER_TOKEN="$DEFAULT_TEACHER_TOKEN"
    warn "DASHBOARD_TEACHER_TOKEN non defini, valeur par defaut utilisee (a changer en prod)."
  fi
  if [ -z "${DASHBOARD_PROOF_SECRET:-}" ] || [ "${#DASHBOARD_PROOF_SECRET}" -lt 16 ]; then
    export DASHBOARD_PROOF_SECRET="$DEFAULT_PROOF_SECRET"
    warn "DASHBOARD_PROOF_SECRET non defini, valeur par defaut utilisee (a changer en prod). Utilise pour signer les preuves de lab."
  fi
  if [ -z "${DASHBOARD_DEFAULT_COHORT:-}" ]; then
    if [ -f "$CONFIG_JSON" ]; then
      local cohort=""
      if command -v python3 >/dev/null 2>&1; then
        cohort="$(python3 -c "import json,sys
try:
  d=json.load(open('$CONFIG_JSON'))
  print(d.get('cohort_id',''))
except Exception:
  pass" 2>/dev/null)"
      fi
      if [ -n "$cohort" ]; then
        export DASHBOARD_DEFAULT_COHORT="$cohort"
      else
        warn "Impossible de lire config.json pour deduire DASHBOARD_DEFAULT_COHORT. Le dashboard exigera ?cohort=... dans l'URL."
      fi
    else
      warn "config.json absent ($CONFIG_JSON). Le dashboard exigera ?cohort=... dans l'URL."
    fi
  fi
  if [ -z "${JUICESHOP_CTF_SECRET:-}" ]; then
    if [ -f "$CTF_KEY_FILE" ]; then
      local key
      key="$(tr -d ' \t\r\n' < "$CTF_KEY_FILE" 2>/dev/null)"
      if [ -n "$key" ]; then
        export JUICESHOP_CTF_SECRET="$key"
      fi
    else
      warn "$CTF_KEY_FILE introuvable. Si tu veux activer la verification de flag, cree le fichier ou exporte JUICESHOP_CTF_SECRET manuellement."
    fi
  fi

  if [ -n "${CTFD_URL:-}" ] && [ -n "${CTFD_ADMIN_TOKEN:-}" ]; then
    say "CTFd push enabled (Mode C) -> $CTFD_URL"
  else
    say "CTFd push disabled (Mode A or B). Set CTFD_URL et CTFD_ADMIN_TOKEN pour activer Mode C."
  fi

  say "demarrage Dashboard  ($py app.py, port $DASH_PORT)"
  (
    cd "$DASH_DIR" || exit 1
    setsid nohup "$py" app.py >"$DASH_LOG" 2>"$DASH_ERR" </dev/null &
    echo $! > "$DASH_PID_FILE"
  )
  local pid
  pid="$(pid_from_file "$DASH_PID_FILE" 2>/dev/null || true)"
  ok "  PID=$pid  log=$DASH_LOG"
}

stop_dash() {
  local existing=""
  existing="$(pid_from_file "$DASH_PID_FILE" 2>/dev/null || true)"
  if [ -n "$existing" ]; then
    stop_pid_tree "$existing" 'Dashboard'
    rm -f "$DASH_PID_FILE"
  else
    warn 'Pas de PID Dashboard enregistre, recherche par port...'
  fi
  stop_by_port "$DASH_PORT" 'Dashboard' || true
}

# ---- Status / Health -------------------------------------------------------
show_status() {
  say '== Status JuiceLab =='
  local shop_pid dash_pid shop_alive dash_alive shop_listen dash_listen
  shop_pid="$(pid_from_file "$SHOP_PID_FILE" 2>/dev/null || true)"
  dash_pid="$(pid_from_file "$DASH_PID_FILE" 2>/dev/null || true)"
  if pid_alive "${shop_pid:-0}"; then shop_alive=true; else shop_alive=false; fi
  if pid_alive "${dash_pid:-0}"; then dash_alive=true; else dash_alive=false; fi
  if port_listening "$SHOP_PORT"; then shop_listen=true; else shop_listen=false; fi
  if port_listening "$DASH_PORT"; then dash_listen=true; else dash_listen=false; fi
  printf '  Juice Shop : PID=%s  alive=%s  listen:%s=%s\n' "${shop_pid:--}" "$shop_alive" "$SHOP_PORT" "$shop_listen"
  printf '  Dashboard  : PID=%s  alive=%s  listen:%s=%s\n' "${dash_pid:--}" "$dash_alive" "$DASH_PORT" "$dash_listen"
}

test_health() {
  say '== Health checks =='
  if command -v curl >/dev/null 2>&1; then
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "http://127.0.0.1:$SHOP_PORT/rest/admin/application-version" || true)"
    if [ -n "$code" ] && [ "$code" != "000" ]; then ok "  Juice Shop  HTTP $code"; else errp "  Juice Shop  KO"; fi
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "http://127.0.0.1:$DASH_PORT/api/health" || true)"
    if [ -n "$code" ] && [ "$code" != "000" ]; then ok "  Dashboard   HTTP $code"; else errp "  Dashboard   KO"; fi
  else
    errp "curl introuvable, health check impossible"
  fi
}

# ---- Logs ------------------------------------------------------------------
show_logs() {
  local which="$1"
  case "$which" in
    shop)
      [ -f "$SHOP_LOG" ] || { warn "Pas de log $SHOP_LOG"; return; }
      tail -n 80 -F "$SHOP_LOG"
      ;;
    dash)
      [ -f "$DASH_LOG" ] || { warn "Pas de log $DASH_LOG"; return; }
      tail -n 80 -F "$DASH_LOG"
      ;;
    *)
      errp "logs : 'shop' ou 'dash' attendu"
      ;;
  esac
}

# ---- Build (Juice Shop only) ----------------------------------------------
invoke_build() {
  if ! command -v npm >/dev/null 2>&1; then
    errp 'npm introuvable dans le PATH'
    return
  fi
  say 'npm install (juice-shop)'
  (
    cd "$SHOP_DIR" || exit 1
    npm install || { errp 'npm install a echoue'; exit 1; }
    say 'npm run build:frontend'
    npm run build:frontend || warn 'build:frontend non disponible, on continue'
    say 'npm run build (server)'
    npm run build || warn 'build server non disponible, on continue'
    ok 'Build termine'
  )
}

# ---- Help ------------------------------------------------------------------
show_help() {
  cat <<'EOF'
juice.sh - Launcher JuiceLab (Linux/macOS)

Commandes :
  start   [shop|dash|all]     demarre les services en arriere-plan
  stop    [shop|dash|all]     arrete les services
  restart [shop|dash|all]     stop puis start
  status                      affiche PIDs et ports
  logs     shop|dash          tail -F sur le log
  health                      ping HTTP des deux services
  build                       npm install + build du Juice Shop
  help                        cet ecran

Environnement :
  DASHBOARD_TEACHER_TOKEN     >= 16 caracteres (sinon valeur par defaut)
  DASHBOARD_PROOF_SECRET      >= 16 caracteres (sinon valeur par defaut)
  DASHBOARD_DEFAULT_COHORT    sinon deduit de juice-shop/frontend/src/assets/juicelab/config.json
  JUICESHOP_CTF_SECRET        sinon lu depuis juice-shop/ctf.key
  CTFD_URL + CTFD_ADMIN_TOKEN active le push CTFd (Mode C)
EOF
}

# ---- Dispatcher ------------------------------------------------------------
cmd="${1:-help}"
target="${2:-all}"
case "${cmd,,}" in
  start)
    case "${target,,}" in
      shop) start_shop ;;
      dash) start_dash ;;
      all)  start_shop; start_dash ;;
      *) errp "start : cible inconnue '$target'" ;;
    esac
    ;;
  stop)
    case "${target,,}" in
      shop) stop_shop ;;
      dash) stop_dash ;;
      all)  stop_shop; stop_dash ;;
      *) errp "stop : cible inconnue '$target'" ;;
    esac
    ;;
  restart)
    case "${target,,}" in
      shop) stop_shop; sleep 1; start_shop ;;
      dash) stop_dash; sleep 1; start_dash ;;
      all)  stop_shop; stop_dash; sleep 1; start_shop; start_dash ;;
      *) errp "restart : cible inconnue '$target'" ;;
    esac
    ;;
  status)  show_status ;;
  health)  test_health ;;
  logs)    show_logs "${target,,}" ;;
  build)   invoke_build ;;
  help|-h|--help) show_help ;;
  *)
    errp "commande inconnue '$cmd'"
    show_help
    ;;
esac
