#!/usr/bin/env python3
"""scripts/run_z_image_style_atlas.py
Z-Image Turbo Visual Style Atlas · CLI & Live Benchmark Testbench.

Commands:
  list          Inspect all registered visual styles across categories.
  compile       Assemble a 7-dimension compliant prompt from a style recipe.
  benchmark     Run the style sweep against live ComfyUI (or dry-run compile check).
  board         Rebuild contact-sheet boards from an existing run manifest.
  score         Record human rubric scores (1-5) into the run manifest.
  report        Rebuild Markdown report + scoring CSV from the manifest.
  export-atlas  Regenerate docs/Z_IMAGE_TURBO_STYLE_ATLAS.md from the YAML registry.

Benchmark modes:
  recipe      Each style uses its own hand-written positive_prompt (the atlas recipe).
  controlled  Every style is forced onto ONE canonical subject via the 7-dimension
              compiler, so style capability is separated from subject difficulty.
  both        recipe + controlled in one pass.

Notes:
  - Rubric scores are NEVER auto-filled. They start as null and are entered by a human
    via `score`, because a fabricated 5/5 is worse than no score at all.
  - The manifest is written after every image, so an interrupted run resumes cleanly.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from drama_studio.domain.style.z_image_atlas import (  # noqa: E402
    DIMENSION_FIELDS,
    ZImageStyleAtlas,
    ZImagePromptCompiler,
    ZImageBenchmarkSuite,
    ZImageVocabulary,
    compile_style_mix,
)
from drama_studio.paths import output_root  # noqa: E402

SIZE_PRESETS = {
    "square": (1024, 1024),
    "portrait": (768, 1360),
    "wide": (1360, 768),
    "fast": (768, 768),
}

RUBRIC_KEYS = ["distinctiveness", "purity", "detail_quality", "composition", "usability"]

# One manifest filename for every producer (benchmark and mix), so board/report/score
# always find the same file regardless of which command created the run.
MANIFEST_NAME = "benchmark_manifest.json"

# Styles used for the controlled cross-media comparison (same subject, different medium).
CONTROLLED_DEFAULT_STYLES = [
    "editorial_fashion",
    "street_documentary",
    "black_white_noir",
    "vintage_film",
    "chinese_ink_wash",
    "gongbi_flower_bird",
    "shinkai_scenery",
    "watercolor",
]

MODEL_CARD = {
    "engine": "z_image_turbo",
    "weights": "z-image-turbo-Q4_K_M.gguf",
    "text_encoder": "Qwen3-4B-Q4_K_M.gguf (lumina2)",
    "vae": "ae.safetensors",
    "steps": 8,
    "cfg": 1.0,
    "sampler": "euler",
    "scheduler": "simple",
    "negative_prompt": "",
    "device": "Intel Arc A750 8GB (XPU)",
}


# --------------------------------------------------------------------------- helpers
def load_produce_module():
    """Import src/produce.py by file path (src/ is not a package)."""
    path = REPO_ROOT / "src" / "produce.py"
    spec = importlib.util.spec_from_file_location("drama_produce", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load production module at {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def save_grayscale_variant(src: Path) -> Path:
    """Deliver a pure-ink variant alongside the original.

    Measured: Z-Image pulls a blue-green landscape prior for mountain subjects even when the
    prompt demands monochrome ink, and stronger positive wording does not suppress it. The leak
    is chroma-only (mean S 18.9/255), so luminance desaturation recovers a clean ink painting
    without touching the brush structure.
    """
    from PIL import Image
    out = src.with_name(src.stem + "_MONO.png")
    Image.open(src).convert("L").convert("RGB").save(out)
    return out


def wait_for_comfy(produce, timeout_s: int = 180, poll_s: float = 5.0) -> bool:
    """Block until ComfyUI answers /system_stats, or give up after timeout_s."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if produce.check_comfy_live():
            return True
        time.sleep(poll_s)
    return produce.check_comfy_live()


def looks_like_connection_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(t in text for t in ("urlerror", "connectionrefused", "10061", "timed out",
                                   "timeout", "remotedisconnected", "connection aborted"))


def default_run_root() -> Path:
    try:
        root = output_root() / "experiments" / "z_image_styles"
    except Exception:
        root = REPO_ROOT / "build" / "experiments" / "z_image_styles"
    root.mkdir(parents=True, exist_ok=True)
    return root


def format_table(rows: list[list[str]], headers: list[str]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)))
    fmt = " | ".join(f"{{:<{w}}}" for w in widths)
    sep = "-+-".join("-" * w for w in widths)
    return "\n".join([fmt.format(*headers), sep] + [fmt.format(*r) for r in rows])


def job_key(job: dict) -> str:
    return (f"{job['style_id']}|{job['mode']}|{job['subject_key'] or '-'}|"
            f"{job['seed']}|{job['width']}x{job['height']}")


def load_manifest(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "schema_version": "2.1",
        "model": MODEL_CARD,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": None,
        "rubric_criteria": [
            {"key": k, "name_cn": cn, "question": q}
            for k, cn, q in ZImageBenchmarkSuite.RUBRIC_CRITERIA
        ],
        "runs": [],
    }


def save_manifest(path: Path, manifest: dict) -> None:
    manifest["updated_at"] = datetime.now().isoformat(timespec="seconds")
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# --------------------------------------------------------------------------- commands
def cmd_list(args):
    atlas = ZImageStyleAtlas()
    styles = atlas.list_styles(category=args.category)
    cats = atlas.list_categories()
    print("\n" + "=" * 100)
    print(f"  Z-Image Turbo Visual Style Atlas · {atlas.count()} styles registered ({len(styles)} shown)")
    print("=" * 100)
    rows = [
        [s.code, s.id, s.name, s.name_en, f"[{s.category}] {cats.get(s.category, {}).get('name', '')}"]
        for s in styles
    ]
    print(format_table(rows, ["No.", "Style ID", "中文名", "English Name", "Category"]))
    print("=" * 100 + "\n")


