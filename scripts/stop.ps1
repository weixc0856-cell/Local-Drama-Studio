#requires -Version 5.1
[CmdletBinding()]
param([int]$Port = 8188)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "logs\comfyui.pid"

# On Windows the venv python.exe is a launcher: it starts the base interpreter
# as a child. The PID we record may therefore not be the process listening on
# the port. Walk up to 3 levels and require a ComfyUI command line before
# killing anything.
function Get-ComfyRoot([int]$ProcessId) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    for ($i = 0; $i -lt 3 -and $proc; $i++) {
        if ($proc.CommandLine -like "*runtime\ComfyUI*") { return [int]$proc.ProcessId }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)" -ErrorAction SilentlyContinue
    }
    return $null
}

function Stop-ComfyTree([int]$ProcessId, [string]$Reason) {
    $rootPid = Get-ComfyRoot $ProcessId
    if (-not $rootPid) {
        Write-Warning "PID $ProcessId ($Reason) does not belong to runtime\ComfyUI; refusing to stop it."
        return $false
    }
    & taskkill /PID $rootPid /T /F | Out-Null
    Start-Sleep -Milliseconds 800
    Write-Host "Stopped ComfyUI process tree rooted at PID $rootPid ($Reason)."
    return $true
}

if (Test-Path $PidFile) {
    $savedPid = 0
    [void][int]::TryParse((Get-Content $PidFile -Raw).Trim(), [ref]$savedPid)
    if ($savedPid -gt 0) { Stop-ComfyTree $savedPid "pid file" | Out-Null }
    Remove-Item $PidFile -Force
}

$connections = @()
try { $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue } catch { }
foreach ($conn in $connections) {
    Stop-ComfyTree $conn.OwningProcess "port $Port listener" | Out-Null
}

Start-Sleep -Milliseconds 500
$still = @()
try { $still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue } catch { }
if ($still) {
    Write-Warning "Port $Port is still listening after stop (PID $($still[0].OwningProcess))."
    exit 1
}
Write-Host "ComfyUI is stopped."
