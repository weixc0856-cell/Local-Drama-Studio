#requires -Version 5.1
<#
.SYNOPSIS
    Start / stop / inspect the local CosyVoice runtime on port 50000.

.DESCRIPTION
    Cosmetic Voice has two runtimes and they are mutually exclusive on 50000:

      cosyvoice2  CosyVoice2-0.5B (start_cosyvoice.bat)      -- zero-shot, better
                  pronunciation and speaker similarity; no preset voices.
      sft         CosyVoice-300M-SFT (start_cosyvoice_sft.bat) -- preset speakers
                  (中文男/中文女); its zero-shot loses finals and drifts in pitch.

    This script only *launches* those batch files. Nothing under
    D:\AI\CosyVoice-Runtime is modified: the project's rule is that the shared
    environment stays untouched, and the choice of runtime belongs here.

    Whoever starts the service stops it. Port 50000 is single-owner, like 8080.

.EXAMPLE
    scripts\cosyvoice_server.ps1 -Action start
    scripts\cosyvoice_server.ps1 -Action start -Model sft
    scripts\cosyvoice_server.ps1 -Action status
    scripts\cosyvoice_server.ps1 -Action stop
#>
[CmdletBinding()]
param(
    [ValidateSet("start", "stop", "status")]
    [string]$Action = "status",

    [ValidateSet("cosyvoice2", "sft")]
    [string]$Model = "cosyvoice2",

    [int]$Port = 50000,
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = "Stop"
$Runtime = "D:\AI\CosyVoice-Runtime"
$Launchers = @{
    "cosyvoice2" = Join-Path $Runtime "start_cosyvoice.bat"
    "sft"        = Join-Path $Runtime "start_cosyvoice_sft.bat"
}

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
        Write-Host "No CosyVoice process is running."
        return
    }
    foreach ($proc in $procs) {
        Write-Host "Stopping CosyVoice python PID $($proc.Id)"
        Stop-Process -Id $proc.Id -Force
    }
    Start-Sleep -Seconds 2
    $health = Get-Health
    if ($health) {
        Write-Warning "Port $Port still answers; another process owns it."
    } else {
        Write-Host "CosyVoice stopped; port $Port is free."
    }
}

switch ($Action) {
    "status" {
        $health = Get-Health
        if (-not $health) {
            Write-Host "CosyVoice is not running on $Port."
            exit 0
        }
        Write-Host ("status={0} model_class={1} sample_rate={2}" -f `
            $health.status, $health.model_class, $health.sample_rate)
        Write-Host ("model_dir={0}" -f $health.model_dir)
        Write-Host ("speakers={0}" -f ($health.speakers -join ", "))
        exit 0
    }
    "stop" {
        Stop-Runtime
        exit 0
    }
    "start" {
        $health = Get-Health
        if ($health) {
            Write-Host ("Port {0} is already in use by {1} ({2}). Not starting another instance." -f `
                $Port, $health.model_class, $health.status)
            exit 0
        }
        $launcher = $Launchers[$Model]
        if (-not (Test-Path $launcher)) {
            Write-Error "Launcher not found: $launcher"
            exit 1
        }
        Start-Process -FilePath $launcher -WindowStyle Hidden | Out-Null
        Write-Host "Starting $Model from $launcher"

        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 5
            $health = Get-Health
            if ($health -and $health.status -eq "ready") {
                Write-Host ("Ready: model_class={0} sample_rate={1}" -f `
                    $health.model_class, $health.sample_rate)
                exit 0
            }
        }
        Write-Warning "CosyVoice did not become ready within $TimeoutSeconds s. Check the runtime console."
        exit 1
    }
}
