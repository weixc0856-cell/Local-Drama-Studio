#requires -Version 5.1
[CmdletBinding()]
param(
    [int]$Port = 8188,
    [string[]]$ExtraArgs = @()
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ComfyDir = Join-Path $Root "runtime\ComfyUI"
$ComfyPy = Join-Path $ComfyDir ".venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"
$PidFile = Join-Path $LogDir "comfyui.pid"

if (-not (Test-Path $ComfyPy)) {
    Write-Error "ComfyUI runtime not found. Run: scripts\setup.ps1 -WithComfyUI"
    exit 1
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$existing = $null
try { $existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue } catch { }
if ($existing) {
    Write-Host "Port $Port is already listening (PID $($existing[0].OwningProcess)). Not starting another instance."
    exit 0
}

$stdout = Join-Path $LogDir "comfyui.log"
$stderr = Join-Path $LogDir "comfyui.err.log"
$comfyArgs = @("main.py", "--listen", "127.0.0.1", "--port", "$Port", "--disable-auto-launch") + $ExtraArgs

$proc = Start-Process -FilePath $ComfyPy -ArgumentList $comfyArgs -WorkingDirectory $ComfyDir `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
$proc.Id | Set-Content -Encoding ascii $PidFile
Write-Host "ComfyUI starting (PID $($proc.Id)); log: $stdout"

$deadline = (Get-Date).AddSeconds(180)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    if ($proc.HasExited) {
        Write-Error "ComfyUI exited with code $($proc.ExitCode). See $stderr"
        exit 1
    }
    # Invoke-RestMethod honors the system proxy and can return 502 for
    # localhost on this machine. curl.exe ignores the WinINET proxy and is the
    # reliable readiness probe.
    $probe = & curl.exe -s -f --max-time 2 "http://127.0.0.1:$Port/system_stats"
    if ($LASTEXITCODE -eq 0 -and $probe) {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listener) { $listener[0].OwningProcess | Set-Content -Encoding ascii $PidFile }
        Write-Host "ComfyUI is ready at http://127.0.0.1:$Port"
        $probe | Set-Content -Encoding utf8 (Join-Path $LogDir "comfyui-system-stats.json")
        exit 0
    }
}
Write-Error "ComfyUI did not become ready within 180s. See $stderr"
exit 1