def cmd_compile(args):
    atlas = ZImageStyleAtlas()
    compiler = ZImagePromptCompiler()
    style = atlas.get_style(args.style)
    vocab_overrides = ZImageVocabulary().resolve(args.vocab) if args.vocab else {}
    compiled = compiler.compile(
        style=style,
        subject=args.subject or vocab_overrides.get("subject"),
        scene=args.scene or vocab_overrides.get("scene"),
        composition=args.composition or vocab_overrides.get("composition"),
        lighting=args.lighting or vocab_overrides.get("lighting"),
        medium_style=args.medium or vocab_overrides.get("medium_style"),
        color_texture=args.color or vocab_overrides.get("color_texture"),
        constraints=args.constraints or vocab_overrides.get("constraints"),
        text_quote=args.text,
    )
    print("\n" + "=" * 80)
    print(f"  7-Dimension Compilation · [{style.code}] {style.name} ({style.name_en})")
    print("=" * 80)
    print(f"  Category:    {style.category} | Application: {style.application}")
    print("-" * 80)
    print("[Recipe baseline positive_prompt]:")
    print(f"  {style.positive_prompt}\n")
    print("[Compiled 7-dimension prompt]:")
    print(f"  {compiled}\n")
    print("[Inference directives]:")
    print(f"  {MODEL_CARD['engine']} | steps={MODEL_CARD['steps']} cfg={MODEL_CARD['cfg']} "
          f"{MODEL_CARD['sampler']}/{MODEL_CARD['scheduler']} | negative prompt: NONE")
    print("=" * 80 + "\n")
    if args.json:
        print(json.dumps({"style_id": style.id, "prompt": compiled}, ensure_ascii=False, indent=2))


def cmd_vocab(args):
    vocab = ZImageVocabulary()
    dims = [args.dimension] if args.dimension else vocab.dimensions()
    print("\n" + "=" * 100)
    print(f"  Z-Image 7-Dimension Vocabulary Bank · {vocab.count()} reusable phrases")
    print("=" * 100)
    for dim in dims:
        entries = vocab.entries(dim)
        print(f"\n[{dim}]  ({len(entries)} entries)")
        rows = [[k, v.get("cn", ""), v.get("en", "")[:70]] for k, v in entries.items()]
        print(format_table(rows, ["entry_id", "中文", "English phrase (truncated)"]))
    print("\n用法: compile -s <style> --vocab \"lighting:low_key_neon,composition:intimate_close_up\"")
    print("=" * 100 + "\n")


def cmd_mix(args):
    """Cross-style combination experiment, e.g. Song aesthetics + luxury commercial lighting."""
    atlas = ZImageStyleAtlas()
    # --borrow is optional: without it this is a pure vocabulary override on the base style,
    # which is how a single recipe dimension gets A/B tested against the original.
    borrow_id = args.borrow or args.base
    dims = [d.strip() for d in args.dims.split(",") if d.strip()] if args.borrow else []
    overrides = ZImageVocabulary().resolve(args.vocab) if args.vocab else {}
    if args.subject:
        overrides["subject"] = args.subject
    if args.scene:
        overrides["scene"] = args.scene
    if args.text:
        overrides["text_quote"] = args.text

    result = compile_style_mix(atlas, args.base, borrow_id, dims, **overrides)
    print("\n" + "=" * 90)
    print(f"  Style Mix Experiment · {result['base_style']}  <-  {result['borrow_style']}")
    print(f"  Borrowed dimensions: {', '.join(result['borrowed_dimensions'])}")
    if result["medium_conflict_warning"]:
        print(f"  [!] {result['medium_conflict_warning']}")
    print("=" * 90)
    for d in DIMENSION_FIELDS:
        mark = "*" if d in result["borrowed_dimensions"] else " "
        print(f" {mark} {d:<14}: {result['dimensions'][d]}")
    print("-" * 90)
    print(result["prompt"])
    print("=" * 90 + "\n")

    if not args.live:
        return

    produce = load_produce_module()
    if not produce.check_comfy_live() and not wait_for_comfy(produce, timeout_s=180):
        raise SystemExit(f"[ABORT] ComfyUI offline at {produce.COMFY_URL}; run scripts\\start.ps1")
    run_dir = Path(args.run_dir) if args.run_dir else default_run_root() / "mixes"
    (run_dir / "images").mkdir(parents=True, exist_ok=True)
    width, height = SIZE_PRESETS[args.size]
    slug = f"mix_{result['base_style']}_x_{result['borrow_style']}_s{args.seed}"
    t0 = time.time()
    src = produce.produce_z_image_turbo(result["prompt"], width, height, args.seed, slug)
    dest = run_dir / "images" / f"{slug}.png"
    shutil.copy(src, dest)
    record = {
        **result,
        "code": "MIX",
        "name": f"{atlas.get_style(args.base).name} × {atlas.get_style(args.borrow).name}",
        "name_en": f"{result['base_style']} x {result['borrow_style']}",
        "style_id": f"{result['base_style']}_x_{result['borrow_style']}",
        "category": atlas.get_style(args.base).category,
        "mode": "mix",
        "subject_key": None,
        "status": "LIVE_GENERATED",
        "seed": args.seed,
        "width": width,
        "height": height,
        "image_path": str(dest),
        "elapsed_s": round(time.time() - t0, 1),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL_CARD,
        "scores": {k: None for k in RUBRIC_KEYS},
        "notes": "",
    }
    mpath = run_dir / MANIFEST_NAME
    manifest = load_manifest(mpath)
    manifest["runs"] = [r for r in manifest.get("runs", []) if r.get("image_path") != str(dest)] + [record]
    save_manifest(mpath, manifest)
    print(f"[+] Mix generated -> {dest} ({record['elapsed_s']}s)")
    print(f"[+] Manifest -> {mpath}")


