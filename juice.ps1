# juice.ps1 - Launcher JuiceLab (Juice Shop + Dashboard pedagogique)
#
# Usage:
#   .\juice.ps1 start  [shop|dash|all]   (defaut: all)
#   .\juice.ps1 stop   [shop|dash|all]
#   .\juice.ps1 restart[shop|dash|all]
#   .\juice.ps1 status
#   .\juice.ps1 logs   [shop|dash]
#   .\juice.ps1 health
#   .\juice.ps1 build
#   .\juice.ps1 help
#
# Ports : Juice Shop = 3000, Dashboard Flask = 5050
# PIDs  : .run\<svc>.pid       Logs : .logs\<svc>.log

[CmdletBinding()]
param(
  [Parameter(Position=0)]
  [string]$Command = 'help',
  [Parameter(Position=1)]
  [string]$Target  = 'all'
)

$ErrorActionPreference = 'Stop'

# ---- Constantes -----------------------------------------------------------
$Root      = $PSScriptRoot
$ShopDir   = Join-Path $Root 'juice-shop'
$DashDir   = Join-Path $Root 'dashboard'
$RunDir    = Join-Path $Root '.run'
$LogDir    = Join-Path $Root '.logs'

$ShopPort  = 3000
$DashPort  = 5050

$ShopPid   = Join-Path $RunDir  'shop.pid'
$DashPid   = Join-Path $RunDir  'dash.pid'
$ShopLog   = Join-Path $LogDir  'shop.log'
$DashLog   = Join-Path $LogDir  'dash.log'
$ShopErr   = Join-Path $LogDir  'shop.err.log'
$DashErr   = Join-Path $LogDir  'dash.err.log'

$DefaultTeacherToken = 'change-me-please-1234567890'
$DefaultProofSecret  = 'change-me-proof-secret-1234567890'
$CtfKeyFile          = Join-Path $Root 'juice-shop\ctf.key'

if (-not (Test-Path $RunDir)) { New-Item -ItemType Directory -Path $RunDir | Out-Null }
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# ---- Helpers d'affichage ---------------------------------------------------
function Say  { param([string]$m) Write-Host $m -ForegroundColor Cyan }
function Ok   { param([string]$m) Write-Host $m -ForegroundColor Green }
function Warn { param([string]$m) Write-Host $m -ForegroundColor Yellow }
function Errp { param([string]$m) Write-Host $m -ForegroundColor Red }

# ---- Helpers process / port ------------------------------------------------
function Test-PortListening {
  param([int]$Port)
  try {
    $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    return $null -ne $c
  } catch {
    return $false
  }
}

function Get-PidFromFile {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return $null }
  $raw = (Get-Content -Path $Path -Raw -ErrorAction SilentlyContinue).Trim()
  if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
  $n = 0
  if ([int]::TryParse($raw, [ref]$n)) { return $n }
  return $null
}

function Test-PidAlive {
  param([int]$ProcId)
  if (-not $ProcId -or $ProcId -le 0) { return $false }
  try {
    $p = Get-Process -Id $ProcId -ErrorAction Stop
    return $null -ne $p
  } catch {
    return $false
  }
}

function Resolve-Python {
  $candidates = @('python', 'py')
  foreach ($c in $candidates) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
  }
  return $null
}

function Stop-PidTree {
  param([int]$ProcId, [string]$Label)
  if (-not $ProcId -or $ProcId -le 0) { return }
  if (-not (Test-PidAlive -ProcId $ProcId)) {
    Warn "  $Label PID=$ProcId deja eteint"
    return
  }
  try {
    Stop-Process -Id $ProcId -Force -ErrorAction Stop
    Ok "  $Label PID=$ProcId arrete"
  } catch {
    Errp "  $Label PID=$ProcId arret impossible : $($_.Exception.Message)"
  }
}

function Stop-ByPort {
  param([int]$Port, [string]$Label)
  $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if (-not $conns) { return $false }
  $killed = $false
  foreach ($c in $conns) {
    $procId = $c.OwningProcess
    if ($procId -and $procId -gt 0) {
      try {
        $p = Get-Process -Id $procId -ErrorAction Stop
        Warn ('  ' + $Label + ' orphelin PID=' + $procId + ' (' + $p.ProcessName + ') sur port ' + $Port + ' -> kill')
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Ok   ('  ' + $Label + ' PID=' + $procId + ' arrete via port')
        $killed = $true
      } catch {
        Errp ('  ' + $Label + ' PID=' + $procId + ' arret par port impossible : ' + $_.Exception.Message)
      }
    }
  }
  return $killed
}

