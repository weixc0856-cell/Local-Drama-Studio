"""Programmatic ink transitions between two rendered shots.

``crossfade`` uses FFmpeg xfade. Ink transitions build a soft, evolving
grayscale mask (distance field + multi-scale noise, no hard threshold) and
composite the next shot through it with ``alphamerge`` + ``overlay``.

The transition never changes the sequence length: each shot is rendered with a
tail ``handle`` as long as its outgoing transition, and the transition consumes
that handle. Audio timing therefore stays untouched.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageFilter

from drama_studio.domain.motion.noise import noise_image
from drama_studio.domain.motion.spec import H, W, MotionPlan, TransitionSpec

MASK_W, MASK_H = 270, 480


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(cmd) + "\n" + proc.stderr[-3000:])
    return proc


def make_masks(spec: TransitionSpec, out_dir: Path, duration: float, fps: int) -> dict:
    """Write a grayscale mask sequence: black keeps the outgoing shot, white reveals the next."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("m_*.png"):
        old.unlink()
    frames = max(1, int(round(duration * fps)))
    seeds = [(0.22, 0.68), (0.72, 0.32), (0.48, 0.55)]
    if spec.direction == "rtl":
        seeds = [(1 - x, y) for x, y in seeds]
    elif spec.direction == "radial":
        seeds = [(0.5, 0.5)]
    noise = noise_image((MASK_W // 6 + 1, MASK_H // 6 + 1), spec.seed, 40).resize(
        (MASK_W, MASK_H), Image.BICUBIC
    ).filter(ImageFilter.GaussianBlur(3))
    noise_px = noise.load()
    field = Image.new("L", (MASK_W, MASK_H), 0)
    field_px = field.load()
    seed_px = [(sx * (MASK_W - 1), sy * (MASK_H - 1)) for sx, sy in seeds]
    for y in range(MASK_H):
        for x in range(MASK_W):
            if spec.type in ("ink_dissolve", "ink_spread") or spec.direction == "radial":
                dist = min(math.hypot(x - sx, y - sy) for sx, sy in seed_px)
                norm = dist / max(1.0, math.hypot(MASK_W, MASK_H) * 0.62)
            elif spec.direction in ("ltr", "rtl"):
                norm = (1.0 - x / (MASK_W - 1)) if spec.direction == "ltr" else x / (MASK_W - 1)
            elif spec.direction == "down":
                norm = y / (MASK_H - 1)
            else:  # up
                norm = 1.0 - y / (MASK_H - 1)
            perturb = (noise_px[x, y] - 128) / 128.0 * 0.14
            field_px[x, y] = max(0, min(255, int(round((norm + perturb) * 255))))
    softness = max(0.03, spec.feather)
    for index in range(frames):
        t = index / max(1, frames - 1)
        # The first frame keeps a little of the incoming shot so the cut never
        # starts on a hard edge; the last frame is fully the new shot.
        progress = 0.02 + (_smoothstep(t) ** 1.6) * 1.06
        lut = []
        for q in range(256):
            value = (progress - q / 255.0) / softness + 0.5
            lut.append(max(0, min(255, int(round(value * 255)))))
        field.point(lut).save(out_dir / f"m_{index:04d}.png")
    return {"dir": str(out_dir), "frames": frames, "size": [MASK_W, MASK_H],
            "type": spec.type, "direction": spec.direction, "softness": softness,
            "seed": spec.seed}


def _probe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {proc.stderr[-400:]}")
    return float(json.loads(proc.stdout or "{}").get("format", {}).get("duration") or 0.0)


def _srgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    def lin(value: float) -> float:
        value /= 255.0
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x / 0.95047), f(y / 1.0), f(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _mean_lab(path: Path, at: float) -> dict:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, at):.3f}", "-i", str(path),
         "-frames:v", "1", "-vf", "scale=64:64,format=rgb24", "-f", "rawvideo", "-"],
        capture_output=True,
    )
    if proc.returncode != 0 or len(proc.stdout) < 64 * 64 * 3:
        raise RuntimeError(f"cannot sample {path} at {at:.3f}s")
    data = proc.stdout[:64 * 64 * 3]
    count = 64 * 64
    rgb = tuple(sum(data[i + channel] for i in range(0, len(data), 3)) / count
                for channel in range(3))
    lab = _srgb_to_lab(rgb)
    return {"rgb": [round(v, 2) for v in rgb],
            "lab": [round(v, 3) for v in lab],
            "chroma": round(math.hypot(lab[1], lab[2]), 3)}


