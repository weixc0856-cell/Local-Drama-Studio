"""Contact sheet for H2 keyframe review."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .assets import latest_output
from .schemas import Storyboard

CELL_W, CELL_H = 288, 512
LABEL_H = 34
PAD = 8
COLS = 4


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
