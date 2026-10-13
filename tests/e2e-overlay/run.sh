#!/usr/bin/env bash
# Overlay e2e guard : every TD challenge solved in Juice Shop must reach the
# teacher dashboard as a `challenge_solved` event, even when the student never
# opened /#/juicelab first, and even when the solve happened over plain HTTP
# (curl / Burp) while no browser tab was open.
#
# Each scenario runs against a fresh container of the JuiceLab image, with the
# overlay pointed at a local mock dashboard (mock_dashboard.py) that records
# what the browser actually sends.
#
# Usage :
#   cd tests/e2e-overlay && npm install
#   ./run.sh [IMAGE]            # default image : juicelab:latest
#
# Env : SHOP_PORT (3998), MOCK_PORT (5998), CHROME_BIN, E2E_TIMEOUT_MS
# Requires : docker, python3, node >= 18, a local Chrome/Chromium.

set -euo pipefail

IMAGE="${1:-juicelab:latest}"
SHOP_PORT="${SHOP_PORT:-3998}"
MOCK_PORT="${MOCK_PORT:-5998}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
CONTAINER="juicelab-e2e-overlay-$$"
MOCK_PID=""

cleanup() {
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    [ -n "$MOCK_PID" ] && kill "$MOCK_PID" 2>/dev/null || true
    rm -rf "$WORK"
}
trap cleanup EXIT

[ -d "$HERE/node_modules/puppeteer-core" ] || { echo "run 'npm install' in $HERE first" >&2; exit 2; }

start_stack() {
    local events="$1"
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    [ -n "$MOCK_PID" ] && kill "$MOCK_PID" 2>/dev/null || true
    : > "$events"
    python3 "$HERE/mock_dashboard.py" "$MOCK_PORT" "$events" &
    MOCK_PID=$!
    docker run -d --name "$CONTAINER" -p "127.0.0.1:${SHOP_PORT}:3000" \
        -e JUICELAB_DASHBOARD_URL="http://127.0.0.1:${MOCK_PORT}" \
        -e JUICELAB_COHORT_ID=E2E-OVERLAY \
        -e JUICELAB_INSTANCE_LABEL=e2e \
        "$IMAGE" >/dev/null
    for _ in $(seq 1 90); do
        curl -sf -o /dev/null "http://127.0.0.1:${SHOP_PORT}/rest/admin/application-version" && return 0
        sleep 1
    done
    echo "Juice Shop did not come up on port ${SHOP_PORT}" >&2
    docker logs --tail 40 "$CONTAINER" >&2
    exit 2
}

FAILED=0
run_scenario() {
    local name="$1" events="$WORK/$1.jsonl"
    start_stack "$events"
    if [ "$name" = "solved-offline" ] || [ "$name" = "notification-consumed" ]; then
        # Solve a TD challenge server-side before any browser connects.
        curl -sf -o /dev/null "http://127.0.0.1:${SHOP_PORT}/ftp/acquisitions.md"
    fi
    node "$HERE/solve-sync.mjs" "$name" "http://127.0.0.1:${SHOP_PORT}" "$events" || FAILED=1
}

run_scenario juicelab-first
run_scenario score-board-direct
run_scenario solved-offline
run_scenario notification-consumed

exit "$FAILED"
