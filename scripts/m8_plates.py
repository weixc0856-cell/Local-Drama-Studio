"""M8-B(1): build a clean plate with FLUX.2 klein inpainting.

The M8-A experiment cut the boat and the right foreground tree out of a
flattened painting and repaired the holes with row interpolation. That works
only because the holes are seen through a thin reveal band; the fill is smooth,
not painted.

This script produces the alternative: mask the same holes slightly wider, let
the installed FLUX.2 klein repaint just those areas, and composite the result
back into the **untouched** original so the rest of the painting stays
bit-identical (a VAE round-trip softens everything it touches).

It is an experiment tool: it writes only under ``experiments/m8_plates`` and
stages copies into ComfyUI's ``input`` folder. It does not modify production
code, workflows or config.

Usage::

    .venv\\Scripts\\python.exe scripts\\m8_plates.py masks --dilate 12
    .venv\\Scripts\\python.exe scripts\\m8_plates.py inpaint --region boat
    .venv\\Scripts\\python.exe scripts\\m8_plates.py build --region boat
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "experiments" / "m8_plates"
M8A = ROOT / "experiments" / "m8_parallax" / "layers"
COMFY = ROOT / "runtime" / "ComfyUI"
COMFY_INPUT = COMFY / "input"
SOURCE = ROOT / "experiments/m7_final/ink/work/images/shot_001/out.png"
WORKFLOW = ROOT / "workflows" / "m8_flux2_inpaint_api.json"
BASE = "http://127.0.0.1:8188"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

# The two holes M8-A had to repair. Masks come from the M8-A layer build so the
# repaint area matches what the layered render can actually expose.
REGIONS = {
    "boat": {
        "mask": M8A / "mask_boat.png",
        "prompt": (
            "写意水墨山水画的水面部分：只有平静的江面，极淡的墨色横纹，大面积留白，"
            "纸本纤维可见。不要船只，不要桅杆，不要倒影，不要人物，"
            "不要沙洲，不要石头，不要草丛，不要鸟，不要任何新物体；"
            "与左右两侧的水面笔触完全连续，不出现硬边、不出现色块"
        ),
    },
    "tree": {
        "mask": M8A / "mask_tree.png",
        "prompt": (
            "写意水墨山水画的江岸部分：大面积留白的江面，极淡的墨色水纹，"
            "岸边只有浅浅的土坡与极稀疏的枯草，纸本纤维可见；"
            "不要树，不要枝干，不要树冠，不要石头，不要人物，不要任何新物体；"
            "与周围水墨笔触完全连续，不出现硬边、不出现色块"
        ),
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def render_placeholders(value, params: dict):
    if isinstance(value, dict):
        return {key: render_placeholders(item, params) for key, item in value.items()}
    if isinstance(value, list):
        return [render_placeholders(item, params) for item in value]
    if isinstance(value, str):
        match = PLACEHOLDER.match(value)
        if match:
            name = match.group(1)
            if name not in params:
                raise KeyError(f"missing placeholder value: {name}")
            return params[name]
    return value


# --------------------------------------------------------------------- masks
def build_masks(dilate: int) -> dict:
    """Widen the M8-A holes into a repaint mask.

    The mask is wider than the cut so the repainted content also covers the thin
    band the moving layer can expose (M8-A measured up to 53 px on the rigging).
    """
    mask_dir = OUT / "masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGB")
    record = {"stage": "m8b1.masks", "source": rel(SOURCE), "dilate_px": dilate, "regions": {}}
    for name, config in REGIONS.items():
        alpha = Image.open(config["mask"]).convert("L")
        if alpha.size != source.size:
            raise ValueError(f"{name}: mask size {alpha.size} != source {source.size}")
        grown = alpha.filter(ImageFilter.MaxFilter(dilate * 2 + 1))
        grown = grown.filter(ImageFilter.GaussianBlur(3))
        path = mask_dir / f"mask_{name}.png"
        grown.save(path)
        coverage = ImageStat.Stat(grown).mean[0] / 255.0
        record["regions"][name] = {
            "mask": rel(path), "mask_sha256": sha256(path),
            "coverage": round(coverage, 5), "bbox": grown.getbbox(),
        }
    # One combined mask: both holes in a single repaint pass, which is cheaper
    # and keeps one prompt covering the whole plate.
    combined = Image.new("L", source.size, 0)
    for name in REGIONS:
        combined = ImageChops.lighter(combined, Image.open(mask_dir / f"mask_{name}.png").convert("L"))
    path = mask_dir / "mask_all.png"
    combined.save(path)
    record["regions"]["all"] = {"mask": rel(path), "mask_sha256": sha256(path),
                                "coverage": round(ImageStat.Stat(combined).mean[0] / 255.0, 5)}
    (OUT / "masks" / "masks.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


# ------------------------------------------------------------------- comfyui
def submit(workflow: dict, timeout: int) -> dict:
    payload = {"prompt": workflow, "client_id": str(uuid.uuid4())}
    request = urllib.request.Request(
        BASE + "/prompt",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with OPENER.open(request, timeout=30) as response:
        created = json.loads(response.read().decode("utf-8"))
    prompt_id = created.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"no prompt_id: {created}")

    started = time.time()
    while time.time() - started < timeout:
        with OPENER.open(BASE + f"/history/{prompt_id}", timeout=30) as response:
            history = json.loads(response.read().decode("utf-8"))
        entry = history.get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error" or status.get("completed") is False:
                raise RuntimeError(json.dumps(status, ensure_ascii=False)[:2000])
            if status.get("completed"):
                return {"prompt_id": prompt_id, "history": entry,
                        "seconds": round(time.time() - started, 2)}
        time.sleep(2)
    raise TimeoutError(f"ComfyUI did not finish in {timeout}s (prompt {prompt_id})")


def download(entry: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for node in (entry.get("outputs") or {}).values():
        for image in node.get("images", []):
            query = urllib.parse.urlencode({
                "filename": image["filename"],
                "subfolder": image.get("subfolder", ""),
                "type": image.get("type", "output"),
            })
            with OPENER.open(BASE + "/view?" + query, timeout=120) as response:
                data = response.read()
            target = out_dir / Path(image["filename"]).name
            target.write_bytes(data)
            saved.append(target)
    return saved


def inpaint(region: str, steps: int, seed: int, timeout: int) -> dict:
    masks = json.loads((OUT / "masks" / "masks.json").read_text(encoding="utf-8"))
    mask_path = ROOT / masks["regions"][region]["mask"]
    if not mask_path.is_file():
        raise FileNotFoundError(f"{mask_path} — run `masks` first")

    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    source_name = "m8_plate_source.png"
    mask_name = f"m8_plate_mask_{region}.png"
    shutil.copy2(SOURCE, COMFY_INPUT / source_name)
    shutil.copy2(mask_path, COMFY_INPUT / mask_name)

    source_size = Image.open(SOURCE).size
    prompt = REGIONS[region]["prompt"]
    workflow = render_placeholders(json.loads(WORKFLOW.read_text(encoding="utf-8")), {
        "unet_name": "flux-2-klein-4b-Q4_K_M.gguf",
        "source_image": source_name,
        "mask_image": mask_name,
        "positive_prompt": prompt,
        "steps": steps,
        "cfg": 1.0,
        "width": source_size[0],
        "height": source_size[1],
        "seed": seed,
        "filename_prefix": f"m8/plate_{region}",
    })

    run_dir = OUT / "runs" / f"{region}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow.submitted.json").write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = submit(workflow, timeout)
    (run_dir / "history.json").write_text(
        json.dumps(result["history"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = download(result["history"], run_dir)
    record = {
        "stage": "m8b1.inpaint",
        "region": region,
        "prompt": prompt,
        "seed": seed,
        "steps": steps,
        "size": list(source_size),
        "workflow": rel(WORKFLOW),
        "workflow_sha256": sha256(WORKFLOW),
        "source": rel(SOURCE),
        "source_sha256": sha256(SOURCE),
        "mask": rel(mask_path),
        "mask_sha256": sha256(mask_path),
        "outputs": [{"path": rel(path), "sha256": sha256(path)} for path in files],
        "seconds": result["seconds"],
        "prompt_id": result["prompt_id"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (run_dir / "run.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


# --------------------------------------------------------------------- build
def _latest_run(region: str) -> Path | None:
    runs = sorted((OUT / "runs").glob(f"{region}-*"))
    return runs[-1] if runs else None


def build(region: str) -> dict:
    """Composite repainted holes back into the untouched original.

    Only pixels inside the feathered mask are replaced: the VAE round-trip
    softens everything it decodes, and the rest of the painting must stay
    bit-exact. ``region == "all"`` stacks every per-region run that exists.
    """
    masks = json.loads((OUT / "masks" / "masks.json").read_text(encoding="utf-8"))
    regions = [name for name in REGIONS if name != "all"] if region == "all" else [region]
    source = Image.open(SOURCE).convert("RGB")
    plate = source.copy()
    applied = []
    for name in regions:
        run = _latest_run(name)
        if run is None:
            if region == "all":
                continue
            raise FileNotFoundError(f"no run for {name} — run `inpaint` first")
        record = json.loads((run / "run.json").read_text(encoding="utf-8"))
        generated = Image.open(ROOT / record["outputs"][0]["path"]).convert("RGB")
        if generated.size != source.size:
            generated = generated.resize(source.size, Image.LANCZOS)
        mask = Image.open(ROOT / masks["regions"][name]["mask"]).convert("L")
        plate = Image.composite(generated, plate, mask.filter(ImageFilter.GaussianBlur(4)))
        applied.append({"region": name, "run": rel(run),
                        "generated_sha256": record["outputs"][0]["sha256"],
                        "seconds": record["seconds"]})

    plates = OUT / "plates"
    plates.mkdir(parents=True, exist_ok=True)
    path = plates / f"plate_{region}.png"
    plate.save(path)

    difference = ImageChops.difference(source, plate)
    in_mask = Image.new("L", source.size, 0)
    for name in regions:
        mask = Image.open(ROOT / masks["regions"][name]["mask"]).convert("L")
        in_mask = ImageChops.lighter(in_mask, mask)
    in_mask = in_mask.filter(ImageFilter.GaussianBlur(4))
    inside = ImageStat.Stat(difference, in_mask)
    outside = ImageStat.Stat(difference, ImageOps.invert(in_mask.point(lambda v: 255 if v > 8 else 0)))

    result = {
        "stage": "m8b1.build",
        "region": region,
        "plate": rel(path),
        "plate_sha256": sha256(path),
        "applied": applied,
        "mean_change_inside_mask": round(inside.mean[0], 3),
        "mean_change_outside_mask": round(outside.mean[0], 4),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (plates / f"plate_{region}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


ASSET_PROMPT = (
    "写意水墨画：几丛细长的芦苇与野草，从画面底部向上生长，叶片细长稀疏，"
    "墨色由浓到淡自然过渡，笔触概括；纯白宣纸背景，主体孤立，四周大量留白；"
    "没有远景，没有水面，没有地面，没有山，没有船，没有人物，没有鸟，没有文字"
)


def key_alpha(image: Image.Image) -> Image.Image:
    """Turn an ink-on-white generation into RGBA.

    Ink wash assets are dark strokes on paper, so the key is luminance, not a
    colour threshold: alpha rises as the pixel gets darker than the measured
    paper level. Anything at or below ``FULL_INK`` is fully opaque.
    """
    rgb = image.convert("RGB")
    gray = rgb.convert("L")
    histogram = gray.histogram()
    total = sum(histogram)
    accumulated = 0
    paper = 250
    for value in range(255, -1, -1):
        accumulated += histogram[value]
        if accumulated >= total * 0.25:
            paper = value
            break
    full_ink = max(40, paper - 110)
    span = max(1, paper - full_ink)
    alpha = gray.point(lambda v: 255 if v <= full_ink else
                       (0 if v >= paper else int(round(255 * (paper - v) / span))))
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.2))
    rgba = rgb.convert("RGBA")
    rgba.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 12 else 0).getbbox()
    if box is None:
        raise ValueError("keying produced an empty asset")
    pad = 6
    box = (max(0, box[0] - pad), max(0, box[1] - pad),
           min(rgb.width, box[2] + pad), min(rgb.height, box[3] + pad))
    return rgba.crop(box), {"paper_luma": paper, "full_ink_luma": full_ink, "bbox": list(box)}


def asset(steps: int, seed: int, timeout: int) -> dict:
    """Generate an independent foreground asset (no scene behind it)."""
    t2i = ROOT / "workflows" / "r0_flux_t2i_api.json"
    workflow = render_placeholders(json.loads(t2i.read_text(encoding="utf-8")), {
        "positive_prompt": ASSET_PROMPT,
        "seed": seed,
        "width": 576,
        "height": 1024,
        "steps": steps,
        "cfg": 1.0,
        "filename_prefix": "m8/asset_reeds",
    })
    run_dir = OUT / "runs" / f"asset-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow.submitted.json").write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = submit(workflow, timeout)
    files = download(result["history"], run_dir)
    if not files:
        raise RuntimeError("asset generation produced no image")

    raw = Image.open(files[0]).convert("RGB")
    rgba, key = key_alpha(raw)
    out_dir = OUT / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "fg_reeds.png"
    rgba.save(path)
    record = {
        "stage": "m8b2.asset",
        "prompt": ASSET_PROMPT,
        "seed": seed,
        "steps": steps,
        "workflow": rel(t2i),
        "workflow_sha256": sha256(t2i),
        "raw": [{"path": rel(p), "sha256": sha256(p)} for p in files],
        "asset": rel(path),
        "asset_sha256": sha256(path),
        "asset_size": list(rgba.size),
        "key": key,
        "alpha_coverage": round(ImageStat.Stat(rgba.getchannel("A")).mean[0] / 255.0, 5),
        "seconds": result["seconds"],
        "prompt_id": result["prompt_id"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (run_dir / "run.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def t2i(prompt: str, out_name: str, width: int, height: int, steps: int, seed: int,
        timeout: int, key: bool) -> dict:
    """Generate a still (key=False) or a foreground asset (key=True)."""
    t2i_path = ROOT / "workflows" / "r0_flux_t2i_api.json"
    workflow = render_placeholders(json.loads(t2i_path.read_text(encoding="utf-8")), {
        "positive_prompt": prompt,
        "seed": seed,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg": 1.0,
        "filename_prefix": f"m8/{out_name}",
    })
    run_dir = OUT / "runs" / f"{out_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "workflow.submitted.json").write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = submit(workflow, timeout)
    files = download(result["history"], run_dir)
    if not files:
        raise RuntimeError("generation produced no image")
    raw = Image.open(files[0]).convert("RGB")
    out_dir = OUT / ("assets" if key else "stills")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{out_name}.png"
    if key:
        rgba, key_info = key_alpha(raw)
        rgba.save(path)
        size = list(rgba.size)
    else:
        raw.save(path)
        key_info = None
        size = list(raw.size)
    record = {
        "stage": "m8d.t2i",
        "prompt": prompt,
        "seed": seed,
        "steps": steps,
        "size": size,
        "keyed": key,
        "key": key_info,
        "workflow": rel(t2i_path),
        "workflow_sha256": sha256(t2i_path),
        "raw": [{"path": rel(item), "sha256": sha256(item)} for item in files],
        "output": rel(path),
        "output_sha256": sha256(path),
        "seconds": result["seconds"],
        "prompt_id": result["prompt_id"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (run_dir / "run.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def key_alpha_color(image: Image.Image, low: float = 10.0, high: float = 60.0) -> Image.Image:
    """Key by distance from the paper colour, not by darkness.

    Court-green assets are light mineral pigment on near-white silk, so a
    luminance key would keep only the darkest strokes. Measuring the paper from
    the border and keying on colour distance keeps the whole painted shape.
    """
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    samples = {"r": [], "g": [], "b": []}
    border = 8
    for y in range(height):
        if not (y < border or y >= height - border):
            continue
        for x in range(width):
            px = pixels[x, y]
            for name, value in zip(("r", "g", "b"), px):
                samples[name].append(value)
    paper = tuple(sorted(samples[name])[len(samples[name]) // 2] for name in ("r", "g", "b"))

    span = max(1.0, high - low)
    alpha = Image.new("L", rgb.size, 0)
    src, dst = pixels, alpha.load()
    for y in range(height):
        for x in range(width):
            px = src[x, y]
            distance = ((px[0] - paper[0]) ** 2 + (px[1] - paper[1]) ** 2
                        + (px[2] - paper[2]) ** 2) ** 0.5
            if distance <= low:
                dst[x, y] = 0
            elif distance >= high:
                dst[x, y] = 255
            else:
                dst[x, y] = int(round(255 * (distance - low) / span))
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.2))
    rgba = rgb.convert("RGBA")
    rgba.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 12 else 0).getbbox()
    if box is None:
        raise ValueError("colour keying produced an empty asset")
    pad = 6
    box = (max(0, box[0] - pad), max(0, box[1] - pad),
           min(width, box[2] + pad), min(height, box[3] + pad))
    return rgba.crop(box)


def rekey(raw_path: Path, out_name: str, method: str, low: float, high: float) -> dict:
    raw = Image.open(raw_path).convert("RGB")
    if method == "color":
        rgba = key_alpha_color(raw, low, high)
    else:
        rgba, _ = key_alpha(raw)
    out_dir = OUT / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{out_name}.png"
    rgba.save(path)
    coverage = round(ImageStat.Stat(rgba.getchannel("A")).mean[0] / 255.0, 4)
    record = {"stage": "m8d.rekey", "method": method, "low": low, "high": high,
              "raw": rel(raw_path), "raw_sha256": sha256(raw_path),
              "output": rel(path), "output_sha256": sha256(path),
              "size": list(rgba.size), "alpha_coverage": coverage}
    (out_dir / f"{out_name}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M8-B(1) clean plate via FLUX.2 inpainting")
    sub = parser.add_subparsers(dest="command", required=True)
    p_masks = sub.add_parser("masks", help="widen the M8-A holes into a repaint mask")
    p_masks.add_argument("--dilate", type=int, default=12)
    p_inpaint = sub.add_parser("inpaint", help="submit the inpaint workflow")
    p_inpaint.add_argument("--region", choices=sorted(REGIONS), required=True)
    p_inpaint.add_argument("--steps", type=int, default=6)
    p_inpaint.add_argument("--seed", type=int, default=8100)
    p_inpaint.add_argument("--timeout", type=int, default=1800)
    p_build = sub.add_parser("build", help="composite the repaint into the original")
    p_build.add_argument("--region", choices=sorted(REGIONS) + ["all"], required=True)
    p_t2i = sub.add_parser("t2i", help="generate a still or a keyed foreground asset")
    p_t2i.add_argument("--prompt", required=True)
    p_t2i.add_argument("--out-name", required=True)
    p_t2i.add_argument("--width", type=int, default=576)
    p_t2i.add_argument("--height", type=int, default=1024)
    p_t2i.add_argument("--steps", type=int, default=4)
    p_t2i.add_argument("--seed", type=int, default=8100)
    p_t2i.add_argument("--timeout", type=int, default=1800)
    p_t2i.add_argument("--key", action="store_true", help="luminance-key to RGBA")
    p_rekey = sub.add_parser("rekey", help="re-key an existing generation to RGBA")
    p_rekey.add_argument("--raw", required=True)
    p_rekey.add_argument("--out-name", required=True)
    p_rekey.add_argument("--method", choices=["luma", "color"], default="color")
    p_rekey.add_argument("--low", type=float, default=10.0)
    p_rekey.add_argument("--high", type=float, default=60.0)
    p_asset = sub.add_parser("asset", help="generate an independent foreground asset")
    p_asset.add_argument("--steps", type=int, default=4)
    p_asset.add_argument("--seed", type=int, default=8100)
    p_asset.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args(argv)

    if args.command == "masks":
        print(json.dumps(build_masks(args.dilate), ensure_ascii=False, indent=2))
        return 0
    if args.command == "inpaint":
        print(json.dumps(inpaint(args.region, args.steps, args.seed, args.timeout),
                         ensure_ascii=False, indent=2))
        return 0
    if args.command == "rekey":
        print(json.dumps(rekey(Path(args.raw), args.out_name, args.method, args.low, args.high),
                         ensure_ascii=False, indent=2))
        return 0
    if args.command == "t2i":
        print(json.dumps(t2i(args.prompt, args.out_name, args.width, args.height,
                             args.steps, args.seed, args.timeout, args.key),
                         ensure_ascii=False, indent=2))
        return 0
    if args.command == "asset":
        print(json.dumps(asset(args.steps, args.seed, args.timeout),
                         ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(build(args.region), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
