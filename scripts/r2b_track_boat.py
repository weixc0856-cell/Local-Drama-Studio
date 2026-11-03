"""Track the dark boat silhouette in H3 frames.

Pure PIL + stdlib. The boat is a compact dark silhouette on brighter water; we
threshold a central ROI, take the largest connected component that does not
touch the ROI border, and report its centroid in full-frame pixels.

This is a heuristic. The report must also include human review of the
first/middle/last frames; the metric alone is not proof of subject motion.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

FRAME_RE = re.compile(r"^(.*)_(\d{5})_?\.png$", re.IGNORECASE)


def components(mask: list[list[bool]], w: int, h: int):
    seen = [[False] * w for _ in range(h)]
    out = []
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]:
                continue
            q = deque([(x, y)])
            seen[y][x] = True
            pts = []
            touches = False
            while q:
                cx, cy = q.popleft()
                pts.append((cx, cy))
                if cx in (0, w - 1) or cy in (0, h - 1):
                    touches = True
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            out.append({"area": len(pts), "touch": touches, "pts": pts})
    return out


def detect(path: Path, roi: tuple[float, float, float, float], threshold: int, sample_w: int = 256):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = (int(roi[0] * W), int(roi[1] * H), int(roi[2] * W), int(roi[3] * H))
    crop = im.crop((x0, y0, x1, y1))
    scale = sample_w / crop.width
    sh = max(1, round(crop.height * scale))
    small = crop.resize((sample_w, sh), Image.BILINEAR).convert("L")
    px = list(small.getdata())
    mask = [[px[y * sample_w + x] < threshold for x in range(sample_w)] for y in range(sh)]
    comps = [c for c in components(mask, sample_w, sh) if not c["touch"] and c["area"] >= 4]
    if not comps:
        return {"found": False, "threshold": threshold, "roi": [x0, y0, x1, y1]}
    comps.sort(key=lambda c: c["area"], reverse=True)
    best = comps[0]
    cx = sum(p[0] for p in best["pts"]) / best["area"]
    cy = sum(p[1] for p in best["pts"]) / best["area"]
    full_x = x0 + cx / scale
    full_y = y0 + cy / scale
    xs = [p[0] for p in best["pts"]]; ys = [p[1] for p in best["pts"]]
    return {
        "found": True,
        "threshold": threshold,
        "area_sample_px": best["area"],
        "bbox_sample": [min(xs), min(ys), max(xs), max(ys)],
        "centroid_frame_px": [round(full_x, 1), round(full_y, 1)],
        "roi_frame_px": [x0, y0, x1, y1],
        "frame_size": [W, H],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--threshold", type=int, default=45)
    parser.add_argument("--out-name", default="h3_boat_track")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    frames = sorted(p for p in run_dir.glob("*.png") if FRAME_RE.match(p.name))
    if not frames:
        raise SystemExit("no frames")
    # Central ROI where the boat sits in KF3.
    roi = (0.32, 0.45, 0.68, 0.72)
    samples = [0, len(frames) // 2, len(frames) - 1]
    results = []
    for idx in samples:
        det = detect(frames[idx], roi, args.threshold)
        det["frame_index"] = idx + 1
        det["file"] = frames[idx].name
        results.append(det)

    found = [r["centroid_frame_px"] for r in results if r.get("found")]
    displacement = None
    if len(found) >= 2:
        dx = found[-1][0] - found[0][0]
        dy = found[-1][1] - found[0][1]
        displacement = {"dx_px": round(dx, 1), "dy_px": round(dy, 1),
                        "magnitude_px": round((dx * dx + dy * dy) ** 0.5, 1)}

    # Background stability: compare a distant mountain patch (top band) first vs last.
    def patch_diff(a: Path, b: Path):
        ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        W, H = ia.size
        box = (int(0.05 * W), int(0.15 * H), int(0.35 * W), int(0.40 * H))
        da = ia.crop(box).resize((128, 72), Image.BILINEAR)
        db = ib.crop(box).resize((128, 72), Image.BILINEAR)
        return round(sum(ImageStat.Stat(ImageChops.difference(da, db)).mean) / 3, 3)

    payload = {
        "run_dir": str(run_dir),
        "frame_count": len(frames),
        "roi_fraction": list(roi),
        "threshold": args.threshold,
        "samples": results,
        "boat_displacement_first_to_last": displacement,
        "background_patch_mean_abs_diff_first_vs_last": patch_diff(frames[0], frames[-1]),
        "note": "Heuristic dark-blob tracking. Confirm with human review; background diff is descriptive.",
    }
    (run_dir / f"{args.out_name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Annotated montage of first/middle/last.
    ims = []
    for r in results:
        im = Image.open(run_dir / r["file"]).convert("RGB").resize((512, 288), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        if r.get("found"):
            x, y = r["centroid_frame_px"]
            sx, sy = x * 512 / r["frame_size"][0], y * 288 / r["frame_size"][1]
            d.ellipse((sx - 10, sy - 10, sx + 10, sy + 10), outline=(255, 80, 80), width=2)
        d.text((8, 8), f"frame {r['frame_index']}", fill=(255, 255, 255))
        ims.append(im)
    sheet = Image.new("RGB", (512, 288 * len(ims)), (10, 10, 10))
    for i, im in enumerate(ims):
        sheet.paste(im, (0, i * 288))
    sheet.save(run_dir / f"{args.out_name}.png")
    print(json.dumps({k: payload[k] for k in ("boat_displacement_first_to_last",
        "background_patch_mean_abs_diff_first_vs_last", "samples")}, ensure_ascii=False)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
