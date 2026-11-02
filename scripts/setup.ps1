#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$WithComfyUI,
    [string]$ComfyUIRef = "",
    [string]$TorchIndexUrl = "https://download.pytorch.org/whl/xpu"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[1/4] Sync orchestration environment (.venv)"
uv sync --python 3.12
if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

Write-Host "[2/4] Prepare directories"
foreach ($d in @("logs", "projects", "workflows", "runtime")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $d) | Out-Null
}

if (-not $WithComfyUI) {
    Write-Host "[3/4] ComfyUI install skipped (pass -WithComfyUI to build runtime/ComfyUI)"
    Write-Host "[4/4] Done"
    exit 0
}

$ComfyDir = Join-Path $Root "runtime\ComfyUI"
$ComfyVenv = Join-Path $ComfyDir ".venv"
$ComfyPy = Join-Path $ComfyVenv "Scripts\python.exe"

Write-Host "[3/4] Install ComfyUI engine at $ComfyDir"
if (-not (Test-Path (Join-Path $ComfyDir ".git"))) {
    git clone https://github.com/comfyanonymous/ComfyUI.git $ComfyDir
    if ($LASTEXITCODE -ne 0) { throw "git clone ComfyUI failed" }
    if ($ComfyUIRef -ne "") {
        git -C $ComfyDir checkout $ComfyUIRef
        if ($LASTEXITCODE -ne 0) { throw "git checkout $ComfyUIRef failed" }
    }
}

if (-not (Test-Path $ComfyPy)) {
    uv venv --python 3.12 $ComfyVenv
    if ($LASTEXITCODE -ne 0) { throw "uv venv for ComfyUI failed" }
}

Write-Host "  - PyTorch XPU from $TorchIndexUrl"
uv pip install --python $ComfyPy torch torchvision torchaudio --index-url $TorchIndexUrl
if ($LASTEXITCODE -ne 0) { throw "PyTorch XPU install failed" }

Write-Host "  - ComfyUI requirements (torch lines filtered out to keep the XPU build)"
$Req = Join-Path $ComfyDir "requirements.txt"
$Filtered = Join-Path $env:TEMP "comfyui-requirements-no-torch.txt"
Get-Content $Req | Where-Object { $_ -notmatch '^\s*(torch|torchvision|torchaudio)\b' } |
    Set-Content -Encoding utf8 $Filtered
uv pip install --python $ComfyPy -r $Filtered
if ($LASTEXITCODE -ne 0) { throw "ComfyUI requirements install failed" }

Write-Host "  - ComfyUI-GGUF custom node"
$GgufDir = Join-Path $ComfyDir "custom_nodes\ComfyUI-GGUF"
if (-not (Test-Path (Join-Path $GgufDir ".git"))) {
    git clone https://github.com/city96/ComfyUI-GGUF.git $GgufDir
    if ($LASTEXITCODE -ne 0) { throw "git clone ComfyUI-GGUF failed" }
}
$GgufReq = Join-Path $GgufDir "requirements.txt"
if (Test-Path $GgufReq) {
    uv pip install --python $ComfyPy -r $GgufReq
    if ($LASTEXITCODE -ne 0) { throw "ComfyUI-GGUF requirements install failed" }
}

Write-Host "  - extra_model_paths.yaml -> D:\AI\models"
Copy-Item (Join-Path $Root "config\comfyui_extra_model_paths.yaml") (Join-Path $ComfyDir "extra_model_paths.yaml") -Force

Write-Host "[4/4] Probe PyTorch XPU"
& $ComfyPy -c "import torch; print('torch', torch.__version__); print('xpu_available', torch.xpu.is_available()); print('device_count', torch.xpu.device_count()); [print('device', i, torch.xpu.get_device_name(i)) for i in range(torch.xpu.device_count())]"
if ($LASTEXITCODE -ne 0) { throw "PyTorch XPU probe failed" }

Write-Host "Setup complete. Next: scripts\doctor.ps1"
