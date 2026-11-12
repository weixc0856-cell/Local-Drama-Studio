"""Assemble the R3-B vertical short.

Inputs:
  experiments/r3b/segments.json          ordered images / Wan clip
  experiments/r3b/audio_manifest.json    line WAVs + durations
                                         optional content_type / pause_after_ms
Outputs (experiments/r3b/renders/):
  segments/*.mp4, video_faded.mp4, mixed.wav, timeline.json, drama.srt,
  drama.ass, fonts/*.otf, fontselect.log,
  final_9x16.mp4 (soft subs), final_9x16_burned.mp4 (burned, optional),
  build_manifest.json

Timeline and subtitle times come from drama_studio.voice.timeline.
Subtitle font role comes from config/fonts.yaml via drama_studio.fonts.
No new dependencies: pysubs2 is already in the project venv.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pysubs2

from drama_studio.fonts import FontConfigurationError, load_font_config
from drama_studio.paths import is_repo_path, output_root
from drama_studio.voice.timeline import (
    build_timeline,
    leading_silence_for,
    make_srt,
    pad_timeline_to,
)

ROOT = Path(__file__).resolve().parents[1]
WS = output_root()  # generated artifacts live outside the repo
FPS = 24
W, H = 1080, 1920
GAP_MS = 800
DEFAULT_CONTENT_TYPE = "narration"


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


def resolve_artifact(value: str | Path) -> Path:
    """A manifest path is either generated (workspace) or a declared input (repo)."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (ROOT if is_repo_path(str(value)) else WS) / path


def relpath(path: Path) -> str:
    for base in (WS, ROOT):
        try:
            return str(path.relative_to(base))
        except ValueError:
            continue
    return str(path)


