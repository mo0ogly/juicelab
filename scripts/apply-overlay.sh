#!/usr/bin/env bash
# Apply the JuiceLab overlay on top of a vanilla OWASP Juice Shop clone.
#
# Usage:
#   ./scripts/apply-overlay.sh [path-to-juice-shop]
#
# If no path is given, defaults to ../juice-shop relative to this repo.
#
# Idempotent : re-running this script copies the same files again (overwriting
# any local edits to the overlay paths — those files are owned by JuiceLab)
# and re-applies the patches with --3way for safe conflict-aware re-application.
#
# Requires : bash 4+, rsync (or cp -r as fallback), git.

set -euo pipefail

JUICELAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JUICESHOP_DEFAULT="${JUICELAB_ROOT}/../juice-shop"
JUICESHOP_DIR="${1:-${JUICESHOP_DEFAULT}}"

OVERLAY_DIR="${JUICELAB_ROOT}/overlay"
PATCHES_DIR="${JUICELAB_ROOT}/patches"

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!!\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m!!!\033[0m %s\n' "$*" >&2; exit 1; }

# ---- Sanity checks --------------------------------------------------------

[[ -d "${JUICESHOP_DIR}" ]] || die "Juice Shop directory not found at ${JUICESHOP_DIR}"
[[ -f "${JUICESHOP_DIR}/package.json" ]] || die "${JUICESHOP_DIR} does not look like a Juice Shop clone (no package.json)"
[[ -f "${JUICESHOP_DIR}/server.ts" ]] || die "${JUICESHOP_DIR} does not look like a Juice Shop clone (no server.ts)"
[[ -d "${OVERLAY_DIR}" ]] || die "Overlay directory missing : ${OVERLAY_DIR}"
[[ -f "${PATCHES_DIR}/juicelab-core.patch" ]] || die "Patch missing : ${PATCHES_DIR}/juicelab-core.patch"

say "Juice Shop target : ${JUICESHOP_DIR}"
say "Overlay source    : ${OVERLAY_DIR}"

# ---- Step 1 : copy overlay files ------------------------------------------

say "Step 1/3 — copying new files from overlay/ into the Juice Shop tree"
if command -v rsync >/dev/null 2>&1; then
    rsync -a --no-perms "${OVERLAY_DIR}/" "${JUICESHOP_DIR}/"
else
    warn "rsync not found, falling back to cp -r"
    (cd "${OVERLAY_DIR}" && find . -mindepth 1 -maxdepth 1 -exec cp -r {} "${JUICESHOP_DIR}/" \;)
fi

# ---- Step 2 : apply the core patch ----------------------------------------

say "Step 2/3 — applying patches/juicelab-core.patch on the Juice Shop tree"
cd "${JUICESHOP_DIR}"

# Check first (does not modify anything) — surfaces conflicts before we touch
# the working tree. --3way lets git use the ancestor blob when the patch
# target has drifted (common after an upstream rebase).
if git apply --check --3way "${PATCHES_DIR}/juicelab-core.patch" 2>/dev/null; then
    git apply --3way "${PATCHES_DIR}/juicelab-core.patch"
    say "Patch applied cleanly"
else
    warn "git apply --check reported conflicts. Trying again with the conflict"
    warn "markers left in place so you can resolve manually."
    if ! git apply --3way --reject "${PATCHES_DIR}/juicelab-core.patch"; then
        die "Patch could not be applied even with --reject. Inspect *.rej files in ${JUICESHOP_DIR}."
    fi
    warn "Patch partially applied with .rej files. Review them then commit your resolution."
fi

# ---- Step 3 : sanity check the result -------------------------------------

say "Step 3/3 — checking that the JuiceLab anchors are present"
errors=0
for anchor in \
    "routes/juicelab.ts" \
    "data/juicelab-private/hints" \
    "frontend/src/app/juicelab-overlay/services/juicelab-sync.service.ts" \
    "frontend/src/assets/juicelab/selected_challenges.yml" ; do
    if [[ ! -e "${JUICESHOP_DIR}/${anchor}" ]]; then
        warn "missing : ${anchor}"
        errors=$((errors + 1))
    fi
done

# server.ts must now reference the juicelab routes
if ! grep -q "from './routes/juicelab'" "${JUICESHOP_DIR}/server.ts" 2>/dev/null; then
    warn "server.ts does not import ./routes/juicelab — the patch may have failed"
    errors=$((errors + 1))
fi

if [[ ${errors} -gt 0 ]]; then
    die "${errors} anchor(s) missing. Re-run with a clean Juice Shop clone."
fi

say "Overlay applied successfully."
say ""
say "Next steps :"
say "  cd ${JUICESHOP_DIR}"
say "  npm install"
say "  npm start"
say ""
say "or, for a full Docker deployment :"
say "  cd ${JUICELAB_ROOT}/docker"
say "  cp .env.example .env && \$EDITOR .env"
say "  docker compose --env-file .env up -d --build"
