"""M8-A: hand-authored three-plane 2.5D parallax experiment.

This is an **experiment tool**, not a production backend. It does not modify
``drama_studio``, does not change any formal region/plate contract, and does not
touch the production quality gates. Everything it writes goes to
``experiments/m8_parallax``.

The question it answers: on the same still, does a layered parallax push-in read
noticeably better than the existing single-plane 2D push?

Three planes, authored here rather than inferred by a model:

``bg``   the whole painting with two holes repaired (boat+reflection, right tree)
``mid``  the lone boat with mast, rigging and its reflection, kept rigid together
``fg``   the right foreground bare tree, which sits on near-white water

A fourth plane (the lower-left tree and bank) is deliberately **not** cut: its
surroundings are textured bank, so removing it would need invented content. It
stays baked into ``bg`` and the report records that limitation.

Layer transport follows one projective camera: each plane gets the exact scale
of an object at depth ratio ``alpha`` under the same dolly,

    s_bg  = 1 / (1 - u)
    s_i   = 1 / (1 - u / alpha_i)

so the planes cannot drift apart or invent their own motion, and ``u(t)`` carries
the style's easing.

Usage::

    .venv\\Scripts\\python.exe scripts\\m8_parallax.py layers
    .venv\\Scripts\\python.exe scripts\\m8_parallax.py render --variant B
    .venv\\Scripts\\python.exe scripts\\m8_parallax.py metrics
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drama_studio.paths import output_root, output_path
OUT = output_path("experiments/m8_parallax")
PLAN = OUT / "plan" / "layers.json"
LAYERS = OUT / "layers"
RENDERS = OUT / "renders"

W, H, FPS = 1080, 1920, 24
DURATION = 6.0
SOURCE = output_path("experiments/m7_final/ink/work/images/shot_001/out.png")
ASSET_PATH = OUT.parent / "m8_plates" / "assets" / "fg_reeds.png"
STYLE_ID = "ink_wash"

# ---------------------------------------------------------------- layer plan
# All boxes are normalized [x0, y0, x1, y1] on the 576x1024 source.
DEFAULT_PLAN: dict = {
    "note": (
        "M8-A 手工三层。盒子与阈值是人按画面内容手写的，不是模型推断。"
        "左前景（土坡上的枯树与山石）刻意不切：其背后是纹理土坡，切开会变成编造。"
    ),
    "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
    "source_size": [576, 1024],
    "fps": FPS,
    "duration_seconds": DURATION,
    "style_id": STYLE_ID,
    "camera": {
        "focus": [0.5, 0.48],
        "easing": "ease_in_out",
        "push_rate_per_s": 0.008,
        "scale_min": 1.03,
        "scale_max": 1.06,
        "note": "与 config/styles.yaml ink_wash camera 策略一致；B/C 复用 A 解析出的同一相机",
    },
    # depth ratio alpha = plane distance / background distance. alpha=1 is the
    # background itself. Values are authored judgement, recorded for review.
    "planes": [
        {"id": "bg", "alpha": 1.00, "z_order": 0},
        {"id": "mid", "alpha": 0.70, "z_order": 1},
        {"id": "fg", "alpha": 0.49, "z_order": 2},
    ],
    "regions": {
        "boat": {
            "role": "rigid_object",
            "roi": [0.30, 0.455, 0.632, 0.612],
            "luma_hi": 212.0,
            "luma_lo": 196.0,
            "dilate_px": 9,
            "blur_px": 3.0,
            "exclude": [[0.585, 0.452, 0.632, 0.505], [0.290, 0.430, 0.425, 0.472]],
            "reflection_band": [0.545, 0.616],
            "reflection_x": [0.30, 0.615],
            "reflection_feather_px": 14.0,
            "note": "船体+桅杆+缆绳为刚体；倒影以软带并入同层，随船平移，不独立运动",
        },
        "tree": {
            "role": "independent_overlay",
            "roi": [0.618, 0.650, 1.0, 1.0],
            "luma_hi": 210.0,
            "luma_lo": 186.0,
            "dilate_px": 2,
            "blur_px": 1.6,
            "exclude": [[0.600, 0.860, 0.780, 1.0]],
            "note": "右侧前景枯枝；压在近白水面上，补底为水面，不是编造结构",
        },
    },
    "inpaint_radii": [8, 4, 2],
}


def plan() -> dict:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def write_plan(data: dict) -> None:
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def px(box: list[float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    w, h = size
    return (
        max(0, int(round(box[0] * w))),
        max(0, int(round(box[1] * h))),
        min(w, int(round(box[2] * w))),
        min(h, int(round(box[3] * h))),
    )


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------------- masks
def luma_alpha(gray: Image.Image, box: tuple[int, int, int, int],
               lo: float, hi: float) -> Image.Image:
    """Soft alpha where the ink is darker than ``hi``; full below ``lo``."""
    x0, y0, x1, y1 = box
    crop = gray.crop(box)
    src = crop.load()
    out = Image.new("L", crop.size, 0)
    dst = out.load()
    span = max(1.0, hi - lo)
    for y in range(crop.height):
        for x in range(crop.width):
            value = src[x, y]
            if value <= lo:
                dst[x, y] = 255
            elif value < hi:
                dst[x, y] = int(round(255 * smoothstep((hi - value) / span)))
    full = Image.new("L", gray.size, 0)
    full.paste(out, (x0, y0))
    return full


def cut_boxes(alpha: Image.Image, boxes: list[list[float]], feather: int = 4) -> Image.Image:
    for box in boxes:
        x0, y0, x1, y1 = px(box, alpha.size)
        hole = Image.new("L", alpha.size, 0)
        hole.paste(255, (x0, y0, x1, y1))
        hole = hole.filter(ImageFilter.GaussianBlur(feather))
        alpha = ImageChops.subtract(alpha, hole)
    return alpha


def band_alpha(size: tuple[int, int], band: list[float], x_range: list[float],
               feather: float, x_feather: float = 0.02,
               top_soft: float = 0.0) -> Image.Image:
    """Soft rectangle: vertical band inside ``x_range``, all edges feathered."""
    w, h = size
    y0, y1 = int(round(band[0] * h)), int(round(band[1] * h))
    x0, x1 = int(round(x_range[0] * w)), int(round(x_range[1] * w))
    fx = max(1.0, x_feather * w)
    alpha = Image.new("L", size, 0)
    draw = alpha.load()
    for y in range(max(0, y0), min(h, y1)):
        top = 1.0 if y >= y0 + top_soft else (y - y0) / max(1.0, top_soft)
        bottom = min(1.0, (y1 - y) / max(1.0, feather))
        vy = smoothstep(top) * smoothstep(bottom)
        if vy <= 0:
            continue
        for x in range(max(0, x0), min(w, x1)):
            vx = smoothstep(min(1.0, (x - x0) / fx, (x1 - x) / fx))
            value = int(round(255 * vy * vx))
            if value:
                draw[x, y] = value
    return alpha


def dilate(alpha: Image.Image, px_value: int) -> Image.Image:
    if px_value <= 0:
        return alpha
    return alpha.filter(ImageFilter.MaxFilter(px_value * 2 + 1))


def row_fill(image: Image.Image, mask: Image.Image) -> Image.Image:
    """Fill each masked horizontal run from the clean pixels at its two ends.

    Water in this painting is horizontally near-uniform, so a per-row ramp
    between the nearest clean pixels is the faithful continuation of the paint
    rather than a fabricated texture. Runs that touch the frame border have only
    one side; they take that side's colour and are smoothed afterwards.
    """
    width, height = image.size
    src = image.load()
    mask_px = mask.load()
    out = image.copy()
    dst = out.load()
    open_rows = []
    for y in range(height):
        x = 0
        touched_border = False
        while x < width:
            if mask_px[x, y] == 0:
                x += 1
                continue
            start = x
            while x < width and mask_px[x, y] > 0:
                x += 1
            end = x - 1
            left = src[start - 1, y] if start > 0 else None
            right = src[end + 1, y] if end < width - 1 else None
            if left is not None and right is not None:
                span = end - start + 2
                for offset in range(start, end + 1):
                    p = (offset - start + 1) / span
                    dst[offset, y] = tuple(
                        int(round(left[c] + (right[c] - left[c]) * p)) for c in range(3))
            else:
                source = left if left is not None else right
                touched_border = True  # no right neighbour: constant extension
                for offset in range(start, end + 1):
                    dst[offset, y] = source
        if touched_border:
            open_rows.append(y)
    return out


def inpaint(image: Image.Image, mask: Image.Image, radii: list[int]) -> Image.Image:
    """Repair the holes in a painting without inventing structure.

    Two stages: a per-row ramp from real water on both sides, then a short
    multi-scale diffusion limited to the mask (radii are small on purpose, so
    distant paint cannot bleed into a raised bank). No mirroring, no tiling, no
    stamped texture.
    """
    filled = row_fill(image, mask)
    out = Image.composite(filled, image, mask.filter(ImageFilter.GaussianBlur(3)))
    for radius in radii:
        blurred = out.filter(ImageFilter.GaussianBlur(radius))
        out = Image.composite(blurred, out, mask)
    return out


# ------------------------------------------------------------------- layers
def build_layers(rebuild: bool = False) -> dict:
    if PLAN.is_file() and not rebuild:
        data = plan()
    else:
        data = DEFAULT_PLAN
        write_plan(data)

    LAYERS.mkdir(parents=True, exist_ok=True)
    source = ROOT / data["source"]
    image = Image.open(source).convert("RGB")
    gray = image.convert("L")
    size = image.size

    boat_cfg = data["regions"]["boat"]
    tree_cfg = data["regions"]["tree"]

    boat_ink = luma_alpha(gray, px(boat_cfg["roi"], size), boat_cfg["luma_lo"], boat_cfg["luma_hi"])
    boat_ink = cut_boxes(boat_ink, boat_cfg.get("exclude", []))
    boat_ink = dilate(boat_ink, int(boat_cfg["dilate_px"])).filter(
        ImageFilter.GaussianBlur(float(boat_cfg["blur_px"])))

    band_weight = band_alpha(size, boat_cfg["reflection_band"], boat_cfg["reflection_x"],
                             feather=float(boat_cfg["reflection_feather_px"]),
                             x_feather=0.03, top_soft=10.0)
    # Provisional hole: ink plus the whole reflection band. The plate is built
    # from this (a superset), so the plate is clean under everything the boat
    # layer can later uncover.
    hole0 = ImageChops.lighter(boat_ink, band_weight)

    tree_alpha = luma_alpha(gray, px(tree_cfg["roi"], size), tree_cfg["luma_lo"], tree_cfg["luma_hi"])
    tree_alpha = cut_boxes(tree_alpha, tree_cfg.get("exclude", []))
    tree_alpha = dilate(tree_alpha, int(tree_cfg["dilate_px"])).filter(
        ImageFilter.GaussianBlur(float(tree_cfg["blur_px"])))
    # No fade at the frame border: a plane that scales up about a focus inside
    # the frame pushes its own cut edges off-canvas, so a border fade would only
    # erase real trunk against the repaired plate.
    hole = ImageChops.lighter(hole0, tree_alpha)
    plate = inpaint(image, hole, [int(r) for r in data["inpaint_radii"]])

    # The reflection is taken from the real paint, not from a rectangle: where
    # the clean plate is lighter than the original, the original holds the
    # smear. That keeps the boat's reflection alpha on the strokes themselves
    # and leaves the pier and open water out of the moving layer.
    darkness = ImageChops.subtract(plate.convert("L"), gray)
    reflection = darkness.point(
        lambda v: 255 if v >= 26 else int(round(255 * smoothstep(v / 26.0))))
    reflection = reflection.filter(ImageFilter.GaussianBlur(3))
    reflection = ImageChops.multiply(reflection, band_weight)
    boat_alpha = ImageChops.lighter(boat_ink, reflection)

    # RGB under the transparent part of a cutout carries the plate colour, so a
    # bicubic resample of the layer cannot pull a wrong colour into the edge.
    boat_rgb = Image.composite(image, plate, boat_alpha)
    tree_rgb = Image.composite(image, plate, tree_alpha)

    outputs = {}
    for name, rgba in (
        ("bg_plate", plate.convert("RGBA")),
        ("mid_boat", boat_rgb.convert("RGBA")),
        ("fg_tree", tree_rgb.convert("RGBA")),
    ):
        if name == "mid_boat":
            rgba.putalpha(boat_alpha)
        elif name == "fg_tree":
            rgba.putalpha(tree_alpha)
        path = LAYERS / f"{name}.png"
        rgba.save(path)
        outputs[name] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "size": list(size)}

    for name, mask in (("mask_boat", boat_alpha), ("mask_tree", tree_alpha),
                       ("mask_hole", hole), ("mask_boat_ink", boat_ink)):
        mask.save(LAYERS / f"{name}.png")

    # Preview: the three planes stacked, and a zoom on each repaired area.
    stacked = plate.copy()
    stacked.paste(boat_rgb, (0, 0), boat_alpha)
    stacked.paste(tree_rgb, (0, 0), tree_alpha)
    stacked.save(LAYERS / "preview_stacked.png")
    for name, box in (("preview_boat", (0.20, 0.44, 0.72, 0.66)),
                      ("preview_tree", (0.55, 0.62, 1.0, 1.0))):
        x0, y0, x1, y1 = px(box, size)
        crop = stacked.crop((x0, y0, x1, y1))
        crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
        crop.save(LAYERS / f"{name}.png")

    coverage = {}
    for key, mask in (("boat", boat_alpha), ("tree", tree_alpha)):
        stat = ImageStat.Stat(mask)
        coverage[key] = {
            "alpha_coverage": round(stat.mean[0] / 255.0, 5),
            "bbox": mask.getbbox(),
        }

    record = {
        "stage": "m8a.layers",
        "source": data["source"],
        "source_size": list(size),
        "plan": str(PLAN.relative_to(ROOT)).replace("\\", "/"),
        "outputs": outputs,
        "coverage": coverage,
        "hole_coverage": round(ImageStat.Stat(hole).mean[0] / 255.0, 5),
        "known_limitations": [
            "左前景（左下枯树、土坡、山石）留在 bg，不做视差：其背后是纹理土坡，切开会变成编造内容",
            "bg 的两处补全是多尺度扩散填充，非镜像/平铺；可见范围由 reveal 指标量化",
            "mid 的倒影带并入船层刚性平移，未做独立形变（C 变体在层内单独加倒影扰动）",
        ],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (LAYERS / "layers.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


# ------------------------------------------------------------------ camera
def ease(name: str, p: float) -> float:
    p = max(0.0, min(1.0, p))
    if name == "linear":
        return p
    if name == "ease_in":
        return p * p
    if name == "ease_out":
        return 1.0 - (1.0 - p) * (1.0 - p)
    return p * p * (3.0 - 2.0 * p)


def camera_curve(cfg: dict, duration: float) -> dict:
    rate = float(cfg["push_rate_per_s"])
    s_end = min(float(cfg["scale_max"]), max(float(cfg["scale_min"]), 1.0 + rate * duration))
    return {
        "scale_start": 1.0,
        "scale_end": s_end,
        "u_end": 1.0 - 1.0 / s_end,
        "focus": tuple(cfg["focus"]),
        "easing": cfg["easing"],
    }


def plane_scale(curve: dict, alpha: float, t: float, duration: float) -> float:
    u = curve["u_end"] * ease(curve["easing"], t / duration)
    if alpha >= 1.0:
        return 1.0 / (1.0 - u)
    return 1.0 / (1.0 - u / alpha)


def camera_map(s: float, focus: tuple[float, float]) -> tuple[float, float, float]:
    """Window origin and size for a camera at scale ``s`` (same rule as affine_scale)."""
    window = 1.0 / s
    x0 = min(max(focus[0] - 0.5 * window, 0.0), 1.0 - window)
    y0 = min(max(focus[1] - 0.5 * window, 0.0), 1.0 - window)
    return x0, y0, window


def map_point(point: tuple[float, float], s: float,
              focus: tuple[float, float]) -> tuple[float, float]:
    """Where a scene point lands on screen under the same camera."""
    x0, y0, window = camera_map(s, focus)
    return ((point[0] - x0) / window, (point[1] - y0) / window)


def affine_scale(image: Image.Image, s: float, focus: tuple[float, float],
                 out_size: tuple[int, int]) -> Image.Image:
    """Sample the plate like production's ``zoompan`` does.

    The visible window is ``1/s`` of the plate, centred on ``focus`` and then
    clamped to the plate, exactly like ``x = max(0, min(iw-iw/zoom, ...))``.
    A pure scale about the focus is *not* the same camera: it drifts the window
    by ``(F - 0.5)/s`` and would put B/C on a different dolly than A whenever
    the focus is off centre.
    """
    lw, lh = image.size
    ow, oh = out_size
    window = 1.0 / s
    fx, fy = focus
    x0 = min(max(fx - 0.5 * window, 0.0), 1.0 - window)
    y0 = min(max(fy - 0.5 * window, 0.0), 1.0 - window)
    return image.transform(
        (ow, oh), Image.AFFINE,
        (window * lw / ow, 0.0, x0 * lw, 0.0, window * lh / oh, y0 * lh),
        resample=Image.BICUBIC)


# ------------------------------------------------------------------ render
def upscale_layer(path: Path, factor: int = 2) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    return image.resize((image.width * factor, image.height * factor), Image.LANCZOS)


def water_mask(size: tuple[int, int], boat_roi: list[float]) -> Image.Image:
    """Open water only: not the banks, the buildings, or the boat.

    Authored from the painting's layout. A ripple must never drive a bank or a
    building; that whole-frame leak is exactly what M0 recorded as F3.
    """
    mask = band_alpha(size, (0.495, 0.975), (0.0, 1.0),
                      feather=0.06 * size[1], x_feather=0.0, top_soft=0.05 * size[1])
    mask = cut_boxes(mask, [
        [0.00, 0.780, 0.520, 1.000],   # lower-left bank, tree, rocks
        [0.800, 0.730, 1.000, 1.000],  # lower-right bank and rocks
        [0.560, 0.440, 0.930, 0.610],  # shore buildings and pier
        [boat_roi[0] - 0.02, boat_roi[1] - 0.02, boat_roi[2] + 0.02, boat_roi[3] + 0.02],
    ], feather=10)
    return mask.resize((size[0] // 4, size[1] // 4), Image.LANCZOS)


def uncovered_stats(hole: Image.Image, cover: Image.Image) -> dict:
    """How much of the repaired plate the moving plane fails to cover.

    Alpha is treated as coverage, not as a binary mask: a soft edge that slips
    by half a pixel is not a hole, so the measurement weights each pixel by the
    hole's alpha times the uncovered fraction. Binarising a feathered alpha
    would report the ramp contour as a defect.
    """
    leak = ImageChops.multiply(hole, ImageChops.invert(cover))
    total = leak.width * leak.height
    histogram = leak.histogram()
    weighted = sum(index * count for index, count in enumerate(histogram))
    hard = leak.point(lambda v: 255 if v > 127 else 0)
    hard_count = sum(hard.histogram()[1:])
    width_run = 0
    bbox = hard.getbbox()
    if hard_count and bbox:
        for y in range(bbox[1], bbox[3]):
            row = hard.crop((0, y, leak.width, y + 1)).tobytes()
            width_run = max(width_run, max(len(run) for run in row.split(b"\x00")))
    return {
        "leak_weighted_px": round(weighted / 255.0, 2),
        "leak_fraction": round(weighted / 255.0 / total, 8),
        "hard_uncovered_px": hard_count,
        "max_row_run_px": width_run,
    }


def render_variant(variant: str, data: dict, curve: dict, force: bool = False) -> dict:
    started = time.time()
    out_dir = RENDERS / variant
    frame_dir = out_dir / "frames"
    if frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir(parents=True, exist_ok=True)

    duration = float(data["duration_seconds"])
    frames = max(1, int(round(duration * FPS)))
    planes = {item["id"]: item for item in data["planes"]}

    bg = upscale_layer(LAYERS / "bg_plate.png")
    mid = upscale_layer(LAYERS / "mid_boat.png")
    fg = upscale_layer(LAYERS / "fg_tree.png")
    mask_l = Image.open(LAYERS / "mask_boat.png").convert("L")
    mask_l = mask_l.resize((mask_l.width * 2, mask_l.height * 2), Image.LANCZOS)
    hole_plane = Image.merge("RGBA", (mask_l, mask_l, mask_l, mask_l))

    if variant in ("D", "E"):
        # Control variants: the untouched still, one plane. D adds exactly the
        # same local micro-motion C uses; E adds none (the renderer's own baseline).
        # local micro-motion C uses. Splits "layers" from "ripple" as causes.
        base = Image.open(ROOT / data["source"]).convert("RGBA")
        bg = base.resize((base.width * 2, base.height * 2), Image.LANCZOS)

    overlay_asset = None
    overlay_box = None
    if variant == "F":
        # The alternative to cutting a plane out of the still: an independently
        # generated RGBA asset laid over the *complete* painting. Nothing is
        # removed from the background, so no hole can ever be exposed.
        base = Image.open(ROOT / data["source"]).convert("RGBA")
        bg = base.resize((base.width * 2, base.height * 2), Image.LANCZOS)
    if variant == "G":
        # The target shape: background with only the boat repainted (small,
        # uniform hole), the boat as its own plane, and an independent
        # foreground asset. The tree stays inside the background on purpose.
        plate_path = output_path("experiments/m8_plates/plates/plate_boat.png")
        if not plate_path.is_file():
            raise FileNotFoundError(f"{plate_path} — run scripts/m8_plates.py build --region boat")
        plate = Image.open(plate_path).convert("RGBA")
        bg = plate.resize((plate.width * 2, plate.height * 2), Image.LANCZOS)

    need_boat = variant in ("B", "C", "G")
    need_tree = variant in ("B", "C")
    if variant in ("F", "G"):
        overlay_asset = Image.open(ASSET_PATH).convert("RGBA")
        overlay_box = tuple(data.get("overlay_box", [0.24, 0.58, 0.57, 1.02]))

    from drama_studio.motion.local import mesh_warp, water_displacement, reflection_displacement

    band = (0.495, 0.955)
    water_cfg = {
        "amplitude": 2.2, "frequency": 1.0 / 13.0, "wavelength_px": 320.0,
        "vertical_ratio": 0.26, "far_scale": 0.12, "bounds": band,
    }
    reflection_cfg = {
        "water_amplitude": 1.2, "water_frequency": 1.0 / 13.0, "wavelength_px": 320.0,
        "vertical_ratio": 0.26, "far_scale": 0.12, "bounds": (0.50, 0.64),
        "ratio": 0.55, "lag_s": 0.2,
    }
    boat_roi = data["regions"]["boat"]["roi"]
    wmask = water_mask((W, H), boat_roi)
    wmw, wmh = wmask.size
    reflective = band_alpha((W, H), [0.558, 0.618], [boat_roi[0], boat_roi[2]],
                            feather=8, x_feather=0.02, top_soft=4.0)

    reveal_checks = []
    for index in range(frames):
        t = index / FPS
        bg_s = plane_scale(curve, planes["bg"]["alpha"], t, duration)
        fg_s_current = plane_scale(curve, planes["fg"]["alpha"], t, duration)
        background = affine_scale(bg, bg_s, curve["focus"], (W, H)).convert("RGB")

        boat = None
        tree = None
        if need_boat:
            mid_s = plane_scale(curve, planes["mid"]["alpha"], t, duration)
            boat = affine_scale(mid, mid_s, curve["focus"], (W, H))
        if need_tree:
            fg_s = plane_scale(curve, planes["fg"]["alpha"], t, duration)
            tree = affine_scale(fg, fg_s, curve["focus"], (W, H))

        if variant in ("C", "D"):
            # Controlled local micro-motion, reusing the production displacement
            # fields so the variants differ by motion, not by look.
            def water(xn: float, yn: float) -> tuple[float, float]:
                weight = wmask.getpixel((min(wmw - 1, int(xn * wmw)),
                                         min(wmh - 1, int(yn * wmh)))) / 255.0
                if weight <= 0.0:
                    return (0.0, 0.0)
                dx, dy = water_displacement(xn, yn, t, phase=0.0, **water_cfg)
                return (dx * weight, dy * weight)

            background = mesh_warp(background, water, grid=(18, 28))
            if boat is not None:
                warped = mesh_warp(
                    boat,
                    lambda xn, yn: reflection_displacement(xn, yn, t, phase=0.0, **reflection_cfg),
                    grid=(14, 20),
                )
                # Only the reflection band wobbles; the hull stays rigid.
                boat = Image.composite(warped, boat, reflective)

        composed = background.convert("RGBA")
        if boat is not None:
            composed.alpha_composite(boat)
        if tree is not None:
            composed.alpha_composite(tree)
        if overlay_asset is not None:
            # The generated foreground is the nearest plane: it goes on last.
            left, top = map_point(overlay_box[:2], fg_s_current, curve["focus"])
            right, bottom = map_point(overlay_box[2:], fg_s_current, curve["focus"])
            box_w = max(2, int(round((right - left) * W)))
            box_h = max(2, int(round((bottom - top) * H)))
            placed = overlay_asset.resize((box_w, box_h), Image.LANCZOS)
            composed.alpha_composite(placed, (int(round(left * W)), int(round(top * H))))
        composed.convert("RGB").save(frame_dir / f"f_{index:04d}.png")

        if boat is not None and (index % 6 == 0 or index == frames - 1):
            hole = affine_scale(hole_plane, bg_s, curve["focus"], (W, H)).getchannel("A")
            reveal_checks.append({"frame": index, "t": round(t, 3),
                                  **uncovered_stats(hole, boat.getchannel("A"))})

    video = out_dir / f"{variant.lower()}.mp4"
    texture = out_dir / "texture_raw_paper.png"
    from drama_studio.motion.texture import make_texture
    make_texture("raw_paper", texture)

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(FPS), "-i", str(frame_dir / "f_%04d.png"),
        "-loop", "1", "-i", str(texture),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
        "-filter_complex",
        f"[1:v]scale={W}:{H}:flags=bicubic[tex];"
        f"[0:v][tex]blend=all_mode=overlay:all_opacity=0.14,format=yuv420p[outv]",
        "-map", "[outv]", "-map", "2:a",
        "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(video),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + proc.stderr[-3000:])

    worst = max(reveal_checks, key=lambda item: item["leak_weighted_px"]) if reveal_checks else None
    record = {
        "variant": variant,
        "video": str(video.relative_to(ROOT)).replace("\\", "/"),
        "frames": frames,
        "duration_seconds": duration,
        "fps": FPS,
        "size": [W, H],
        "camera": {
            "focus": list(curve["focus"]),
            "easing": curve["easing"],
            "scale_bg_end": round(plane_scale(curve, 1.0, duration, duration), 6),
            "scale_mid_end": round(plane_scale(curve, planes["mid"]["alpha"], duration, duration), 6),
            "scale_fg_end": round(plane_scale(curve, planes["fg"]["alpha"], duration, duration), 6),
        },
        "plane_alpha": {k: planes[k]["alpha"] for k in planes},
        "planes_rendered": (["bg", "mid", "fg_overlay"] if variant == "G" else
                    ["bg", "fg_overlay"] if variant == "F" else
                    ["bg"] if variant in ("D", "E") else ["bg", "mid", "fg"]),
        "reveal_checks": reveal_checks,
        "reveal_worst": worst,
        "render_seconds": round(time.time() - started, 2),
    }
    (out_dir / "render.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def render_production(data: dict) -> dict:
    """Variant A: the existing production 2D push, called unchanged."""
    from drama_studio.motion.render import render_plan
    from drama_studio.domain.motion.spec import CameraOverride, MotionPlan, ShotSpec

    plan_obj = MotionPlan(
        style_id=data["style_id"],
        fps=FPS,
        width=W,
        height=H,
        shots=[ShotSpec(
            id="shot_001",
            source=data["source"],
            duration_seconds=float(data["duration_seconds"]),
            motion="",
            camera=CameraOverride(move="slow_push_in"),
        )],
    )
    out_root = RENDERS / "A"
    info = render_plan(plan_obj, root=ROOT, out_root=out_root, build_sequence=False)
    manifest = json.loads((ROOT / info["manifest"]).read_text(encoding="utf-8"))
    shot = manifest["shots"][0]
    video = ROOT / shot["output"]
    record = {
        "variant": "A",
        "video": str(video.relative_to(ROOT)).replace("\\", "/"),
        "manifest": info["manifest"],
        "build": info["build"],
        "camera": shot["camera"],
        "frames": int(round(float(data["duration_seconds"]) * FPS)),
        "duration_seconds": float(data["duration_seconds"]),
        "fps": FPS,
        "size": [W, H],
        "note": "生产 motion.render 直接输出；未改动任何生产参数或质量门",
    }
    (out_root / "render.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


# ----------------------------------------------------------------- metrics
REGIONS = {
    # normalized boxes on the output frame; contents chosen so each box holds a
    # single plane, otherwise the measurement cannot attribute anything.
    "boat": (0.29, 0.44, 0.65, 0.63),
    "tree": (0.63, 0.66, 1.00, 0.97),
    "background_buildings": (0.60, 0.435, 0.80, 0.545),
    "background_ridge": (0.05, 0.20, 0.35, 0.33),
}


def grab(video: Path, at: float, out: Path) -> Image.Image:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(video),
                    "-frames:v", "1", str(out)], check=True, capture_output=True)
    return Image.open(out).convert("RGB")


def region_signature(img: Image.Image, box: tuple[float, float, float, float],
                     threshold: int = 170) -> dict:
    width, height = img.size
    x0, y0, x1, y1 = (int(box[0] * width), int(box[1] * height),
                      int(box[2] * width), int(box[3] * height))
    gray = img.crop((x0, y0, x1, y1)).convert("L")
    dark = gray.point(lambda v: 255 if v < threshold else 0)
    histogram = dark.histogram()
    count = sum(histogram[1:])
    bbox = dark.getbbox()
    centroid = None
    if count:
        sum_x = sum_y = 0
        pixels = dark.load()
        for y in range(dark.height):
            for x in range(dark.width):
                if pixels[x, y]:
                    sum_x += x
                    sum_y += y
        centroid = (round(x0 + sum_x / count, 2), round(y0 + sum_y / count, 2))
    return {
        "dark_px": count,
        "bbox": [bbox[0] + x0, bbox[1] + y0, bbox[2] + x0, bbox[3] + y0] if bbox else None,
        "bbox_size": [bbox[2] - bbox[0], bbox[3] - bbox[1]] if bbox else None,
        "centroid": centroid,
    }


def luma_series(video: Path, size: tuple[int, int] = (270, 480)) -> list[float]:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={size[0]}:{size[1]}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True)
    data = proc.stdout
    frame = size[0] * size[1]
    return [round(sum(data[i:i + frame]) / frame, 3) for i in range(0, len(data) - frame + 1, frame)]


def diff_region(a: Image.Image, b: Image.Image, box: tuple[float, float, float, float]) -> float:
    width, height = a.size
    x0, y0, x1, y1 = (int(box[0] * width), int(box[1] * height),
                      int(box[2] * width), int(box[3] * height))
    difference = ImageChops.difference(a.crop((x0, y0, x1, y1)), b.crop((x0, y0, x1, y1)))
    return round(ImageStat.Stat(difference).mean[0], 3)


def tree_reveal(data: dict, curve: dict, duration: float) -> dict:
    """Same exact geometery check as the boat, for the foreground plane."""
    from PIL import ImageChops as chops

    def plane(path: str) -> Image.Image:
        image = Image.open(LAYERS / path).convert("L")
        image = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
        return Image.merge("RGBA", (image, image, image, image))

    hole_l = plane("mask_tree.png")
    fg_l = Image.open(LAYERS / "fg_tree.png").convert("RGBA")
    fg_l = Image.merge("RGBA", [fg_l.getchannel("A")] * 4)
    fg_alpha = next(p["alpha"] for p in data["planes"] if p["id"] == "fg")
    worst = {"leak_weighted_px": 0}
    checks = []
    for index in range(0, int(round(duration * FPS)), 6):
        t = index / FPS
        hole = affine_scale(hole_l, plane_scale(curve, 1.0, t, duration),
                            curve["focus"], (W, H)).getchannel("A")
        cover = affine_scale(fg_l, plane_scale(curve, fg_alpha, t, duration),
                             curve["focus"], (W, H)).getchannel("A")
        entry = {"frame": index, "t": round(t, 3), **uncovered_stats(hole, cover)}
        checks.append(entry)
        if entry["leak_weighted_px"] > worst.get("leak_weighted_px", 0):
            worst = entry
    return {"plane": "fg", "checks": checks, "worst": worst}


def dark_centroid(img: Image.Image, box: tuple[float, float, float, float],
                  threshold: int = 140) -> dict:
    """Centroid and extent of the dark strokes inside a box (output pixels)."""
    width, height = img.size
    x0, y0, x1, y1 = (int(box[0] * width), int(box[1] * height),
                      int(box[2] * width), int(box[3] * height))
    gray = img.crop((x0, y0, x1, y1)).convert("L")
    dark = gray.point(lambda v: 255 if v < threshold else 0)
    count = sum(dark.histogram()[1:])
    if not count:
        return {"dark_px": 0, "centroid_x": None, "centroid_y": None,
                "leftmost_x": None, "topmost_y": None}
    sum_x = sum_y = 0
    leftmost = None
    topmost = None
    pixels = dark.load()
    for y in range(dark.height):
        for x in range(dark.width):
            if pixels[x, y]:
                sum_x += x
                sum_y += y
                if leftmost is None or x < leftmost:
                    leftmost = x
                if topmost is None or y < topmost:
                    topmost = y
    return {
        "dark_px": count,
        "centroid_x": round(x0 + sum_x / count, 2),
        "centroid_y": round(y0 + sum_y / count, 2),
        "leftmost_x": x0 + leftmost,
        "topmost_y": y0 + topmost,
    }


def shift_probe(a: Image.Image, b: Image.Image, box: tuple[float, float, float, float],
                span: int = 4) -> dict:
    """How many pixels did this region actually move between two variants?

    ``b`` is compared with ``a`` under each candidate horizontal shift over the
    overlapping window. If the region moved, a non-zero shift scores better than
    zero. ``energy`` is that improvement, which separates a real displacement
    from the resampling noise every region shares.
    """
    width, height = a.size
    x0, y0, x1, y1 = (int(box[0] * width), int(box[1] * height),
                      int(box[2] * width), int(box[3] * height))
    scores = {}
    for dx in range(-span, span + 1):
        lo = x0 + max(0, dx)
        hi = x1 - max(0, -dx)
        if hi - lo < 8:
            continue
        left = a.crop((lo, y0, hi, y1))
        right = b.crop((lo + dx, y0, hi + dx, y1))
        scores[dx] = round(ImageStat.Stat(ImageChops.difference(left, right)).mean[0], 4)
    best = min(scores, key=scores.get)
    return {"best_shift_px": best, "best_score": scores[best],
            "zero_score": scores[0],
            "energy": round(scores[0] - scores[best], 4)}


def metrics(data: dict, curve: dict) -> dict:
    duration = float(data["duration_seconds"])
    variants = {}
    frames_dir = OUT / "metrics" / "frames"
    for variant in ("A", "B", "C", "D", "E", "F", "G"):
        if not (RENDERS / variant / "render.json").is_file():
            continue
        record = json.loads((RENDERS / variant / "render.json").read_text(encoding="utf-8"))
        video = ROOT / record["video"]
        entries = {}
        for label, at in (("first", 0.0), ("mid", round(duration / 2, 3)),
                          ("last", round(duration - 1.0 / FPS, 3))):
            img = grab(video, at, frames_dir / f"{variant}_{label}.png")
            entries[label] = {name: region_signature(img, box) for name, box in REGIONS.items()}
        luma = luma_series(video)
        steps = [round(abs(b - a), 3) for a, b in zip(luma, luma[1:])]
        variants[variant] = {
            "video": record["video"],
            "camera": record.get("camera"),
            "regions": entries,
            "luma": {
                "first": luma[0] if luma else None,
                "last": luma[-1] if luma else None,
                "min": min(luma) if luma else None,
                "max": max(luma) if luma else None,
                "max_step": max(steps) if steps else None,
                "frames_measured": len(luma),
            },
        }

    # Parallax read: how much each plane grew over the clip, and by how much
    # each variant differs from the production baseline on the same plane.
    growth = {}
    for variant, record in variants.items():
        growth[variant] = {}
        for name in REGIONS:
            first = record["regions"]["first"][name]
            last = record["regions"]["last"][name]
            area_ratio = None
            if first["dark_px"] and last["dark_px"]:
                # area grows with the square of the plane scale; it is not
                # clipped by the region box the way a bbox is.
                area_ratio = round(last["dark_px"] / first["dark_px"], 4)
            shift = None
            if first["centroid"] and last["centroid"]:
                shift = (round(last["centroid"][0] - first["centroid"][0], 2),
                         round(last["centroid"][1] - first["centroid"][1], 2))
            growth[variant][name] = {"dark_area_ratio_last_over_first": area_ratio, "centroid_shift_px": shift}

    relative = {}
    for variant in ("B", "C", "D", "E", "F", "G"):
        if variant not in variants:
            continue
        relative[variant] = {}
        for name in REGIONS:
            a = variants["A"]["regions"]["last"][name]
            b = variants[variant]["regions"]["last"][name]
            if a["dark_px"] and b["dark_px"]:
                relative[variant][name] = {
                    "dark_area_ratio_vs_A": round(b["dark_px"] / a["dark_px"], 4)}

    # Locality of C's micro-motion: it must change water and nothing else.
    locality = {}
    for label, at in (("mid", round(duration / 2, 3)), ("last", round(duration - 1.0 / FPS, 3))):
        b_img = Image.open(frames_dir / f"B_{label}.png").convert("RGB")
        c_img = Image.open(frames_dir / f"C_{label}.png").convert("RGB")
        locality[label] = {
            "water_open": diff_region(b_img, c_img, (0.10, 0.52, 0.55, 0.68)),
            "boat": diff_region(b_img, c_img, (0.33, 0.47, 0.60, 0.56)),
            "land_left": diff_region(b_img, c_img, (0.00, 0.80, 0.45, 1.00)),
            "sky": diff_region(b_img, c_img, (0.10, 0.02, 0.90, 0.18)),
        }

    # Attribution control: A (production 2D) vs D (same still, one plane, same
    # ripple as C). If A~D differs as much as B~C in the water, the preference
    # for C is explained by the micro-motion, not by the layers.
    attribution = {}
    if "D" in variants:
        for label, at in (("mid", round(duration / 2, 3)), ("last", round(duration - 1.0 / FPS, 3))):
            a_img = Image.open(frames_dir / f"A_{label}.png").convert("RGB")
            d_img = Image.open(frames_dir / f"D_{label}.png").convert("RGB")
            attribution[label] = {
                "A_vs_D_water": diff_region(a_img, d_img, (0.10, 0.52, 0.40, 0.66)),
                "A_vs_D_land": diff_region(a_img, d_img, (0.02, 0.82, 0.40, 0.98)),
                "A_vs_D_sky": diff_region(a_img, d_img, (0.10, 0.02, 0.90, 0.18)),
                "A_vs_D_boat": diff_region(a_img, d_img, (0.36, 0.495, 0.58, 0.545)),
            }

    # 2x2 factorial inside one renderer: E = no layers/no ripple, B = layers,
    # D = ripple, C = both. Each pair isolates one variable without crossing
    # renderers (A is production's zoompan and differs from this renderer by a
    # small but non-zero geometric offset, so A cannot serve as a control).
    factorial = {}
    pairs = {"layer_effect_B_minus_E": ("E", "B"), "ripple_effect_D_minus_E": ("E", "D"),
             "both_C_minus_B": ("B", "C"), "C_minus_D": ("D", "C")}
    if all(v in variants for v in ("B", "C", "D", "E", "F", "G")):
        for name, (left, right) in pairs.items():
            fact = {}
            for label, at in (("mid", round(duration / 2, 3)),
                              ("last", round(duration - 1.0 / FPS, 3))):
                l_img = Image.open(frames_dir / f"{left}_{label}.png").convert("RGB")
                r_img = Image.open(frames_dir / f"{right}_{label}.png").convert("RGB")
                fact[label] = {
                    "water": diff_region(l_img, r_img, (0.10, 0.52, 0.40, 0.66)),
                    "tree": diff_region(l_img, r_img, (0.62, 0.66, 0.99, 0.97)),
                    "boat": diff_region(l_img, r_img, (0.36, 0.495, 0.58, 0.545)),
                    "land": diff_region(l_img, r_img, (0.02, 0.82, 0.40, 0.98)),
                    "sky": diff_region(l_img, r_img, (0.10, 0.02, 0.90, 0.18)),
                }
            factorial[name] = fact

    reveal = {"boat": json.loads((RENDERS / "B" / "render.json").read_text(encoding="utf-8"))["reveal_worst"],
              "tree": tree_reveal(data, curve, duration)["worst"]}

    # Landmark positions: two planes that must move differently and one that
    # must not move relative to the production baseline.
    landmarks = {}
    for label in ("first", "last"):
        entry = {}
        for variant in ("A", "B", "C"):
            img = Image.open(frames_dir / f"{variant}_{label}.png").convert("RGB")
            entry[variant] = {
                "tree_branch_tips": dark_centroid(img, (0.62, 0.665, 0.99, 0.780), 120),
                "far_shore_landmark": dark_centroid(img, (0.02, 0.400, 0.230, 0.470), 150),
            }
        landmarks[label] = entry

    # Resampling floor: C warps the whole background frame through Pillow's
    # mesh, which resamples every pixel even where the displacement is zero.
    # Measuring that control separates the ripple from plain resampling.
    from drama_studio.motion.local import mesh_warp
    floors = {}
    for label in ("mid", "last"):
        b_img = Image.open(frames_dir / f"B_{label}.png").convert("RGB")
        control = mesh_warp(b_img, lambda xn, yn: (0.0, 0.0), grid=(18, 28))
        floors[label] = {
            "water_open": diff_region(b_img, control, (0.10, 0.52, 0.40, 0.66)),
            "land_left": diff_region(b_img, control, (0.02, 0.82, 0.40, 0.98)),
            "sky": diff_region(b_img, control, (0.10, 0.02, 0.90, 0.18)),
            "boat_hull": diff_region(b_img, control, (0.36, 0.495, 0.58, 0.545)),
        }

    locality_probe = {}
    for label, at in (("mid", round(duration / 2, 3)), ("last", round(duration - 1.0 / FPS, 3))):
        b_img = Image.open(frames_dir / f"B_{label}.png").convert("RGB")
        c_img = Image.open(frames_dir / f"C_{label}.png").convert("RGB")
        locality_probe[label] = {
            "water_open": shift_probe(b_img, c_img, (0.10, 0.52, 0.40, 0.66)),
            "land_left": shift_probe(b_img, c_img, (0.02, 0.82, 0.40, 0.98)),
            "sky": shift_probe(b_img, c_img, (0.10, 0.02, 0.90, 0.18)),
            "boat_hull": shift_probe(b_img, c_img, (0.36, 0.495, 0.58, 0.545)),
        }

    report = {
        "stage": "m8a.metrics",
        "variants": variants,
        "growth": growth,
        "relative_to_A": relative,
        "micro_motion_locality_B_vs_C": locality,
        "micro_motion_resample_floor": floors,
        "attribution_A_vs_D": attribution,
        "factorial_2x2": factorial,
        "micro_motion_shift_probe": locality_probe,
        "landmarks": landmarks,
        "reveal_worst": reveal,
        "camera_by_construction": {
            "bg_end": round(plane_scale(curve, 1.0, duration, duration), 6),
            "mid_end": round(plane_scale(curve, 0.70, duration, duration), 6),
            "fg_end": round(plane_scale(curve, 0.49, duration, duration), 6),
        },
    }
    (OUT / "metrics" / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Contact sheet: first / mid / last for the three variants, plus the boat and
    # tree crops at the last frame so a human can compare without scrubbing.
    order = [v for v in ("A", "E", "B", "D", "C", "F", "G") if v in variants]
    sheet = Image.new("RGB", (W // 4 * len(order) + 8 * len(order), H // 4 * 3 + 16), (240, 240, 240))
    for column, variant in enumerate(order):
        for row, label in enumerate(("first", "mid", "last")):
            img = Image.open(frames_dir / f"{variant}_{label}.png").convert("RGB")
            thumb = img.resize((W // 4, H // 4), Image.LANCZOS)
            sheet.paste(thumb, (column * (W // 4 + 8), row * (H // 4 + 8)))
    sheet.save(OUT / "metrics" / "contact_sheet_ABC.png")

    for name, box in (("boat", (0.24, 0.42, 0.70, 0.65)), ("tree", (0.58, 0.62, 1.0, 1.0))):
        crops = []
        for variant in order:
            img = Image.open(frames_dir / f"{variant}_last.png").convert("RGB")
            x0, y0, x1, y1 = (int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H))
            crops.append(img.crop((x0, y0, x1, y1)))
        width = crops[0].width
        height = crops[0].height
        strip = Image.new("RGB", (width * len(order) + 8 * len(order), height), (255, 0, 0))
        for index, crop in enumerate(crops):
            strip.paste(crop, (index * (width + 8), 0))
        strip.save(OUT / "metrics" / f"last_frame_{name}_ABC.png")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M8-A layered parallax experiment")
    sub = parser.add_subparsers(dest="command", required=True)
    p_layers = sub.add_parser("layers", help="build bg plate and the two cutouts")
    p_layers.add_argument("--rebuild", action="store_true")
    p_render = sub.add_parser("render", help="render variant A, B or C")
    p_render.add_argument("--variant", choices=["A", "B", "C", "D", "E", "F", "G"], required=True)
    p_render.add_argument("--force", action="store_true")
    sub.add_parser("metrics", help="measure A/B/C and write comparison sheets")
    args = parser.parse_args(argv)

    if args.command == "layers":
        print(json.dumps(build_layers(rebuild=args.rebuild), ensure_ascii=False, indent=2))
        return 0

    data = plan()
    if args.command == "metrics":
        curve = camera_curve(data["camera"], float(data["duration_seconds"]))
        print(json.dumps(metrics(data, curve), ensure_ascii=False, indent=2))
        return 0
    if args.variant == "A":
        print(json.dumps(render_production(data), ensure_ascii=False, indent=2))
        return 0
    curve = camera_curve(data["camera"], float(data["duration_seconds"]))
    print(json.dumps(render_variant(args.variant, data, curve, force=args.force),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
