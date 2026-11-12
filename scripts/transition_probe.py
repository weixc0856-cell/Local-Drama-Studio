"""Technical probe for the four transition types on two synthetic clips.

This is a validation harness, not a second renderer: it calls the same
``make_masks`` / ``render_transition`` used by the production motion sequence.
Synthetic solid clips make mask leakage and black frames obvious; they are not
style samples.

Usage::

    .venv\\Scripts\\python.exe scripts\\transition_probe.py --out experiments/mv/transition
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from drama_studio.config import find_project_root
from drama_studio.domain.motion.spec import TransitionSpec
from drama_studio.application.motion.transition import make_masks, render_transition

ROOT = find_project_root()
W, H, FPS = 1080, 1920, 24
LEFT_RGB = (176, 44, 38)
RIGHT_RGB = (30, 68, 120)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(cmd) + "\n" + proc.stderr[-2000:])
    return proc


def _clip(path: Path, color: str, seconds: float) -> None:
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
          "-i", f"color=c={color}:s={W}x{H}:d={seconds}:r={FPS}",
          "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18", str(path)])


def _frame(video: Path, at: float, out: Path) -> Image.Image:
    _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(video),
          "-frames:v", "1", str(out)])
    return Image.open(out).convert("RGB")


def _mean(image: Image.Image) -> tuple[int, int, int]:
    pixels = list(image.resize((64, 64)).getdata())
    count = len(pixels)
    return tuple(round(sum(pixel[index] for pixel in pixels) / count) for index in range(3))  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe transition types on synthetic clips")
    parser.add_argument("--out", default="experiments/mv/transition")
    parser.add_argument("--duration", type=float, default=1.2)
    args = parser.parse_args(argv)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = (ROOT / args.out / f"build-{stamp}").resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    left = out_dir / "left.mp4"
    right = out_dir / "right.mp4"
    _clip(left, "0xB02C26", 3.0)
    _clip(right, "0x1E4478", 3.0)

    records = []
    failed = []
    for kind in ("crossfade", "ink_dissolve", "ink_reveal", "ink_spread"):
        spec = TransitionSpec(type=kind, duration_s=args.duration, feather=0.12,
                              direction="ltr", seed=13)
        mask_info = None
        mask_dir = out_dir / f"masks_{kind}"
        if kind != "crossfade":
            mask_info = make_masks(spec, mask_dir, spec.duration_s, FPS)
        output = out_dir / f"transition_{kind}.mp4"
        result = render_transition(left, right, output, spec, mask_dir, fps=FPS)
        argv = result["argv"]
        probe = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-show_entries", "stream=r_frame_rate",
                      "-of", "json", str(output)])
        probed = json.loads(probe.stdout)
        duration = float(probed["format"]["duration"])
        rate = str((probed.get("streams") or [{}])[0].get("r_frame_rate") or "0/1")
        fps_ok = rate == f"{FPS}/1"
        black = subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(output),
             "-vf", "blackdetect=d=0.1:pix_th=0.10", "-an", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        black_hits = [line for line in black.stderr.splitlines() if "black_start" in line]
        start = _mean(_frame(output, 0.0, out_dir / f"{kind}_start.png"))
        mid = _mean(_frame(output, duration / 2, out_dir / f"{kind}_mid.png"))
        end = _mean(_frame(output, max(0.0, duration - 0.05), out_dir / f"{kind}_end.png"))
        checks = {
            "duration_ok": abs(duration - args.duration) <= 0.12,
            "fps_ok": fps_ok,
            "no_black": not black_hits,
            "starts_left": sum(abs(a - b) for a, b in zip(start, LEFT_RGB)) < 80,
            "ends_right": sum(abs(a - b) for a, b in zip(end, RIGHT_RGB)) < 80,
            "mid_is_mixed": start != mid and end != mid,
            "colour_planes_stable": all(0 <= v <= 255 for v in mid),
            "no_maskedmerge": "maskedmerge" not in " ".join(argv),
        }
        ok = all(checks.values())
        records.append({
            "type": kind,
            "output": str(output.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "duration": round(duration, 3),
            "fps": rate,
            "algorithm": result["algorithm"],
            "timing": result["timing"],
            "colour_check": result["colour"],
            "mask": mask_info,
            "mean_start": start,
            "mean_mid": mid,
            "mean_end": end,
            "black_segments": black_hits,
            "checks": checks,
            "ok": ok,
            "argv": argv,
        })
        if not ok:
            failed.append(kind)
        print(json.dumps({"type": kind, "ok": ok, "mid": mid, "checks": checks}, ensure_ascii=False))

    manifest = {
        "stage": "transition_probe",
        "left": {"path": str(left.relative_to(ROOT)).replace("\\", "/"), "rgb": LEFT_RGB},
        "right": {"path": str(right.relative_to(ROOT)).replace("\\", "/"), "rgb": RIGHT_RGB},
        "fps": FPS,
        "records": records,
        "failed": failed,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = out_dir / "transition_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(path.relative_to(ROOT)).replace("\\", "/"),
                      "failed": failed}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
