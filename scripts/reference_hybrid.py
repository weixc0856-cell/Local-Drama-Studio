"""Turn a still-based segments.json into a hybrid Wan/still edit.

For every segment where ``<clips_dir>/<segment_id>.mp4`` exists, the clip is
trimmed or looped to the segment's planned duration and recorded as a video
source. Missing clips stay as images. This does not invent motion: it only
uses an actually generated Wan clip.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit(f"ffmpeg failed: {proc.stderr[-2000:]}")


def _probe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise SystemExit(f"cannot probe clip duration: {path}") from exc


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segments", required=True)
    parser.add_argument("--clips", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--ready-dir", default=None)
    parser.add_argument("--mode", choices=("stretch", "loop"), default="stretch",
                        help="stretch slows the clip to the segment duration; loop repeats it")
    args = parser.parse_args()
    segments_path = (ROOT / args.segments).resolve()
    clips_dir = (ROOT / args.clips).resolve()
    ready_dir = (ROOT / args.ready_dir).resolve() if args.ready_dir else clips_dir / "ready"
    ready_dir.mkdir(parents=True, exist_ok=True)
    segments = json.loads(segments_path.read_text(encoding="utf-8"))
    used = 0
    for seg in segments:
        clip = clips_dir / f"{seg['id']}.mp4"
        if not clip.is_file():
            continue
        duration = float(seg["duration"])
        ready = ready_dir / f"{seg['id']}.mp4"
        if args.mode == "stretch":
            source_duration = max(1e-6, _probe_duration(clip))
            factor = max(1.0, duration / source_duration)
            cmd = [
                "ffmpeg", "-y", "-v", "error", "-i", str(clip),
                "-vf", f"setpts={factor:.6f}*PTS,fps=24",
                "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-crf", "18",
                "-preset", "medium", "-pix_fmt", "yuv420p", str(ready),
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(clip),
                "-t", f"{duration:.3f}", "-an", "-c:v", "libx264", "-crf", "18",
                "-preset", "medium", "-pix_fmt", "yuv420p", str(ready),
            ]
        _run(cmd)
        seg["type"] = "video"
        seg["source"] = ready.relative_to(ROOT).as_posix()
        seg["sha256"] = _sha(ready)
        seg["hybrid_source"] = clip.relative_to(ROOT).as_posix()
        seg["hybrid_source_sha256"] = _sha(clip)
        used += 1
    out = (ROOT / args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(segments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "segments": len(segments), "video_shots": used,
                      "mode": args.mode, "out": str(out)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