def build_plan(atlas, suite, args) -> list[dict]:
    compiler = ZImagePromptCompiler()
    width, height = SIZE_PRESETS[args.size]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    if args.styles:
        style_ids = [s.strip() for s in args.styles.split(",") if s.strip()]
    elif args.mode == "controlled":
        style_ids = list(CONTROLLED_DEFAULT_STYLES)
    elif args.all:
        style_ids = [s.id for s in atlas.list_styles()]
    else:
        style_ids = list(suite.DEFAULT_EVAL_STYLES)

    modes = ["recipe", "controlled"] if args.mode == "both" else [args.mode]
    plan: list[dict] = []
    for sid in style_ids:
        style = atlas.get_style(sid)  # raises on typo instead of silently skipping
        for mode in modes:
            if mode == "recipe":
                prompt, subject_key = style.positive_prompt, None
            else:
                subject_key = args.subject_key
                prompt = compiler.compile(
                    style=style, subject=suite.CANONICAL_SUBJECTS[subject_key]
                )
            for seed in seeds:
                plan.append({
                    "style_id": style.id,
                    "code": style.code,
                    "category": style.category,
                    "name": style.name,
                    "name_en": style.name_en,
                    "mode": mode,
                    "subject_key": subject_key,
                    "seed": seed,
                    "width": width,
                    "height": height,
                    "prompt": prompt,
                    "prompt_source": "recipe.positive_prompt" if mode == "recipe" else "compiler.7dim",
                    "postprocess": style.postprocess,
                    "mono_path": None,
                    "steps": MODEL_CARD["steps"],
                    "cfg": MODEL_CARD["cfg"],
                    "sampler": MODEL_CARD["sampler"],
                    "scheduler": MODEL_CARD["scheduler"],
                    "status": "PENDING",
                    "image_path": None,
                    "elapsed_s": None,
                    "error": None,
                    "scores": {k: None for k in RUBRIC_KEYS},
                    "notes": "",
                })
    if args.limit:
        plan = plan[: args.limit]
    return plan


def cmd_benchmark(args):
    atlas = ZImageStyleAtlas()
    suite = ZImageBenchmarkSuite(atlas)
    plan = build_plan(atlas, suite, args)

    run_dir = Path(args.run_dir) if args.run_dir else default_run_root() / args.run_name
    img_dir = run_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / MANIFEST_NAME

    # Always merge into an existing manifest: it may hold human rubric scores that a
    # re-run must not silently discard. Use --fresh to deliberately start a clean run.
    manifest = load_manifest(Path("__none__") if args.fresh else manifest_path)
    if args.fresh and manifest_path.exists():
        print(f"[!] --fresh: discarding previous manifest at {manifest_path}", flush=True)
    done = {job_key(r): r for r in manifest["runs"]}

    produce = None
    live = not args.dry_run
    if live:
        produce = load_produce_module()
        if not produce.check_comfy_live():
            print("[*] ComfyUI not answering; waiting up to 180s before giving up...", flush=True)
            if not wait_for_comfy(produce, timeout_s=180):
                # An explicit --live run must never silently degrade into a fake dry run.
                raise SystemExit(
                    "[ABORT] --live requested but ComfyUI is offline at "
                    f"{produce.COMFY_URL}. Start it with: scripts\\start.ps1 -Port 8188"
                )

    print("\n" + "=" * 100)
    print(f"  Z-Image Turbo Style Atlas Benchmark · {len(plan)} jobs")
    print(f"  Mode: {args.mode} | Seeds: {args.seeds} | Size: {args.size} "
          f"({SIZE_PRESETS[args.size][0]}x{SIZE_PRESETS[args.size][1]})")
    print(f"  Subject key (controlled): {args.subject_key}")
    print(f"  Run directory: {run_dir}")
    print(f"  Execution: {'LIVE PRODUCTION' if live else 'DRY-RUN VERIFICATION'} | resume={args.resume}")
    print("=" * 100, flush=True)

    t_start = time.time()
    generated = 0
    skipped = 0
    failed = 0
    timings: list[float] = []

    for i, job in enumerate(plan, 1):
        key = job_key(job)
        prev = done.get(key)
        if (args.resume and prev and prev.get("status") == "LIVE_GENERATED"
                and prev.get("image_path") and Path(prev["image_path"]).exists()):
            skipped += 1
            # Self-heal: a run started before a style gained a postprocess fix still gets the variant.
            if job.get("postprocess") == "grayscale" and not prev.get("mono_path"):
                prev["postprocess"] = "grayscale"
                prev["mono_path"] = str(save_grayscale_variant(Path(prev["image_path"])))
                save_manifest(manifest_path, manifest)
                print(f"       [+] added pure-ink variant {Path(prev['mono_path']).name}", flush=True)
            print(f"[{i:02d}/{len(plan):02d}] SKIP (cached) [{job['code']}] {job['style_id']} "
                  f"{job['mode']} s{job['seed']}", flush=True)
            continue

        eta = ""
        if timings:
            avg = sum(timings) / len(timings)
            eta = f" | ETA {(len(plan) - i) * avg / 60:.0f} min"
        print(f"\n[{i:02d}/{len(plan):02d}] [{job['code']}] {job['name']} ({job['name_en']}) "
              f"· {job['mode']} · seed {job['seed']}{eta}", flush=True)
        print(f"       prompt: {job['prompt'][:100]}...", flush=True)

        if not live:
            job["status"] = "DRY_RUN_VERIFIED"
            job["elapsed_s"] = 0.0
        else:
            prefix = f"atlas_{job['code']}_{job['style_id']}_{job['mode']}_s{job['seed']}"
            t0 = time.time()
            for attempt in (1, 2):
                try:
                    src_img = produce.produce_z_image_turbo(
                        prompt=job["prompt"],
                        width=job["width"],
                        height=job["height"],
                        seed=job["seed"],
                        prefix=prefix,
                    )
                    dest = img_dir / f"{prefix}.png"
                    shutil.copy(src_img, dest)
                    job["image_path"] = str(dest)
                    job["elapsed_s"] = round(time.time() - t0, 1)
                    if job.get("postprocess") == "grayscale":
                        job["mono_path"] = str(save_grayscale_variant(dest))
                    job["status"] = "LIVE_GENERATED"
                    job["error"] = None
                    timings.append(job["elapsed_s"])
                    generated += 1
                    print(f"       [+] {dest.name} ({job['elapsed_s']}s)", flush=True)
                    break
                except Exception as exc:  # a single failure must not kill the whole sweep
                    job["status"] = "ERROR"
                    job["error"] = f"{type(exc).__name__}: {exc}"
                    job["elapsed_s"] = round(time.time() - t0, 1)
                    print(f"       [-] attempt {attempt} failed: {job['error']}", flush=True)
                    if attempt == 1 and looks_like_connection_error(exc):
                        print("       [*] server lost; waiting up to 300s then retrying once...",
                              flush=True)
                        if wait_for_comfy(produce, timeout_s=300):
                            continue
                    failed += 1
                    break

        if prev:  # keep human-entered rubric scores and notes across a regeneration
            if any(v is not None for v in prev.get("scores", {}).values()):
                job["scores"] = prev["scores"]
            if prev.get("notes"):
                job["notes"] = prev["notes"]
        done[key] = job
        manifest["runs"] = sorted(
            done.values(), key=lambda r: (r["mode"], r["category"], r["code"], r["seed"])
        )
        save_manifest(manifest_path, manifest)

    elapsed = time.time() - t_start
    print("\n" + "=" * 100)
    print(f"  Sweep finished in {elapsed / 60:.1f} min · generated={generated} "
          f"cached={skipped} failed={failed}")
    if timings:
        print(f"  Mean per image: {sum(timings) / len(timings):.1f}s")
    print(f"  Manifest: {manifest_path}")
    print("=" * 100 + "\n", flush=True)

    write_report(run_dir, manifest)
    if generated and not args.no_board:
        write_boards(run_dir, manifest)