# ---- Start / Stop : Juice Shop --------------------------------------------
function Start-Shop {
  $existing = Get-PidFromFile -Path $ShopPid
  if ($existing -and (Test-PidAlive -ProcId $existing)) {
    Warn "Juice Shop deja en cours (PID=$existing)"
    return
  }
  if (Test-PortListening -Port $ShopPort) {
    Errp "Port $ShopPort deja utilise par un autre process. Tape 'netstat -ano | findstr :$ShopPort' pour voir."
    return
  }
  if (-not (Test-Path (Join-Path $ShopDir 'package.json'))) {
    Errp "package.json introuvable dans $ShopDir"
    return
  }

  # Sur Windows, Get-Command npm renvoie npm.ps1 (ExternalScript) que
  # Start-Process ne peut pas exec en binaire. On force npm.cmd, sinon on
  # passe par cmd.exe /c "npm start".
  $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
  if ($npmCmd) {
    $exe  = $npmCmd.Source
    $args = @('start')
  } else {
    $exe  = "$env:WINDIR\System32\cmd.exe"
    $args = @('/c', 'npm start')
  }

  Say "demarrage Juice Shop (npm start, port $ShopPort)"
  $proc = Start-Process -FilePath $exe `
                        -ArgumentList $args `
                        -WorkingDirectory $ShopDir `
                        -RedirectStandardOutput $ShopLog `
                        -RedirectStandardError  $ShopErr `
                        -WindowStyle Hidden `
                        -PassThru
  $proc.Id | Out-File -FilePath $ShopPid -Encoding ascii -Force
  Ok "  PID=$($proc.Id)  log=$ShopLog"
}

function Stop-Shop {
  $existing = Get-PidFromFile -Path $ShopPid
  if ($existing) {
    Stop-PidTree -ProcId $existing -Label 'Juice Shop'
    Remove-Item -Path $ShopPid -Force -ErrorAction SilentlyContinue
  } else {
    Warn 'Pas de PID Juice Shop enregistre, recherche par port...'
  }
  [void](Stop-ByPort -Port $ShopPort -Label 'Juice Shop')
}

