param(
  [ValidateSet('start','stop','status')]
  [string]$Action = 'status',
  [int]$Port = 8080,
  [int]$WaitSeconds = 600
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvFile = Join-Path $ProjectRoot '.env'
if (Test-Path $EnvFile) {
  Get-Content -LiteralPath $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$') {
      $k = $matches[1]; $v = $matches[2].Trim('"').Trim("'")
      if (-not [Environment]::GetEnvironmentVariable($k)) { [Environment]::SetEnvironmentVariable($k, $v) }
    }
  }
}
$AiHome = $env:DRAMA_AI_HOME
$ModelsRoot = $env:DRAMA_MODELS_ROOT
if (-not $AiHome -or -not $ModelsRoot) { throw 'Set DRAMA_AI_HOME and DRAMA_MODELS_ROOT in .env (see .env.example)' }
$ServerExe = Join-Path $AiHome 'bin-sycl\llama-server.exe'
$ModelPath = Join-Path $ModelsRoot 'Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf'
$Alias = 'Qwen3-30B-A3B-Instruct-2507'
$LogDir = Join-Path $ProjectRoot 'logs'
$PidFile = Join-Path $LogDir 'llm-8080.pid'
$OutLog = Join-Path $LogDir 'llm-8080.out.log'
$ErrLog = Join-Path $LogDir 'llm-8080.err.log'

function Test-Health {
  try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
    return ($r.status -eq 'ok')
  } catch { return $false }
}

function Get-ListenerPid {
  $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
       Select-Object -First 1
  if ($c) { return [int]$c.OwningProcess }
  return 0
}

function Get-CmdLine([int]$procId) {
  if ($procId -le 0) { return '' }
  $p = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
  if ($p) { return [string]$p.CommandLine }
  return ''
}

function Test-ProjectServer([string]$cmd) {
  if (-not $cmd) { return $false }
  return ($cmd -like "*$ModelPath*") -and ($cmd -like "*--port $Port*") -and ($cmd -notlike '*--api-key*')
}

function Get-Inflight {
  try {
    $m = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/metrics" -UseBasicParsing -TimeoutSec 2
    $text = [string]$m.Content
    $p = [regex]::Match($text, '(?m)^llamacpp:requests_processing\s+(\d+)')
    $q = [regex]::Match($text, '(?m)^llamacpp:requests_deferred\s+(\d+)')
    if ($p.Success) {
      $d = '0'
      if ($q.Success) { $d = $q.Groups[1].Value }
      return "$($p.Groups[1].Value) processing / $d deferred"
    }
    return 'metrics unavailable'
  } catch { return 'metrics unavailable' }
}

function Show-Status {
  $healthy = Test-Health
  $procId = Get-ListenerPid
  Write-Host "port: $Port"
  Write-Host "health: $healthy"
  if ($procId -gt 0) {
    Write-Host "listener pid: $procId"
    Write-Host "command: $(Get-CmdLine $procId)"
    Write-Host "inflight: $(Get-Inflight)"
  } else {
    Write-Host "listener: none"
  }
}

# Only stop a server this project started: the model path and port must match and it must not
# carry --api-key (the daily task's server does). Anything else is someone else's process.
function Stop-ProjectServer {
  $stopped = $false
  if (Test-Path $PidFile) {
    $raw = (Get-Content $PidFile -Raw).Trim()
    $procId = 0
    [void][int]::TryParse($raw, [ref]$procId)
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -eq 'llama-server' -and (Test-ProjectServer (Get-CmdLine $procId))) {
      Stop-Process -Id $procId -Force
      Write-Host "stopped llama-server pid $procId (port $Port)"
      $stopped = $true
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
  }
  $listener = Get-ListenerPid
  if ($listener -gt 0 -and (Test-ProjectServer (Get-CmdLine $listener))) {
    Stop-Process -Id $listener -Force
    Write-Host "stopped llama-server pid $listener (port $Port, listener fallback)"
    $stopped = $true
  }
  if (-not $stopped) { Write-Host "no project llama-server on port $Port" }
}

function Start-ProjectServer {
  if (Test-Health) {
    Write-Host "llama-server already healthy on port $Port; leaving it alone"
    return 0
  }
  $listener = Get-ListenerPid
  if ($listener -gt 0) {
    Write-Host "port $Port is already occupied by pid $listener; refusing to start a second server"
    return 2
  }
  if (-not (Test-Path $ServerExe)) { throw "llama-server not found: $ServerExe" }
  if (-not (Test-Path $ModelPath)) { throw "model not found: $ModelPath" }
  New-Item -ItemType Directory -Force $LogDir | Out-Null
  $serverArgs = @(
    '-m', $ModelPath,
    '--host', '127.0.0.1',
    '--port', "$Port",
    '-ngl', '0',
    '-c', '65536',
    '--parallel', '1',
    '-b', '256',
    '-ub', '128',
    '-fa', 'on',
    '--metrics',
    '--alias', "$Alias,default",
    '--reasoning', 'off',
    '--jinja'
  )
  $proc = Start-Process -FilePath $ServerExe -ArgumentList $serverArgs -NoNewWindow -PassThru `
    -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog
  Set-Content -Path $PidFile -Value $proc.Id -Encoding ASCII
  for ($i = 0; $i -lt $WaitSeconds; $i++) {
    Start-Sleep -Seconds 1
    if ($proc.HasExited) {
      Write-Host "llama-server exited with code $($proc.ExitCode)"
      Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
      return 1
    }
    if (Test-Health) {
      Write-Host "llama-server ready on http://127.0.0.1:$Port (pid $($proc.Id))"
      return 0
    }
  }
  Write-Host "llama-server did not become healthy within $WaitSeconds s (pid $($proc.Id))"
  return 1
}

switch ($Action) {
  'start'  { exit (Start-ProjectServer) }
  'stop'   { Stop-ProjectServer; exit 0 }
  'status' { Show-Status; exit 0 }
}
