"""Compare the Wan baseline (A) and the protected composite (B) on the same shot.

Metrics are deliberately simple and are not a substitute for watching the clip:

* boat / reflection dark-pixel area and centroid (rigidity check);
* tree-band high-frequency energy and frame-to-frame difference (flicker);
* cloud-band and static-mountain frame differences (local motion vs frozen).

Both inputs are expected to be 1080x1920 / 24 fps / the same duration. The Wan
output is upscaled first with the same Lanczos rule used by the production
master, so the comparison is like-for-like.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def frame(video: Path, at: float, out: Path) -> Path:
    import subprocess

    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(video),
         "-frames:v", "1", str(out)],
        check=True,
        capture_output=True,
    )
    return out


def region_box(box: list[float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    w, h = size
    return (int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))


def dark_stats(image: Image.Image, box: tuple[int, int, int, int]) -> dict:
    crop = image.crop(box).convert("L")
    px = crop.load()
    w, h = crop.size
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            if px[x, y] < 80:
                xs.append(x)
                ys.append(y)
    if not xs:
        return {"area": 0, "centroid": [None, None]}
    return {
        "area": len(xs),
        "area_ratio": round(len(xs) / (w * h), 4),
        "centroid": [round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2)],
    }


def band_stats(image: Image.Image, box: tuple[int, int, int, int]) -> dict:
    gray = image.crop(box).convert("L")
    blurred = gray.filter(ImageFilter.GaussianBlur(2))
    hf = ImageStat.Stat(ImageChops.difference(gray, blurred)).mean[0] / 255.0
    return {"high_frequency": round(hf, 4)}


def diff_value(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> float:
    return round(ImageStat.Stat(ImageChops.difference(a.crop(box), b.crop(box))).mean[0], 4)


def analyze(video: Path, out_dir: Path, duration: float,
            boat_box: list[float], reflection_box: list[float],
            cloud_box: list[float], tree_box: list[float], static_box: list[float],
            water_box: list[float]) -> dict:
    times = {"first": 0.1, "mid": duration / 2, "last": max(0.1, duration - 0.15)}
    images = {name: Image.open(frame(video, t, out_dir / f"{name}.png")).convert("RGB")
              for name, t in times.items()}
    size = images["first"].size
    boxes = {
        "boat": region_box(boat_box, size),
        "reflection": region_box(reflection_box, size),
        "cloud": region_box(cloud_box, size),
        "tree": region_box(tree_box, size),
        "static": region_box(static_box, size),
        "water": region_box(water_box, size),
    }
    result = {
        "video": rel(video),
        "size": list(size),
        "times": times,
        "boxes": {k: list(v) for k, v in boxes.items()},
        "boat": {name: dark_stats(images[name], boxes["boat"]) for name in times},
        "reflection": {name: dark_stats(images[name], boxes["reflection"]) for name in times},
        "tree": {name: band_stats(images[name], boxes["tree"]) for name in times},
        "tree_frame_diff": diff_value(images["first"], images["mid"], boxes["tree"]),
        "cloud_frame_diff": diff_value(images["first"], images["mid"], boxes["cloud"]),
        "static_frame_diff": diff_value(images["first"], images["mid"], boxes["static"]),
        "water_frame_diff": diff_value(images["first"], images["mid"], boxes["water"]),
        "frames": {name: rel(out_dir / f"{name}.png") for name in times},
    }
    diff = ImageChops.difference(images["first"], images["mid"]).point(lambda v: min(255, v * 5))
    diff_path = out_dir / "diff_first_mid_x5.png"
    diff.save(diff_path)
    result["diff"] = rel(diff_path)
    for name, image in images.items():
        image.crop(boxes["boat"]).resize((760, 420)).save(out_dir / f"crop_boat_{name}.png")
        image.crop(boxes["cloud"]).save(out_dir / f"crop_cloud_{name}.png")
        image.crop(boxes["tree"]).save(out_dir / f"crop_tree_{name}.png")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare Wan A and protected B")
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--boat-bbox", default="0.3125,0.7324,0.9549,0.887")
    parser.add_argument("--reflection-bbox", default="0.3125,0.887,0.9549,0.952")
    parser.add_argument("--cloud-box", default="0,0.46,1,0.63")
    parser.add_argument("--tree-box", default="0,0.65,1,0.80")
    parser.add_argument("--static-box", default="0.1,0.22,0.9,0.45")
    parser.add_argument("--water-box", default="0,0.80,1,1.0")
    args = parser.parse_args(argv)

    def nums(value: str) -> list[float]:
        return [float(x) for x in value.split(",")]

    out = (ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "a": analyze((ROOT / args.a).resolve(), out / "a", args.duration,
                     nums(args.boat_bbox), nums(args.reflection_bbox),
                     nums(args.cloud_box), nums(args.tree_box), nums(args.static_box),
                     nums(args.water_box)),
        "b": analyze((ROOT / args.b).resolve(), out / "b", args.duration,
                     nums(args.boat_bbox), nums(args.reflection_bbox),
                     nums(args.cloud_box), nums(args.tree_box), nums(args.static_box),
                     nums(args.water_box)),
        "note": "area/centroid in the boat box; high_frequency is normalized; diff values are 0-255",
    }
    (out / "compare.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "out": rel(out),
        "a_boat_area": {k: v["area"] for k, v in result["a"]["boat"].items()},
        "b_boat_area": {k: v["area"] for k, v in result["b"]["boat"].items()},
        "a_tree_diff": result["a"]["tree_frame_diff"],
        "b_tree_diff": result["b"]["tree_frame_diff"],
        "a_cloud_diff": result["a"]["cloud_frame_diff"],
        "b_cloud_diff": result["b"]["cloud_frame_diff"],
        "a_water_diff": result["a"]["water_frame_diff"],
        "b_water_diff": result["b"]["water_frame_diff"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