# --------------------------------------------------------------------------- boards
def _load_font(size: int):
    from PIL import ImageFont
    candidates = [
        REPO_ROOT / "assets" / "fonts" / "source-han-sans-cn" / "SourceHanSansCN-Medium.otf",
        REPO_ROOT / "assets" / "fonts" / "source-han-sans-cn" / "SourceHanSansCN-Regular.otf",
    ]
    for c in candidates:
        if c.exists():
            try:
                return ImageFont.truetype(str(c), size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_board(entries: list[dict], out_path: Path, title: str, cols: int = 4, thumb: int = 384):
    from PIL import Image, ImageDraw
    entries = [e for e in entries if e.get("image_path") and Path(e["image_path"]).exists()]
    if not entries:
        return None
    cols = max(1, min(cols, len(entries)))
    rows = (len(entries) + cols - 1) // cols
    label_h, pad, banner = 56, 12, 76
    cell_w, cell_h = thumb + pad, thumb + label_h + pad
    canvas = Image.new("RGB", (cols * cell_w + pad, banner + rows * cell_h + pad), (18, 20, 24))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad + 6, 18), title, fill=(240, 240, 240), font=_load_font(26))
    draw.text((pad + 6, 50),
              f"Z-Image Turbo · 8 steps · CFG 1.0 · euler/simple · zero negative prompt · {len(entries)} frames",
              fill=(150, 160, 175), font=_load_font(16))
    f_label, f_sub = _load_font(19), _load_font(15)

    def fit(text: str, font, max_px: int) -> str:
        """Truncate by rendered width, not character count, so labels never bleed into the next cell."""
        if font.getlength(text) <= max_px:
            return text
        while text and font.getlength(text + "…") > max_px:
            text = text[:-1]
        return text.rstrip() + "…"

    for idx, e in enumerate(entries):
        r, c = divmod(idx, cols)
        x, y = pad + c * cell_w, banner + pad + r * cell_h
        try:
            im = Image.open(e["image_path"]).convert("RGB")
        except Exception:
            continue
        im.thumbnail((thumb, thumb), Image.LANCZOS)
        canvas.paste(im, (x + (thumb - im.width) // 2, y + (thumb - im.height) // 2))
        ly = y + thumb + 4
        draw.text((x + 2, ly), fit(f"{e['code']}｜{e['name']}", f_label, thumb - 4),
                  fill=(235, 238, 245), font=f_label)
        sub = f"{e['name_en']} · {e['mode']} · seed {e['seed']}"
        draw.text((x + 2, ly + 26), fit(sub, f_sub, thumb - 4), fill=(150, 162, 180), font=f_sub)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=92)
    print(f"[Board] {out_path.name} ({len(entries)} frames)")
    return out_path


def write_boards(run_dir: Path, manifest: dict):
    runs = [r for r in manifest["runs"] if r.get("status") == "LIVE_GENERATED"]
    if not runs:
        return
    board_dir = run_dir / "boards"
    cats = ZImageStyleAtlas().list_categories()
    for mode in sorted({r["mode"] for r in runs}):
        subset = [r for r in runs if r["mode"] == mode]
        make_board(subset, board_dir / f"atlas_{mode}_ALL.jpg",
                   f"Z-Image Visual Style Atlas · {mode} sweep · ALL", cols=6, thumb=320)
        for cat in sorted({r["category"] for r in subset}):
            cat_runs = [r for r in subset if r["category"] == cat]
            info = cats.get(cat, {})
            make_board(cat_runs, board_dir / f"atlas_{mode}_{cat}.jpg",
                       f"[{cat}] {info.get('name', '')} · {info.get('name_en', '')} · {mode}",
                       cols=3, thumb=420)


def cmd_board(args):
    run_dir = Path(args.run_dir)
    write_boards(run_dir, load_manifest(run_dir / MANIFEST_NAME))


# --------------------------------------------------------------------------- report
def write_report(run_dir: Path, manifest: dict):
    runs = manifest["runs"]
    live = [r for r in runs if r.get("status") == "LIVE_GENERATED"]
    errs = [r for r in runs if r.get("status") == "ERROR"]
    dry = [r for r in runs if r.get("status") == "DRY_RUN_VERIFIED"]
    times = [r["elapsed_s"] for r in live if r.get("elapsed_s")]
    scored = [r for r in runs if any(v is not None for v in r["scores"].values())]

    md = run_dir / "Z_IMAGE_STYLE_BENCHMARK_REPORT.md"
    with open(md, "w", encoding="utf-8") as f:
        f.write("# Z-Image Turbo 风格图谱实测报告 (Style Atlas Benchmark Report)\n\n")
        f.write(f"- **生成时间**: {manifest.get('updated_at') or manifest.get('created_at')}\n")
        m = manifest["model"]
        f.write(f"- **引擎**: `{m['engine']}` · `{m['weights']}` · {m['device']}\n")
        f.write(f"- **推理参数**: steps={m['steps']} · CFG={m['cfg']} · {m['sampler']}/{m['scheduler']} · "
                f"Negative Prompt: 无（零负面提示词范式）\n")
        f.write(f"- **任务总数**: {len(runs)} · 实拍成功 **{len(live)}** · 失败 {len(errs)} · 干跑校验 {len(dry)}\n")
        if times:
            f.write(f"- **单图耗时**: 均值 {sum(times) / len(times):.1f}s · "
                    f"最快 {min(times):.1f}s · 最慢 {max(times):.1f}s · 累计 {sum(times) / 60:.1f} min\n")
        f.write(f"- **已评分**: {len(scored)} / {len(runs)}\n")
        reviewers = sorted({r.get("reviewer") for r in scored if r.get("reviewer")})
        if reviewers:
            f.write(f"- **评分来源**: {', '.join(reviewers)}\n")
        f.write("\n> 评分由 `score` / `score-import` 显式写入，脚本不会自动编造分数。未评分项显示 `—`。\n")
        f.write("> `reviewer=claude-visual-review` 是模型看图给出的初评，供人工复核后定稿。\n\n")

        for mode in sorted({r["mode"] for r in runs}):
            subset = [r for r in runs if r["mode"] == mode]
            f.write(f"## 模式：{mode}\n\n")
            if mode == "controlled":
                keys = sorted({r["subject_key"] for r in subset if r["subject_key"]})
                f.write(f"统一对照主体：`{', '.join(keys)}`"
                        "（同一主体跨媒介对比，用于分离“模型风格能力”与“主体本身难易”）\n\n")
            else:
                f.write("每个风格使用其自身配方 `positive_prompt`（图谱原生配方，主体随风格设计）。\n\n")
            f.write("| 编号 | 风格 | English | 分类 | Seed | 状态 | 耗时 | 辨识度 | 纯度 | 细节 | 构图 | 可用性 | 均分 | 图片 |\n")
            f.write("| :-- | :-- | :-- | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | :-- |\n")
            for r in subset:
                vals = [r["scores"].get(k) for k in RUBRIC_KEYS]
                cells = [str(v) if v is not None else "—" for v in vals]
                known = [v for v in vals if isinstance(v, (int, float))]
                avg = f"{sum(known) / len(known):.1f}" if known else "—"
                img = f"[png](images/{Path(r['image_path']).name})" if r.get("image_path") else "—"
                if r.get("mono_path"):
                    img += f" · [纯墨](images/{Path(r['mono_path']).name})"
                el = f"{r['elapsed_s']:.0f}s" if r.get("elapsed_s") else "—"
                f.write(f"| {r['code']} | {r['name']} | {r['name_en']} | {r['category']} | {r['seed']} | "
                        f"{r['status']} | {el} | {' | '.join(cells)} | {avg} | {img} |\n")
            f.write("\n")

        ranked = []
        for r in runs:
            vals = [r["scores"].get(k) for k in RUBRIC_KEYS]
            known = [v for v in vals if isinstance(v, (int, float))]
            if known:
                ranked.append((sum(known) / len(known), r))
        if ranked:
            ranked.sort(key=lambda t: (-t[0], t[1]["code"]))
            f.write("## 评分总览\n\n")
            f.write("### 均分最高（可直接进生产）\n\n")
            f.write("| 均分 | 编号 | 风格 | 模式 | Seed |\n| --: | :-- | :-- | :-- | :-- |\n")
            for avg, r in ranked[:10]:
                f.write(f"| {avg:.1f} | {r['code']} | {r['name']} | {r['mode']} | {r['seed']} |\n")
            flagged = [(a, r) for a, r in ranked
                       if any(isinstance(v, (int, float)) and v <= 3 for v in r["scores"].values())]
            f.write("\n### 需要修订后才可用（任一维度 ≤ 3）\n\n")
            if flagged:
                f.write("| 编号 | 风格 | 模式 | 低分维度 | 观察 |\n| :-- | :-- | :-- | :-- | :-- |\n")
                for _, r in flagged:
                    low = [f"{k}={r['scores'][k]}" for k in RUBRIC_KEYS
                           if isinstance(r["scores"].get(k), (int, float)) and r["scores"][k] <= 3]
                    note = (r.get("notes") or "").replace("|", "/")
                    f.write(f"| {r['code']} | {r['name']} | {r['mode']} | {', '.join(low)} | {note} |\n")
            else:
                f.write("无。\n")
            f.write("\n")

        if errs:
            f.write("## 失败记录\n\n")
            for r in errs:
                f.write(f"- [{r['code']}] {r['style_id']} {r['mode']} s{r['seed']}: `{r.get('error')}`\n")
            f.write("\n")

        notes = [r for r in runs if r.get("notes")]
        if notes:
            f.write("## 实测观察备注\n\n")
            for r in notes:
                f.write(f"- **[{r['code']}] {r['name']}** ({r['mode']} s{r['seed']}): {r['notes']}\n")
            f.write("\n")

        f.write("## 五维评分标准 (Rubric)\n\n")
        for c in manifest["rubric_criteria"]:
            f.write(f"- **{c['name_cn']} ({c['key']})**: {c['question']} · 1~5 分\n")
        f.write("\n## 复现命令\n\n```powershell\n")
        f.write(".venv\\Scripts\\python.exe scripts\\run_z_image_style_atlas.py benchmark "
                "--mode recipe --all --seeds 42 --size square --live --resume\n")
        f.write(".venv\\Scripts\\python.exe scripts\\run_z_image_style_atlas.py score "
                f"--run-dir \"{run_dir}\" --style editorial_fashion --mode recipe --seed 42 "
                "--distinctiveness 5 --purity 5 --detail 4 --composition 5 --usability 5 "
                "--notes \"...\"\n```\n")
    print(f"[Report] {md}")

    csv_path = run_dir / "scores.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "style_id", "name", "name_en", "category", "mode", "subject_key", "seed",
                    "status", "elapsed_s"] + RUBRIC_KEYS + ["mean", "notes", "image_path"])
        for r in runs:
            vals = [r["scores"].get(k) for k in RUBRIC_KEYS]
            known = [v for v in vals if isinstance(v, (int, float))]
            mean = round(sum(known) / len(known), 2) if known else ""
            w.writerow([r["code"], r["style_id"], r["name"], r["name_en"], r["category"], r["mode"],
                        r["subject_key"] or "", r["seed"], r["status"], r.get("elapsed_s") or ""]
                       + ["" if v is None else v for v in vals]
                       + [mean, r.get("notes", ""), r.get("image_path") or ""])
    print(f"[Scores] {csv_path}")


