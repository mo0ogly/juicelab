<#
.SYNOPSIS
    JuiceLab - installateur eleve / smoke test enseignant (Windows / PowerShell 7+).

.DESCRIPTION
    Equivalent PowerShell de scripts/install-student.sh. Idempotent : preserve
    les tokens deja valides dans docker/.env. Necessite Docker Desktop (avec
    docker compose v2 integre) et OpenSSL (livre avec Git for Windows ou
    installable via winget install ShiningLight.OpenSSL).

.PARAMETER Cohort
    Identifiant de cohorte (ex M2-IA-2026). Si absent et docker/.env n'a pas
    deja JUICELAB_COHORT_ID, est demande interactivement.

.PARAMETER Yes
    Mode non interactif : accepte tous les defauts (cohort = M2-IA-2026).

.PARAMETER Reset
    docker compose down -v + suppression de docker/.env avant reinstall.

.EXAMPLE
    .\scripts\install-student.ps1 -Cohort M2-IA-2026

.EXAMPLE
    .\scripts\install-student.ps1 -Yes

.EXAMPLE
    .\scripts\install-student.ps1 -Reset
#>

[CmdletBinding()]
param(
    [Alias('c')] [string]$Cohort = '',
    [Alias('y')] [switch]$Yes,
    [switch]$Reset
)

$ErrorActionPreference = 'Stop'

$JuicelabRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$DockerDir    = Join-Path $JuicelabRoot 'docker'
$EnvFile      = Join-Path $DockerDir '.env'
$EnvExample   = Join-Path $DockerDir '.env.example'

function Say  ($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok   ($msg) { Write-Host "OK  $msg" -ForegroundColor Green }
function Warn ($msg) { Write-Host "!!! $msg" -ForegroundColor Yellow }
function Die  ($msg) { Write-Host "!!! $msg" -ForegroundColor Red; exit 1 }

function Need-Cmd ($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Die "Outil manquant : $name. Installe-le avant de relancer."
    }
}

function Get-EnvValue ($key) {
    if (-not (Test-Path $EnvFile)) { return '' }
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match "^\s*$([regex]::Escape($key))=(.*)$") {
            return $Matches[1]
        }
    }
    return ''
}

function Set-EnvValue ($key, $value) {
    if (-not (Test-Path $EnvFile)) {
        Set-Content -LiteralPath $EnvFile -Value ("{0}={1}" -f $key, $value) -Encoding UTF8
        return
    }
    $lines = Get-Content $EnvFile
    $found = $false
    $out = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($key))=") {
            $found = $true
            "{0}={1}" -f $key, $value
        } else {
            $line
        }
    }
    if (-not $found) { $out += ("{0}={1}" -f $key, $value) }
    Set-Content -LiteralPath $EnvFile -Value $out -Encoding UTF8
}

function New-Token {
    # 32 chars hex, equivalent openssl rand -hex 16. Fallback si openssl absent.
    if (Get-Command openssl -ErrorAction SilentlyContinue) {
        return (& openssl rand -hex 16).Trim()
    }
    $bytes = New-Object byte[] 16
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return -join ($bytes | ForEach-Object { '{0:x2}' -f $_ })
}

function Test-Token ($value) {
    return ($value -and $value -notmatch '^replace-me-with' -and $value.Length -ge 16)
}

function Prompt-Default ($question, $default) {
    if ($Yes) { return $default }
    if ($default) {
        $reply = Read-Host -Prompt "$question [$default]"
        if ([string]::IsNullOrWhiteSpace($reply)) { return $default }
        return $reply
    }
    return (Read-Host -Prompt $question)
}

function Get-DockerCompose {
    try {
        & docker compose version *> $null
        if ($LASTEXITCODE -eq 0) { return @('docker','compose') }
    } catch { }
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        return @('docker-compose')
    }
    Die 'docker compose v2 (ou docker-compose v1) introuvable.'
}

function Wait-Http ($url, $name, $timeoutSec = 120) {
    $elapsed = 0
    while ($elapsed -lt $timeoutSec) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                Ok "$name : $url"
                return $true
            }
        } catch { }
        Start-Sleep -Seconds 3
        $elapsed += 3
    }
    Warn "$name pas encore pret apres ${timeoutSec}s : $url"
    return $false
}

# ---- Step 0 : prereqs ------------------------------------------------------

Say 'Verification des prerequis'
Need-Cmd docker
$DC = Get-DockerCompose
Ok ("docker, {0} disponibles" -f ($DC -join ' '))

