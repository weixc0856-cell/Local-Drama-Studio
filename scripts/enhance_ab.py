"""Minimal A/B harness for the video enhancement layer.

It compares the production Lanczos path with the optional learned backends using
the same source clip and output settings. Missing executables or weights are
reported as NOT_RUN; the script never invents a result.

    .venv\\Scripts\\python.exe scripts\\enhance_ab.py ^
        --source projects/<id>/shots/S01/S01_clip.mp4 ^
        --out experiments/enhance_ab/S01
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from drama_studio.application.film.upscale import UpscaleError, available_backends, upscale_clip  # noqa: E402


def probe(path: Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate,duration:format=duration,size",
         "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return json.loads(proc.stdout or "{}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--shot", default=None)
    parser.add_argument("--tile", type=int, default=128)
    args = parser.parse_args()

    source = (ROOT / args.source).resolve() if not Path(args.source).is_absolute() else Path(args.source)
    out_dir = (ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    avail = available_backends()
    versions = [
        {"name": "lanczos", "backend": "lanczos", "model": None},
        {"name": "realesrnet", "backend": "realesrgan-ncnn", "model": "realesrnet-x4plus"},
        {"name": "realesrgan", "backend": "realesrgan-ncnn", "model": "realesrgan-x4plus"},
    ]
    results = []
    for version in versions:
        backend = version["backend"]
        record = {
            "name": version["name"],
            "backend": backend,
            "model": version["model"],
            "source": str(source),
            "source_sha256": None,
            "status": "NOT_RUN",
            "reason": None,
            "runtime_seconds": None,
            "output": None,
            "probe": None,
        }
        if not source.is_file():
            record["reason"] = f"source not found: {source}"
            results.append(record)
            continue
        record["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        if backend != "lanczos" and not avail["realesrgan-ncnn"]["available"]:
            record["reason"] = (
                "realesrgan-ncnn exe/weights not installed; set REALESRGAN_NCNN "
                "or install under D:/AI/tools/realesrgan-ncnn-vulkan")
            results.append(record)
            continue
        target = out_dir / f"{args.shot or source.stem}_{version['name']}_1080p.mp4"
        started = time.time()
        try:
            info = upscale_clip(
                source, target, backend=backend, width=1080, height=1920,
                denoise=(backend == "lanczos"), model=version["model"] or "realesrnet-x4plus",
                tile_size=args.tile,
            )
        except (UpscaleError, OSError) as exc:
            record["reason"] = str(exc)
            results.append(record)
            continue
        record.update({
            "status": "DONE",
            "runtime_seconds": round(time.time() - started, 2),
            "output": str(target.relative_to(ROOT)).replace("\\", "/"),
            "probe": probe(target),
            "settings": info,
        })
        results.append(record)

    report = {
        "schema_version": "1.0",
        "source": str(source.relative_to(ROOT)).replace("\\", "/") if source.is_relative_to(ROOT) else str(source),
        "source_probe": probe(source) if source.is_file() else None,
        "backends": avail,
        "versions": results,
        "note": "NOT_RUN 不是失败结论；没有权重/可执行文件时不得宣称学习型超分优于 Lanczos。",
    }
    path = out_dir / "ab_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "versions": [
        {"name": item["name"], "status": item["status"], "reason": item["reason"]}
        for item in results]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
