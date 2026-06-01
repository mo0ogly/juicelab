#!/usr/bin/env bash
#
# dashboard.sh - gestion du dashboard prof JuiceLab (docker compose).
#
# Le code du dashboard est bati dans l'image (pas monte en volume), donc un
# changement de code .py exige un REBUILD, pas un simple restart. Le volume
# juicelab_dashboard_data (la base SQLite) survit a tous les sous-commandes
# ci-dessous : aucune ne detruit les donnees.
#
# Usage :
#   scripts/dashboard.sh rebuild   # git pull deja fait -> rebuild image + recreate
#   scripts/dashboard.sh start     # demarre (sans rebuild)
#   scripts/dashboard.sh stop      # arrete le container
#   scripts/dashboard.sh restart   # stop + start (sans rebuild)
#   scripts/dashboard.sh status    # etat + healthcheck
#   scripts/dashboard.sh logs      # suit les logs
#
set -euo pipefail

# Racine du repo, quel que soit le cwd d'appel.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$ROOT/docker"
ENV_FILE="$COMPOSE_DIR/.env"
SERVICE="dashboard"
CONTAINER="juicelab-dashboard"

cd "$COMPOSE_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERREUR: $ENV_FILE absent. Copier .env.example -> .env et renseigner les tokens." >&2
  exit 1
fi

dc() { docker compose --env-file "$ENV_FILE" "$@"; }

wait_healthy() {
  local i status
  for i in $(seq 1 30); do
    status="$(docker inspect "$CONTAINER" --format '{{.State.Health.Status}}' 2>/dev/null || echo absent)"
    [[ "$status" == "healthy" ]] && { echo "healthy"; return 0; }
    [[ "$status" == "absent" ]] && { echo "container absent"; return 1; }
    sleep 2
  done
  echo "timeout (dernier etat: ${status:-?})"; return 1
}

cmd="${1:-status}"
case "$cmd" in
  rebuild)
    echo "[dashboard] rebuild image + recreate (la base SQLite est preservee)"
    dc build "$SERVICE"
    dc up -d "$SERVICE"
    echo -n "[dashboard] sante: "; wait_healthy
    ;;
  start)
    echo "[dashboard] start"
    dc up -d "$SERVICE"
    echo -n "[dashboard] sante: "; wait_healthy
    ;;
  stop)
    echo "[dashboard] stop"
    dc stop "$SERVICE"
    ;;
  restart)
    echo "[dashboard] restart (sans rebuild)"
    dc restart "$SERVICE"
    echo -n "[dashboard] sante: "; wait_healthy
    ;;
  status)
    docker ps --filter "name=$CONTAINER" --format '  {{.Names}}  {{.Status}}  {{.Ports}}' || true
    echo -n "  health: "; docker inspect "$CONTAINER" --format '{{.State.Health.Status}}' 2>/dev/null || echo "absent"
    ;;
  logs)
    dc logs -f --tail=100 "$SERVICE"
    ;;
  *)
    echo "Usage: scripts/dashboard.sh {rebuild|start|stop|restart|status|logs}" >&2
    exit 2
    ;;
esac
