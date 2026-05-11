#!/usr/bin/env bash
# Regenerate dashboard/LICENSES.md from the current lockfile.
# Run after every requirements.lock.txt change : `bash scripts/gen_licenses.sh`.
# CI also runs this and fails if the committed file is stale.
set -eu

cd "$(dirname "$0")/.."

LOCKFILE=dashboard/requirements.lock.txt
OUT=dashboard/LICENSES.md

if [ ! -f "$LOCKFILE" ]; then
  echo "ERROR: $LOCKFILE not found" >&2
  exit 1
fi

PIPLIC=$(command -v pip-licenses 2>/dev/null || ls "$HOME/.local/bin/pip-licenses" 2>/dev/null)
if [ -z "$PIPLIC" ]; then
  echo "ERROR: pip-licenses missing (pip install --user pip-licenses)" >&2
  exit 1
fi

pkgs=$(grep -oE '^[a-zA-Z][a-zA-Z0-9_.-]*' "$LOCKFILE" | sort -u | tr '\n' ' ')

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
"$PIPLIC" --packages $pkgs --format=json --no-version > "$TMP" 2>/dev/null

python3 - "$TMP" "$OUT" <<'PY'
import json, sys
in_path, out_path = sys.argv[1], sys.argv[2]
with open(in_path) as f:
    data = json.load(f)
# Dedup by lowercase package name (Python 3.11 vs 3.13 wheels appear twice).
seen = {}
for p in data:
    seen.setdefault(p["Name"].lower(), p)

lines = [
    "# Dashboard Third-Party Licenses",
    "",
    "Auto-generated from `dashboard/requirements.lock.txt` via `pip-licenses`.",
    "Regenerate with: `bash scripts/gen_licenses.sh`.",
    "",
    f"Total components : {len(seen)}",
    "",
    "| Component | License |",
    "|---|---|",
]
for k in sorted(seen):
    p = seen[k]
    lines.append(f"| {p['Name']} | {p['License']} |")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"wrote {out_path} : {len(seen)} components", file=sys.stderr)
PY
