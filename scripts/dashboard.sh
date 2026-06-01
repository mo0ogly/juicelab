#!/usr/bin/env bash
#
# dashboard.sh - gestion du dashboard prof JuiceLab (docker compose).
#
# Le code du dashboard est bati dans l'image (pas monte en volume), donc un
# changement de code .py / .css / template exige un REBUILD, pas un simple
# restart. Le volume juicelab_dashboard_data (la base SQLite) survit a toutes
# les sous-commandes ci-dessous : aucune ne detruit les donnees.
#
# Lance sans argument : menu interactif.
# Sinon, sous-commandes directes :
#   scripts/dashboard.sh update    # git pull origin main PUIS rebuild image
#   scripts/dashboard.sh rebuild   # rebuild image + recreate (sans git pull)
#   scripts/dashboard.sh start     # demarre (sans rebuild)
#   scripts/dashboard.sh stop      # arrete le container
#   scripts/dashboard.sh restart   # stop + start (sans rebuild)
#   scripts/dashboard.sh status    # etat + healthcheck
#   scripts/dashboard.sh logs      # suit les logs
#   scripts/dashboard.sh menu      # force le menu interactif
#
set -euo pipefail

# Racine du repo, quel que soit le cwd d'appel.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$ROOT/docker"
ENV_FILE="$COMPOSE_DIR/.env"
SERVICE="dashboard"
CONTAINER="juicelab-dashboard"
GIT_REMOTE="origin"
GIT_BRANCH="main"

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

if [[ ! -f "$ENV_FILE" ]]; then
  errp "ERREUR: $ENV_FILE absent. Copier .env.example -> .env et renseigner les tokens."
  exit 1
fi

dc() { (cd "$COMPOSE_DIR" && docker compose --env-file "$ENV_FILE" "$@"); }

wait_healthy() {
  local i status
  for i in $(seq 1 30); do
    status="$(docker inspect "$CONTAINER" --format '{{.State.Health.Status}}' 2>/dev/null || echo absent)"
    [[ "$status" == "healthy" ]] && { ok "healthy"; return 0; }
    [[ "$status" == "absent" ]] && { errp "container absent"; return 1; }
    sleep 2
  done
  warn "timeout (dernier etat: ${status:-?})"; return 1
}

# ---- Actions ---------------------------------------------------------------
do_rebuild() {
  say "[dashboard] rebuild image + recreate (la base SQLite est preservee)"
  dc build "$SERVICE"
  dc up -d "$SERVICE"
  printf '[dashboard] sante: '; wait_healthy
}

do_update() {
  say "[dashboard] git pull $GIT_REMOTE/$GIT_BRANCH dans $ROOT"
  if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    errp "ERREUR: $ROOT n'est pas un depot git."
    return 1
  fi
  local before after
  before="$(git -C "$ROOT" rev-parse --short HEAD)"
  git -C "$ROOT" pull --no-rebase --no-edit "$GIT_REMOTE" "$GIT_BRANCH"
  after="$(git -C "$ROOT" rev-parse --short HEAD)"
  if [[ "$before" == "$after" ]]; then
    warn "[dashboard] deja a jour ($before) - rebuild quand meme pour appliquer l'image"
  else
    ok "[dashboard] $before -> $after"
  fi
  do_rebuild
}

do_start()   { say "[dashboard] start"; dc up -d "$SERVICE"; printf '[dashboard] sante: '; wait_healthy; }
do_stop()    { say "[dashboard] stop"; dc stop "$SERVICE"; }
do_restart() { say "[dashboard] restart (sans rebuild)"; dc restart "$SERVICE"; printf '[dashboard] sante: '; wait_healthy; }
do_status()  {
  docker ps --filter "name=$CONTAINER" --format '  {{.Names}}  {{.Status}}  {{.Ports}}' || true
  printf '  health: '; docker inspect "$CONTAINER" --format '{{.State.Health.Status}}' 2>/dev/null || echo "absent"
}
do_logs()    { dc logs -f --tail=100 "$SERVICE"; }

# ---- Menu interactif -------------------------------------------------------
menu() {
  while true; do
    echo
    say   "=== JuiceLab dashboard prof ==="
    echo  "  1) update   - git pull + rebuild (deployer une maj)"
    echo  "  2) rebuild  - rebuild image (sans git pull)"
    echo  "  3) start    - demarrer"
    echo  "  4) stop     - arreter"
    echo  "  5) restart  - redemarrer (sans rebuild)"
    echo  "  6) status   - etat + healthcheck"
    echo  "  7) logs     - suivre les logs (Ctrl-C pour sortir)"
    echo  "  0) quitter"
    printf "%sChoix:%s " "$C_CYAN" "$C_RST"
    local choice; read -r choice || { echo; return 0; }
    case "$choice" in
      1) do_update ;;
      2) do_rebuild ;;
      3) do_start ;;
      4) do_stop ;;
      5) do_restart ;;
      6) do_status ;;
      7) do_logs ;;
      0|q|Q) return 0 ;;
      "") : ;;
      *) warn "choix invalide: $choice" ;;
    esac
  done
}

# ---- Dispatch --------------------------------------------------------------
cmd="${1:-menu}"
case "$cmd" in
  update)  do_update ;;
  rebuild) do_rebuild ;;
  start)   do_start ;;
  stop)    do_stop ;;
  restart) do_restart ;;
  status)  do_status ;;
  logs)    do_logs ;;
  menu)    menu ;;
  *)
    errp "Usage: scripts/dashboard.sh {update|rebuild|start|stop|restart|status|logs|menu}"
    exit 2
    ;;
esac
