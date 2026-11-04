"""M0 visual failure audit: measure motion, flicker, style jumps and tail drift.

This is an audit tool, not a production gate. It reads existing videos and stills
and writes a new directory; it never modifies the samples it inspects.

It deliberately reuses the measurement helpers in ``scripts/compare_motion.py``
(dark-silhouette stats, band high-frequency energy, frame differences) and adds
the time-series that the earlier three-point comparison could not show:

* per-frame luma for the whole frame and for authored regions;
* frame-to-frame difference and cut positions;
* local flicker energy (second difference + sign flips);
* dark-object centroid / bbox path (boat drift and scale);
* changed-area coverage inside a region (sliding layer vs local motion);
* per-shot Lab mean and Delta-E between shots (style continuity);
* tail brightness trend (last fraction of the clip).

All thresholds live in ``THRESHOLDS`` and every flag carries the measured value,
so a human can disagree with the rule without re-measuring.

Example:

    .venv\\Scripts\\python.exe scripts\\visual_audit.py ^
        --spec experiments/audit/M0/audit_spec.json ^
        --out experiments/audit/M0
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from compare_motion import dark_stats

ROOT = Path(__file__).resolve().parents[1]

# Audit thresholds. These are evidence filters, not aesthetic acceptance criteria.
THRESHOLDS = {
    "flicker_residual_std": 0.60,      # luma residual after removing the linear trend
    "flicker_oscillation": 0.30,       # fraction of residual steps that reverse direction
    "region_brightness_drift": 3.0,    # max-min luma inside a region during one shot
    "region_drift_monotonic": 0.85,    # rise/drop ratio that makes a drift one-directional
    "tail_drop_luma": 4.0,             # last window vs preceding window
    "tail_slope_luma_per_s": -0.25,    # linear slope over the tail window
    "shot_luma_mismatch": 10.0,        # mean luma difference between adjacent shots
    "style_delta_e": 12.0,             # CIE76 between shot means
    "style_chroma_ratio": 1.5,         # chroma ratio between shots
    "style_chroma_abs": 3.0,           # ... only when the absolute chroma also changes
    "motion_insufficient_diff": 0.20,  # mean frame difference 0-255
    "object_drift_pct_width_per_s": 1.0,  # centroid path length per second, % of width
    "cut_spike_ratio": 3.0,            # diff relative to the local median
    "cut_min_diff": 5.0,
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(cmd) + "\n"
                           + proc.stderr.decode("utf-8", "replace")[-2000:])
    return proc


def decode_frames(video: Path, width: int = 270, height: int = 480) -> list[Image.Image]:
    """Decode every frame at audit resolution (grayscale)."""
    proc = run(["ffmpeg", "-v", "error", "-i", str(video),
                "-vf", f"scale={width}:{height}:flags=area,format=gray",
                "-f", "rawvideo", "-"])
    size = width * height
    data = proc.stdout
    return [Image.frombytes("L", (width, height), data[i:i + size])
            for i in range(0, len(data) - size + 1, size)]


def decode_frames_rgb(video: Path, width: int = 270, height: int = 480) -> list[Image.Image]:
    proc = run(["ffmpeg", "-v", "error", "-i", str(video),
                "-vf", f"scale={width}:{height}:flags=area,format=rgb24",
                "-f", "rawvideo", "-"])
    size = width * height * 3
    data = proc.stdout
    return [Image.frombytes("RGB", (width, height), data[i:i + size])
            for i in range(0, len(data) - size + 1, size)]


def box_px(box: list[float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    w, h = size
    return (max(0, int(box[0] * w)), max(0, int(box[1] * h)),
            min(w, int(box[2] * w)), min(h, int(box[3] * h)))


def luma_series(frames: list[Image.Image], box: list[float] | None = None) -> list[float]:
    out = []
    for frame in frames:
        crop = frame if box is None else frame.crop(box_px(box, frame.size))
        out.append(round(ImageStat.Stat(crop).mean[0], 3))
    return out


def diff_series(frames: list[Image.Image]) -> list[float]:
    out = [0.0]
    for prev, cur in zip(frames, frames[1:]):
        out.append(round(ImageStat.Stat(ImageChops.difference(prev, cur)).mean[0], 3))
    return out


def linear_slope(values: list[float], fps: float) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return round((num / den) * fps, 4)


def fit_line(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        return 0.0, values[0] if values else 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    slope = num / den if den else 0.0
    return slope, mean_y - slope * mean_x


def flicker(values: list[float], fps: float = 24.0) -> dict:
    """Separate a slow drift from oscillation.

    A slow camera push or a one-way layer drift changes the mean but leaves a
    small residual after the linear trend is removed. Real flicker leaves a
    large residual and reverses direction often.
    """
    n = len(values)
    if n < 4:
        return {"residual_std": 0.0, "oscillation": 0.0, "range": 0.0,
                "slope_luma_per_s": 0.0, "max_step": 0.0,
                "monotonic_rise_ratio": 0.0, "monotonic_drop_ratio": 0.0}
    slope, intercept = fit_line(values)
    residual = [v - (slope * i + intercept) for i, v in enumerate(values)]
    residual_std = math.sqrt(sum(r * r for r in residual) / n)
    steps = [residual[i] - residual[i - 1] for i in range(1, n)]
    flips = 0
    for a, b in zip(steps, steps[1:]):
        if a == 0 or b == 0:
            continue
        if (a > 0) != (b > 0):
            flips += 1
    raw_steps = [values[i] - values[i - 1] for i in range(1, n)]
    rises = sum(1 for v in raw_steps if v > 0)
    drops = sum(1 for v in raw_steps if v < 0)
    return {
        "residual_std": round(residual_std, 4),
        "oscillation": round(flips / max(1, len(steps) - 1), 4),
        "range": round(max(values) - min(values), 4),
        "slope_luma_per_s": round(slope * fps, 4),
        "max_step": round(max(abs(v) for v in raw_steps), 4),
        "monotonic_rise_ratio": round(rises / len(raw_steps), 4),
        "monotonic_drop_ratio": round(drops / len(raw_steps), 4),
    }


def _components(mask: list[list[bool]], width: int, height: int) -> list[dict]:
    from collections import deque
    seen = [[False] * width for _ in range(height)]
    out = []
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or seen[y][x]:
                continue
            queue = deque([(x, y)])
            seen[y][x] = True
            points = []
            touches = False
            while queue:
                cx, cy = queue.popleft()
                points.append((cx, cy))
                if cx in (0, width - 1) or cy in (0, height - 1):
                    touches = True
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        queue.append((nx, ny))
            out.append({"area": len(points), "touch": touches, "pts": points})
    return out


def track_dark(frames: list[Image.Image], box: list[float],
               threshold: int = 75, sample_width: int = 128) -> dict:
    """Track the largest compact dark silhouette inside the search box.

    Reuses the connected-component rule from ``scripts/r2b_track_boat.py``:
    the boat is a compact dark blob on brighter water; a component that touches
    the search border is usually waterline or bank, so it is deprioritised.
    """
    path = []
    for index, frame in enumerate(frames):
        crop = frame.crop(box_px(box, frame.size))
        scale = sample_width / crop.width
        small = crop.resize((sample_width, max(1, round(crop.height * scale))),
                            Image.BILINEAR)
        width, height = small.size
        data = list(small.getdata())
        mask = [[data[y * width + x] < threshold for x in range(width)]
                for y in range(height)]
        comps = [c for c in _components(mask, width, height) if c["area"] >= 6]
        inner = [c for c in comps if not c["touch"]]
        pool = inner or comps
        if not pool:
            path.append({"frame": index, "found": False, "dark_ratio": 0.0})
            continue
        best = max(pool, key=lambda c: c["area"])
        cx = sum(q[0] for q in best["pts"]) / best["area"]
        cy = sum(q[1] for q in best["pts"]) / best["area"]
        luma = sum(data[q[1] * width + q[0]] for q in best["pts"]) / best["area"]
        full_x = box[0] * frame.width + cx / scale
        full_y = box[1] * frame.height + cy / scale
        path.append({
            "frame": index, "found": True,
            "centroid": [round(full_x, 2), round(full_y, 2)],
            "area_ratio": round(best["area"] / (width * height), 4),
            "silhouette_luma": round(luma, 2),
            "touches_border": best["touch"],
        })
    found = [q for q in path if q["found"]]
    if len(found) < 2:
        return {"found_frames": len(found), "path": path}
    xs = [q["centroid"][0] for q in found]
    ys = [q["centroid"][1] for q in found]
    lengths = [math.hypot(b["centroid"][0] - a["centroid"][0],
                          b["centroid"][1] - a["centroid"][1])
               for a, b in zip(found, found[1:])]
    lumas = [q["silhouette_luma"] for q in found]
    width = frames[0].width
    return {
        "found_frames": len(found),
        "silhouette_threshold": threshold,
        "search_box": box,
        "start": found[0]["centroid"],
        "end": found[-1]["centroid"],
        "x_span": round(max(xs) - min(xs), 2),
        "y_span": round(max(ys) - min(ys), 2),
        "path_length": round(sum(lengths), 2),
        "path_length_pct_width": round(sum(lengths) / width * 100, 3),
        "max_step_pct_width": round(max(lengths) / width * 100, 3),
        "area_ratio_start": found[0]["area_ratio"],
        "area_ratio_end": found[-1]["area_ratio"],
        "area_ratio_range": round(max(q["area_ratio"] for q in found)
                                  - min(q["area_ratio"] for q in found), 4),
        "silhouette_luma": {"start": lumas[0], "end": lumas[-1],
                            "range": round(max(lumas) - min(lumas), 2)},
        "path": path if len(path) <= 400 else path[::max(1, len(path) // 400)],
    }


def changed_coverage(frames: list[Image.Image], box: list[float],
                     pixel_threshold: int = 6) -> dict:
    """Fraction of pixels in a region that change at any point; max accumulated change."""
    crop_box = box_px(box, frames[0].size)
    acc = None
    for prev, cur in zip(frames, frames[1:]):
        d = ImageChops.difference(prev.crop(crop_box), cur.crop(crop_box))
        acc = d if acc is None else ImageChops.lighter(acc, d)
    if acc is None:
        return {"coverage": 0.0, "max_pixel_diff": 0}
    hist = acc.histogram()
    total = sum(hist)
    changed = sum(hist[pixel_threshold:])
    return {
        "coverage": round(changed / total, 4),
        "max_pixel_diff": max(i for i, v in enumerate(hist) if v),
        "mean_pixel_diff": round(sum(i * v for i, v in enumerate(hist)) / total, 3),
    }


def srgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    def lin(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def color_stats(frames: list[Image.Image]) -> dict:
    """Mean Lab and chroma of a decoded-frame list."""
    sample = frames[::max(1, len(frames) // 24)] or frames[:1]
    pixels = []
    for frame in sample:
        stat = ImageStat.Stat(frame)
        pixels.append(stat.mean)
    rgb = tuple(sum(p[i] for p in pixels) / len(pixels) for i in range(3))
    lab = srgb_to_lab(rgb)
    chroma = math.hypot(lab[1], lab[2])
    return {"rgb": [round(v, 2) for v in rgb],
            "lab": [round(v, 2) for v in lab],
            "chroma": round(chroma, 2)}


def delta_e(a: list[float], b: list[float]) -> float:
    return round(math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))), 3)


def cut_positions(diffs: list[float], fps: float) -> list[dict]:
    """A cut is a spike well above the clip's own frame-difference baseline.

    A steady scroll produces a large but constant difference every frame; it is
    not a cut. Only local maxima above both the baseline and an absolute floor count.
    """
    if len(diffs) < 5:
        return []
    hits = []
    window = 12
    for index, value in enumerate(diffs):
        lo, hi = max(1, index - window), min(len(diffs), index + window + 1)
        neighbours = sorted(diffs[lo:hi])
        median = neighbours[len(neighbours) // 2] if neighbours else 0.0
        local_max = value >= max(diffs[lo:hi]) if hi > lo else True
        floor = max(THRESHOLDS["cut_spike_ratio"] * max(median, 1e-6),
                    THRESHOLDS["cut_min_diff"])
        if value >= THRESHOLDS["cut_min_diff"] and local_max and value > floor:
            hits.append({"frame": index, "seconds": round(index / fps, 3),
                         "diff": value, "local_median": round(median, 3)})
    return hits


def frames_at(video: Path, times: list[float], out_dir: Path, prefix: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, at in enumerate(times):
        path = out_dir / f"{prefix}_{index:02d}_{at:.2f}s.png"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, at):.3f}",
             "-i", str(video), "-frames:v", "1", str(path)])
        paths.append(path)
    return paths


def contact_sheet(images: list[tuple[str, Path]], out: Path, tile_w: int = 270) -> None:
    opened = []
    for label, path in images:
        im = Image.open(path).convert("RGB")
        h = max(1, round(im.height * tile_w / im.width))
        opened.append((label, im.resize((tile_w, h)), h))
    tile_h = max(h for _, _, h in opened)
    sheet = Image.new("RGB", (tile_w * len(opened), tile_h + 24), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, im, _) in enumerate(opened):
        sheet.paste(im, (index * tile_w, 24))
        draw.text((index * tile_w + 4, 5), label, fill="black")
    sheet.save(out)


def region_crops(frames: dict[str, Path], regions: list[dict], out_dir: Path) -> list[str]:
    """first/mid/last crop per authored region, tiled into one sheet per region."""
    written = []
    for region in regions:
        if not region.get("crops", True):
            continue
        tiles = []
        for name, path in frames.items():
            im = Image.open(path).convert("RGB")
            box = box_px(region["box"], im.size)
            crop = im.crop(box)
            target_h = 300
            crop = crop.resize((max(1, round(crop.width * target_h / crop.height)), target_h))
            tiles.append((f"{region['id']} {name}", crop))
        width = sum(t.width for _, t in tiles)
        sheet = Image.new("RGB", (width, 324), "white")
        draw = ImageDraw.Draw(sheet)
        x = 0
        for label, tile in tiles:
            sheet.paste(tile, (x, 24))
            draw.text((x + 4, 5), label, fill="black")
            x += tile.width
        path = out_dir / f"region_{region['id']}.png"
        sheet.save(path)
        written.append(rel(path))
    return written


def anomaly_sheet(video: Path, diff: list[float], fps: float, out_dir: Path,
                  name: str, count: int = 3) -> list[str]:
    ranked = sorted(range(1, len(diff)), key=lambda i: diff[i], reverse=True)[:count]
    written = []
    for rank, index in enumerate(ranked):
        at = max(0.0, (index - 1) / fps)
        pair = frames_at(video, [at, index / fps], out_dir, f"{name}_anomaly{rank}")
        prev = Image.open(pair[0]).convert("L")
        cur = Image.open(pair[1]).convert("L")
        diff_img = ImageChops.difference(prev, cur).point(lambda v: min(255, v * 8))
        out = out_dir / f"{name}_anomaly{rank}_diff_x8.png"
        diff_img.save(out)
        contact_sheet([("before", pair[0]), ("after", pair[1]),
                       ("diff x8", out)],
                      out_dir / f"{name}_anomaly{rank}_sheet.png", tile_w=300)
        written.append(rel(out_dir / f"{name}_anomaly{rank}_sheet.png"))
    return written


def line_chart(series: dict[str, list[float]], out: Path, fps: float,
               width: int = 1000, height: int = 360) -> None:
    """Small Pillow-only luma timeline so a human can see drift vs flicker."""
    colors = ["#111111", "#C0392B", "#1F6FB2", "#2E8B57", "#B8860B", "#7D3C98"]
    values = [v for s in series.values() for v in s]
    lo, hi = min(values), max(values)
    span = max(1.0, hi - lo)
    pad = 36
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([pad, pad, width - pad, height - pad], outline="#999999")
    draw.text((pad + 4, 6), f"luma timeline  min {lo:.1f}  max {hi:.1f}  (0-255)",
              fill="black")
    for index, (name, vals) in enumerate(series.items()):
        color = colors[index % len(colors)]
        n = max(1, len(vals) - 1)
        points = []
        for i, value in enumerate(vals):
            x = pad + (width - 2 * pad) * i / n
            y = height - pad - (height - 2 * pad) * (value - lo) / span
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=2)
        draw.text((pad + 6 + index * 130, height - pad + 8), f"{name}", fill=color)
    # second/vertical grid every 5 s
    seconds = len(next(iter(series.values()))) / fps
    step = 5.0 if seconds > 12 else 1.0
    t = 0.0
    while t < seconds:
        x = pad + (width - 2 * pad) * (t / max(0.001, seconds))
        draw.line([(x, pad), (x, height - pad)], fill="#E5E5E5")
        draw.text((x + 2, pad - 14), f"{t:.0f}s", fill="#777777")
        t += step
    canvas.save(out)


def analyze_sample(sample: dict, out_root: Path) -> dict:
    video = (ROOT / sample["video"]).resolve()
    sample_dir = out_root / "samples" / sample["id"]
    sample_dir.mkdir(parents=True, exist_ok=True)
    gray = decode_frames(video)
    rgb = decode_frames_rgb(video)
    if not gray:
        raise RuntimeError(f"{sample['id']}: no frames decoded from {video}")
    fps = float(sample.get("fps", 24))
    duration = len(gray) / fps

    diffs = diff_series(gray)
    global_luma = luma_series(gray)
    result = {
        "id": sample["id"],
        "video": rel(video),
        "kind": sample.get("kind", ""),
        "style_id": sample.get("style_id", ""),
        "note": sample.get("note", ""),
        "fps": fps,
        "frames": len(gray),
        "duration_seconds": round(duration, 3),
        "global_luma": {
            "first": global_luma[0], "mid": global_luma[len(global_luma) // 2],
            "last": global_luma[-1], "min": min(global_luma), "max": max(global_luma),
            "mean": round(sum(global_luma) / len(global_luma), 3),
        },
        "frame_diff": {
            "mean": round(sum(diffs) / len(diffs), 4),
            "max": max(diffs), "max_at_seconds": round(diffs.index(max(diffs)) / fps, 3),
            "cuts": cut_positions(diffs, fps),
        },
        "color": color_stats(rgb),
        "shots": [],
        "regions": [],
        "flags": [],
    }

    shots = sample.get("shots") or [{"id": "whole", "start_s": 0.0,
                                      "end_s": duration, "camera": ""}]
    for index, shot in enumerate(shots):
        start = int(round(float(shot["start_s"]) * fps))
        end = min(len(gray), int(round(float(shot["end_s"]) * fps)))
        astart = int(round(float(shot.get("analysis_start_s", shot["start_s"])) * fps))
        aend = min(len(gray), int(round(float(shot.get("analysis_end_s", shot["end_s"])) * fps)))
        seg_gray = gray[start:end]
        ana_gray = gray[astart:aend]
        ana_rgb = rgb[astart:aend]
        if not seg_gray or len(ana_gray) < 3:
            continue
        seg_diff = diff_series(seg_gray)
        shot_luma = luma_series(seg_gray)
        ana_luma = luma_series(ana_gray)
        record = {
            "id": shot.get("id", f"shot_{index + 1:03d}"),
            "start_s": shot["start_s"], "end_s": shot["end_s"],
            "analysis_window_s": [round(astart / fps, 3), round(aend / fps, 3)],
            "camera": shot.get("camera", ""),
            "luma": {"first": shot_luma[0], "mid": shot_luma[len(shot_luma) // 2],
                     "last": shot_luma[-1], "mean": round(sum(shot_luma) / len(shot_luma), 3),
                     "min": min(shot_luma), "max": max(shot_luma)},
            "analysis_luma_mean": round(sum(ana_luma) / len(ana_luma), 3),
            "frame_diff_mean": round(sum(seg_diff) / len(seg_diff), 4),
            "frame_diff_max": max(seg_diff),
            "color": color_stats(ana_rgb),
        }
        times = [float(shot["start_s"]), (float(shot["start_s"]) + float(shot["end_s"])) / 2,
                 max(float(shot["start_s"]), float(shot["end_s"]) - 0.15)]
        frame_paths = frames_at(video, times, sample_dir / "frames",
                                record["id"])
        record["sample_frames"] = [{"at": round(t, 3), "path": rel(q)}
                                   for t, q in zip(times, frame_paths)]
        sheet = sample_dir / f"{record['id']}_first_mid_last.png"
        contact_sheet([("first", frame_paths[0]), ("mid", frame_paths[1]),
                       ("last", frame_paths[2])], sheet)
        record["sheet"] = rel(sheet)
        record["frame_paths"] = frame_paths
        result["shots"].append(record)

    # per-author-region time series, split per shot so the cut does not pollute
    # flicker. The largest segment is promoted for a one-line summary.
    segments = [(r["id"], int(round(r["analysis_window_s"][0] * fps)),
                 min(len(gray), int(round(r["analysis_window_s"][1] * fps))),
                 r["camera"]) for r in result["shots"]]
    for region in sample.get("regions", []):
        entry = {"id": region["id"], "box": region["box"],
                 "role": region.get("role", ""), "segments": []}
        best = None
        for shot_id, start, end, camera in segments:
            if region.get("shots") and shot_id not in region["shots"]:
                continue
            seg = gray[start:end]
            if len(seg) < 3:
                continue
            series = luma_series(seg, region["box"])
            stats = flicker(series)
            coverage = changed_coverage(seg, region["box"])
            item = {
                "shot": shot_id,
                "luma": {"first": series[0], "mid": series[len(series) // 2],
                         "last": series[-1], "min": min(series), "max": max(series),
                         "mean": round(sum(series) / len(series), 3)},
                "flicker": stats,
                "changed_area": coverage,
                "luma_series": [round(v, 2) for v in series],
            }
            entry["segments"].append(item)
            if best is None or stats["residual_std"] > best["flicker"]["residual_std"]:
                best = item
            camera_moving = camera not in ("static", "")
            item["isolates_local_motion"] = not camera_moving
            if not camera_moving and stats["residual_std"] >= THRESHOLDS["flicker_residual_std"] and                     stats["oscillation"] >= THRESHOLDS["flicker_oscillation"] and                     stats["range"] >= 1.5:
                result["flags"].append({
                    "flag": "region_flicker",
                    "region": region["id"],
                    "shot": shot_id,
                    "value": stats,
                    "threshold": {"residual_std": THRESHOLDS["flicker_residual_std"],
                                  "oscillation": THRESHOLDS["flicker_oscillation"]},
                })
            directional = max(stats["monotonic_rise_ratio"], stats["monotonic_drop_ratio"])
            if not camera_moving and stats["range"] >= THRESHOLDS["region_brightness_drift"] and                     directional >= THRESHOLDS["region_drift_monotonic"] and                     abs(stats["slope_luma_per_s"]) >= 0.10:
                result["flags"].append({
                    "flag": "region_brightness_drift",
                    "region": region["id"],
                    "shot": shot_id,
                    "value": stats,
                    "threshold": {"range": THRESHOLDS["region_brightness_drift"],
                                  "directional": THRESHOLDS["region_drift_monotonic"]},
                })
        if not entry["segments"]:
            continue
        entry["luma"] = best["luma"]
        entry["flicker"] = best["flicker"]
        entry["changed_area"] = best["changed_area"]
        entry["worst_segment"] = best["shot"]
        result["regions"].append(entry)

    tracking = sample.get("object_tracking")
    if tracking:
        entry = {"id": tracking["id"], "search_box": tracking["search_box"],
                 "boxes_by_shot": tracking.get("boxes_by_shot", {}), "segments": []}
        for shot_id, start, end, camera in segments:
            seg = gray[start:end]
            if len(seg) < 3:
                continue
            search = tracking.get("boxes_by_shot", {}).get(shot_id,
                                                           tracking["search_box"])
            item = track_dark(seg, search)
            item["shot"] = shot_id
            item["isolates_local_motion"] = camera in ("static", "")
            seconds = max(0.1, len(seg) / fps)
            item["drift_pct_width_per_s"] = round(
                item.get("path_length_pct_width", 0.0) / seconds, 3)
            entry["segments"].append(item)
            if camera in ("static", "") and                     item.get("drift_pct_width_per_s", 0) > THRESHOLDS["object_drift_pct_width_per_s"]:
                result["flags"].append({
                    "flag": "rigid_object_drift",
                    "object": tracking["id"],
                    "shot": shot_id,
                    "value": {"path_length_pct_width": item["path_length_pct_width"],
                              "drift_pct_width_per_s": item["drift_pct_width_per_s"],
                              "x_span": item["x_span"], "y_span": item["y_span"],
                              "silhouette_luma": item.get("silhouette_luma")},
                    "threshold": THRESHOLDS["object_drift_pct_width_per_s"],
                })
        result["object_tracking"] = entry

    # style continuity between consecutive shots
    if len(result["shots"]) > 1:
        pairs = []
        for prev, cur in zip(result["shots"], result["shots"][1:]):
            de = delta_e(prev["color"]["lab"], cur["color"]["lab"])
            ratio = round(cur["color"]["chroma"] / max(0.01, prev["color"]["chroma"]), 3)
            chroma_abs = abs(cur["color"]["chroma"] - prev["color"]["chroma"])
            pair = {"from": prev["id"], "to": cur["id"], "delta_e": de,
                    "chroma_ratio": ratio, "chroma_abs": round(chroma_abs, 3),
                    "luma_delta": round(cur["luma"]["mean"] - prev["luma"]["mean"], 3)}
            pairs.append(pair)
            if de > THRESHOLDS["style_delta_e"] or (
                    ratio > THRESHOLDS["style_chroma_ratio"]
                    and chroma_abs > THRESHOLDS["style_chroma_abs"]):
                pair["flag"] = "style_jump"
                result["flags"].append({
                    "flag": "style_jump", "pair": [prev["id"], cur["id"]],
                    "value": {"delta_e": de, "chroma_ratio": ratio,
                              "chroma_abs": round(chroma_abs, 3)},
                    "threshold": {"delta_e": THRESHOLDS["style_delta_e"],
                                  "chroma_ratio": THRESHOLDS["style_chroma_ratio"],
                                  "chroma_abs": THRESHOLDS["style_chroma_abs"]},
                })
            if abs(pair["luma_delta"]) >= THRESHOLDS["shot_luma_mismatch"]:
                result["flags"].append({
                    "flag": "shot_luma_mismatch", "pair": [prev["id"], cur["id"]],
                    "value": {"luma_delta": pair["luma_delta"]},
                    "threshold": THRESHOLDS["shot_luma_mismatch"],
                })
        result["shot_continuity"] = pairs

    # tail brightness trend over the last window, excluding a deliberate fade-out
    fade_seconds = float(sample.get("fade_out_seconds", 0.0))
    fade_frames = min(max(0, len(global_luma) - 2), int(round(fade_seconds * fps)))
    analysis_luma = global_luma[:len(global_luma) - fade_frames] if fade_frames > 0         else global_luma
    tail_fraction = float(sample.get("tail_fraction", 0.25))
    tail_start = int(len(analysis_luma) * (1 - tail_fraction))
    tail = analysis_luma[tail_start:]
    before = analysis_luma[max(0, tail_start - len(tail)):tail_start]
    if tail and before:
        slope = linear_slope(tail, fps)
        drop = round(sum(before) / len(before) - sum(tail) / len(tail), 3)
        result["tail"] = {
            "fade_out_seconds_excluded": round(fade_frames / fps, 3),
            "window_seconds": round(len(tail) / fps, 3),
            "mean_before": round(sum(before) / len(before), 3),
            "mean_tail": round(sum(tail) / len(tail), 3),
            "drop_luma": drop,
            "slope_luma_per_s": slope,
            "monotonic_drop_ratio": round(
                sum(1 for x, y in zip(tail, tail[1:]) if y < x) / max(1, len(tail) - 1), 3),
        }
        if drop >= THRESHOLDS["tail_drop_luma"] and                 slope <= THRESHOLDS["tail_slope_luma_per_s"]:
            result["flags"].append({
                "flag": "tail_darkening",
                "value": {"drop_luma": drop, "slope_luma_per_s": slope},
                "threshold": {"drop_luma": THRESHOLDS["tail_drop_luma"],
                              "slope_luma_per_s": THRESHOLDS["tail_slope_luma_per_s"]},
            })

    if result["frame_diff"]["mean"] < THRESHOLDS["motion_insufficient_diff"]:
        result["flags"].append({
            "flag": "motion_insufficient",
            "value": {"frame_diff_mean": result["frame_diff"]["mean"]},
            "threshold": THRESHOLDS["motion_insufficient_diff"],
        })

    # region crop sheets use the first/mid/last full-resolution frames of shot 1
    if result["shots"]:
        base = result["shots"][0]["frame_paths"]
        frames = {"first": base[0], "mid": base[1], "last": base[2]}
        result["region_sheets"] = region_crops(frames, sample.get("regions", []),
                                               sample_dir)

    result["global_luma_series"] = [round(v, 2) for v in global_luma]
    chart_series = {"global": global_luma}
    for region in result["regions"]:
        if region["segments"]:
            chart_series[region["id"]] = region["segments"][0]["luma_series"]
    chart = sample_dir / "luma_timeline.png"
    line_chart(chart_series, chart, fps)
    result["luma_timeline"] = rel(chart)
    result["anomaly_sheets"] = anomaly_sheet(video, diffs, fps, sample_dir,
                                             sample["id"])
    for shot in result["shots"]:
        shot.pop("frame_paths", None)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M0 visual failure audit")
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    spec_path = args.spec if args.spec.is_absolute() else ROOT / args.spec
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out_root = (args.out if args.out.is_absolute() else ROOT / args.out)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = out_root / f"run-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)

    samples = []
    for sample in spec["samples"]:
        print(json.dumps({"auditing": sample["id"]}, ensure_ascii=False), flush=True)
        samples.append(analyze_sample(sample, run_dir))

    audit = {
        "stage": "M0.visual_failure_audit",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec": rel(spec_path),
        "thresholds": THRESHOLDS,
        "environment": {
            "ffmpeg": run(["ffmpeg", "-version"]).stdout.decode("utf-8", "replace").splitlines()[0],
            "pillow_only": True,
            "note": "audit only; no sample is modified",
        },
        "samples": samples,
        "summary": {
            "samples": len(samples),
            "flags": {flag: sum(1 for s in samples for f in s["flags"] if f["flag"] == flag)
                      for flag in sorted({f["flag"] for s in samples for f in s["flags"]})},
        },
    }
    audit_path = run_dir / "visual_failure_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print(json.dumps({"audit": rel(audit_path), "summary": audit["summary"],
                      "run_dir": rel(run_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
