"""FFmpeg multi-track audio mixer.

The mixer is intentionally a thin graph builder around FFmpeg. It consumes the
strict :mod:`audio_timeline` contract and the audio asset registry; it does not
invent tracks, times or licensing. Narration/dialogue events may carry a direct
WAV path (derived from ``audio_manifest.json``); BGM/SFX must use ``asset_id`` so
the registry can verify status and hashes.

The old narration-only path in ``scripts/r3_build.py`` remains the default when
no timeline is supplied. This module is only used with an explicit timeline.
"""

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path
from typing import Any

from .audio_assets import AudioAssetError, AudioAssetRegistry, load_registry
from .audio_timeline import AudioEvent, AudioTimeline, AudioTrack, TimelineError, load_timeline


class MixError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _event_path(event: AudioEvent, root: Path, registry: AudioAssetRegistry | None) -> Path:
    if event.path:
        path = Path(event.path)
        path = path if path.is_absolute() else (root / path)
        if not path.is_file():
            raise MixError(f"{event.event_id}: file not found: {path}")
        return path
    if not event.asset_id:
        raise MixError(f"{event.event_id}: no path or asset_id")
    if registry is None:
        raise MixError(f"{event.event_id}: asset_id requires an audio asset registry")
    try:
        return registry.resolve(event.asset_id, root, require_ready=True)
    except AudioAssetError as exc:
        raise MixError(str(exc)) from exc


def _chain(*parts: str) -> str:
    return ",".join(part for part in parts if part)


def _fade_filters(fade_in_ms: int, fade_out_ms: int, duration_s: float) -> list[str]:
    filters: list[str] = []
    if fade_in_ms:
        filters.append(f"afade=t=in:st=0:d={fade_in_ms / 1000.0:.3f}")
    if fade_out_ms:
        start = max(0.0, duration_s - fade_out_ms / 1000.0)
        filters.append(f"afade=t=out:st={start:.3f}:d={fade_out_ms / 1000.0:.3f}")
    return filters


def _event_chain(event: AudioEvent, gain_db: float, sample_rate: int) -> str:
    duration_s = event.duration_ms / 1000.0
    return _chain(
        f"atrim=duration={duration_s:.3f}",
        "asetpts=PTS-STARTPTS",
        f"aresample={sample_rate}",
        "aformat=channel_layouts=mono",
        f"volume={gain_db:.2f}dB",
        *_fade_filters(event.fade_in_ms, event.fade_out_ms, duration_s),
        f"adelay={event.start_ms}|{event.start_ms}",
    )


def _bgm_chain(track: AudioTrack, duration_s: float, sample_rate: int) -> str:
    fade = _fade_filters(track.fade_in_ms, track.fade_out_ms, duration_s)
    return _chain(
        f"atrim=duration={duration_s:.3f}",
        "asetpts=PTS-STARTPTS",
        f"aresample={sample_rate}",
        "aformat=channel_layouts=mono",
        f"volume={track.gain_db:.2f}dB",
        *fade,
        f"apad=whole_dur={duration_s:.3f}",
        f"adelay={track.start_ms}|{track.start_ms}",
    )


