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

.PARAMETER Dashboard
    Scenario 4 (eleve) : IP/host du dashboard du prof. Lance UNIQUEMENT
    juice-shop, configure pour pousser ses events vers ce dashboard.

.PARAMETER Label
    Scenario 4 (eleve) : nom unique de l'instance dans la matrice prof
    (defaut : nom d'utilisateur Windows).

.PARAMETER Server
    Scenario 4 (prof) : lance UNIQUEMENT le dashboard, joignable sur le LAN,
    et affiche l'IP a distribuer aux eleves.

.EXAMPLE
    .\scripts\install-student.ps1 -Cohort M2-IA-2026

.EXAMPLE
    # Scenario 4 cote eleve : pointe vers le dashboard du prof
    .\scripts\install-student.ps1 -Dashboard 192.168.1.10 -Label amelie -Cohort M2-IA-2026

.EXAMPLE
    # Scenario 4 cote prof : dashboard seul, joignable sur le LAN
    .\scripts\install-student.ps1 -Server -Cohort M2-IA-2026

.EXAMPLE
    .\scripts\install-student.ps1 -Reset
#>

[CmdletBinding()]
param(
    [Alias('c')] [string]$Cohort = '',
    [Alias('d')] [string]$Dashboard = '',
    [Alias('l')] [string]$Label = '',
    [switch]$Server,
    [Alias('y')] [switch]$Yes,
    [switch]$Reset
)

if ($Dashboard -and $Server) {
    Write-Host '!!! -Dashboard (eleve) et -Server (prof) sont exclusifs.' -ForegroundColor Red
    exit 2
}

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

# Secret de signature des preuves (mode solo : active /api/proof et le diplome).
$currentProof = Get-EnvValue 'DASHBOARD_PROOF_SECRET'
if (Test-Token $currentProof) {
    Ok 'DASHBOARD_PROOF_SECRET deja configure (preserve)'
} else {
    Set-EnvValue 'DASHBOARD_PROOF_SECRET' (New-Token)
    Ok 'DASHBOARD_PROOF_SECRET genere'
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

# ---- Step 2b : cablage scenario 4 (eleve distant) --------------------------

if ($Dashboard) {
    # Accepte HOST ou HOST:PORT. Si le prof expose 5000 au lieu du defaut
    # 5050, l'eleve passe -Dashboard IP:5000 et l'URL bakee suit.
    if ($Dashboard -match ':') {
        $parts = $Dashboard -split ':', 2
        $Dashboard = $parts[0]
        Set-EnvValue 'DASHBOARD_PORT' $parts[1]
    }
    Set-EnvValue 'DASHBOARD_PUBLIC_HOST' $Dashboard
    Ok "DASHBOARD_PUBLIC_HOST = $Dashboard (events pousses vers le dashboard prof)"

    if (-not $Label) {
        $Label = if ($env:USERNAME) { $env:USERNAME } else { 'eleve' }
    }
    Set-EnvValue 'JUICELAB_INSTANCE_LABEL' $Label
    Ok "JUICELAB_INSTANCE_LABEL = $Label"
} elseif ($Label) {
    Set-EnvValue 'JUICELAB_INSTANCE_LABEL' $Label
    Ok "JUICELAB_INSTANCE_LABEL = $Label"
}

function Get-PortPid ($port) {
    try {
        return @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                 Select-Object -ExpandProperty OwningProcess -Unique)
    } catch { return @() }
}

# Libere un port hote en stoppant les process qui l'ecoutent (TERM force).
function Free-Port ($port) {
    $procs = Get-PortPid $port
    if (-not $procs) { return }
    foreach ($procId in $procs) {
        if ($procId -eq 0) { continue }
        Warn "Port $port occupe (PID $procId) - arret force"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    if (Get-PortPid $port) { Die "Port $port toujours occupe. Le liberer manuellement puis relancer." }
    Ok "Port $port libere"
}

# ---- Step 3 : build + up ---------------------------------------------------

# Selection des services selon le mode :
#   -Server          -> dashboard seul (prof, scenario 4)
#   -Dashboard HOST  -> juicelab-demo seul (eleve, scenario 4)
#   (defaut)         -> dashboard + juicelab-demo (solo local)
if ($Server) {
    $Services = @('dashboard')
    Say 'Mode prof (-Server) : build + lancement du dashboard seul'
} elseif ($Dashboard) {
    $Services = @('juicelab-demo')
    Say "Mode eleve (-Dashboard $Dashboard) : build + lancement de juice-shop seul"
} else {
    $Services = @('dashboard','juicelab-demo')
    Say 'Mode solo local : build + lancement dashboard + juice-shop'
}

# Ports hote a binder selon le mode (defaut .env : dashboard 5050, demo 3000).
$dashPort = Get-EnvValue 'DASHBOARD_PORT'; if (-not $dashPort) { $dashPort = '5050' }
$demoPort = Get-EnvValue 'JUICELAB_DEMO_PORT'; if (-not $demoPort) { $demoPort = '3000' }

# Retire d'abord nos propres conteneurs/reseau stale (idempotent, garde les volumes).
Push-Location $DockerDir
try { & $DC[0] @($DC[1..($DC.Length - 1)]) '--env-file' '.env' 'down' 2>$null } catch { } finally { Pop-Location }

# Libere les ports que ce mode va utiliser.
if ($Server) { Free-Port $dashPort }
elseif ($Dashboard) { Free-Port $demoPort }
else { Free-Port $dashPort; Free-Port $demoPort }

Push-Location $DockerDir
try {
    $dcArgs = @($DC[1..($DC.Length - 1)]) + @('--env-file','.env','up','-d','--build') + $Services
    & $DC[0] @dcArgs
    if ($LASTEXITCODE -ne 0) { Die "docker compose a echoue (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}
Ok 'Conteneurs lances'

# ---- Step 4 : health checks ------------------------------------------------

Say 'Attente des endpoints (timeout 120s par endpoint)'

$dashboardPort = Get-EnvValue 'DASHBOARD_PORT'
if (-not $dashboardPort) { $dashboardPort = '5050' }

if ($Server) {
    [void] (Wait-Http "http://127.0.0.1:$dashboardPort/api/health" 'Dashboard /api/health')
} elseif ($Dashboard) {
    [void] (Wait-Http 'http://127.0.0.1:3000/' 'Juice Shop')
    try {
        $r = Invoke-WebRequest -Uri "http://${Dashboard}:$dashboardPort/api/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
            Ok "Dashboard prof joignable : http://${Dashboard}:$dashboardPort/api/health"
        }
    } catch {
        Warn "Dashboard prof http://${Dashboard}:$dashboardPort injoignable depuis ici."
        Warn "Verifier que le prof a lance -Server, le LAN plat, et le firewall (port $dashboardPort)."
    }
} else {
    [void] (Wait-Http 'http://127.0.0.1:3000/'                     'Juice Shop')
    [void] (Wait-Http "http://127.0.0.1:$dashboardPort/api/health" 'Dashboard /api/health')
}

# ---- Step 5 : recap --------------------------------------------------------

$dcStr = $DC -join ' '
Write-Host ''
Write-Host '========================================================================'
Write-Host 'Installation OK' -ForegroundColor Green
Write-Host ''

if ($Server) {
    $lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
        Select-Object -First 1).IPAddress
    if (-not $lanIp) { $lanIp = '<ip-de-cette-machine>' }
    Write-Host '  Mode prof (-Server) : dashboard de consolidation lance.'
    Write-Host ''
    Write-Host "  Prof   -> http://127.0.0.1:$dashboardPort/login            (token ci-dessous)"
    Write-Host "  Prof   -> http://127.0.0.1:$dashboardPort/dashboard?cohort=$Cohort"
    Write-Host ''
    Write-Host '  A DISTRIBUER AUX ELEVES (scenario 4) :'
    Write-Host "    Cohorte   : $Cohort"
    Write-Host "    Dashboard : $lanIp     (commande eleve : .\scripts\install-student.ps1 -Dashboard $lanIp -Cohort $Cohort -Label <prenom>)"
    Write-Host ''
    Write-Host '  CORS : verifier que DASHBOARD_CORS_ORIGINS autorise l''origine des eleves.'
    Write-Host '         Si tous les eleves ouvrent http://127.0.0.1:3000, valeur actuelle OK :'
    Write-Host ("         {0}" -f (Get-EnvValue 'DASHBOARD_CORS_ORIGINS'))
    Write-Host ''
    Write-Host ("  DASHBOARD_TEACHER_TOKEN = {0}" -f (Get-EnvValue 'DASHBOARD_TEACHER_TOKEN'))
} elseif ($Dashboard) {
    Write-Host '  Mode eleve (scenario 4) : juice-shop lance, events pousses vers le prof.'
    Write-Host ''
    Write-Host "  Eleve  -> http://127.0.0.1:3000/#/juicelab           (parcours TD)"
    Write-Host "  Eleve  -> http://127.0.0.1:3000/#/score-board        (challenges OWASP)"
    Write-Host ''
    Write-Host "  Cohorte           : $Cohort"
    Write-Host ("  Instance (label)  : {0}" -f (Get-EnvValue 'JUICELAB_INSTANCE_LABEL'))
    Write-Host "  Dashboard prof    : http://${Dashboard}:$dashboardPort"
} else {
    Write-Host '  Mode solo local : dashboard + juice-shop sur cette machine.'
    Write-Host ''
    Write-Host "  Eleve  -> http://127.0.0.1:3000/#/juicelab           (parcours TD)"
    Write-Host "  Eleve  -> http://127.0.0.1:3000/#/score-board        (challenges OWASP)"
    Write-Host "  Prof   -> http://127.0.0.1:$dashboardPort/login            (token ci-dessous)"
    Write-Host "  Prof   -> http://127.0.0.1:$dashboardPort/dashboard?cohort=$Cohort"
    Write-Host ''
    Write-Host ("  DASHBOARD_TEACHER_TOKEN = {0}" -f (Get-EnvValue 'DASHBOARD_TEACHER_TOKEN'))
    Write-Host ("  TEACHER_ADMIN_TOKEN     = {0}" -f (Get-EnvValue 'TEACHER_ADMIN_TOKEN'))
}

Write-Host ''
Write-Host "  Stop  : cd docker; $dcStr --env-file .env down"
Write-Host "  Wipe  : cd docker; $dcStr --env-file .env down -v"
Write-Host "  Logs  : cd docker; $dcStr --env-file .env logs -f"
Write-Host '========================================================================'