def cmd_report(args):
    run_dir = Path(args.run_dir)
    write_report(run_dir, load_manifest(run_dir / MANIFEST_NAME))


def cmd_score_import(args):
    """Import a filled scores CSV back into the manifest (Excel-friendly review loop)."""
    run_dir = Path(args.run_dir)
    mpath = run_dir / MANIFEST_NAME
    manifest = load_manifest(mpath)
    index = {(r["style_id"], r["mode"], r["seed"]): r for r in manifest["runs"]}

    updated, missing, bad = 0, [], []
    with open(args.csv, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sid = (row.get("style_id") or "").strip()
            mode = (row.get("mode") or "").strip()
            try:
                seed = int((row.get("seed") or "").strip())
            except ValueError:
                bad.append(f"{sid}/{mode}: bad seed")
                continue
            entry = index.get((sid, mode, seed))
            if entry is None:
                missing.append(f"{sid}/{mode}/s{seed}")
                continue
            touched = False
            for key in RUBRIC_KEYS:
                raw = (row.get(key) or "").strip()
                if not raw:
                    continue
                try:
                    val = int(float(raw))
                except ValueError:
                    bad.append(f"{sid}/{mode}/s{seed}: {key}={raw!r}")
                    continue
                if not 1 <= val <= 5:
                    bad.append(f"{sid}/{mode}/s{seed}: {key}={val} out of 1..5")
                    continue
                entry["scores"][key] = val
                touched = True
            if (row.get("notes") or "").strip():
                entry["notes"] = row["notes"].strip()
                touched = True
            if touched:
                entry["reviewer"] = args.reviewer
                updated += 1

    save_manifest(mpath, manifest)
    print(f"[ScoreImport] updated {updated} entries (reviewer={args.reviewer})")
    if missing:
        print(f"[ScoreImport] {len(missing)} rows had no matching entry: {missing[:5]}")
    if bad:
        print(f"[ScoreImport] {len(bad)} invalid cells skipped: {bad[:5]}")
    write_report(run_dir, manifest)


def cmd_score(args):
    run_dir = Path(args.run_dir)
    mpath = run_dir / MANIFEST_NAME
    manifest = load_manifest(mpath)
    updates = {
        "distinctiveness": args.distinctiveness,
        "purity": args.purity,
        "detail_quality": args.detail,
        "composition": args.composition,
        "usability": args.usability,
    }
    hits = 0
    for r in manifest["runs"]:
        if r["style_id"] != args.style and r["code"] != args.style:
            continue
        if args.mode and r["mode"] != args.mode:
            continue
        if args.seed is not None and r["seed"] != args.seed:
            continue
        for k, v in updates.items():
            if v is not None:
                r["scores"][k] = v
        if args.notes:
            r["notes"] = args.notes
        if any(v is not None for v in updates.values()) or args.notes:
            r["reviewer"] = args.reviewer
        hits += 1
    if not hits:
        raise SystemExit(f"No manifest entry matched style={args.style} mode={args.mode} seed={args.seed}")
    save_manifest(mpath, manifest)
    print(f"[Score] updated {hits} entry/entries for {args.style}")
    write_report(run_dir, manifest)


# --------------------------------------------------------------------------- export
def cmd_export_atlas(args):
    atlas = ZImageStyleAtlas()
    cats = atlas.list_categories()
    styles = atlas.list_styles()
    out_file = REPO_ROOT / "docs" / "Z_IMAGE_TURBO_STYLE_ATLAS.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# Z-Image Turbo 视觉风格图谱与 Prompt 写法体系 (Visual Style Atlas)\n\n")
        f.write("> 面向生产的本地 6B 单流 DiT 风格实验库与提示词体系。"
                "本文件由 `scripts/run_z_image_style_atlas.py export-atlas` 从 "
                "`config/z_image_styles.yaml` 自动生成，请勿手工编辑。\n\n")
        f.write("> 实测结论（评分、失败模式、已验证修法、吞吐基线）见 "
                "[Z_IMAGE_STYLE_FINDINGS.md](Z_IMAGE_STYLE_FINDINGS.md)。\n\n")
        f.write("## 一、Z-Image Turbo 官方提示词工程规范\n\n")
        f.write("1. **自然语言长句描述**：细节充实的完整段落，禁止 `masterpiece, 8k, best quality` 标签堆叠。\n")
        f.write("2. **零负面提示词 (Zero Negative Prompt)**：少步蒸馏 DiT（8 次前向），"
                "不依赖传统 CFG；否定约束一律转成正向语言（如 `a clean empty background without graphic overlays`）。\n")
        f.write("3. **画面文字精准控制**：需要出现的文字必须用英文双引号标明（如 `\"STATION\"`）。\n")
        f.write("4. **7 维度结构**：Subject / Scene / Composition / Lighting / Medium & Style / "
                "Color & Texture / Constraints。\n")
        f.write("5. **一次只给一个主风格**：不要把水墨 + 3D 卡通 + 写实摄影 + 赛博朋克堆在同一 Prompt。\n\n")
        f.write(f"## 二、{len(styles)} 套视觉风格完整配方库\n\n")
        for cat_id, cat_info in cats.items():
            cat_styles = [s for s in styles if s.category == cat_id]
            if not cat_styles:
                continue
            f.write(f"### {cat_id}. {cat_info.get('name')} ({cat_info.get('name_en')}) "
                    f"· 优先级 {cat_info.get('priority', '')}\n\n")
            for s in cat_styles:
                f.write(f"#### {s.code}｜{s.name} ({s.name_en}) · `{s.id}`\n\n")
                f.write(f"- **适用场景**: {s.application}\n- **7 维度特征表**:\n")
                for label, val in [
                    ("Subject", s.dimensions.subject), ("Scene", s.dimensions.scene),
                    ("Composition", s.dimensions.composition), ("Lighting", s.dimensions.lighting),
                    ("Medium & Style", s.dimensions.medium_style),
                    ("Color & Texture", s.dimensions.color_texture),
                    ("Constraints", s.dimensions.constraints),
                ]:
                    f.write(f"  - **{label}**: {val}\n")
                f.write("\n```text\n" + s.positive_prompt + "\n```\n\n")
        vocab = ZImageVocabulary()
        f.write("## 三、七维度视觉词典与组合实验\n\n")
        f.write("配方库是成品菜，词典是调料架。当 38 套配方都不合适时，"
                "用 `config/z_image_style_vocabulary.yaml` 里的客观视觉词条按 7 维度组装新风格，"
                "而不是继续堆标签。\n\n")
        f.write("| 维度 | 词条数 | 示例 entry_id |\n| :-- | --: | :-- |\n")
        for dim in vocab.dimensions():
            ids = list(vocab.entries(dim))
            f.write(f"| `{dim}` | {len(ids)} | {', '.join(f'`{i}`' for i in ids[:3])} |\n")
        f.write("\n```powershell\n")
        f.write("# 查词典\n")
        f.write("python src/produce.py atlas vocab --dimension lighting\n\n")
        f.write("# 用词典词条覆盖某几个维度\n")
        f.write('python src/produce.py atlas compile -s song_aesthetics '
                '--vocab "lighting:narrow_golden_spotlight,color_texture:celadon_mineral"\n\n')
        f.write("# 跨风格组合实验：宋式美学 + 奢侈品广告布光（只借光线与色彩，保留主媒介）\n")
        f.write('python src/produce.py atlas mix --base song_aesthetics --borrow luxury_product '
                '--dims lighting,color_texture --subject "a celadon tea bowl on a dark wooden table" --live\n')
        f.write("```\n\n")
        f.write("> **组合纪律**：一次只保留一个主媒介（`medium_style`）。"
                "借用 `medium_style` 时 CLI 会给出冲突告警——水墨 + 3D 卡通 + 写实摄影堆在一起只会得到风格糊。\n\n")

        f.write("## 四、实测工作台 (Benchmark Testbench)\n\n")
        f.write("```powershell\n")
        f.write("# 全量原生配方实拍（38 风格 x 1 seed）\n")
        f.write("python src/produce.py atlas benchmark --mode recipe --all --seeds 42 "
                "--size square --live --resume\n\n")
        f.write("# 同主体跨媒介对照（分离风格能力与主体难易）\n")
        f.write("python src/produce.py atlas benchmark --mode controlled --seeds 42,2026 "
                "--size square --live --resume\n\n")
        f.write("# 人工五维评分（脚本绝不自造分数）\n")
        f.write('python src/produce.py atlas score --run-dir "<run>" --style chinese_ink_wash '
                "--mode recipe --seed 42 --distinctiveness 5 --purity 3 --detail 4 "
                '--composition 5 --usability 4 --notes "水墨成立但混入青绿色块"\n\n')
        f.write("# 重建拼版与报告\n")
        f.write('python src/produce.py atlas board --run-dir "<run>"\n')
        f.write('python src/produce.py atlas report --run-dir "<run>"\n')
        f.write("```\n\n")
        f.write("运行目录结构（位于输出根 `experiments/z_image_styles/<run-name>/`）：\n\n")
        f.write("- `images/` 实拍原图，文件名含编号、风格 ID、模式与 seed\n")
        f.write("- `boards/` 分类拼版 + 全量总览拼版（CJK 标注）\n")
        f.write("- `benchmark_manifest.json` 逐图增量落盘，含完整 Prompt、耗时、状态、评分位\n")
        f.write("- `Z_IMAGE_STYLE_BENCHMARK_REPORT.md` / `scores.csv` 实测报告与评分表\n\n")
        f.write("工程约束：\n\n")
        f.write("- `--live` 且 ComfyUI 离线时**直接报错退出**，不会伪装成干跑成功。\n")
        f.write("- 单图失败不中断整轮；连接类错误等待服务器恢复后自动重试一次。\n")
        f.write("- `--resume` 按 `风格|模式|主体|seed|分辨率` 去重，可随时中断续跑。\n")
        f.write("- 五维评分初始为 `null`，只能由人工 `score` 写入。\n\n")

        f.write("## 五、生产调用方式\n\n```powershell\n")
        f.write("# 单图生产（自动路由 Z-Image Turbo）\n")
        f.write("python src/produce.py image --project <id> --type portrait --style song_aesthetics "
                "--subject \"a celadon tea bowl on a dark wooden table\"\n\n")
        f.write("# 图谱批量实测\n")
        f.write("python scripts/run_z_image_style_atlas.py benchmark --mode recipe --all "
                "--seeds 42 --size square --live --resume\n")
        f.write("```\n")
    print(f"[+] Atlas exported -> {out_file} ({len(styles)} styles)")


