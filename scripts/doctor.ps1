#requires -Version 5.1
[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    Write-Host "Creating .venv with uv ..."
    uv sync --python 3.12
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

& $Py -m drama_studio doctor @Rest
exit $LASTEXITCODE
