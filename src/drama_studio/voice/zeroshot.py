"""Zero-shot TTS against the local CosyVoice runtime.

The runtime has no ``/inference_zero_shot``; zero-shot is ``POST /tts/upload``
with the reference wav as a form file. Two facts constrain everything here:

* ``prompt_text`` must match the reference audio **word for word**. The runtime
  falls back to a ``.txt`` sidecar next to the wav and refuses the request if
  neither exists.
* What the clone learns is the prompt's *delivery*, not only its timbre. A
  conversational reference produces conversational speech, whatever the text is.

The module never assumes a service is running (the caller owns the lifecycle)
and never routes localhost through a proxy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_BASE = "http://127.0.0.1:50000"
DEFAULT_TIMEOUT = 600.0


class ZeroShotError(RuntimeError):
    pass


@dataclass(frozen=True)
class ZeroShotResult:
    path: Path
    seconds: float
    synth_seconds: float
    sample_rate: int
    prompt: Path
    prompt_sha256: str
    prompt_text: str
    speed: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def healthy(base: str = DEFAULT_BASE) -> dict[str, Any] | None:
    """Runtime status, or None when nothing is listening."""
    try:
        with httpx.Client(timeout=5.0, trust_env=False) as client:
            response = client.get(base.rstrip("/") + "/health")
        if response.status_code != 200:
            return None
        return response.json()
    except httpx.HTTPError:
        return None


def synthesize(text: str, *, prompt_wav: Path, prompt_text: str, out_wav: Path,
               speed: float = 0.82, base: str = DEFAULT_BASE,
               timeout: float = DEFAULT_TIMEOUT,
               text_frontend: bool = True) -> ZeroShotResult:
    text = (text or "").strip()
    if not text:
        raise ZeroShotError("text is empty")
    prompt_wav = Path(prompt_wav)
    if not prompt_wav.is_file():
        raise ZeroShotError(f"参考音频不存在：{prompt_wav}")
    prompt_text = (prompt_text or "").strip()
    if not prompt_text:
        raise ZeroShotError("prompt_text 必填：必须与参考音频逐字一致，否则克隆会跑偏")

    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "text": text,
        "prompt_text": prompt_text,
        "speed": str(speed),
        "text_frontend": "true" if text_frontend else "false",
    }
    with prompt_wav.open("rb") as handle:
        files = {"prompt_wav": (prompt_wav.name, handle, "audio/wav")}
        try:
            with httpx.Client(timeout=timeout, trust_env=False) as client:
                response = client.post(base.rstrip("/") + "/tts/upload",
                                       data=data, files=files)
        except httpx.HTTPError as exc:
            raise ZeroShotError(f"CosyVoice 请求失败：{exc}") from exc

    if response.status_code != 200:
        raise ZeroShotError(f"CosyVoice 返回 {response.status_code}: {response.text[:600]}")

    out_wav.write_bytes(response.content)
    headers = response.headers
    return ZeroShotResult(
        path=out_wav,
        seconds=float(headers.get("X-Audio-Seconds") or 0.0),
        synth_seconds=float(headers.get("X-Synth-Seconds") or 0.0),
        sample_rate=int(headers.get("X-Sample-Rate") or 0),
        prompt=prompt_wav,
        prompt_sha256=sha256(prompt_wav),
        prompt_text=prompt_text,
        speed=speed,
    )


def record(result: ZeroShotResult, *, text: str, out_dir: Path,
           extra: dict[str, Any] | None = None) -> Path:
    """Write the provenance next to the audio: prompt hash, text, timings."""
    payload = {
        "stage": "voice.zeroshot",
        "text": text,
        "prompt": str(result.prompt),
        "prompt_sha256": result.prompt_sha256,
        "prompt_text": result.prompt_text,
        "speed": result.speed,
        "audio": str(result.path),
        "audio_sha256": sha256(result.path),
        "seconds": round(result.seconds, 3),
        "synth_seconds": round(result.synth_seconds, 3),
        "rtf": round(result.synth_seconds / max(result.seconds, 1e-6), 3),
        "sample_rate": result.sample_rate,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **(extra or {}),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "zeroshot.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
