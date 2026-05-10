# Apply the JuiceLab overlay on top of a vanilla OWASP Juice Shop clone.
#
# Usage :
#   .\scripts\apply-overlay.ps1 [-JuiceShopDir <path>]
#
# Defaults to ..\juice-shop relative to this repo if -JuiceShopDir is omitted.
#
# Idempotent : re-running copies the same files again (overlay paths are owned
# by JuiceLab) and re-applies the patch with --3way for safe re-application.
#
# Requires : PowerShell 7+, git in PATH.

param(
    [string]$JuiceShopDir = ""
)

$ErrorActionPreference = "Stop"

$JuicelabRoot = (Get-Item $PSScriptRoot).Parent.FullName
if (-not $JuiceShopDir) {
    $JuiceShopDir = Join-Path (Split-Path $JuicelabRoot -Parent) "juice-shop"
}
$OverlayDir = Join-Path $JuicelabRoot "overlay"
$PatchesDir = Join-Path $JuicelabRoot "patches"
$CorePatch = Join-Path $PatchesDir "juicelab-core.patch"

function Say($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "!!! $msg" -ForegroundColor Yellow }
function Die($msg) { Write-Host "!!! $msg" -ForegroundColor Red; exit 1 }

# ---- Sanity checks --------------------------------------------------------

if (-not (Test-Path $JuiceShopDir)) { Die "Juice Shop directory not found at $JuiceShopDir" }
if (-not (Test-Path (Join-Path $JuiceShopDir "package.json"))) { Die "$JuiceShopDir does not look like a Juice Shop clone (no package.json)" }
if (-not (Test-Path (Join-Path $JuiceShopDir "server.ts"))) { Die "$JuiceShopDir does not look like a Juice Shop clone (no server.ts)" }
if (-not (Test-Path $OverlayDir)) { Die "Overlay directory missing : $OverlayDir" }
if (-not (Test-Path $CorePatch)) { Die "Patch missing : $CorePatch" }

Say "Juice Shop target : $JuiceShopDir"
Say "Overlay source    : $OverlayDir"

# ---- Step 1 : copy overlay files ------------------------------------------

Say "Step 1/3 — copying new files from overlay\ into the Juice Shop tree"
Get-ChildItem -Path $OverlayDir -Force | ForEach-Object {
    $src = $_.FullName
    $dest = Join-Path $JuiceShopDir $_.Name
    Copy-Item -Path $src -Destination $dest -Recurse -Force
}

# ---- Step 2 : apply the core patch ----------------------------------------

Say "Step 2/3 — applying patches\juicelab-core.patch on the Juice Shop tree"
Push-Location $JuiceShopDir
try {
    & git apply --check --3way "$CorePatch" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & git apply --3way "$CorePatch"
        if ($LASTEXITCODE -ne 0) { Die "git apply failed unexpectedly after --check passed" }
        Say "Patch applied cleanly"
    } else {
        Warn "git apply --check reported conflicts, trying with --reject"
        & git apply --3way --reject "$CorePatch"
        if ($LASTEXITCODE -ne 0) {
            Die "Patch could not be applied even with --reject. Inspect *.rej files in $JuiceShopDir."
        }
        Warn "Patch partially applied with .rej files. Review them then commit your resolution."
    }
} finally {
    Pop-Location
}

# ---- Step 3 : sanity check the result -------------------------------------

Say "Step 3/3 — checking that the JuiceLab anchors are present"
$errors = 0
$anchors = @(
    "routes/juicelab.ts",
    "data/juicelab-private/hints",
    "frontend/src/app/juicelab-overlay/services/juicelab-sync.service.ts",
    "frontend/src/assets/juicelab/selected_challenges.yml"
)
foreach ($anchor in $anchors) {
    if (-not (Test-Path (Join-Path $JuiceShopDir $anchor))) {
        Warn "missing : $anchor"
        $errors++
    }
}

$serverTs = Get-Content (Join-Path $JuiceShopDir "server.ts") -Raw
if (-not ($serverTs -match "from './routes/juicelab'")) {
    Warn "server.ts does not import ./routes/juicelab — the patch may have failed"
    $errors++
}

if ($errors -gt 0) {
    Die "$errors anchor(s) missing. Re-run with a clean Juice Shop clone."
}

Say "Overlay applied successfully."
Say ""
Say "Next steps :"
Say "  cd $JuiceShopDir"
Say "  npm install"
Say "  npm start"
Say ""
Say "or, for a full Docker deployment :"
Say "  cd $JuicelabRoot\docker"
Say "  Copy-Item .env.example .env ; notepad .env"
Say "  docker compose --env-file .env up -d --build"
