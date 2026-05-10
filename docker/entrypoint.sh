#!/bin/sh
# JuiceLab Juice Shop entrypoint.
#
# Rewrites /juice-shop/frontend/dist/frontend/assets/juicelab/config.json
# from environment variables so the same container image can be deployed
# with different (dashboard_url, cohort_id, instance_label) per replica.
#
# Falls back to the values baked at build time if env vars are unset.

set -eu

CONFIG_FILE="/juice-shop/frontend/dist/frontend/assets/juicelab/config.json"

if [ -f "$CONFIG_FILE" ]; then
    DASHBOARD_URL="${JUICELAB_DASHBOARD_URL:-$(grep -oE '"dashboard_url"\s*:\s*"[^"]*"' "$CONFIG_FILE" | sed -E 's/.*"([^"]*)"$/\1/')}"
    COHORT_ID="${JUICELAB_COHORT_ID:-$(grep -oE '"cohort_id"\s*:\s*"[^"]*"' "$CONFIG_FILE" | sed -E 's/.*"([^"]*)"$/\1/')}"
    INSTANCE_LABEL="${JUICELAB_INSTANCE_LABEL:-$(grep -oE '"instance_label"\s*:\s*"[^"]*"' "$CONFIG_FILE" | sed -E 's/.*"([^"]*)"$/\1/')}"
    DEFAULT_LANG="${JUICELAB_DEFAULT_LANGUAGE:-fr}"

    cat > "$CONFIG_FILE" <<JSON
{
  "dashboard_url": "${DASHBOARD_URL}",
  "cohort_id": "${COHORT_ID}",
  "instance_label": "${INSTANCE_LABEL}",
  "default_language": "${DEFAULT_LANG}"
}
JSON
    echo "[juicelab] config.json rewritten: dashboard=${DASHBOARD_URL} cohort=${COHORT_ID} instance=${INSTANCE_LABEL} lang=${DEFAULT_LANG}"
else
    echo "[juicelab] WARNING: $CONFIG_FILE missing — frontend will use defaults"
fi

exec "$@"