def colour_check(left: Path, right: Path, left_at: float, right_at: float,
                 *, threshold: float = 12.0, chroma_ratio: float = 1.5) -> dict:
    """Compare the two sides of a transition and warn on a style jump.

    This is a warning in the manifest, not a hard failure: the editor may
    deliberately cut between two colour worlds. It exists so a mismatch cannot
    pass silently.
    """
    a = _mean_lab(left, left_at)
    b = _mean_lab(right, right_at)
    delta = round(math.sqrt(sum((x - y) ** 2 for x, y in zip(a["lab"], b["lab"]))), 3)
    ratio = round(b["chroma"] / max(0.01, a["chroma"]), 3)
    warning = None
    if delta > threshold or ratio > chroma_ratio:
        warning = "style_jump"
    return {"left": a, "right": b, "delta_e": delta, "chroma_ratio": ratio,
            "threshold_delta_e": threshold, "threshold_chroma_ratio": chroma_ratio,
            "warning": warning}


def render_transition(
    left: Path,
    right: Path,
    out: Path,
    spec: TransitionSpec,
    mask_dir: Path,
    *,
    fps: int = 24,
    left_start: float | None = None,
    right_start: float = 0.0,
) -> dict:
    """Render one transition from the left clip's tail to the right clip's head.

    ``left_start`` is the beginning of the outgoing handle. It must be greater
    than 0 and the tail ``[left_start, left_start + duration]`` must fit inside
    the left clip. The old implementation used ``-ss 0`` here, which replayed
    the *head* of the previous shot after its body had already ended.
    """
    duration = spec.duration_s
    left_duration = _probe_duration(left)
    right_duration = _probe_duration(right)
    if left_start is None:
        left_start = left_duration - duration
    if left_start <= 1e-6:
        raise ValueError(
            f"transition left handle must start after 0, got {left_start:.3f}; "
            "the left clip has no tail handle"
        )
    if left_start + duration > left_duration + 1e-3:
        raise ValueError(
            f"transition tail [{left_start:.3f}, {left_start + duration:.3f}] "
            f"exceeds left clip duration {left_duration:.3f}"
        )
    if right_start < 0 or right_start + duration > right_duration + 1e-3:
        raise ValueError(
            f"transition head [{right_start:.3f}, {right_start + duration:.3f}] "
            f"exceeds right clip duration {right_duration:.3f}"
        )
    timing = {
        "left_start": round(left_start, 3),
        "left_duration": round(duration, 3),
        "left_clip_duration": round(left_duration, 3),
        "right_start": round(right_start, 3),
        "right_duration": round(duration, 3),
        "right_clip_duration": round(right_duration, 3),
    }
    if spec.type == "crossfade":
        graph = (
            f"[0:v]fps={fps},format=yuv420p,setpts=PTS-STARTPTS[a];"
            f"[1:v]fps={fps},format=yuv420p,setpts=PTS-STARTPTS[b];"
            f"[a][b]xfade=transition=fade:duration={duration:.3f}:offset=0,format=yuv420p[outv]"
        )
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-ss", f"{left_start:.3f}", "-t", f"{duration:.3f}", "-i", str(left),
            "-ss", f"{right_start:.3f}", "-t", f"{duration:.3f}", "-i", str(right),
            "-filter_complex", graph, "-map", "[outv]",
            "-t", f"{duration:.3f}", "-frames:v", str(max(1, round(duration * fps))),
            "-r", str(fps),
            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-an", str(out),
        ]
    else:
        graph = (
            f"[0:v]fps={fps},scale={W}:{H},format=yuv420p,setpts=PTS-STARTPTS[a];"
            f"[1:v]fps={fps},scale={W}:{H},format=yuv420p,setpts=PTS-STARTPTS[b];"
            f"[2:v]scale={W}:{H}:flags=bicubic,format=gray,gblur=sigma=5[m];"
            f"[b][m]alphamerge[bfg];"
            f"[a][bfg]overlay=format=auto,format=yuv420p[outv]"
        )
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-ss", f"{left_start:.3f}", "-t", f"{duration:.3f}", "-i", str(left),
            "-ss", f"{right_start:.3f}", "-t", f"{duration:.3f}", "-i", str(right),
            "-framerate", str(fps), "-start_number", "0", "-i", str(mask_dir / "m_%04d.png"),
            "-filter_complex", graph, "-map", "[outv]",
            "-t", f"{duration:.3f}", "-frames:v", str(max(1, round(duration * fps))),
            "-r", str(fps),
            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-an", str(out),
        ]
    _run(cmd)
    command = " ".join(cmd)
    if "maskedmerge" in command:
        raise RuntimeError("maskedmerge is forbidden: it mixes chroma planes and breaks colour")
    algorithm = "xfade" if spec.type == "crossfade" else "alphamerge_overlay"
    sample_at = duration / 2.0
    colours = colour_check(left, right, left_start + sample_at, right_start + sample_at)
    return {
        "argv": cmd,
        "timing": timing,
        "algorithm": algorithm,
        "colour": colours,
        "duration": round(duration, 3),
    }


