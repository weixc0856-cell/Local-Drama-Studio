"""Fast, honest environment probes.

A service that cannot be observed is reported as ``UNKNOWN`` / ``NOT_RUN``.
Nothing here assumes a service is healthy because it is configured.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from drama_studio.config import Settings, load_audio, load_settings

PASS_VERIFIED = "PASS_VERIFIED"
PASS_LIMITED = "PASS_LIMITED"
FAIL = "FAIL"
NOT_RUN = "NOT_RUN"
UNKNOWN = "UNKNOWN"

_cache: dict[str, Any] = {"at": 0.0, "value": None}
_lock = threading.Lock()
TTL_SECONDS = 5.0


def _port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _host_port(base_url: str) -> tuple[str, int]:
    parsed = urlparse(base_url)
    return parsed.hostname or "127.0.0.1", parsed.port or 80


def _http_json(url: str, headers: dict[str, str] | None = None, timeout: float = 1.6) -> tuple[int | None, Any, str]:
    try:
        resp = httpx.get(url, headers=headers or {}, timeout=timeout, trust_env=False)
    except httpx.HTTPError as exc:
        return None, None, f"{type(exc).__name__}: {exc}"
    try:
        data = resp.json()
    except ValueError:
        data = None
    return resp.status_code, data, ""


def _service(id_: str, name: str, url: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"id": id_, "name": name, "url": url, "status": status, "detail": detail, **extra}


def _probe_comfy(settings: Settings) -> tuple[dict[str, Any], dict[str, Any] | None]:
    comfy = settings.comfyui
    host, port = comfy.host, comfy.port
    url = f"http://{host}:{port}"
    if not _port_open(host, port):
        return _service("comfyui", "ComfyUI", url, NOT_RUN, f"{host}:{port} 未监听"), None
    code, data, error = _http_json(f"{url}/system_stats")
    if code == 200 and isinstance(data, dict):
        devices = data.get("devices") or []
        gpu = None
        if devices:
            device = devices[0]
            total = device.get("vram_total")
            free = device.get("vram_free")
            gpu = {
                "name": device.get("name"),
                "vram_total_gib": round(total / 1024**3, 2) if isinstance(total, (int, float)) else None,
                "vram_free_gib": round(free / 1024**3, 2) if isinstance(free, (int, float)) else None,
                "source": "ComfyUI /system_stats",
            }
        return _service("comfyui", "ComfyUI", url, PASS_VERIFIED, "HTTP 200 /system_stats"), gpu
    if code is not None:
        return _service("comfyui", "ComfyUI", url, PASS_LIMITED, f"端口开放但 HTTP {code}"), None
    return _service("comfyui", "ComfyUI", url, PASS_LIMITED, f"端口开放但请求失败：{error}"), None


def _probe_llm(settings: Settings) -> dict[str, Any]:
    llm = settings.llm
    host, port = _host_port(llm.base_url)
    root = llm.base_url.rstrip("/").removesuffix("/v1")
    url = f"http://{host}:{port}"
    if not _port_open(host, port):
        return _service("llm", "本地 LLM", url, NOT_RUN, f"{host}:{port} 未监听；使用时由 scripts/llm_server.ps1 启动")
    code, data, error = _http_json(f"{root}/health")
    if code == 200 and isinstance(data, dict) and data.get("status") == "ok":
        return _service("llm", "本地 LLM", url, PASS_VERIFIED, f"healthy；模型 {llm.model}", model=llm.model)
    if code == 200:
        return _service("llm", "本地 LLM", url, PASS_LIMITED, "HTTP 200，但 /health 未返回 status=ok")
    if code in (401, 403):
        return _service("llm", "本地 LLM", url, PASS_LIMITED, f"HTTP {code}：可能被其他实例占用")
    if code is not None:
        return _service("llm", "本地 LLM", url, PASS_LIMITED, f"端口开放但 HTTP {code}")
    return _service("llm", "本地 LLM", url, PASS_LIMITED, f"端口开放但请求失败：{error}")


def _probe_tts(settings: Settings) -> dict[str, Any]:
    tts = settings.tts
    host, port = _host_port(tts.base_url)
    url = f"http://{host}:{port}"
    if not _port_open(host, port):
        return _service("tts", "VoxCPM2", url, NOT_RUN, f"{host}:{port} 未监听；R6 前不要求")
    code, data, error = _http_json(f"{url}/health")
    if code == 200 and isinstance(data, dict):
        speakers = data.get("speakers")
        detail = f"status={data.get('status')}"
        if speakers:
            detail += f"；speakers={len(speakers)}"
        return _service("tts", "VoxCPM2", url, PASS_VERIFIED, detail, speakers=speakers)
    if code is not None:
        return _service("tts", "VoxCPM2", url, PASS_LIMITED, f"端口开放但 HTTP {code}")
    return _service("tts", "VoxCPM2", url, PASS_LIMITED, f"端口开放但请求失败：{error}")


def _tool(name: str, args: list[str], label: str) -> dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {"id": f"tool.{name}", "name": label, "status": FAIL, "detail": "未找到可执行文件", "path": None}
    try:
        proc = subprocess.run([path, *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"id": f"tool.{name}", "name": label, "status": FAIL, "detail": str(exc), "path": path}
    first = next((line.strip() for line in (proc.stdout or proc.stderr or "").splitlines() if line.strip()), "")
    return {
        "id": f"tool.{name}",
        "name": label,
        "status": PASS_VERIFIED if proc.returncode == 0 else FAIL,
        "detail": first[:160],
        "path": path,
    }


def _disk(path: Path, label: str) -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(path)
        return {
            "id": f"disk.{label}",
            "name": f"磁盘 / {label}",
            "path": str(path),
            "total_gib": round(usage.total / 1024**3, 1),
            "free_gib": round(usage.free / 1024**3, 1),
            "status": PASS_VERIFIED if usage.free / 1024**3 >= 40 else PASS_LIMITED,
        }
    except OSError as exc:
        return {"id": f"disk.{label}", "name": f"磁盘 / {label}", "path": str(path), "status": FAIL, "detail": str(exc)}


def probe(force: bool = False) -> dict[str, Any]:
    now = time.monotonic()
    with _lock:
        if not force and _cache["value"] is not None and now - _cache["at"] < TTL_SECONDS:
            return _cache["value"]
        settings = load_settings()
        comfy, gpu = _probe_comfy(settings)
        services = [comfy, _probe_llm(settings), _probe_tts(settings)]
        tools = [
            _tool(settings.ffmpeg.binary, ["-version"], "FFmpeg"),
            _tool(settings.ffmpeg.ffprobe, ["-version"], "ffprobe"),
            _tool("uv", ["--version"], "uv"),
        ]
        tts_cfg = load_audio(settings.root).get("tts") or {}
        value = {
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "services": services,
            "tools": tools,
            "disk": [_disk(settings.root, "project"), _disk(settings.paths.models_root, "models")],
            "gpu": gpu
            or {
                "name": None,
                "vram_total_gib": None,
                "vram_free_gib": None,
                "source": None,
                "status": UNKNOWN,
                "detail": "ComfyUI 未运行，无法读取 XPU 显存；不以配置或设备管理器推测",
            },
            "llm_model": settings.llm.model,
            "comfyui_url": settings.comfyui.base_url,
            "tts_mode": str(tts_cfg.get("mode") or "zero_shot"),
            "tts_default_speaker": tts_cfg.get("default_speaker"),
        }
        _cache.update({"at": now, "value": value})
        return value
