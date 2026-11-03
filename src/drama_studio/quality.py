"""Independent technical quality checks.

The build script already fails on FFmpeg errors, but that is not a quality gate.
This module inspects the produced files directly: image blankness, video decode,
duration/streams, and audio peak. A failed check marks the build FAILED; it never
rewrites or deletes the artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

PASS = "PASS"
FAIL = "FAIL"


class QualityError(RuntimeError):
    pass


def _result(ok: bool, **detail: Any) -> dict[str, Any]:
    return {"status": PASS if ok else FAIL, **detail}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_image(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _result(False, path=str(path), error="missing")
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            stat = ImageStat.Stat(image)
            mean = sum(stat.mean) / 3.0
            stddev = sum(stat.stddev) / 3.0
            width, height = image.size
    except Exception as exc:  # noqa: BLE001 - decode failure is a quality failure
        return _result(False, path=str(path), error=f"{type(exc).__name__}: {exc}")
    blank = stddev < 1.5
    black = mean < 4.0 and stddev < 3.0
    return _result(
        not blank and not black,
        path=str(path),
        width=width,
        height=height,
        mean=round(mean, 2),
        stddev=round(stddev, 2),
        blank=blank,
        black=black,
    )


def _ffprobe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,duration,channels,sample_rate",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if proc.returncode != 0:
        raise QualityError(proc.stderr.strip()[-800:])
    return json.loads(proc.stdout)


def check_video(
    path: Path,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> dict[str, Any]:
    if not path.is_file():
        return _result(False, path=str(path), error="missing")
    try:
        probe = _ffprobe(path)
    except (QualityError, ValueError, OSError) as exc:
        return _result(False, path=str(path), error=str(exc))
    streams = probe.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        return _result(False, path=str(path), error="no video stream")
    decode = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    duration = float((probe.get("format") or {}).get("duration") or 0)
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    size_ok = (expected_width is None or width == expected_width) and (
        expected_height is None or height == expected_height
    )
    return _result(
        decode.returncode == 0 and duration > 0 and size_ok,
        path=str(path),
        duration=round(duration, 3),
        width=width,
        height=height,
        has_audio=audio is not None,
        audio_codec=(audio or {}).get("codec_name"),
        decode_returncode=decode.returncode,
        decode_stderr=decode.stderr.strip()[-500:],
        size_ok=size_ok,
    )


def check_audio(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _result(False, path=str(path), error="missing")
    try:
        probe = _ffprobe(path)
    except (QualityError, ValueError, OSError) as exc:
        return _result(False, path=str(path), error=str(exc))
    stream = next((s for s in probe.get("streams") or [] if s.get("codec_type") == "audio"), None)
    if stream is None:
        return _result(False, path=str(path), error="no audio stream")
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    match = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", proc.stderr)
    max_volume = float(match.group(1)) if match else None
    clipped = max_volume is not None and max_volume >= -0.1
    return _result(
        proc.returncode == 0 and not clipped,
        path=str(path),
        sample_rate=stream.get("sample_rate"),
        channels=stream.get("channels"),
        duration=round(float((probe.get("format") or {}).get("duration") or 0), 3),
        max_volume_db=max_volume,
        clipped=clipped,
    )


def _infer_root(manifest_path: Path) -> Path:
    for parent in manifest_path.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "config").is_dir():
            return parent
    return Path.cwd()


def check_build(manifest_path: Path, *, root: Path | None = None) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    root = (root or _infer_root(manifest_path)).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = manifest.get("outputs") or {}

    def resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (root / path)

    checks: dict[str, Any] = {"manifest": str(manifest_path), "root": str(root)}
    final = resolve(outputs["final"]) if outputs.get("final") else None
    if final is None or not final.is_file():
        checks["final"] = _result(False, path=str(final), error="manifest has no existing final")
    else:
        checks["final"] = check_video(final, expected_width=1080, expected_height=1920)
        if outputs.get("final_sha256"):
            checks["final"]["sha256_ok"] = _sha256(final) == outputs["final_sha256"]

    images = []
    for segment in manifest.get("segments") or []:
        source = segment.get("source")
        if source:
            images.append(check_image(resolve(source)))
    if images:
        checks["images"] = images
    mixed = outputs.get("mixed")
    if mixed:
        checks["audio"] = check_audio(resolve(mixed))

    ok = checks["final"]["status"] == PASS
    ok = ok and all(item["status"] == PASS for item in images)
    ok = ok and checks["final"].get("sha256_ok", True)
    if "audio" in checks:
        ok = ok and checks["audio"]["status"] == PASS
    checks["status"] = PASS if ok else FAIL
    checks["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report_path = manifest_path.parent / "quality_report.json"
    report_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks["report"] = str(report_path)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="build_manifest.json of one render")
    parser.add_argument("--root", default=None, help="project root (default: infer)")
    args = parser.parse_args()
    try:
        result = check_build(
            Path(args.manifest),
            root=Path(args.root) if args.root else None,
        )
    except (OSError, ValueError, QualityError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": result["status"] == PASS, "report": result["report"]}, ensure_ascii=False))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