# ---- Start / Stop : Dashboard ---------------------------------------------
function Start-Dash {
  $existing = Get-PidFromFile -Path $DashPid
  if ($existing -and (Test-PidAlive -ProcId $existing)) {
    Warn "Dashboard deja en cours (PID=$existing)"
    return
  }
  if (Test-PortListening -Port $DashPort) {
    Errp "Port $DashPort deja utilise par un autre process."
    return
  }
  if (-not (Test-Path (Join-Path $DashDir 'app.py'))) {
    Errp "app.py introuvable dans $DashDir"
    return
  }

  $py = Resolve-Python
  if (-not $py) { Errp "python ou py introuvable dans le PATH"; return }

  $env:DASHBOARD_PORT = "$DashPort"
  if (-not $env:DASHBOARD_TEACHER_TOKEN -or $env:DASHBOARD_TEACHER_TOKEN.Length -lt 16) {
    $env:DASHBOARD_TEACHER_TOKEN = $DefaultTeacherToken
    Warn "DASHBOARD_TEACHER_TOKEN non defini, valeur par defaut utilisee (a changer en prod)."
  }
  if (-not $env:DASHBOARD_PROOF_SECRET -or $env:DASHBOARD_PROOF_SECRET.Length -lt 16) {
    $env:DASHBOARD_PROOF_SECRET = $DefaultProofSecret
    Warn "DASHBOARD_PROOF_SECRET non defini, valeur par defaut utilisee (a changer en prod). Utilise pour signer les preuves de lab."
  }
  if (-not $env:DASHBOARD_DEFAULT_COHORT -or $env:DASHBOARD_DEFAULT_COHORT.Length -eq 0) {
    # Reflect what the frontend config.json defines, so that GET /dashboard
    # without ?cohort= still loads the same cohort the students sync to.
    # Update via : $env:DASHBOARD_DEFAULT_COHORT = '<your-cohort-id>'
    try {
      $cfg = Get-Content -Raw -Path (Join-Path $Root 'juice-shop\frontend\src\assets\juicelab\config.json') -ErrorAction Stop | ConvertFrom-Json
      if ($cfg.cohort_id) { $env:DASHBOARD_DEFAULT_COHORT = $cfg.cohort_id }
    } catch {
      Warn "Impossible de lire config.json pour deduire DASHBOARD_DEFAULT_COHORT. Le dashboard exigera ?cohort=... dans l'URL."
    }
  }
  if (-not $env:JUICESHOP_CTF_SECRET -or $env:JUICESHOP_CTF_SECRET.Length -eq 0) {
    # Read the same CTF key that Juice Shop uses to compute flag HMACs in
    # solve notifications (lib/utils.ts ctfFlag()). Letting the dashboard
    # know this secret enables /api/verify-flag to validate student
    # submissions and award the +10 bonus.
    if (Test-Path $CtfKeyFile) {
      try {
        $key = (Get-Content -Raw -Path $CtfKeyFile -ErrorAction Stop).Trim()
        if ($key.Length -gt 0) { $env:JUICESHOP_CTF_SECRET = $key }
      } catch {
        Warn "Impossible de lire $CtfKeyFile, /api/verify-flag retournera 503."
      }
    } else {
      Warn "$CtfKeyFile introuvable. Si tu veux activer la verification de flag, cree le fichier ou exporte JUICESHOP_CTF_SECRET manuellement."
    }
  }

  # CTFd push (Mode C, opt-in). When CTFD_URL et CTFD_ADMIN_TOKEN sont set
  # dans l'env utilisateur, le dashboard les recoit via heritage et active
  # le push automatique des hints penalties vers le serveur CTFd central.
  # Sans ces deux vars, le dashboard tourne en Mode A (local solo) ou
  # Mode B (cohorte tracking sans competition). Aucun fichier de fallback :
  # le token CTFd est sensible, env var only.
  if ($env:CTFD_URL -and $env:CTFD_URL.Length -gt 0 -and $env:CTFD_ADMIN_TOKEN -and $env:CTFD_ADMIN_TOKEN.Length -gt 0) {
    Say "CTFd push enabled (Mode C) -> $($env:CTFD_URL)"
  } else {
    Say "CTFd push disabled (Mode A or B). Set CTFD_URL et CTFD_ADMIN_TOKEN pour activer Mode C."
  }

  $msg = 'demarrage Dashboard  (' + $py + ' app.py, port ' + $DashPort + ')'
  Say $msg
  $proc = Start-Process -FilePath $py `
                        -ArgumentList 'app.py' `
                        -WorkingDirectory $DashDir `
                        -RedirectStandardOutput $DashLog `
                        -RedirectStandardError  $DashErr `
                        -WindowStyle Hidden `
                        -PassThru
  $proc.Id | Out-File -FilePath $DashPid -Encoding ascii -Force
  $line = '  PID=' + $proc.Id + '  log=' + $DashLog
  Ok $line
}

function Stop-Dash {
  $existing = Get-PidFromFile -Path $DashPid
  if ($existing) {
    Stop-PidTree -ProcId $existing -Label 'Dashboard'
    Remove-Item -Path $DashPid -Force -ErrorAction SilentlyContinue
  } else {
    Warn 'Pas de PID Dashboard enregistre, recherche par port...'
  }
  [void](Stop-ByPort -Port $DashPort -Label 'Dashboard')
}

# ---- Status / Health -------------------------------------------------------
function Show-Status {
  Say '== Status JuiceLab =='
  $shopProcId = Get-PidFromFile -Path $ShopPid
  $dashProcId = Get-PidFromFile -Path $DashPid

  $shopAlive  = Test-PidAlive -ProcId $shopProcId
  $dashAlive  = Test-PidAlive -ProcId $dashProcId
  $shopListen = Test-PortListening -Port $ShopPort
  $dashListen = Test-PortListening -Port $DashPort

  Write-Host ('  Juice Shop : PID=' + ($(if ($shopProcId) { $shopProcId } else { '-' })) + '  alive=' + $shopAlive + '  listen:' + $ShopPort + '=' + $shopListen)
  Write-Host ('  Dashboard  : PID=' + ($(if ($dashProcId) { $dashProcId } else { '-' })) + '  alive=' + $dashAlive + '  listen:' + $DashPort + '=' + $dashListen)
}

