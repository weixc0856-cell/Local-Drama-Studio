#requires -Version 5.1
<#
.SYNOPSIS
    Start / stop / inspect the local TTS runtime on port 50000 (VoxCPM2).

.DESCRIPTION
    50000 belongs to exactly one runtime: VoxCPM-Runtime (VoxCPM2, CPU only,
    no VRAM). The file keeps its historical name because the docs and daily habit
    refer to it; the CosyVoice runtimes it used to launch are retired
    (2026-11-06) and CosyVoice-Runtime is being deleted.

    The script only launches VoxCPM-Runtime\start_voxcpm.bat and stops
    python processes whose executable lives under that directory. Nothing in the
    shared runtime is modified.

    Whoever starts the service stops it. Port 50000 is single-owner, like 8080.

.EXAMPLE
    scripts\cosyvoice_server.ps1 -Action start
    scripts\cosyvoice_server.ps1 -Action status
    scripts\cosyvoice_server.ps1 -Action stop
#>
[CmdletBinding()]
param(
    [ValidateSet("start", "stop", "status")]
    [string]$Action = "status",

    # Old command lines pass -Model cosyvoice2/sft. Only voxcpm2 still exists.
    [string]$Model = "voxcpm2",

    [int]$Port = 50000,
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

$EnvFile = Join-Path $ProjectRoot '.env'
if (Test-Path $EnvFile) {
  Get-Content -LiteralPath $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$') {
      $k = $matches[1]; $v = $matches[2].Trim('"').Trim("'")
      if (-not [Environment]::GetEnvironmentVariable($k)) { [Environment]::SetEnvironmentVariable($k, $v) }
    }
  }
}
$Runtime = $env:VOXCPM_RUNTIME
if (-not $Runtime -and $env:DRAMA_AI_HOME) { $Runtime = Join-Path $env:DRAMA_AI_HOME 'VoxCPM-Runtime' }
if (-not $Runtime) { throw 'Set VOXCPM_RUNTIME or DRAMA_AI_HOME in .env (see .env.example)' }
$Launcher = Join-Path $Runtime "start_voxcpm.bat"
$ExpectedModelClass = "VoxCPM2"

function Get-Health {
    try {
        $raw = & curl.exe -s -m 3 "http://127.0.0.1:$Port/health"
        if (-not $raw) { return $null }
        return $raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Stop-Runtime {
    $procs = Get-Process -Name python -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -like "$Runtime*" }
    if (-not $procs) {
        Write-Host "No VoxCPM2 process is running."
        return
    }
    foreach ($proc in $procs) {
        Write-Host "Stopping VoxCPM2 python PID $($proc.Id)"
        Stop-Process -Id $proc.Id -Force
    }
    Start-Sleep -Seconds 2
    $health = Get-Health
    if ($health) {
        Write-Warning "Port $Port still answers; another process owns it."
    } else {
        Write-Host "VoxCPM2 stopped; port $Port is free."
    }
}

switch ($Action) {
    "status" {
        $health = Get-Health
        if (-not $health) {
            Write-Host "VoxCPM2 is not running on $Port."
            exit 0
        }
        Write-Host ("status={0} model_class={1} sample_rate={2}" -f `
            $health.status, $health.model_class, $health.sample_rate)
        Write-Host ("model_dir={0}" -f $health.model_dir)
        Write-Host ("load_seconds={0} timesteps={1} cfg={2}" -f `
            $health.load_seconds, $health.timesteps, $health.cfg)
        $modeText = if ($health.modes) { $health.modes -join "," } else { "none" }
        $speakerText = if ($health.speakers) { $health.speakers -join "," } else { "none" }
        Write-Host ("modes={0} speakers={1}" -f $modeText, $speakerText)
        if ($health.model_class -and $health.model_class -ne $ExpectedModelClass) {
            Write-Warning "Port $Port is served by $($health.model_class), not $ExpectedModelClass."
        }
        exit 0
    }
    "stop" {
        Stop-Runtime
        exit 0
    }
    "start" {
        if ($Model -ne "voxcpm2") {
            Write-Error ("TTS 后端 $Model 已退休：50000 现在只跑 VoxCPM2。" +
                "用 -Model voxcpm2（或不传 -Model），SFT 预置音色不再可用。")
            exit 1
        }
        $health = Get-Health
        if ($health) {
            Write-Host ("Port {0} is already in use by {1} ({2}). Not starting another instance." -f `
                $Port, $health.model_class, $health.status)
            exit 0
        }
        if (-not (Test-Path $Launcher)) {
            Write-Error "Launcher not found: $Launcher"
            exit 1
        }
        Start-Process -FilePath $Launcher -WindowStyle Hidden | Out-Null
        Write-Host "Starting VoxCPM2 from $Launcher"

        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 5
            $health = Get-Health
            if ($health -and $health.status -eq "ready") {
                Write-Host ("Ready: model_class={0} sample_rate={1} load_seconds={2}" -f `
                    $health.model_class, $health.sample_rate, $health.load_seconds)
                exit 0
            }
        }
        Write-Warning "VoxCPM2 did not become ready within $TimeoutSeconds s. Check $Runtime\logs\server.log."
        exit 1
    }
}