# --------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description="Z-Image Turbo Visual Style Atlas CLI")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("list", help="List styles in the atlas")
    pl.add_argument("--category", "-c", choices=list("ABCDEFGHT"))

    pc = sub.add_parser("compile", help="Compile a 7-dimension prompt")
    pc.add_argument("--style", "-s", required=True)
    pc.add_argument("--subject")
    pc.add_argument("--scene")
    pc.add_argument("--composition")
    pc.add_argument("--lighting")
    pc.add_argument("--medium")
    pc.add_argument("--color")
    pc.add_argument("--constraints")
    pc.add_argument("--text", help="On-screen text, will be double-quoted")
    pc.add_argument("--vocab", help='Vocabulary overrides, e.g. "lighting:low_key_neon,composition:intimate_close_up"')
    pc.add_argument("--json", action="store_true")

    pv = sub.add_parser("vocab", help="List the reusable 7-dimension phrase bank")
    pv.add_argument("--dimension", "-d", choices=list(DIMENSION_FIELDS))

    pm = sub.add_parser("mix", help="Cross-style combination experiment")
    pm.add_argument("--base", required=True, help="Base style ID/code (keeps its identity)")
    pm.add_argument("--borrow", help="Style to borrow dimensions from (omit for a pure vocabulary override)")
    pm.add_argument("--dims", default="lighting,color_texture",
                    help="Comma-separated dimensions to borrow (default: lighting,color_texture)")
    pm.add_argument("--subject")
    pm.add_argument("--scene")
    pm.add_argument("--text")
    pm.add_argument("--vocab", help="Additional vocabulary overrides")
    pm.add_argument("--size", choices=list(SIZE_PRESETS), default="square")
    pm.add_argument("--seed", type=int, default=42)
    pm.add_argument("--live", action="store_true", help="Actually generate the mix via ComfyUI")
    pm.add_argument("--run-dir")

    pb = sub.add_parser("benchmark", help="Run the style sweep")
    pb.add_argument("--mode", choices=["recipe", "controlled", "both"], default="recipe")
    pb.add_argument("--styles", help="Comma-separated style IDs/codes (overrides default set)")
    pb.add_argument("--all", action="store_true", help="Sweep every registered style")
    pb.add_argument("--seeds", default="42", help="Comma-separated seeds, e.g. 42,2026")
    pb.add_argument("--subject-key", choices=list(ZImageBenchmarkSuite.CANONICAL_SUBJECTS),
                    default="portrait")
    pb.add_argument("--size", choices=list(SIZE_PRESETS), default="square")
    pb.add_argument("--limit", type=int, help="Cap number of jobs (smoke tests)")
    pb.add_argument("--dry-run", action="store_true", default=True)
    pb.add_argument("--live", dest="dry_run", action="store_false")
    pb.add_argument("--resume", action="store_true", help="Reuse finished images in the run dir")
    pb.add_argument("--fresh", action="store_true",
                    help="Discard the existing manifest (including human scores) and start clean")
    pb.add_argument("--run-name", default="atlas_v1", help="Sub-directory under experiments/z_image_styles")
    pb.add_argument("--run-dir", help="Explicit run directory (overrides --run-name)")
    pb.add_argument("--no-board", action="store_true")

    pbd = sub.add_parser("board", help="Rebuild contact sheets")
    pbd.add_argument("--run-dir", required=True)

    pr = sub.add_parser("report", help="Rebuild report + CSV")
    pr.add_argument("--run-dir", required=True)

    ps = sub.add_parser("score", help="Record human rubric scores")
    ps.add_argument("--run-dir", required=True)
    ps.add_argument("--style", required=True)
    ps.add_argument("--mode", choices=["recipe", "controlled"])
    ps.add_argument("--seed", type=int)
    for name in ["distinctiveness", "purity", "detail", "composition", "usability"]:
        ps.add_argument(f"--{name}", type=int, choices=range(1, 6))
    ps.add_argument("--notes")
    ps.add_argument("--reviewer", default="human", help="Who entered these scores")

    psi = sub.add_parser("score-import", help="Import a filled scores CSV into the manifest")
    psi.add_argument("--run-dir", required=True)
    psi.add_argument("--csv", required=True)
    psi.add_argument("--reviewer", default="human")

    sub.add_parser("export-atlas", help="Regenerate the Markdown atlas doc")

    args = p.parse_args()
    {
        "list": cmd_list,
        "compile": cmd_compile,
        "vocab": cmd_vocab,
        "mix": cmd_mix,
        "benchmark": cmd_benchmark,
        "board": cmd_board,
        "report": cmd_report,
        "score": cmd_score,
        "score-import": cmd_score_import,
        "export-atlas": cmd_export_atlas,
    }[args.command](args)


if __name__ == "__main__":
    main()