def build_segment(seg: dict, out: Path, *, render_duration: float | None = None) -> None:
    src = resolve_artifact(seg["source"])
    if not src.is_file():
        raise FileNotFoundError(src)
    dur = float(render_duration if render_duration is not None else seg["duration"])
    target = float(seg["duration"])
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
        pad = max(0.0, dur - target)
        pad_filter = f"tpad=stop_mode=clone:stop_duration={pad:.3f}," if pad > 0 else ""
        vf = f"{pad_filter}scale={W}:{H}:flags=lanczos,fps={FPS},format=yuv420p"
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf,
               "-t", f"{dur:.3f}", "-an", "-c:v", "libx264", "-crf", "18",
               "-preset", "medium", "-r", str(FPS), str(out)]
    run(cmd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segments", default="experiments/r3b/segments.json")
    parser.add_argument("--audio", default="experiments/r3b/audio_manifest.json")
    parser.add_argument("--out", default="experiments/r3b/renders")
    parser.add_argument("--content-type", choices=("poetry", "narration", "mixed"), default=None)
    parser.add_argument("--leading-ms", type=int, default=None,
                        help="override the content-type leading silence (default: 400/300/350)")
    parser.add_argument("--audio-timeline", default=None,
                        help="optional multi-track audio_timeline.json; keeps legacy line mix when absent")
    parser.add_argument("--audio-assets", default=None,
                        help="audio asset registry for BGM/SFX (default: assets/audio/manifest.json if present)")
    parser.add_argument("--bgm-id", default=None,
                        help="override every BGM track's asset_id in --audio-timeline; "
                             "writes audio_timeline_effective.json into --out for provenance")
    parser.add_argument("--allow-overwrite", action="store_true",
                        help="allow replacing an existing final_9x16.mp4 in --out")
    parser.add_argument("--crossfade", type=float, default=0.5,
                        help="crossfade seconds on dissolve cuts (0 disables)")
    args = parser.parse_args()

    segments = json.loads(resolve_artifact(args.segments).read_text(encoding="utf-8"))
    audio = json.loads(resolve_artifact(args.audio).read_text(encoding="utf-8"))
    out_dir = resolve_artifact(args.out).resolve()
    if (out_dir / "final_9x16.mp4").exists() and not args.allow_overwrite:
        raise SystemExit(
            f"refusing to overwrite existing render in {out_dir}; "
            "pass --allow-overwrite to rebuild deliberately"
        )
    try:
        font_config = load_font_config(ROOT)
    except FontConfigurationError as exc:
        raise SystemExit(f"font configuration error: {exc}") from exc
    subtitle_role = font_config.role("subtitle")
    subtitle_face = font_config.face(subtitle_role)
    seg_dir = out_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    lines = audio["lines"]
    content_type = args.content_type or audio.get("content_type", DEFAULT_CONTENT_TYPE)
    leading_ms = args.leading_ms if args.leading_ms is not None else leading_silence_for(content_type)
    if leading_ms < 0:
        raise SystemExit("--leading-ms must be >= 0")

    # The spoken title is part of the leading silence: it plays first, then the
    # body starts. Audio owns the clock, so the header extends the lead rather
    # than being squeezed into a fixed title slot.
    header = audio.get("header") or None
    header_offset_ms = 0
    if header:
        header_offset_ms = (int(round(float(header["duration_seconds"]) * 1000))
                            + int(header.get("pause_ms", 0)))
        leading_ms += header_offset_ms

    timeline_segments = []
    for i, line in enumerate(lines, start=1):
        timeline_segments.append({
            "segment_id": f"line_{i:02d}",
            "duration": float(line["duration_seconds"]),
            "pause_after_ms": int(line.get("pause_after_ms", GAP_MS)),
            "gap_before_ms": int(line.get("gap_before_ms", 0)),
            # Spoken text and on-screen text are allowed to differ (e.g. a
            # simplified TTS script with traditional subtitles).
            "subtitle_text": line.get("subtitle_text") or line["text"],
        })
    timeline = build_timeline(timeline_segments, leading_ms)
    starts_ms = [event["speech_start_ms"] for event in timeline["segments"]]
    starts = [round(ms / 1000.0, 3) for ms in starts_ms]
    audio_end_ms = timeline["audio_end_ms"]

    total_ms = int(round(sum(float(seg["duration"]) for seg in segments) * 1000))
    if audio_end_ms > total_ms:
        # Extend the last visual segment so narration is never cut off; keep 1 s tail.
        extension_ms = audio_end_ms + 1000 - total_ms
        segments[-1]["duration"] = round(float(segments[-1]["duration"]) + extension_ms / 1000.0, 3)
        total_ms += extension_ms

    timeline = pad_timeline_to(timeline, total_ms)
    total = total_ms / 1000.0
    audio_end = timeline["audio_end_ms"] / 1000.0
    print(
        f"video total={total:.3f}s audio_end={audio_end:.3f}s "
        f"voice_end={timeline['voice_end_ms'] / 1000.0:.3f}s "
        f"leading={leading_ms}ms content={content_type} lines={len(lines)}"
    )

    durations = [float(seg["duration"]) for seg in segments]
    handles: list[float] = []
    transitions: list[str] = []
    for index, seg in enumerate(segments):
        if index + 1 < len(segments):
            nxt = segments[index + 1]
            kind = str(nxt.get("transition_in") or "cut")
            handles.append(args.crossfade if kind == "dissolve" else 0.04)
            transitions.append(kind)
        else:
            handles.append(0.0)
            transitions.append("end")

    seg_files = []
    for index, seg in enumerate(segments):
        path = seg_dir / f"{seg['id']}.mp4"
        render_duration = durations[index] + handles[index]
        print("build segment", seg["id"], seg["type"], seg["duration"],
              "render", round(render_duration, 3), "next", transitions[index])
        build_segment(seg, path, render_duration=render_duration)
        seg_files.append(path)

    video_raw = out_dir / "video_raw.mp4"
    use_xfade = args.crossfade > 0 and any(kind == "dissolve" for kind in transitions)
    if use_xfade and len(seg_files) > 1:
        inputs: list[str] = []
        for path in seg_files:
            inputs += ["-i", str(path)]
        graph_parts = [f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[v{i}]"
                       for i in range(len(seg_files))]
        current = "v0"
        for index in range(1, len(seg_files)):
            overlap = handles[index - 1]
            offset = sum(durations[:index])
            label = f"x{index}"
            graph_parts.append(
                f"[{current}][v{index}]xfade=transition=fade:"
                f"duration={overlap:.3f}:offset={offset:.3f}[{label}]")
            current = label
        run(["ffmpeg", "-y", "-v", "error", *inputs,
             "-filter_complex", ";".join(graph_parts),
             "-map", f"[{current}]", "-an", "-c:v", "libx264", "-crf", "18",
             "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-t", f"{sum(durations):.3f}", str(video_raw)])
    else:
        concat_list = out_dir / "concat.txt"
        concat_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in seg_files), encoding="utf-8")
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-c", "copy", str(video_raw)])

    video_faded = out_dir / "video_faded.mp4"
    fade_out = max(0.0, total - 0.9)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video_raw),
         "-vf", f"fade=t=in:st=0:d=0.6,fade=t=out:st={fade_out:.3f}:d=0.9,format=yuv420p",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", str(FPS), str(video_faded)])

    # Audio: explicit multi-track timeline, or the legacy narration-only mix.
    from drama_studio.voice.soundscape import load_settings as load_soundscape
    from drama_studio.voice.soundscape import master as master_soundscape

    soundscape = load_soundscape(ROOT)
    mixed = out_dir / "mixed.wav"
    mix_target = out_dir / "mixed_pre.wav" if soundscape.enabled else mixed
    audio_timeline_report = None
    if args.audio_timeline:
        from drama_studio.voice.mix import MixError, mix_timeline

        timeline_arg = Path(args.audio_timeline)
        timeline_arg = timeline_arg if timeline_arg.is_absolute() else resolve_artifact(timeline_arg)
        if args.bgm_id:
            effective = json.loads(timeline_arg.read_text(encoding="utf-8"))
            seen = 0
            for track in effective.get("tracks", []):
                if track.get("type") == "bgm":
                    track["asset_id"] = args.bgm_id
                    seen += 1
            if not seen:
                raise SystemExit("--bgm-id given but the timeline has no bgm track")
            timeline_arg = out_dir / "audio_timeline_effective.json"
            timeline_arg.write_text(
                json.dumps(effective, ensure_ascii=False, indent=2) + '\n',
                encoding="utf-8",
            )
        if args.audio_assets:
            assets_arg = Path(args.audio_assets)
            assets_arg = assets_arg if assets_arg.is_absolute() else resolve_artifact(assets_arg)
        else:
            candidate = ROOT / "assets" / "audio" / "manifest.json"
            assets_arg = candidate if candidate.is_file() else None
        try:
            audio_timeline_report = mix_timeline(
                timeline_arg, mix_target, root=ROOT,
                asset_registry_path=assets_arg,
                duration_ms=int(round(total * 1000)),
            )
        except MixError as exc:
            raise SystemExit(f"audio timeline mix failed: {exc}") from exc
    else:
        inputs: list[str] = []
        filters: list[str] = []
        labels: list[str] = []
        input_index = 0
        if header:
            base_leading = max(0, leading_ms - header_offset_ms)
            inputs += ["-i", str(ROOT / header["file"])]
            filters.append(f"[{input_index}:a]adelay={base_leading}|{base_leading}[ahdr]")
            labels.append("[ahdr]")
            input_index += 1
        for i, line in enumerate(lines, start=1):
            inputs += ["-i", str(ROOT / line["file"])]
            delay = starts_ms[i - 1]
            filters.append(f"[{input_index}:a]adelay={delay}|{delay}[a{i}]")
            labels.append(f"[a{i}]")
            input_index += 1
        # Loudness is applied exactly once. When the soundscape stage is on, it
        # owns the loudness pass (two-pass, on the assembled track); otherwise the
        # build keeps its original single pass, byte for byte.
        loudness = "" if soundscape.enabled else "loudnorm=I=-16:TP=-1.5:LRA=11,"
        filters.append(
            f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95,"
            f"{loudness}apad=whole_dur={total:.3f}[aout]"
        )
        run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
             "-map", "[aout]", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(mix_target)])

    soundscape_report = None
    if soundscape.enabled:
        result = master_soundscape(mix_target, mixed, root=ROOT, settings=soundscape)
        soundscape_report = {"status": result.status, "note": result.note,
                             "report": result.report}
        if result.status != "PASS":
            raise SystemExit(f"声景母带未通过：{result.status} {result.note}")

    # Timeline and SRT share the exact same event data as the audio mix.
    timeline_path = out_dir / "timeline.json"
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    srt = out_dir / "drama.srt"
    make_srt(timeline, srt)

    # Burn-in ASS: explicit 1080x1920 PlayRes avoids libass scaling the font
    # relative to its 288-line default.
    ass_subs = pysubs2.SSAFile()
    ass_subs.info["PlayResX"] = str(W)
    ass_subs.info["PlayResY"] = str(H)
    style = pysubs2.SSAStyle()
    style.fontname = subtitle_face.ass_name
    style.fontsize = subtitle_role.size_px
    style.bold = subtitle_face.ass_bold
    style.primarycolor = pysubs2.Color(255, 255, 255, 0)
    style.outlinecolor = pysubs2.Color(0, 0, 0, 0)
    style.backcolor = pysubs2.Color(0, 0, 0, 0)
    style.outline = subtitle_role.outline_px
    style.shadow = 0
    style.marginv = subtitle_role.margin_bottom_px
    style.alignment = pysubs2.Alignment.BOTTOM_CENTER
    ass_subs.styles["Default"] = style
    for event in timeline["segments"]:
        ass_subs.append(pysubs2.SSAEvent(
            start=pysubs2.make_time(ms=event["subtitle_start_ms"]),
            end=pysubs2.make_time(ms=event["subtitle_end_ms"]),
            text=event["subtitle_text"],
        ))
    ass_path = out_dir / "drama.ass"
    ass_subs.save(str(ass_path))

    # Stage only the selected OTF next to the ASS file. libass gets a local
    # fontsdir, so it cannot silently use a system font or try to parse the
    # adjacent LICENSE.txt as a font.
    render_fonts_dir = out_dir / "fonts"
    render_fonts_dir.mkdir(parents=True, exist_ok=True)
    render_font_path = render_fonts_dir / subtitle_face.path.name
    if not render_font_path.is_file() or sha256(render_font_path) != subtitle_face.sha256:
        shutil.copy2(subtitle_face.path, render_font_path)

    # Verify libass actually selected the configured local face before the
    # final burn. A missing family or a silent fallback fails the build.
    fontselect_log = out_dir / "fontselect.log"
    fontcheck_seek = max(0.5, (starts_ms[0] if starts_ms else 0) / 1000.0 + 0.1)
    font_check = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "debug",
         "-i", str(video_faded), "-ss", f"{fontcheck_seek:.3f}",
         "-vf", "ass='drama.ass':fontsdir='fonts'",
         "-frames:v", "1", "-f", "null", "-"],
        cwd=out_dir, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    fontselect_log.write_text(font_check.stderr, encoding="utf-8")
    if font_check.returncode != 0:
        raise RuntimeError("libass font check failed: " + font_check.stderr[-3000:])
    fontselect_lines = [line for line in font_check.stderr.splitlines() if "fontselect:" in line]
    if not any(subtitle_face.postscript_name in line for line in fontselect_lines):
        raise RuntimeError(
            "libass did not select configured font "
            f"{subtitle_face.postscript_name}; fontselect lines: {fontselect_lines[-10:]}"
        )

    final = out_dir / "final_9x16.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video_faded), "-i", str(mixed), "-i", str(srt),
         "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text", "-metadata:s:s:0", "language=chi",
         "-t", f"{total:.3f}", "-movflags", "+faststart", str(final)])

    burned = out_dir / "final_9x16_burned.mp4"
    burned_ok = False
    try:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(video_faded), "-i", str(mixed),
             "-vf", "ass='drama.ass':fontsdir='fonts'",
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
        "segments": [{**s, "file": relpath(seg_files[i]), "sha256": sha256(seg_files[i])}
                     for i, s in enumerate(segments)],
        "audio_timeline": (
            {k: v for k, v in audio_timeline_report.items() if k != "graph"}
            if audio_timeline_report else None
        ),
        "content_type": content_type,
        "leading_silence_ms": leading_ms,
        "total_seconds": total,
        "audio_end_seconds": round(audio_end, 3),
        "soundscape": soundscape_report,
        "header": header,
        "ledger": audio.get("ledger"),
        "voice_end_seconds": round(timeline["voice_end_ms"] / 1000.0, 3),
        "trailing_silence_seconds": round(timeline["trailing_silence_ms"] / 1000.0, 3),
        "line_starts_ms": starts_ms,
        "line_starts": starts,
        "timeline": {
            "file": relpath(timeline_path),
            "audio_start_ms": timeline["audio_start_ms"],
            "audio_end_ms": timeline["audio_end_ms"],
            "voice_end_ms": timeline["voice_end_ms"],
            "trailing_silence_ms": timeline["trailing_silence_ms"],
        },
        "font": {
            "config": "config/fonts.yaml",
            "manifest": relpath(font_config.manifest_path),
            "role": subtitle_role.name,
            "font_key": subtitle_role.font_key,
            "weight": subtitle_face.weight,
            "family": subtitle_face.ass_name,
            "postscript_name": subtitle_face.postscript_name,
            "source_file": relpath(subtitle_face.path),
            "render_copy": relpath(render_font_path),
            "sha256": subtitle_face.sha256,
            "fontsdir": "fonts",
            "fontselect_log": relpath(fontselect_log),
            "fontselect_match": True,
            "roles_preview_only": [
                name for name, role in font_config.roles.items()
                if role.integration != "formal_build"
            ],
        },
        "outputs": {
            "final": relpath(final), "final_sha256": sha256(final),
            "burned": relpath(burned) if burned_ok else None,
            "srt": relpath(srt), "ass": relpath(ass_path),
            "mixed": relpath(mixed), "timeline": relpath(timeline_path),
            "fontselect_log": relpath(fontselect_log), "render_font": relpath(render_font_path),
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