def build_filter_graph(
    timeline: AudioTimeline,
    *,
    root: Path,
    registry: AudioAssetRegistry | None = None,
    duration_ms: int | None = None,
) -> tuple[list[str], str]:
    """Return ``(ffmpeg_inputs, filter_complex)`` for one timeline.

    Narration/dialogue are built first so their labels can drive BGM ducking.
    """
    inputs: list[str] = []
    graph: list[str] = []
    labels: list[str] = []
    labels_by_track: dict[str, list[str]] = {}
    index = 0
    sample_rate = timeline.sample_rate

    def add_input(path: Path, *, loop: bool = False) -> int:
        nonlocal index
        if loop:
            inputs.extend(["-stream_loop", "-1", "-i", str(path)])
        else:
            inputs.extend(["-i", str(path)])
        current = index
        index += 1
        return current

    def add_event(track: AudioTrack, event: AudioEvent) -> str:
        nonlocal index
        path = _event_path(event, root, registry)
        source = add_input(path)
        label = f"[e{index - 1}]"
        gain = track.gain_db + event.gain_db
        graph.append(f"[{source}:a]{_event_chain(event, gain, sample_rate)}{label}")
        labels.append(label)
        labels_by_track.setdefault(track.track_id, []).append(label)
        return label

    # 1) narration + dialogue
    for track in [t for t in timeline.tracks if t.type in ("narration", "dialogue")]:
        for event in track.events:
            add_event(track, event)
    # A ducking trigger is the sum of the requested narration/dialogue tracks.
    ducking_tracks = [t for t in timeline.tracks if t.type == "bgm" and t.ducking and t.ducking.enabled]
    trigger_labels: list[str] = []
    for bgm in ducking_tracks:
        assert bgm.ducking is not None
        for track_id in bgm.ducking.trigger_track_ids:
            trigger_labels.extend(labels_by_track.get(track_id, []))
    trigger_label: str | None = None
    if trigger_labels:
        if len(trigger_labels) == 1:
            trigger_label = trigger_labels[0]
        else:
            trigger_label = "[duck_trigger]"
            graph.append(
                f"{''.join(trigger_labels)}amix=inputs={len(trigger_labels)}:"
                f"duration=longest:normalize=0{trigger_label}"
            )

    # 2) BGM
    for track in [t for t in timeline.tracks if t.type == "bgm"]:
        if not track.asset_id:
            raise MixError(f"{track.track_id}: missing asset_id")
        if registry is None:
            raise MixError(f"{track.track_id}: BGM requires an audio asset registry")
        try:
            path = registry.resolve(track.asset_id, root, require_ready=True)
        except AudioAssetError as exc:
            raise MixError(str(exc)) from exc
        source = add_input(path, loop=track.loop)
        raw = f"[bgm_raw_{source}]"
        duration_ms = track.duration_ms or max(0, timeline.duration_ms - track.start_ms)
        if duration_ms <= 0:
            raise MixError(f"{track.track_id}: invalid BGM duration")
        graph.append(f"[{source}:a]{_bgm_chain(track, duration_ms / 1000.0, sample_rate)}{raw}")
        label = raw
        if track.ducking and track.ducking.enabled:
            if trigger_label is None:
                raise MixError(f"{track.track_id}: ducking requested but no trigger events")
            duck = f"[bgm_duck_{source}]"
            d = track.ducking
            graph.append(
                f"{raw}{trigger_label}sidechaincompress="
                f"threshold={d.threshold}:ratio={d.ratio}:"
                f"attack={d.attack_ms}:release={d.release_ms}{duck}"
            )
            label = duck
        labels.append(label)
        labels_by_track.setdefault(track.track_id, []).append(label)

    # 3) SFX
    for track in [t for t in timeline.tracks if t.type == "sfx"]:
        for event in track.events:
            if event.path:
                path = _event_path(event, root, registry)
            else:
                if registry is None:
                    raise MixError(f"{event.event_id}: SFX requires an audio asset registry")
                try:
                    path = registry.resolve(event.asset_id or "", root, require_ready=True)
                except AudioAssetError as exc:
                    raise MixError(str(exc)) from exc
            source = add_input(path)
            label = f"[e{index - 1}]"
            gain = track.gain_db + event.gain_db
            graph.append(f"[{source}:a]{_event_chain(event, gain, sample_rate)}{label}")
            labels.append(label)
            labels_by_track.setdefault(track.track_id, []).append(label)

    if not labels:
        raise MixError("timeline produced no audio inputs")
    final_duration_ms = duration_ms or timeline.duration_ms
    if final_duration_ms <= 0:
        raise MixError("final mix duration must be positive")
    duration_s = final_duration_ms / 1000.0
    mixed = "[mixed]"
    if len(labels) == 1:
        graph.append(
            f"{labels[0]}alimiter=limit=0.95,apad=whole_dur={duration_s:.3f},"
            f"atrim=duration={duration_s:.3f}{mixed}"
        )
    else:
        graph.append(
            f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,"
            f"alimiter=limit=0.95,apad=whole_dur={duration_s:.3f},"
            f"atrim=duration={duration_s:.3f}{mixed}"
        )
    return inputs, ";".join(graph)


