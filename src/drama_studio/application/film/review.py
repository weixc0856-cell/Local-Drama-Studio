"""Contact sheets for H2 keyframe review and H3 clip review."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from drama_studio.application.film.assets import latest_output, resolve_asset
from drama_studio.domain.film.schemas import Storyboard

CELL_W, CELL_H = 288, 512
LABEL_H = 34
PAD = 8
COLS = 4
SAMPLE_POINTS = (0.1, 0.5, 0.9)


def build_contact_sheet(project_root: Path, storyboard: Storyboard, out_path: Path) -> Path:
    shots = storyboard.shots
    rows = (len(shots) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CELL_W + PAD * (COLS + 1),
                              rows * (CELL_H + LABEL_H) + PAD * (rows + 1)), (22, 22, 22))
    draw = ImageDraw.Draw(sheet)
    for index, shot in enumerate(shots):
        row, col = divmod(index, COLS)
        left = PAD + col * (CELL_W + PAD)
        top = PAD + row * (CELL_H + LABEL_H + PAD)
        path = latest_output(project_root / "assets" / "keyframes" / shot.shot_id, shot.shot_id)
        if path is not None:
            with Image.open(path) as raw:
                thumb = raw.convert("RGB").resize((CELL_W, CELL_H), Image.LANCZOS)
            sheet.paste(thumb, (left, top + LABEL_H))
        else:
            draw.rectangle([left, top + LABEL_H, left + CELL_W, top + CELL_H + LABEL_H],
                           outline=(120, 60, 60), width=2)
            draw.text((left + 8, top + LABEL_H + 8), "MISSING", fill=(220, 120, 120))
        label = f"{shot.shot_id}  {shot.shot_size.value}  {shot.camera.move.value}  {shot.duration_seconds:.0f}s"
        draw.text((left, top + 6), label, fill=(235, 235, 235))
        draw.text((left, top + 18), shot.scene_id, fill=(150, 150, 150))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path


def _sample_frames(clip: Path, points: tuple[float, ...]) -> list[Image.Image]:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(clip)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    duration = float(probe.stdout.strip() or 0.0)
    frames: list[Image.Image] = []
    with tempfile.TemporaryDirectory() as directory:
        for index, point in enumerate(points):
            target = Path(directory) / f"{index}.png"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, duration * point):.3f}",
                 "-i", str(clip), "-frames:v", "1", str(target)],
                check=True,
            )
            with Image.open(target) as raw:
                frames.append(raw.convert("RGB").copy())
    return frames


def build_clip_contact_sheet(project_root: Path, storyboard: Storyboard, out_path: Path) -> Path:
    """One row per shot: first / middle / last frame of the actual clip.

    This is the H3 review sheet. It uses the clip that will enter the build, not
    the keyframe, so a static shot is immediately visible as three identical
    frames.
    """
    rows = len(storyboard.shots)
    cell = CELL_W // 2
    height = CELL_H // 2
    sheet = Image.new("RGB", (3 * cell + PAD * 4, rows * (height + LABEL_H) + PAD),
                      (22, 22, 22))
    draw = ImageDraw.Draw(sheet)
    for index, shot in enumerate(storyboard.shots):
        top = PAD // 2 + index * (height + LABEL_H)
        asset = resolve_asset(project_root, shot.shot_id)
        label = f"{shot.shot_id}  {asset.kind if asset else 'MISSING'}  {shot.camera.move.value}"
        draw.text((PAD // 2, top), label, fill=(235, 235, 235))
        frames: list[Image.Image] = []
        if asset is not None and asset.kind == "video" and asset.path is not None:
            frames = _sample_frames(asset.path, SAMPLE_POINTS)
        elif asset is not None and asset.kind == "image" and asset.path is not None:
            with Image.open(asset.path) as raw:
                frames = [raw.convert("RGB")] * 3
        if not frames:
            draw.text((PAD // 2, top + LABEL_H + 8), "NO CLIP", fill=(220, 120, 120))
            continue
        for col, frame in enumerate(frames[:3]):
            thumb = frame.resize((cell, height), Image.LANCZOS)
            sheet.paste(thumb, (PAD // 2 + col * cell, top + LABEL_H))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path