def _trim(src: Path, out: Path, start: float, duration: float, fps: int) -> list[str]:
    frames = max(1, int(round(duration * fps)))
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
        "-i", str(src), "-an", "-frames:v", str(frames), "-r", str(fps),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        str(out),
    ]
    _run(cmd)
    return cmd


def assemble_sequence(
    plan: MotionPlan,
    clips: list[Path],
    out_dir: Path,
    *,
    fps: int = 24,
) -> dict:
    """Assemble shot clips (already containing their outgoing handle) into one silent film."""
    if len(clips) != len(plan.shots):
        raise ValueError("clip count does not match plan")
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    transitions: list[dict] = []
    for index, shot in enumerate(plan.shots):
        # A shot whose head is consumed by the transition before it starts later.
        start = shot.transition_in.duration_s if (index > 0 and shot.transition_in is not None) else 0.0
        duration = round(shot.duration_seconds - start, 3)
        if duration <= 0:
            raise ValueError(f"{shot.id}: transition longer than the shot")
        body = out_dir / f"body_{index:02d}.mp4"
        _trim(clips[index], body, start, duration, fps)
        parts.append(body)

    # The transition before shot i is stored on shot i; build it after the bodies.
    for index in range(len(plan.shots) - 1):
        spec = plan.shots[index + 1].transition_in
        if spec is None:
            continue
        left = clips[index]
        right = clips[index + 1]
        mask_dir = out_dir / f"masks_{index:02d}"
        mask_info = make_masks(spec, mask_dir, spec.duration_s, fps)
        trans = out_dir / f"trans_{index:02d}.mp4"
        # The handle starts at the planned end of the outgoing shot; the body
        # already stops there, so the transition continues the same timeline.
        timing = render_transition(
            left, right, trans, spec, mask_dir, fps=fps,
            left_start=float(plan.shots[index].duration_seconds),
            right_start=0.0,
        )
        transitions.append({
            "after_shot": plan.shots[index].id,
            "before_shot": plan.shots[index + 1].id,
            "before_index": index + 1,
            "spec": spec.model_dump(),
            "mask": mask_info,
            "file": str(trans),
            "argv": timing["argv"],
            "timing": timing["timing"],
            "algorithm": timing["algorithm"],
            "colour": timing["colour"],
        })

    # Interleave: body0, trans0, body1, trans1, ...
    ordered: list[Path] = []
    trans_by_boundary = {item["before_index"]: Path(item["file"]) for item in transitions}
    for index, body in enumerate(parts):
        if index in trans_by_boundary:
            ordered.append(trans_by_boundary[index])
        ordered.append(body)

    concat = out_dir / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in ordered), encoding="utf-8")
    sequence = out_dir / "sequence.mp4"
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
          "-c", "copy", str(sequence)])
    measured = _probe_duration(sequence)
    error = round(measured - plan.total_seconds, 3)
    if abs(error) > (1.0 / fps) + 0.02:
        raise ValueError(
            f"sequence duration {measured:.3f}s does not match plan total "
            f"{plan.total_seconds:.3f}s (error {error:+.3f}s); a transition is "
            "not absorbing exactly its handle"
        )
    return {
        "sequence": str(sequence),
        "total_seconds": plan.total_seconds,
        "measured_seconds": round(measured, 3),
        "duration_error_seconds": error,
        "duration_ok": True,
        "transitions": transitions,
        "parts": [str(p) for p in ordered],
        "concat": str(concat),
    }
