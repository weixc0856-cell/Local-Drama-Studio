"""Environment diagnostics.

Every check returns one of four R0 statuses:

    PASS_VERIFIED  executed and succeeded, evidence attached
    PASS_LIMITED   executed but only partially usable / degraded
    FAIL           executed and failed
    NOT_RUN        precondition missing, so the check was not executed

The doctor never guesses hardware or model state: anything it cannot observe
is reported as NOT_RUN, never as PASS.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import (
    ModelRegistry,
    Settings,
    load_audio,
    load_generation,
    load_models,
    load_settings,
)

PASS_VERIFIED = "PASS_VERIFIED"
PASS_LIMITED = "PASS_LIMITED"
FAIL = "FAIL"
NOT_RUN = "NOT_RUN"

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@dataclass
class Check:
    id: str
    title: str
    status: str
    detail: str
    required: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)


def _run(cmd: list[str], timeout: float = 30.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return 127, "command not found"
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def _ps(script: str) -> Any:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if exe is None:
        return None
    cmd = [
        exe,
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; " + script,
    ]
    code, out = _run(cmd, timeout=30)
    if code != 0 or not out.strip():
        return None
    try:
        return json.loads(out.strip())
    except json.JSONDecodeError:
        return None


def _port_open(host: str, port: int, timeout: float = 0.7) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_probe(url: str, headers: dict[str, str] | None = None) -> tuple[str, str]:
    """Return (r0_status, detail)."""
    import httpx

    try:
        resp = httpx.get(url, headers=headers or {}, timeout=3.0, trust_env=False)
    except httpx.HTTPError as exc:
        return PASS_LIMITED, f"端口开放但请求失败: {type(exc).__name__}: {exc}"
    if resp.status_code == 200:
        return PASS_VERIFIED, f"HTTP 200 ({url})"
    if resp.status_code in (401, 403):
        return PASS_LIMITED, f"HTTP {resp.status_code}: 该端口实例需要 API Key，可能被其他服务占用"
    return PASS_LIMITED, f"HTTP {resp.status_code} ({url})"


def _parse_host_port(base_url: str) -> tuple[str, int]:
    rest = base_url.split("://", 1)[-1].rstrip("/")
    host_port = rest.split("/", 1)[0]
    host, _, port = host_port.partition(":")
    return host, int(port) if port else 80


def _check_tool(name: str, args: list[str], required: bool, check_id: str, title: str) -> Check:
    path = shutil.which(name)
    if path is None:
        return Check(check_id, title, FAIL, f"找不到可执行文件: {name}", required)
    code, out = _run([path, *args], timeout=20)
    first = next((line.strip() for line in out.splitlines() if line.strip()), "")
    if code == 0:
        return Check(check_id, title, PASS_VERIFIED, first[:200], required, {"path": path})
    return Check(check_id, title, FAIL, f"退出码 {code}: {out.strip()[:300]}", required, {"path": path})


def _hardware_checks(settings: Settings) -> list[Check]:
    checks: list[Check] = []

    cpu = _ps(
        "Get-CimInstance Win32_Processor | "
        "Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress"
    )
    if cpu:
        cpu = cpu[0] if isinstance(cpu, list) else cpu
        checks.append(
            Check(
                "hw.cpu",
                "CPU",
                PASS_VERIFIED,
                f"{cpu.get('Name', '?')} / {cpu.get('NumberOfCores')}C{cpu.get('NumberOfLogicalProcessors')}T",
                False,
                cpu,
            )
        )
    else:
        checks.append(Check("hw.cpu", "CPU", NOT_RUN, "无法通过 CIM 读取 CPU 信息"))

    cs = _ps(
        "Get-CimInstance Win32_ComputerSystem | "
        "Select-Object TotalPhysicalMemory | ConvertTo-Json -Compress"
    )
    if cs and cs.get("TotalPhysicalMemory"):
        gib = round(int(cs["TotalPhysicalMemory"]) / 1024**3, 1)
        checks.append(Check("hw.ram", "内存", PASS_VERIFIED, f"{gib} GiB", False, cs))
    else:
        checks.append(Check("hw.ram", "内存", NOT_RUN, "无法读取物理内存"))

    gpus = _ps(
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name,DriverVersion,AdapterRAM | ConvertTo-Json -Compress"
    )
    if gpus:
        gpus = gpus if isinstance(gpus, list) else [gpus]
        names = [f"{g.get('Name')} (驱动 {g.get('DriverVersion')})" for g in gpus]
        has_arc = any("Arc" in (g.get("Name") or "") for g in gpus)
        checks.append(
            Check(
                "hw.gpu",
                "GPU",
                PASS_VERIFIED if has_arc else PASS_LIMITED,
                "; ".join(names),
                False,
                {
                    "gpus": gpus,
                    "note": "AdapterRAM 是 32 位字段，不能当作显存；显存以 XPU 探测结果为准",
                },
            )
        )
    else:
        checks.append(Check("hw.gpu", "GPU", NOT_RUN, "无法读取显卡信息"))

    for label, path in (("project", settings.root), ("models", settings.paths.models_root)):
        try:
            usage = shutil.disk_usage(path)
            free_gib = round(usage.free / 1024**3, 1)
            checks.append(
                Check(
                    f"hw.disk.{label}",
                    f"磁盘空间 / {label}",
                    PASS_VERIFIED if free_gib >= 40 else PASS_LIMITED,
                    f"{path} 剩余 {free_gib} GiB",
                    False,
                    {"free_gib": free_gib, "path": str(path)},
                )
            )
        except OSError as exc:
            checks.append(Check(f"hw.disk.{label}", f"磁盘空间 / {label}", FAIL, str(exc)))

    return checks


def _service_checks(settings: Settings) -> list[Check]:
    checks: list[Check] = []

    comfy = settings.comfyui
    if _port_open(comfy.host, comfy.port):
        status, detail = _http_probe(f"{comfy.base_url}/system_stats")
        checks.append(Check("svc.comfyui", "ComfyUI 服务", status, detail, False))
    else:
        checks.append(
            Check("svc.comfyui", "ComfyUI 服务", NOT_RUN, f"{comfy.host}:{comfy.port} 未监听")
        )

    llm = settings.llm
    llm_host, llm_port = _parse_host_port(llm.base_url)
    if _port_open(llm_host, llm_port):
        headers = {"Authorization": f"Bearer {llm.api_key}"} if llm.api_key else {}
        status, detail = _http_probe(f"{llm.base_url.rstrip('/')}/models", headers)
        checks.append(
            Check("svc.llm", "本地 LLM 服务", status, detail, False, {"base_url": llm.base_url})
        )
    else:
        checks.append(
            Check("svc.llm", "本地 LLM 服务", NOT_RUN, f"{llm.base_url} 未监听（R4 前不要求）")
        )

    tts = settings.tts
    tts_host, tts_port = _parse_host_port(tts.base_url)
    if _port_open(tts_host, tts_port):
        status, detail = _http_probe(f"{tts.base_url.rstrip('/')}/health")
        checks.append(
            Check("svc.tts", "CosyVoice TTS 服务", status, detail, False, {"base_url": tts.base_url})
        )
    else:
        checks.append(
            Check("svc.tts", "CosyVoice TTS 服务", NOT_RUN, f"{tts.base_url} 未监听（R6 前不要求）")
        )

    return checks


def _comfyui_checks(settings: Settings) -> list[Check]:
    checks: list[Check] = []
    comfy_dir = settings.comfyui_dir
    main_py = comfy_dir / "main.py"
    python_exe = settings.comfyui_python

    if main_py.is_file():
        checks.append(Check("comfy.install", "ComfyUI 安装", PASS_VERIFIED, str(comfy_dir), False))
    else:
        checks.append(
            Check("comfy.install", "ComfyUI 安装", NOT_RUN, f"未找到 {main_py}（R0-B 待执行）")
        )

    if not python_exe.is_file():
        checks.append(
            Check("comfy.xpu", "PyTorch XPU", NOT_RUN, f"未找到独立运行时 {python_exe}（R0-B 待执行）")
        )
        return checks

    probe = (
        "import json\n"
        "try:\n"
        "    import torch\n"
        "    info={'torch':torch.__version__,'xpu_available':bool(torch.xpu.is_available()),"
        "'device_count':torch.xpu.device_count() if hasattr(torch.xpu,'device_count') else None}\n"
        "    if info['xpu_available']:\n"
        "        info['devices']=[torch.xpu.get_device_name(i) for i in range(info['device_count'] or 0)]\n"
        "    print(json.dumps(info))\n"
        "except Exception as exc:\n"
        "    print(json.dumps({'error':f'{type(exc).__name__}: {exc}'}))\n"
    )
    code, out = _run([str(python_exe), "-c", probe], timeout=120)
    try:
        info = json.loads(out.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        info = {"error": out.strip()[:400]}
    if info.get("error"):
        checks.append(Check("comfy.xpu", "PyTorch XPU", FAIL, info["error"], False, info))
    elif info.get("xpu_available"):
        checks.append(
            Check(
                "comfy.xpu",
                "PyTorch XPU",
                PASS_VERIFIED,
                f"torch {info.get('torch')} / {info.get('device_count')} 个 XPU: {info.get('devices')}",
                False,
                info,
            )
        )
    else:
        checks.append(
            Check(
                "comfy.xpu",
                "PyTorch XPU",
                FAIL,
                f"torch {info.get('torch')} 已安装但 torch.xpu.is_available() == False",
                False,
                info,
            )
        )
    return checks


def _model_checks(registry: ModelRegistry) -> list[Check]:
    checks: list[Check] = []
    for key, spec in registry.models.items():
        missing: list[str] = []
        present: list[str] = []
        total = 0
        for name, path in spec.files.items():
            expected = spec.sizes.get(name)
            actual = path.stat().st_size if path.is_file() else 0
            if actual <= 0:
                missing.append(f"{name}={path} (缺失)")
            elif expected is not None and actual != expected:
                missing.append(f"{name}={path} (大小 {actual} != 预期 {expected}，可能未下载完)")
            else:
                present.append(name)
                total += actual
        if missing:
            checks.append(
                Check(
                    f"model.{key}",
                    f"模型 / {key}",
                    FAIL,
                    "不可用: " + "; ".join(missing),
                    True,
                    {"present": present, "missing": missing},
                )
            )
        else:
            checks.append(
                Check(
                    f"model.{key}",
                    f"模型 / {key}",
                    PASS_VERIFIED,
                    f"{len(present)} 个文件, {round(total / 1024**3, 2)} GiB",
                    True,
                    {"files": {n: str(p) for n, p in spec.files.items()}},
                )
            )
    return checks


def _config_checks(settings: Settings) -> list[Check]:
    try:
        root = settings.root
        load_settings(root)
        load_models(root)
        load_generation(root)
        load_audio(root)
        return [
            Check("cfg.load", "配置文件", PASS_VERIFIED, "settings/models/generation/audio 均可解析", True)
        ]
    except Exception as exc:  # noqa: BLE001 - report any config error verbatim
        return [Check("cfg.load", "配置文件", FAIL, f"{type(exc).__name__}: {exc}", True)]


def collect_checks(settings: Settings) -> list[Check]:
    checks: list[Check] = [
        Check(
            "env.python",
            "Python",
            PASS_VERIFIED if sys.version_info[:2] == (3, 12) else PASS_LIMITED,
            f"{platform.python_version()} ({sys.executable})",
            True,
            {"version": platform.python_version()},
        )
    ]
    in_venv = sys.prefix != sys.base_prefix
    checks.append(
        Check(
            "env.venv",
            "虚拟环境",
            PASS_VERIFIED if in_venv else FAIL,
            sys.prefix if in_venv else "当前解释器不是虚拟环境",
            True,
        )
    )
    checks.append(_check_tool("uv", ["--version"], True, "tool.uv", "uv"))
    checks.append(_check_tool(settings.ffmpeg.binary, ["-version"], True, "tool.ffmpeg", "FFmpeg"))
    checks.append(_check_tool(settings.ffmpeg.ffprobe, ["-version"], True, "tool.ffprobe", "ffprobe"))

    checks.extend(_config_checks(settings))
    checks.extend(_hardware_checks(settings))
    checks.extend(_service_checks(settings))
    checks.extend(_comfyui_checks(settings))
    checks.extend(_model_checks(load_models(settings.root)))
    return checks


def summarize(checks: list[Check]) -> dict[str, Any]:
    counts = {status: 0 for status in (PASS_VERIFIED, PASS_LIMITED, FAIL, NOT_RUN)}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    required_failed = [c.id for c in checks if c.required and c.status == FAIL]
    return {
        "counts": counts,
        "required_failed": required_failed,
        "ok": not required_failed,
    }


def write_report(settings: Settings, checks: list[Check], target: Path | None = None) -> Path:
    now = datetime.now()
    target = target or settings.paths.logs_root / f"doctor-{now:%Y%m%d-%H%M%S}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": now.isoformat(timespec="seconds"),
        "host": platform.node(),
        "platform": platform.platform(),
        "root": str(settings.root),
        "summary": summarize(checks),
        "checks": [asdict(c) for c in checks],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
