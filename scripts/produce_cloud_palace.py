#!/usr/bin/env python3
"""scripts/produce_cloud_palace.py
「云上天宫」— an original Oriental celestial-fantasy short film, end to end.

Genre reference: the AI fantasy short "云上天宫｜AI打造的东方仙境" (YouTube fwcECmI1mYs).
Only the genre language is referenced (cloud sea, vermilion colonnade, lone pine,
white-robed scale figures, symmetry, mirror terrace). Every scene, prompt and frame
here is original and generated locally.

Pipeline (all local, A750 8GB + 64GB DDR5):
  keyframes  Z-Image Turbo 6B, 1360x768, driven by atlas style `cloud_palace_celestial`
  video      Wan 2.2-14B I2V dual-expert GGUF + LightX2V 6-step LoRA, 832x480, 49 frames
  post       2x Lanczos to 1664x960 + FFmpeg minterpolate optical-flow 32 fps
  assemble   concat + optional score mux

DELIBERATE DEVIATION FROM THE WIDESTCREEN GUARD
docs/WIDESCREEN_VIDEO_GENERATION_GUIDELINES.md forbids wide establishing shots at 480P
and auto-injects "medium close-up + bokeh". That rule exists to protect *face* tokens:
a 35-45px face collapses to 2-3 latent tokens. This film has no readable faces at all --
the figures are distant silhouette scale anchors, exactly as in the reference. Applying
the guard would destroy the symmetrical architectural composition that is the whole point.
So the guard is intentionally NOT applied here, and this run doubles as a test of whether
the 480P wide-shot penalty actually bites for *scenery* rather than faces. Findings are
recorded in the run manifest and report.

Usage:
  python scripts/produce_cloud_palace.py --stage keyframes
  python scripts/produce_cloud_palace.py --stage video --shots S01
  python scripts/produce_cloud_palace.py --stage all --resume
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from drama_studio.domain.style.z_image_atlas import (  # noqa: E402
    ZImageStyleAtlas,
    ZImagePromptCompiler,
)
from drama_studio.paths import output_root  # noqa: E402

STYLE_ID = "cloud_palace_celestial"
PROJECT_ID = "cloud_palace"

KEYFRAME_W, KEYFRAME_H = 1360, 768      # 16:9 keyframe, downscaled for the video anchor
VIDEO_W, VIDEO_H = 832, 480             # Wan 480P standard tier
POST_W, POST_H = 1664, 960              # 2x Lanczos delivery
FRAMES = 49                             # 4n+1; 3.06 s at 16 fps
RAW_FPS, POST_FPS = 16, 32

VIDEO_NEGATIVE = (
    "blur, distort, low quality, erratic jerking, morphing architecture, warping columns, "
    "melting stone, bending railings, duplicated figures, flickering, "
    "zoom in, dolly in, extreme close-up, cropping the subject out of frame, rushing camera"
)

# Motion is restricted to the class Wan handles reliably: slow camera moves plus
# atmospheric drift, with architecture explicitly held rigid.
SHOTS = [
    {
        "id": "S01",
        "title": "云廊",
        "title_en": "The Cloud Colonnade",
        "subject": None,   # use the style's own hero subject
        "scene": None,
        "composition": None,
        "motion": (
            "Extremely slow cinematic push-in along the terrace axis. The sea of clouds drifts slowly "
            "beneath the marble terrace. The distant white robes and long hair sway gently in the wind. "
            "The vermilion colonnade, railings and marble terrace stay perfectly rigid and unchanged. "
            "Fine atmospheric haze moves slowly through the frame."
        ),
    },
    {
        "id": "S02",
        "title": "孤松",
        "title_en": "The Lone Pine",
        "subject": "a single ancient windswept pine growing from a small rocky island suspended in the cloud sea",
        "scene": "high above an endless sea of clouds at golden hour, distant floating peaks fading into haze",
        "composition": "centered wide composition with the pine as the sole focal point, vast empty sky above, extensive negative space",
        # Take 1 used "very slow lateral drift" and Wan rendered a huge push-in that ended
        # on a trunk close-up, losing the island entirely. Degree adverbs do not constrain
        # magnitude; an explicit first/last framing lock does.
        "motion": (
            "Static camera, locked framing. The whole pine tree and its rocky island stay fully "
            "visible and centred at the same size in the last frame as in the first frame. "
            "Only the thin needles and small twigs sway gently in the wind. Clouds drift slowly "
            "far behind the island. The trunk, rocks and marble terrace remain rigid. "
            "No zoom, no dolly, no close-up, no change of shot scale."
        ),
    },
    {
        "id": "S03",
        "title": "白衣",
        "title_en": "White Robes",
        "subject": "two distant figures in flowing white robes seen from behind, standing at the edge of a white marble terrace above the clouds",
        "scene": "the far end of a vermilion colonnade opening onto an endless sea of clouds",
        "composition": "symmetrical wide shot, the two figures small against the vast cloud sea, framed by red timber columns, generous negative space",
        "motion": (
            "Static camera. The two white-robed figures stand still at the terrace edge while their robes, "
            "sleeves and long hair move gently in the wind. The cloud sea rolls slowly below. "
            "The columns, railings and terrace remain completely rigid. No walking, no turning around."
        ),
    },
    {
        "id": "S04",
        "title": "天阶",
        "title_en": "The Sky Stair",
        "subject": "a long white marble staircase descending from a celestial terrace down into an endless sea of clouds",
        "scene": "high above the clouds at golden hour, the lower steps disappearing into drifting mist",
        "composition": "symmetrical centered composition looking down the staircase, strong leading lines, vast cloud sea filling the lower frame",
        # Take 1's "clouds pour over the steps" swallowed both flanking towers by the last
        # frame. The atmosphere must be bounded explicitly, not just described as slow.
        "motion": (
            "Static camera, locked framing. The marble staircase and both flanking towers stay "
            "fully visible and unchanged in size and position from the first frame to the last. "
            "Only a thin low layer of mist drifts slowly across the bottom steps; the mist never "
            "rises above the base of the buildings and never covers them. "
            "The stone steps and balustrades stay rigid. No zoom, no tilt, no camera move."
        ),
    },
    {
        "id": "S05",
        "title": "远阙",
        "title_en": "The Distant Towers",
        "subject": "distant tiered palace towers with vermilion columns and pale tiled roofs rising above an endless sea of clouds",
        "scene": "sunset above the cloud sea, warm golden light on the roofs, cool blue shadow in the cloud valleys",
        "composition": "wide establishing composition, the towers occupying the upper third, an ocean of clouds below, extensive negative space",
        "motion": (
            "Very slow lateral reveal to the left. The cloud sea drifts slowly between the towers. "
            "Warm sunset light shifts subtly across the roofs. All buildings remain rigid and unchanged."
        ),
    },
]


def load_produce():
    path = REPO_ROOT / "src" / "produce.py"
    spec = importlib.util.spec_from_file_location("drama_produce", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_root() -> Path:
    root = output_root() / "experiments" / PROJECT_ID
    for sub in ("keyframes", "frames", "shots", "deliver", "reference"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def load_manifest(root: Path) -> dict:
    p = root / "film_manifest.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "project": PROJECT_ID,
        "title": "云上天宫",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "style_id": STYLE_ID,
        "reference": "YouTube fwcECmI1mYs (genre only; all scenes original)",
        "widescreen_guard": "intentionally not applied: no readable faces, figures are distant scale anchors",
        "keyframe": {"engine": "z_image_turbo", "width": KEYFRAME_W, "height": KEYFRAME_H,
                     "steps": 8, "cfg": 1.0},
        "video": {"engine": "wan22_14b_i2v", "width": VIDEO_W, "height": VIDEO_H,
                  "frames": FRAMES, "steps": 6, "cfg": 1.0, "shift": 5.0, "raw_fps": RAW_FPS},
        "post": {"width": POST_W, "height": POST_H, "fps": POST_FPS},
        "shots": {},
    }


def save_manifest(root: Path, m: dict) -> None:
    m["updated_at"] = datetime.now().isoformat(timespec="seconds")
    p = root / "film_manifest.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def shot_entry(m: dict, shot: dict) -> dict:
    return m["shots"].setdefault(shot["id"], {
        "id": shot["id"], "title": shot["title"], "title_en": shot["title_en"],
        "keyframe_path": None, "keyframe_prompt": None, "keyframe_s": None,
        "video_prompt": shot["motion"], "frames_dir": None, "frame_count": None, "video_s": None,
        "post_path": None, "post_s": None, "status": "PENDING", "error": None,
    })


def build_keyframe_prompt(style, shot) -> str:
    return ZImagePromptCompiler().compile(
        style=style,
        subject=shot["subject"],
        scene=shot["scene"],
        composition=shot["composition"],
    )


def stage_keyframes(root, m, shots, produce, resume, dry_run):
    style = ZImageStyleAtlas().get_style(STYLE_ID)
    for shot in shots:
        e = shot_entry(m, shot)
        prompt = build_keyframe_prompt(style, shot)
        e["keyframe_prompt"] = prompt
        dest = root / "keyframes" / f"{shot['id']}_{shot['title_en'].replace(' ', '_')}.png"
        if resume and e.get("keyframe_path") and Path(e["keyframe_path"]).exists():
            print(f"[KF] {shot['id']} cached", flush=True)
            continue
        print(f"\n[KF] {shot['id']} {shot['title']} · {KEYFRAME_W}x{KEYFRAME_H}", flush=True)
        print(f"     {prompt[:110]}...", flush=True)
        if dry_run:
            e["status"] = "DRY_RUN"
            save_manifest(root, m)
            continue
        t0 = time.time()
        try:
            src = produce.produce_z_image_turbo(prompt, KEYFRAME_W, KEYFRAME_H, 42,
                                                f"{PROJECT_ID}_{shot['id']}_kf")
            shutil.copy(src, dest)
            e["keyframe_path"] = str(dest)
            e["keyframe_s"] = round(time.time() - t0, 1)
            print(f"     [+] {dest.name} ({e['keyframe_s']}s)", flush=True)
        except Exception as exc:
            e["error"] = f"keyframe: {type(exc).__name__}: {exc}"
            e["status"] = "ERROR"
            print(f"     [-] {e['error']}", flush=True)
        save_manifest(root, m)


def stage_video(root, m, shots, produce, resume, dry_run, force=False):
    template = (REPO_ROOT / "workflows" / "wan22_14b_i2v_api.json").read_text(encoding="utf-8")
    for shot in shots:
        e = shot_entry(m, shot)
        frames_dir = root / "frames" / shot["id"]
        if resume and not force and e.get("frame_count") and frames_dir.exists() and len(list(frames_dir.glob("*.png"))) >= FRAMES:
            print(f"[VID] {shot['id']} cached ({e['frame_count']} frames)", flush=True)
            continue
        kf = e.get("keyframe_path")
        if not kf or not Path(kf).exists():
            e["error"] = "video: keyframe missing"
            e["status"] = "ERROR"
            save_manifest(root, m)
            print(f"[VID] {shot['id']} skipped: no keyframe", flush=True)
            continue

        anchor_name = f"{PROJECT_ID}_{shot['id']}_anchor_{VIDEO_W}x{VIDEO_H}.png"
        anchor = produce.COMFY_INPUT / anchor_name
        anchor.parent.mkdir(parents=True, exist_ok=True)
        from PIL import Image
        Image.open(kf).convert("RGB").resize((VIDEO_W, VIDEO_H), Image.LANCZOS).save(anchor)

        subs = {
            "{{positive_prompt}}": shot["motion"],
            "{{negative_prompt}}": VIDEO_NEGATIVE,
            "{{input_image}}": anchor_name,
            "{{width}}": str(VIDEO_W),
            "{{height}}": str(VIDEO_H),
            "{{frames}}": str(FRAMES),
            "{{seed}}": str(7100 + int(shot["id"][1:])),
            "{{steps}}": "6",
            "{{cfg}}": "1.0",
            "{{shift}}": "5.0",
            "{{filename_prefix}}": f"{PROJECT_ID}/{shot['id']}",
        }
        raw = template
        for k, v in subs.items():
            raw = raw.replace(k, v)
        wf = json.loads(raw)

        print(f"\n[VID] {shot['id']} {shot['title']} · Wan 14B {VIDEO_W}x{VIDEO_H} / {FRAMES}f", flush=True)
        print(f"      motion: {shot['motion'][:100]}...", flush=True)
        if dry_run:
            e["status"] = "DRY_RUN"
            save_manifest(root, m)
            continue

        t0 = time.time()
        try:
            pid = produce.submit_workflow(wf)
            hist = produce.wait_for_completion(pid, timeout=7200, poll_interval=10.0)
            frames = produce.retrieve_output_images(hist)
            if not frames:
                raise RuntimeError("no frames returned")
            frames_dir.mkdir(parents=True, exist_ok=True)
            for old in frames_dir.glob("*.png"):
                old.unlink()
            for i, f in enumerate(frames):
                shutil.copy(f, frames_dir / f"frame_{i:05d}.png")
            e["frames_dir"] = str(frames_dir)
            e["frame_count"] = len(frames)
            e["video_s"] = round(time.time() - t0, 1)
            e["comfy_prompt_id"] = pid
            print(f"      [+] {len(frames)} frames in {e['video_s'] / 60:.1f} min", flush=True)
        except Exception as exc:
            e["error"] = f"video: {type(exc).__name__}: {exc}"
            e["status"] = "ERROR"
            e["video_s"] = round(time.time() - t0, 1)
            print(f"      [-] {e['error']}", flush=True)
        save_manifest(root, m)


def _ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", *args], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stage_post(root, m, shots, resume, dry_run):
    for shot in shots:
        e = shot_entry(m, shot)
        out = root / "shots" / f"{shot['id']}_{POST_W}x{POST_H}_{POST_FPS}fps.mp4"
        if resume and e.get("post_path") and Path(e["post_path"]).exists():
            print(f"[POST] {shot['id']} cached", flush=True)
            continue
        frames_dir = Path(e["frames_dir"]) if e.get("frames_dir") else None
        if not frames_dir or not frames_dir.exists():
            print(f"[POST] {shot['id']} skipped: no frames", flush=True)
            continue
        if dry_run:
            continue
        print(f"[POST] {shot['id']} 2x Lanczos + {POST_FPS}fps optical flow...", flush=True)
        t0 = time.time()
        vf = (f"scale={POST_W}:{POST_H}:flags=lanczos,"
              f"minterpolate=fps={POST_FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
        _ffmpeg(["-framerate", str(RAW_FPS), "-i", str(frames_dir / "frame_%05d.png"),
                 "-vf", vf, "-c:v", "libx264", "-crf", "17", "-preset", "slow",
                 "-pix_fmt", "yuv420p", str(out)])
        e["post_path"] = str(out)
        e["post_s"] = round(time.time() - t0, 1)
        e["status"] = "SHOT_READY"
        print(f"       [+] {out.name} ({e['post_s']}s)", flush=True)
        save_manifest(root, m)


def make_title_clip(root: Path, seconds: float = 2.5) -> Path:
    """Render the title card with the shared OFL-font renderer, then fade it in and out.

    Text is composited, never diffusion-generated: the style atlas measurements showed
    Z-Image renders unspecified lettering as garbled glyphs.
    """
    spec = importlib.util.spec_from_file_location(
        "title_card_renderer", REPO_ROOT / "scripts" / "render_title_card.py")
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)

    png = root / "deliver" / "title_card.png"
    renderer.render_title_card(
        png, title="云上天宫", subtitle="CLOUD PALACE",
        font_key="lxgw_wenkai_medium", latin_key="cinzel", latin_weight=500,
        width=POST_W, height=POST_H, title_size=150, tracking_em=0.34,
    )
    clip = root / "deliver" / "title_card.mp4"
    _ffmpeg(["-loop", "1", "-i", str(png), "-t", str(seconds),
             "-vf", f"fade=t=in:st=0:d=0.7,fade=t=out:st={seconds - 0.7:.2f}:d=0.7",
             "-r", str(POST_FPS), "-c:v", "libx264", "-crf", "17",
             "-preset", "slow", "-pix_fmt", "yuv420p", str(clip)])
    print(f"[ASM] title card rendered -> {clip.name}", flush=True)
    return clip


def stage_assemble(root, m, shots, score_path, dry_run, title=True):
    ready = [s for s in shots
             if m["shots"].get(s["id"], {}).get("post_path")
             and Path(m["shots"][s["id"]]["post_path"]).exists()]
    if not ready:
        print("[ASM] no finished shots to assemble", flush=True)
        return
    if dry_run:
        return
    parts = []
    if title:
        parts.append(make_title_clip(root))
    parts += [Path(m["shots"][s["id"]]["post_path"]) for s in ready]
    concat_list = root / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in parts),
        encoding="utf-8",
    )
    silent = root / "deliver" / f"{PROJECT_ID}_silent_{POST_W}x{POST_H}.mp4"
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(silent)])
    print(f"[ASM] {len(ready)} shots -> {silent.name}", flush=True)

    final = root / "deliver" / f"{PROJECT_ID}_master.mp4"
    if score_path and Path(score_path).exists():
        _ffmpeg(["-i", str(silent), "-i", str(score_path),
                 "-filter_complex", "[1:a]volume=0.8,afade=t=out:st=13:d=2.5[aout]",
                 "-map", "0:v", "-map", "[aout]",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)])
        print(f"[ASM] score muxed -> {final.name}", flush=True)
    else:
        shutil.copy(silent, final)
        print(f"[ASM] no score supplied -> silent master {final.name}", flush=True)

    m["deliverable"] = str(final)
    m["shot_count"] = len(ready)
    m["duration_seconds"] = round(len(ready) * FRAMES / RAW_FPS + (2.5 if title else 0), 2)
    save_manifest(root, m)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
         "-of", "default=noprint_wrappers=1", str(final)],
        capture_output=True, text=True,
    )
    print(probe.stdout.strip(), flush=True)


def main():
    ap = argparse.ArgumentParser(description="云上天宫 · original Oriental fantasy short film")
    ap.add_argument("--stage", choices=["keyframes", "video", "post", "assemble", "all"], default="all")
    ap.add_argument("--shots", help="Comma-separated shot ids (default: all five)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-render even if cached frames exist")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--score", help="Path to a WAV score to mux during assemble")
    ap.add_argument("--no-title", action="store_true", help="Skip the rendered title card")
    args = ap.parse_args()

    root = run_root()
    m = load_manifest(root)
    shots = SHOTS if not args.shots else [s for s in SHOTS if s["id"] in
                                          {x.strip() for x in args.shots.split(",")}]
    if not shots:
        raise SystemExit("no matching shots")

    produce = None
    if args.stage in ("keyframes", "video", "all") and not args.dry_run:
        produce = load_produce()
        if not produce.check_comfy_live():
            raise SystemExit(f"ComfyUI offline at {produce.COMFY_URL}; run scripts\\start.ps1")

    print("=" * 90)
    print(f"  云上天宫 · {len(shots)} shots · stage={args.stage} · resume={args.resume}")
    print(f"  keyframe {KEYFRAME_W}x{KEYFRAME_H} Z-Image Turbo | video {VIDEO_W}x{VIDEO_H} "
          f"{FRAMES}f Wan 14B | delivery {POST_W}x{POST_H} {POST_FPS}fps")
    print(f"  run root: {root}")
    print("=" * 90, flush=True)

    t0 = time.time()
    if args.stage in ("keyframes", "all"):
        stage_keyframes(root, m, shots, produce, args.resume, args.dry_run)
    if args.stage in ("video", "all"):
        stage_video(root, m, shots, produce, args.resume, args.dry_run, force=args.force)
    if args.stage in ("post", "all"):
        stage_post(root, m, shots, args.resume, args.dry_run)
    if args.stage in ("assemble", "all"):
        stage_assemble(root, m, shots, args.score, args.dry_run, title=not args.no_title)

    print(f"\n[Done] stage={args.stage} elapsed {(time.time() - t0) / 60:.1f} min", flush=True)
    save_manifest(root, m)


if __name__ == "__main__":
    main()