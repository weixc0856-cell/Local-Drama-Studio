"""Assemble the R3-B vertical short.

Inputs:
  experiments/r3b/segments.json          ordered images / Wan clip
  experiments/r3b/audio_manifest.json    CosyVoice line WAVs + durations
Outputs (experiments/r3b/renders/):
  segments/*.mp4, video_faded.mp4, mixed.wav, drama.srt,
  final_9x16.mp4 (soft subs), final_9x16_burned.mp4 (burned, optional),
  build_manifest.json

No new dependencies: pysubs2 is already in the project venv.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pysubs2

ROOT = Path(__file__).resolve().parents[1]
FPS = 24
W, H = 1080, 1920
GAP = 0.8
LEAD = 1.0


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(cmd) + "\n" + proc.stderr[-3000:])
    return proc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_segment(seg: dict, out: Path) -> None:
    src = ROOT / seg["source"]
    if not src.is_file():
        raise FileNotFoundError(src)
    dur = float(seg["duration"])
    if seg["type"] == "image":
        frames = max(1, round(dur * FPS))
        vf = (
            f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
            f"zoompan=z='min(zoom+0.0006,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={W}x{H}:fps={FPS},format=yuv420p"
        )
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(src),
               "-vf", vf, "-t", f"{dur:.3f}", "-an", "-c:v", "libx264", "-crf", "18",
               "-preset", "medium", "-r", str(FPS), str(out)]
    else:
        vf = f"scale={W}:{H}:flags=lanczos,fps={FPS},format=yuv420p"
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf,
               "-t", f"{dur:.3f}", "-an", "-c:v", "libx264", "-crf", "18",
               "-preset", "medium", "-r", str(FPS), str(out)]
    run(cmd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segments", default="experiments/r3b/segments.json")
    parser.add_argument("--audio", default="experiments/r3b/audio_manifest.json")
    parser.add_argument("--out", default="experiments/r3b/renders")
    args = parser.parse_args()

    segments = json.loads((ROOT / args.segments).read_text(encoding="utf-8"))
    audio = json.loads((ROOT / args.audio).read_text(encoding="utf-8"))
    out_dir = (ROOT / args.out).resolve()
    seg_dir = out_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    total = sum(float(s["duration"]) for s in segments)
    lines = audio["lines"]
    starts: list[float] = []
    cursor = LEAD
    for line in lines:
        starts.append(round(cursor, 3))
        cursor += float(line["duration_seconds"]) + GAP
    audio_end = cursor
    if audio_end > total:
        # Extend the last visual segment so narration is never cut off.
        extension = round(audio_end + 1.0 - total, 3)
        segments[-1]["duration"] = round(float(segments[-1]["duration"]) + extension, 3)
        total = round(total + extension, 3)

    print(f"video total={total:.3f}s audio_end={audio_end:.3f}s lines={len(lines)}")

    seg_files = []
    for seg in segments:
        path = seg_dir / f"{seg['id']}.mp4"
        print("build segment", seg["id"], seg["type"], seg["duration"])
        build_segment(seg, path)
        seg_files.append(path)

    concat_list = out_dir / "concat.txt"
    concat_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in seg_files), encoding="utf-8")
    video_raw = out_dir / "video_raw.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", str(video_raw)])

    video_faded = out_dir / "video_faded.mp4"
    fade_out = max(0.0, total - 0.9)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video_raw),
         "-vf", f"fade=t=in:st=0:d=0.6,fade=t=out:st={fade_out:.3f}:d=0.9,format=yuv420p",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", str(FPS), str(video_faded)])

    # Audio: delay each line to its start, mix, pad to video duration.
    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    for i, line in enumerate(lines, start=1):
        inputs += ["-i", str(ROOT / line["file"])]
        delay = int(round(starts[i - 1] * 1000))
        filters.append(f"[{i - 1}:a]adelay={delay}|{delay}[a{i}]")
        labels.append(f"[a{i}]")
    filters.append(
        f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur={total:.3f}[aout]"
    )
    mixed = out_dir / "mixed.wav"
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[aout]", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(mixed)])

    # SRT
    subs = pysubs2.SSAFile()
    for line, start in zip(lines, starts):
        ev = pysubs2.SSAEvent(
            start=pysubs2.make_time(s=start),
            end=pysubs2.make_time(s=start + float(line["duration_seconds"])),
            text=line["text"],
        )
        subs.append(ev)
    srt = out_dir / "drama.srt"
    subs.save(str(srt))

    # Burn-in ASS: explicit 1080x1920 PlayRes avoids libass scaling the font
    # relative to its 288-line default.
    ass_subs = pysubs2.SSAFile()
    ass_subs.info["PlayResX"] = str(W)
    ass_subs.info["PlayResY"] = str(H)
    style = pysubs2.SSAStyle()
    style.fontname = "Microsoft YaHei"
    style.fontsize = 56
    style.primarycolor = pysubs2.Color(255, 255, 255, 0)
    style.outlinecolor = pysubs2.Color(0, 0, 0, 0)
    style.backcolor = pysubs2.Color(0, 0, 0, 0)
    style.outline = 3
    style.shadow = 0
    style.marginv = 180
    style.alignment = pysubs2.Alignment.BOTTOM_CENTER
    ass_subs.styles["Default"] = style
    for line, start in zip(lines, starts):
        ass_subs.append(pysubs2.SSAEvent(
            start=pysubs2.make_time(s=start),
            end=pysubs2.make_time(s=start + float(line["duration_seconds"])),
            text=line["text"],
        ))
    ass_path = out_dir / "drama.ass"
    ass_subs.save(str(ass_path))

    final = out_dir / "final_9x16.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video_faded), "-i", str(mixed), "-i", str(srt),
         "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text", "-metadata:s:s:0", "language=chi",
         "-t", f"{total:.3f}", "-movflags", "+faststart", str(final)])

    burned = out_dir / "final_9x16_burned.mp4"
    burned_ok = False
    try:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(video_faded), "-i", str(mixed),
             "-vf", "ass='drama.ass'",
             "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", str(burned)], cwd=out_dir)
        burned_ok = True
    except RuntimeError as exc:
        print("burned subtitle render failed:", str(exc)[-500:])

    probe = run(["ffprobe", "-v", "error", "-show_entries",
                 "stream=index,codec_type,codec_name,width,height,r_frame_rate,duration:format=duration",
                 "-of", "json", str(final)])
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    manifest = {
        "segments": [{**s, "file": str(seg_files[i].relative_to(ROOT)), "sha256": sha256(seg_files[i])}
                     for i, s in enumerate(segments)],
        "total_seconds": total,
        "audio_end_seconds": round(audio_end, 3),
        "line_starts": starts,
        "outputs": {
            "final": str(final.relative_to(ROOT)), "final_sha256": sha256(final),
            "burned": str(burned.relative_to(ROOT)) if burned_ok else None,
            "srt": str(srt.relative_to(ROOT)), "ass": str(ass_path.relative_to(ROOT)),
            "mixed": str(mixed.relative_to(ROOT)),
        },
        "ffprobe": json.loads(probe.stdout),
        "decode_returncode": decode.returncode,
        "decode_stderr": decode.stderr.strip()[-1000:],
    }
    (out_dir / "build_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total": total, "final": manifest["outputs"]["final"],
                      "burned": manifest["outputs"]["burned"],
                      "decode": decode.returncode}, ensure_ascii=False))
    return 0 if decode.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
