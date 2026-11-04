"""Legacy per-shot scroll adapter (kept for the G3 experiments).

Production motion now goes through ``scripts/motion_build.py``, which adds
camera easing, local micro-motion and transitions. This script remains only to
reproduce the earlier S2/G3 scroll samples; do not add new features here.

Render per-shot G3 long-scroll clips from a shot list.

This is the production adapter between a storyboard's stills and the verified
S2 long-scroll composite (``scripts/s2_build.py``): same 1080x1920 / 24 fps
crop-window scroll, same silk-texture overlay, but one clip per shot at an
explicit duration and pan range.

It is style-driven: the style preset supplies the texture kind and opacity, and
the preset must declare ``scroll_pan`` as a compositing primitive.

Shot list (JSON)::

    {
      "shots": [
        {"id": "shot_001", "source": "path/to/still.png",
         "duration_seconds": 6.5, "pan_start_px": 0, "pan_end_px": 180}
      ]
    }

``pan_*_px`` are pixels inside the scaled canvas (height 1920); the pan range is
``scaled_width - 1080``. Output is ``<out-dir>/<id>.mp4`` (silent video; audio is
assembled later by ``scripts/r3_build.py``). Existing clips are skipped unless
``--force`` is given, so an interrupted run resumes.

Example:

    .venv\\Scripts\\python.exe scripts/scroll_shot.py ^
        --style court_green_fine_line ^
        --shots projects/<project>/episodes/<episode>/work/scroll_shots.json ^
        --out-dir projects/<project>/episodes/<episode>/work/clips
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from s2_build import H, W, black_frames, build_scroll, make_texture, rel, sample_frames, sha256
from drama_studio.config import find_project_root
from drama_studio.quality import check_video
from drama_studio.style_presets import load_style_presets

ROOT = find_project_root()


def _scaled_width(width: int, height: int) -> int:
    """Width after ``scale=-2:1920`` (aspect kept, rounded to an even integer)."""
    value = width * H / height
    even = int(round(value / 2.0)) * 2
    return max(2, even)


def render_shot(
    shot: dict,
    *,
    texture: Path,
    texture_opacity: float,
    out_dir: Path,
    force: bool,
) -> dict:
    source = (ROOT / shot["source"]).resolve() if not Path(shot["source"]).is_absolute() else Path(shot["source"])
    if not source.is_file():
        raise SystemExit(f"{shot['id']}: source not found: {source}")
    duration = float(shot["duration_seconds"])
    if duration <= 0:
        raise SystemExit(f"{shot['id']}: duration must be > 0")
    out = out_dir / f"{shot['id']}.mp4"

    with Image.open(source) as image:
        width, height = image.size
    scaled = _scaled_width(width, height)
    span = scaled - W
    if span <= 0:
        raise SystemExit(
            f"{shot['id']}: source {width}x{height} scales to {scaled}px wide; "
            f"no horizontal pan room for {W}px output"
        )
    start_px = float(shot.get("pan_start_px", 0))
    end_px = float(shot.get("pan_end_px", 0))
    for name, value in (("pan_start_px", start_px), ("pan_end_px", end_px)):
        if not 0.0 <= value <= span:
            raise SystemExit(f"{shot['id']}: {name}={value} outside pan range 0..{span}")
    pan_start, pan_end = start_px / span, end_px / span

    record = {
        "id": shot["id"],
        "source": rel(source),
        "source_sha256": sha256(source),
        "source_size": [width, height],
        "scaled_width": scaled,
        "pan_range_px": span,
        "duration_seconds": duration,
        "pan_start_px": start_px,
        "pan_end_px": end_px,
        "pan_start_fraction": round(pan_start, 6),
        "pan_end_fraction": round(pan_end, 6),
        "speed_px_s": round(abs(end_px - start_px) / duration, 3),
        "output": rel(out),
    }
    if out.is_file() and not force:
        record.update({"status": "skipped", "output_sha256": sha256(out), "bytes": out.stat().st_size})
        return record

    argv = build_scroll(
        source=source,
        texture=texture,
        out=out,
        duration=duration,
        texture_opacity=texture_opacity,
        pan_start=pan_start,
        pan_end=pan_end,
    )
    record.update({"status": "rendered", "argv": argv, "output_sha256": sha256(out), "bytes": out.stat().st_size})
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render per-shot G3 long-scroll clips")
    parser.add_argument("--style", required=True, help="style preset id")
    parser.add_argument("--shots", required=True, help="shot list JSON")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--texture-seed", type=int, default=7)
    parser.add_argument("--force", action="store_true", help="re-render existing clips")
    args = parser.parse_args(argv)

    preset = load_style_presets(ROOT).get(args.style)
    if "scroll_pan" not in preset.compositing.primitives:
        raise SystemExit(f"{preset.id}: preset does not declare scroll_pan")
    texture_kind = preset.compositing.texture.kind
    if texture_kind not in ("silk", "raw_paper"):
        raise SystemExit(f"{preset.id}: no renderable texture kind ({texture_kind})")

    shots_path = (ROOT / args.shots).resolve() if not Path(args.shots).is_absolute() else Path(args.shots)
    data = json.loads(shots_path.read_text(encoding="utf-8"))
    shots = data.get("shots") if isinstance(data, dict) else data
    if not isinstance(shots, list) or not shots:
        raise SystemExit("shot list must be a non-empty list (or {shots: [...]})")

    out_dir = (ROOT / args.out_dir).resolve() if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    texture = out_dir / f"texture_{texture_kind}.png"
    if not texture.is_file():
        make_texture(texture_kind, texture, seed=args.texture_seed)

    opacity = preset.compositing.texture.opacity
    records = []
    for shot in shots:
        record = render_shot(shot, texture=texture, texture_opacity=opacity, out_dir=out_dir, force=args.force)
        record["video_check"] = check_video(out_dir / f"{shot['id']}.mp4", expected_width=W, expected_height=H)
        record["black_frames"] = black_frames(out_dir / f"{shot['id']}.mp4")
        record["sample_frames"] = sample_frames(
            out_dir / f"{shot['id']}.mp4", out_dir / "frames" / shot["id"], float(shot["duration_seconds"])
        )
        records.append(record)
        print(
            json.dumps(
                {
                    "id": record["id"],
                    "status": record["status"],
                    "duration": record["duration_seconds"],
                    "pan_px": [record["pan_start_px"], record["pan_end_px"]],
                    "video": record["video_check"]["status"],
                    "black": len(record["black_frames"]["black_segments"]),
                },
                ensure_ascii=False,
            )
        )

    manifest = {
        "stage": "G3 per-shot scroll",
        "style_id": preset.id,
        "style_name": preset.name,
        "style_config": rel(ROOT / "config" / "styles.yaml"),
        "style_config_sha256": sha256(ROOT / "config" / "styles.yaml"),
        "texture": {"path": rel(texture), "sha256": sha256(texture), "kind": texture_kind, "opacity": opacity},
        "shots_file": rel(shots_path),
        "shots_file_sha256": sha256(shots_path),
        "shots": records,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path = out_dir / "scroll_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed = [
        r for r in records
        if r["video_check"]["status"] != "PASS" or r["black_frames"]["returncode"] != 0
    ]
    print(json.dumps({"manifest": rel(manifest_path), "shots": len(records), "failed": len(failed)}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