function Test-Health {
  Say '== Health checks =='
  try {
    $r = Invoke-WebRequest -Uri ("http://127.0.0.1:" + $ShopPort + "/rest/admin/application-version") -TimeoutSec 4 -UseBasicParsing
    Ok ('  Juice Shop  HTTP ' + $r.StatusCode)
  } catch {
    Errp ('  Juice Shop  KO : ' + $_.Exception.Message)
  }
  try {
    $r = Invoke-WebRequest -Uri ("http://127.0.0.1:" + $DashPort + "/api/health") -TimeoutSec 4 -UseBasicParsing
    Ok ('  Dashboard   HTTP ' + $r.StatusCode)
  } catch {
    Errp ('  Dashboard   KO : ' + $_.Exception.Message)
  }
}

# ---- Logs ------------------------------------------------------------------
function Show-Logs {
  param([string]$Which)
  switch ($Which) {
    'shop' {
      if (-not (Test-Path $ShopLog)) { Warn "Pas de log $ShopLog"; return }
      Get-Content -Path $ShopLog -Tail 80 -Wait
    }
    'dash' {
      if (-not (Test-Path $DashLog)) { Warn "Pas de log $DashLog"; return }
      Get-Content -Path $DashLog -Tail 80 -Wait
    }
    default { Errp "logs : 'shop' ou 'dash' attendu" }
  }
}

# ---- Build (Juice Shop only) ----------------------------------------------
function Invoke-Build {
  $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
  if (-not $npmCmd) { Errp 'npm.cmd introuvable dans le PATH'; return }
  $npmExe = $npmCmd.Source
  Say 'npm install (juice-shop)'
  Push-Location $ShopDir
  try {
    & $npmExe install
    if ($LASTEXITCODE -ne 0) { Errp 'npm install a echoue'; return }
    Say 'npm run build:frontend'
    & $npmExe run build:frontend
    if ($LASTEXITCODE -ne 0) { Warn 'build:frontend non disponible, on continue' }
    Say 'npm run build (server)'
    & $npmExe run build
    if ($LASTEXITCODE -ne 0) { Warn 'build server non disponible, on continue' }
    Ok 'Build termine'
  } finally {
    Pop-Location
  }
}

# ---- Help ------------------------------------------------------------------
function Show-Help {
  Write-Host @'
juice.ps1 - Launcher JuiceLab

Commandes :
  start   [shop|dash|all]     demarre les services en arriere-plan
  stop    [shop|dash|all]     arrete les services
  restart [shop|dash|all]     stop puis start
  status                      affiche PIDs et ports
  logs     shop|dash          tail -f sur le log
  health                      ping HTTP des deux services
  build                       npm install + build du Juice Shop
  help                        cet ecran

Environnement :
  DASHBOARD_TEACHER_TOKEN     >= 16 caracteres (sinon valeur par defaut)
'@
}

# ---- Dispatcher ------------------------------------------------------------
switch ($Command.ToLower()) {
  'start' {
    switch ($Target.ToLower()) {
      'shop' { Start-Shop }
      'dash' { Start-Dash }
      'all'  { Start-Shop; Start-Dash }
      default { Errp "start : cible inconnue '$Target'" }
    }
  }
  'stop' {
    switch ($Target.ToLower()) {
      'shop' { Stop-Shop }
      'dash' { Stop-Dash }
      'all'  { Stop-Shop; Stop-Dash }
      default { Errp "stop : cible inconnue '$Target'" }
    }
  }
  'restart' {
    switch ($Target.ToLower()) {
      'shop' { Stop-Shop; Start-Sleep -Seconds 1; Start-Shop }
      'dash' { Stop-Dash; Start-Sleep -Seconds 1; Start-Dash }
      'all'  { Stop-Shop; Stop-Dash; Start-Sleep -Seconds 1; Start-Shop; Start-Dash }
      default { Errp "restart : cible inconnue '$Target'" }
    }
  }
  'status'  { Show-Status }
  'health'  { Test-Health }
  'logs'    { Show-Logs -Which $Target.ToLower() }
  'build'   { Invoke-Build }
  'help'    { Show-Help }
  default   { Errp "commande inconnue '$Command'"; Show-Help }
}
