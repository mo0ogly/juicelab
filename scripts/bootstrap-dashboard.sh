#!/usr/bin/env bash
#
# bootstrap-dashboard.sh - deploie la SEULE partie prof (dashboard Flask) sur
# une machine vierge, sans cloner le code eleve juice.
#
# Tire UNIQUEMENT dashboard/ + docker/ via git sparse-checkout a une ref
# pinnee, puis lance docker-compose.dashboard.yml. Jamais overlay/, juice-shop/,
# scripts d'install eleve.
#
# Usage :
#   scripts/bootstrap-dashboard.sh [TARGET_DIR]
#
# Variables d'env :
#   JUICELAB_REPO_URL      defaut https://github.com/mo0ogly/juicelab.git
#   JUICELAB_DASHBOARD_REF branche ou SHA a deployer (defaut: main ; PIN conseille)
#   DASHBOARD_ENV_FILE     chemin du .env a utiliser (defaut: <TARGET>/docker/.env)
#
set -euo pipefail

REPO_URL="${JUICELAB_REPO_URL:-https://github.com/mo0ogly/juicelab.git}"
REF="${JUICELAB_DASHBOARD_REF:-main}"
TARGET="${1:-${JUICELAB_DASHBOARD_DIR:-./juicelab-dashboard}}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERREUR: docker absent." >&2; exit 1
fi

# 1. Sparse clone (cone) ou reutilisation d'un clone existant.
#    Set = dashboard docker scripts. `scripts` est inclus pour que ce bootstrap
#    ne se supprime pas lui-meme du working tree (narrowing) et pour qu'un
#    wrapper externe (PwnzzAI) puisse le reutiliser. scripts/ ne contient aucun
#    code PRODUIT eleve (overlay/juice-shop) : juste des bootstrappers.
if [ ! -d "$TARGET/.git" ]; then
  echo "[bootstrap] sparse clone $REPO_URL -> $TARGET (dashboard/ + docker/ + scripts/)"
  git clone --filter=blob:none --sparse "$REPO_URL" "$TARGET"
  git -C "$TARGET" sparse-checkout set dashboard docker scripts
else
  echo "[bootstrap] clone existant detecte dans $TARGET"
  git -C "$TARGET" sparse-checkout set dashboard docker scripts
  git -C "$TARGET" fetch --filter=blob:none origin
fi

# 2. Checkout de la ref pinnee.
echo "[bootstrap] checkout ref: $REF"
git -C "$TARGET" checkout -q "$REF"
echo "[bootstrap] HEAD: $(git -C "$TARGET" rev-parse --short HEAD)"

# 3. Garde-fou : on ne doit avoir tire QUE dashboard/ + docker/.
extra="$(git -C "$TARGET" ls-tree --name-only HEAD | grep -Ev '^(dashboard|docker)$' || true)"
checked_out="$(cd "$TARGET" && ls -A | grep -Ev '^\.git$' | sort | tr '\n' ' ')"
echo "[bootstrap] presents sur le disque: $checked_out"

# 4. .env.
ENV_FILE="${DASHBOARD_ENV_FILE:-$TARGET/docker/.env}"
if [ ! -f "$ENV_FILE" ]; then
  cp "$TARGET/docker/.env.example" "$ENV_FILE"
  echo "[bootstrap] $ENV_FILE cree depuis .env.example."
  echo "[bootstrap] RENSEIGNE les secrets (DASHBOARD_TEACHER_TOKEN >= 16,"
  echo "[bootstrap] DASHBOARD_PROOF_SECRET >= 16) puis relance ce script."
  exit 1
fi

# 5. Up.
echo "[bootstrap] docker compose up (dashboard-only)"
( cd "$TARGET/docker" && docker compose --env-file "$ENV_FILE" \
    -f docker-compose.dashboard.yml up -d --build )
echo "[bootstrap] dashboard lance. Sante: docker inspect juicelab-dashboard --format '{{.State.Health.Status}}'"