if (-not (Test-Path $DockerDir))   { Die "Dossier docker/ introuvable : $DockerDir" }
if (-not (Test-Path $EnvExample))  { Die ".env.example introuvable : $EnvExample" }

# ---- Step 1 : reset --------------------------------------------------------

if ($Reset) {
    Say '--reset : docker compose down -v (efface les volumes)'
    Push-Location $DockerDir
    try {
        & $DC[0] $DC[1..($DC.Length - 1)] '--env-file' '.env' 'down' '-v' 2>$null
    } catch { }
    Pop-Location
    if (Test-Path $EnvFile) { Remove-Item $EnvFile -Force }
    Ok 'Etat precedent supprime'
}

# ---- Step 2 : .env ---------------------------------------------------------

if (-not (Test-Path $EnvFile)) {
    Say 'Creation de docker/.env a partir de .env.example'
    Copy-Item $EnvExample $EnvFile
}

$currentTeacher   = Get-EnvValue 'TEACHER_ADMIN_TOKEN'
$currentDashboard = Get-EnvValue 'DASHBOARD_TEACHER_TOKEN'
$currentCohort    = Get-EnvValue 'JUICELAB_COHORT_ID'

if (Test-Token $currentTeacher) {
    Ok 'TEACHER_ADMIN_TOKEN deja configure (preserve)'
} else {
    Set-EnvValue 'TEACHER_ADMIN_TOKEN' (New-Token)
    Ok 'TEACHER_ADMIN_TOKEN genere'
}

if (Test-Token $currentDashboard) {
    Ok 'DASHBOARD_TEACHER_TOKEN deja configure (preserve)'
} else {
    Set-EnvValue 'DASHBOARD_TEACHER_TOKEN' (New-Token)
    Ok 'DASHBOARD_TEACHER_TOKEN genere'
}

if (-not $Cohort) {
    if ($currentCohort -and $currentCohort -notmatch '^replace-me-with') {
        $Cohort = $currentCohort
        Ok "JUICELAB_COHORT_ID deja configure : $Cohort"
    } else {
        $Cohort = Prompt-Default 'Identifiant de cohorte (ex M2-IA-2026)' 'M2-IA-2026'
    }
}
Set-EnvValue 'JUICELAB_COHORT_ID' $Cohort
Ok "JUICELAB_COHORT_ID = $Cohort"

# ---- Step 3 : build + up ---------------------------------------------------

Say 'docker compose up -d --build (premier build : 5-8 min, builds suivants : 10s)'
Push-Location $DockerDir
try {
    $dcArgs = @($DC[1..($DC.Length - 1)]) + @('--env-file','.env','up','-d','--build')
    & $DC[0] @dcArgs
    if ($LASTEXITCODE -ne 0) { Die "docker compose a echoue (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}
Ok 'Conteneurs lances'

# ---- Step 4 : health checks ------------------------------------------------

Say 'Attente des endpoints (timeout 120s par endpoint)'

$dashboardPort = Get-EnvValue 'DASHBOARD_PORT'
if (-not $dashboardPort) { $dashboardPort = '5000' }

[void] (Wait-Http 'http://127.0.0.1:3000/'                              'Juice Shop')
[void] (Wait-Http "http://127.0.0.1:$dashboardPort/api/health"          'Dashboard /api/health')

# ---- Step 5 : recap --------------------------------------------------------

$dcStr = $DC -join ' '
Write-Host ''
Write-Host '========================================================================'
Write-Host 'Installation OK' -ForegroundColor Green
Write-Host ''
Write-Host "  Eleve  -> http://127.0.0.1:3000/#/juicelab           (parcours TD)"
Write-Host "  Eleve  -> http://127.0.0.1:3000/#/score-board        (challenges OWASP)"
Write-Host "  Prof   -> http://127.0.0.1:$dashboardPort/login            (token ci-dessous)"
Write-Host "  Prof   -> http://127.0.0.1:$dashboardPort/dashboard?cohort=$Cohort"
Write-Host ''
Write-Host ("  DASHBOARD_TEACHER_TOKEN = {0}" -f (Get-EnvValue 'DASHBOARD_TEACHER_TOKEN'))
Write-Host ("  TEACHER_ADMIN_TOKEN     = {0}" -f (Get-EnvValue 'TEACHER_ADMIN_TOKEN'))
Write-Host ''
Write-Host "  Stop  : cd docker; $dcStr --env-file .env down"
Write-Host "  Wipe  : cd docker; $dcStr --env-file .env down -v"
Write-Host "  Logs  : cd docker; $dcStr --env-file .env logs -f"
Write-Host '========================================================================'