def _loudnorm_stats(path: Path, target_lufs: float = -16.0,
                    true_peak: float = -1.5, lra: float = 11.0) -> dict[str, Any]:
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:print_format=json",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise MixError(f"loudness measurement failed: {proc.stderr[-1200:]}")
    start, end = proc.stderr.rfind("{"), proc.stderr.rfind("}")
    if start < 0 or end <= start:
        raise MixError("loudness measurement did not return JSON")
    try:
        return json.loads(proc.stderr[start:end + 1])
    except json.JSONDecodeError as exc:
        raise MixError(f"cannot parse loudness measurement: {exc}") from exc


def _normalise_loudness(path: Path, sample_rate: int, *, target_lufs: float = -16.0,
                        true_peak: float = -1.5, lra: float = 11.0) -> dict[str, Any]:
    """Two-pass loudnorm; one-pass dynamic mode under-shoots on short clips."""
    stats = _loudnorm_stats(path, target_lufs, true_peak, lra)
    if str(stats.get("input_i")) in ("-inf", "inf", "nan"):
        return stats
    tmp = path.with_suffix(".loudnorm.wav")
    af = (
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:"
        f"measured_I={stats.get('input_i')}:measured_TP={stats.get('input_tp')}:"
        f"measured_LRA={stats.get('input_lra')}:measured_thresh={stats.get('input_thresh')}:"
        f"offset={stats.get('target_offset')}:linear=true"
    )
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-af", af,
           "-ac", "1", "-ar", str(sample_rate), "-c:a", "pcm_s16le", str(tmp)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise MixError(f"ffmpeg loudness normalization failed: {proc.stderr[-1200:]}")
    tmp.replace(path)
    return _loudnorm_stats(path, target_lufs, true_peak, lra)


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as fh:
        return fh.getnframes() / float(fh.getframerate())


def mix_timeline(
    timeline_path: Path,
    out_wav: Path,
    *,
    root: Path,
    asset_registry_path: Path | None = None,
    duration_ms: int | None = None,
    ffmpeg: str = "ffmpeg",
) -> dict[str, Any]:
    root = Path(root).resolve()
    timeline = load_timeline(timeline_path)
    try:
        registry = load_registry(asset_registry_path) if asset_registry_path else None
    except AudioAssetError as exc:
        raise MixError(str(exc)) from exc
    inputs, graph = build_filter_graph(timeline, root=root, registry=registry, duration_ms=duration_ms)
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y", "-v", "error", *inputs,
        "-filter_complex", graph,
        "-map", "[mixed]", "-ac", "1", "-ar", str(timeline.sample_rate),
        "-c:a", "pcm_s16le", str(out_wav),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise MixError(f"ffmpeg mix failed: {proc.stderr[-2000:]}")
    if not out_wav.is_file():
        raise MixError("ffmpeg reported success but produced no file")
    measured = _wav_duration(out_wav)
    expected = (duration_ms or timeline.duration_ms) / 1000.0
    if abs(measured - expected) > 0.15:
        raise MixError(f"mix duration {measured:.3f}s does not match timeline {expected:.3f}s")
    loudness = _normalise_loudness(out_wav, timeline.sample_rate)
    return {
        "status": "PASS",
        "timeline": str(timeline_path),
        "timeline_sha256": _sha256(Path(timeline_path)),
        "output": str(out_wav),
        "output_sha256": _sha256(out_wav),
        "duration_seconds": round(measured, 3),
        "sample_rate": timeline.sample_rate,
        "loudness": loudness,
        "tracks": [t.track_id for t in timeline.tracks],
        "graph": graph,
        "asset_registry": str(asset_registry_path) if asset_registry_path else None,
    }
