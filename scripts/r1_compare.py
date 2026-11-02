"""Build a visual consistency comparison sheet for R1.

Compares, for each theme, the reference image, the reference-assisted result
and the text-only result. Outputs a PNG contact sheet plus simple color
statistics. These statistics are descriptive only; they do not prove identity
or style consistency - the human review in the report is authoritative.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[1]
CELL = (384, 216)
THEMES = [
    ("flower", "J3", "J6"),
    ("boat", "J4", "J7"),
    ("dawn", "J5", "J8"),
]


def first_png(run_id: str) -> Path:
    run_dir = ROOT / "experiments" / "r1" / "runs" / run_id
    meta = run_dir / "job.json"
    if meta.is_file():
        data = json.loads(meta.read_text(encoding="utf-8"))
        outputs = [Path(o["path"]) for o in data.get("outputs", []) if Path(o["path"]).suffix.lower() == ".png"]
        if outputs:
            return outputs[0]
    pngs = sorted(run_dir.glob("*.png"))
    if not pngs:
        raise FileNotFoundError(f"no PNG in {run_dir}")
    return pngs[0]


def cell(path: Path, size=CELL) -> Image.Image:
    im = Image.open(path).convert("RGB")
    im.thumbnail(size, Image.LANCZOS)
    canvas = Image.new("RGB", size, (18, 22, 28))
    canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return canvas


def hist_signature(path: Path, bins: int = 16) -> list[float]:
    im = Image.open(path).convert("RGB")
    hist = im.histogram()
    values: list[float] = []
    per_channel = 256 // bins
    total = im.width * im.height
    for channel in range(3):
        base = channel * 256
        for b in range(bins):
            values.append(sum(hist[base + b * per_channel: base + (b + 1) * per_channel]) / total)
    return values


def hist_intersection(a: list[float], b: list[float]) -> float:
    # Each of the three channels sums to 1.0; normalize to 0..1.
    return round(sum(min(x, y) for x, y in zip(a, b)) / 3, 4)


def mean_rgb(path: Path) -> list[float]:
    return [round(v, 2) for v in ImageStat.Stat(Image.open(path).convert("RGB")).mean]


def main() -> int:
    ref = first_png("r1a_river_16x9")
    rows = []
    metrics = {}
    for theme, ref_job, text_job in THEMES:
        ref_path, text_path = first_png(ref_job), first_png(text_job)
        rows.append([(ref, "REF J2"), (ref_path, "REF-ASSISTED"), (text_path, "TEXT-ONLY")])
        metrics[theme] = {
            "reference_assisted": str(ref_path),
            "text_only": str(text_path),
            "mean_rgb": {"reference": mean_rgb(ref), "ref_assisted": mean_rgb(ref_path), "text_only": mean_rgb(text_path)},
            "hist_intersection": {
                "ref_vs_ref_assisted": hist_intersection(hist_signature(ref), hist_signature(ref_path)),
                "ref_vs_text_only": hist_intersection(hist_signature(ref), hist_signature(text_path)),
            },
        }

    width, height = CELL[0] * 3, CELL[1] * 3
    sheet = Image.new("RGB", (width, height + 22 * 3), (12, 16, 20))
    draw = ImageDraw.Draw(sheet)
    for r, row in enumerate(rows):
        y = r * (CELL[1] + 22) + 22
        draw.text((6, y - 16), f"{THEMES[r][0].upper()}", fill=(220, 230, 234))
        for c, (path, label) in enumerate(row):
            sheet.paste(cell(path), (c * CELL[0], y))
            draw.text((c * CELL[0] + 6, y + CELL[1] - 16), label, fill=(200, 210, 216))

    out = ROOT / "assets" / "visual_style" / "consistency_comparison.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)
    (out.with_suffix(".json")).write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
