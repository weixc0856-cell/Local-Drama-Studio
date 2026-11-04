"""Independent technical quality checks.

The build script already fails on FFmpeg errors, but that is not a quality gate.
This module inspects the produced files directly: image blankness, video decode,
duration/streams, and audio peak. A failed check marks the build FAILED; it never
rewrites or deletes the artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat

from .motion.spec import H, W, scaled_width

PASS = "PASS"
FAIL = "FAIL"


class QualityError(RuntimeError):
    pass


def _result(ok: bool, **detail: Any) -> dict[str, Any]:
    return {"status": PASS if ok else FAIL, **detail}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_image(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _result(False, path=str(path), error="missing")
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            stat = ImageStat.Stat(image)
            mean = sum(stat.mean) / 3.0
            stddev = sum(stat.stddev) / 3.0
            width, height = image.size
    except Exception as exc:  # noqa: BLE001 - decode failure is a quality failure
        return _result(False, path=str(path), error=f"{type(exc).__name__}: {exc}")
    blank = stddev < 1.5
    black = mean < 4.0 and stddev < 3.0
    return _result(
        not blank and not black,
        path=str(path),
        width=width,
        height=height,
        mean=round(mean, 2),
        stddev=round(stddev, 2),
        blank=blank,
        black=black,
    )


def _ffprobe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,duration,channels,sample_rate",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if proc.returncode != 0:
        raise QualityError(proc.stderr.strip()[-800:])
    return json.loads(proc.stdout)


def check_video(
    path: Path,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> dict[str, Any]:
    if not path.is_file():
        return _result(False, path=str(path), error="missing")
    try:
        probe = _ffprobe(path)
    except (QualityError, ValueError, OSError) as exc:
        return _result(False, path=str(path), error=str(exc))
    streams = probe.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        return _result(False, path=str(path), error="no video stream")
    decode = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    duration = float((probe.get("format") or {}).get("duration") or 0)
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    size_ok = (expected_width is None or width == expected_width) and (
        expected_height is None or height == expected_height
    )
    return _result(
        decode.returncode == 0 and duration > 0 and size_ok,
        path=str(path),
        duration=round(duration, 3),
        width=width,
        height=height,
        has_audio=audio is not None,
        audio_codec=(audio or {}).get("codec_name"),
        decode_returncode=decode.returncode,
        decode_stderr=decode.stderr.strip()[-500:],
        size_ok=size_ok,
    )


def check_audio(
    path: Path,
    *,
    expected_duration: float | None = None,
    min_mean_db: float | None = None,
    detect_silence: bool = False,
) -> dict[str, Any]:
    if not path.is_file():
        return _result(False, path=str(path), error="missing")
    try:
        probe = _ffprobe(path)
    except (QualityError, ValueError, OSError) as exc:
        return _result(False, path=str(path), error=str(exc))
    stream = next((s for s in probe.get("streams") or [] if s.get("codec_type") == "audio"), None)
    if stream is None:
        return _result(False, path=str(path), error="no audio stream")
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    match = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", proc.stderr)
    max_volume = float(match.group(1)) if match else None
    mean_match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", proc.stderr)
    mean_volume = float(mean_match.group(1)) if mean_match else None
    clipped = max_volume is not None and max_volume >= -0.1
    duration = round(float((probe.get("format") or {}).get("duration") or 0), 3)

    silences = []
    if detect_silence:
        silence = subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(path),
             "-af", "silencedetect=noise=-45dB:d=0.35", "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
        )
        for line in silence.stderr.splitlines():
            start = re.search(r"silence_start:\s*(-?[\d.]+)", line)
            if start:
                silences.append({"start": float(start.group(1)), "end": None})
            end = re.search(r"silence_end:\s*([\d.]+).*silence_duration:\s*([\d.]+)", line)
            if end and silences:
                silences[-1]["end"] = float(end.group(1))
                silences[-1]["duration"] = float(end.group(2))
    silent_seconds = round(sum(item.get("duration", 0.0) for item in silences), 3)
    silence_ratio = round(silent_seconds / duration, 3) if duration > 0 else 1.0
    too_quiet = bool(
        min_mean_db is not None and (mean_volume is None or mean_volume < min_mean_db)
    )
    duration_ok = True
    if expected_duration is not None:
        duration_ok = abs(duration - float(expected_duration)) <= max(
            0.35, 0.08 * float(expected_duration)
        )
    # A whole-line recording that is almost entirely silence is a broken cut,
    # not a pause.
    broken = detect_silence and duration > 0 and silence_ratio >= 0.85
    ok = (
        proc.returncode == 0
        and not clipped
        and not too_quiet
        and duration_ok
        and not broken
    )
    return _result(
        ok,
        path=str(path),
        sample_rate=stream.get("sample_rate"),
        channels=stream.get("channels"),
        duration=duration,
        expected_duration=expected_duration,
        duration_ok=duration_ok,
        mean_volume_db=mean_volume,
        max_volume_db=max_volume,
        clipped=clipped,
        too_quiet=too_quiet,
        silence_seconds=silent_seconds,
        silence_ratio=silence_ratio,
        broken_silence=broken,
        silences=silences[:20],
    )


def check_audio_manifest(
    manifest_path: Path,
    *,
    root: Path | None = None,
    timeline_path: Path | None = None,
) -> dict[str, Any]:
    """Per-line audio QA + optional subtitle/audio time alignment.

    The pronunciation layer is *not* judged here; it stays PENDING until a human
    listens or ASR is run (see ``scripts/tts_qa.py``).
    """
    manifest_path = manifest_path.resolve()
    root = (root or _infer_root(manifest_path)).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    lines = []
    for entry in data.get("lines") or []:
        path = Path(entry["file"])
        path = path if path.is_absolute() else (root / path)
        expected = float(entry.get("duration_seconds") or 0) or None
        check = check_audio(path, expected_duration=expected, min_mean_db=-45.0, detect_silence=True)
        check.update({
            "index": entry.get("index"),
            "text": entry.get("text"),
            "display_text": entry.get("display_text") or entry.get("subtitle_text"),
            "parts": len(entry.get("parts") or []),
        })
        lines.append(check)
    checks: dict[str, Any] = {
        "manifest": str(manifest_path),
        "mode": data.get("mode", "narration"),
        "lines": lines,
        "summary": {
            "lines": len(lines),
            "failed_lines": sum(1 for line in lines if line["status"] != PASS),
            "clipped_lines": sum(1 for line in lines if line.get("clipped")),
            "quiet_lines": sum(1 for line in lines if line.get("too_quiet")),
            "broken_lines": sum(1 for line in lines if line.get("broken_silence")),
            "max_silence_ratio": max((line.get("silence_ratio") or 0 for line in lines), default=0),
        },
    }
    if timeline_path is not None:
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        events = timeline.get("segments") or []
        mismatches = []
        for event in events:
            if event["subtitle_start_ms"] < event["speech_start_ms"]:
                mismatches.append({"segment": event["segment_id"], "issue": "subtitle starts before speech"})
            if event["subtitle_end_ms"] > event["audio_end_ms"]:
                mismatches.append({"segment": event["segment_id"], "issue": "subtitle extends past pause"})
        checks["timeline"] = {
            "path": str(timeline_path),
            "events": len(events),
            "mismatches": mismatches,
            "status": PASS if not mismatches else FAIL,
        }
    pronunciation = manifest_path.parent / "pronunciation_report.json"
    if pronunciation.is_file():
        report = json.loads(pronunciation.read_text(encoding="utf-8"))
        checks["pronunciation"] = {
            "report": str(pronunciation),
            "hit_lines": report.get("summary", {}).get("hit_lines"),
            "review_status": report.get("summary", {}).get("review_status", "PENDING"),
        }
    audio_ok = all(line["status"] == PASS for line in lines)
    if "timeline" in checks:
        audio_ok = audio_ok and checks["timeline"]["status"] == PASS
    # Even a clean waveform cannot prove pronunciation: the gate stops at PARTIAL.
    checks["status"] = PASS if audio_ok else FAIL
    if audio_ok and checks.get("pronunciation", {}).get("review_status") != "PASS":
        checks["status"] = "PARTIAL"
        checks["note"] = "波形与时长通过；发音正确性仍需人工抽听或 ASR（scripts/tts_qa.py）"
    checks["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report_path = manifest_path.parent / "audio_qa_report.json"
    report_path.write_text(
        json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    checks["report"] = str(report_path)
    return checks


def image_metrics(path: Path) -> dict[str, Any]:
    """Colour/edge/luma metrics shared by the static gate and A/B comparison."""
    with Image.open(path) as raw:
        image = raw.convert("RGB")
    width, height = image.size
    if width > 512:
        small = image.resize((512, round(512 * height / width)), Image.LANCZOS)
    else:
        small = image
    gray = small.convert("L")
    hist = gray.histogram()
    total = sum(hist) or 1
    mean, stddev = ImageStat.Stat(gray).mean[0], ImageStat.Stat(gray).stddev[0]
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_density = ImageStat.Stat(edges).mean[0] / 255.0
    blurred = gray.filter(ImageFilter.GaussianBlur(2))
    high_frequency = ImageStat.Stat(ImageChops.difference(gray, blurred)).mean[0] / 255.0
    saturation = ImageStat.Stat(small.convert("HSV")).mean[1] / 255.0
    lab = small.convert("LAB")
    raw_lab = ImageStat.Stat(lab).mean
    # Normalise PIL's 8-bit LAB to CIELAB: L 0-100, a/b centred at 0.
    lab_mean = [raw_lab[0] * 100.0 / 255.0, raw_lab[1] - 128.0, raw_lab[2] - 128.0]
    return {
        "width": width,
        "height": height,
        "aspect_ratio": round(width / height, 4),
        "mean": round(mean, 2),
        "stddev": round(stddev, 2),
        "whitespace_fraction": round(sum(hist[240:]) / total, 4),
        "black_fraction": round(sum(hist[:16]) / total, 4),
        "edge_density": round(edge_density, 4),
        "high_frequency_ratio": round(high_frequency, 4),
        "saturation_mean": round(saturation, 4),
        "lab_mean": [round(value, 2) for value in lab_mean],
    }


def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"bad hex colour: {value!r}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _rgb_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """PIL LAB is 8-bit: L 0-255, a/b 0-255 around 128."""
    pixel = Image.new("RGB", (1, 1), rgb).convert("LAB").getpixel((0, 0))
    return (pixel[0] * 100.0 / 255.0, pixel[1] - 128.0, pixel[2] - 128.0)


def _lab_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return round(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5, 2)


def _percentile(hist: list[int], fraction: float) -> int:
    target = sum(hist) * fraction
    running = 0
    for value, count in enumerate(hist):
        running += count
        if running >= target:
            return value
    return 255


def _region_mean(gray: Image.Image, box: tuple[float, float, float, float]) -> float:
    width, height = gray.size
    x0, y0, x1, y1 = (
        int(box[0] * width), int(box[1] * height), int(box[2] * width), int(box[3] * height)
    )
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return round(ImageStat.Stat(gray.crop((x0, y0, x1, y1))).mean[0], 2)


def check_aesthetic_risk(
    path: Path,
    design: dict[str, Any],
    palette: dict[str, str],
    *,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Risk hints for a generated still against its shot aesthetic design.

    These are *indicators*, not an aesthetic verdict: the result always ends in
    ``PENDING_HUMAN_REVIEW``. Thresholds are deliberately loose and recorded in
    the report so they can be recalibrated from real comparisons.
    """
    from .aesthetics import POSITION_TARGET

    metrics = image_metrics(path)
    with Image.open(path) as raw:
        image = raw.convert("RGB")
    if image.width > 512:
        image = image.resize((512, round(512 * image.height / image.width)), Image.LANCZOS)
    gray = image.convert("L")
    hist = gray.histogram()
    total = sum(hist) or 1
    mean = metrics["mean"]
    contrast = _percentile(hist, 0.95) - _percentile(hist, 0.05)
    highlight = round(sum(hist[240:]) / total, 4)
    shadow = round(sum(hist[:40]) / total, 4)
    left = _region_mean(gray, (0.0, 0.0, 0.42, 1.0))
    right = _region_mean(gray, (0.58, 0.0, 1.0, 1.0))
    top = _region_mean(gray, (0.0, 0.0, 1.0, 0.38))
    bottom = _region_mean(gray, (0.0, 0.62, 1.0, 1.0))
    lr_delta = round(left - right, 2)
    tb_delta = round(top - bottom, 2)

    # Edge-weighted centroid (saliency proxy, not subject segmentation).
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edges)
    threshold = edge_stat.mean[0] + 0.75 * edge_stat.stddev[0]
    pixels = edges.load()
    width, height = edges.size
    sx = sy = count = 0
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if pixels[x, y] >= threshold:
                sx += x
                sy += y
                count += 1
    centroid = [round(sx / count / width, 3), round(sy / count / height, 3)] if count else [0.5, 0.5]
    target = POSITION_TARGET.get(design["composition"]["subject_position"], (0.5, 0.5))
    placement_error = round(((centroid[0] - target[0]) ** 2 + (centroid[1] - target[1]) ** 2) ** 0.5, 3)

    # Focus clarity: the clearest tile should stand out from the average tile.
    tile_stds = []
    for ty in range(4):
        for tx in range(4):
            box = (tx * width // 4, ty * height // 4, (tx + 1) * width // 4, (ty + 1) * height // 4)
            tile_stds.append(ImageStat.Stat(gray.crop(box)).stddev[0])
    focus_ratio = round(max(tile_stds) / max(1.0, sum(tile_stds) / len(tile_stds)), 2)

    # Depth layering proxy: three horizontal bands.
    bands = [_region_mean(gray, (0.0, 0.0, 1.0, 0.33)),
             _region_mean(gray, (0.0, 0.33, 1.0, 0.66)),
             _region_mean(gray, (0.0, 0.66, 1.0, 1.0))]
    band_spread = round(max(bands) - min(bands), 2)

    lab_mean = tuple(metrics["lab_mean"])
    design_colors = [design["color"]["dominant"], *design["color"].get("secondary", []),
                     *design["color"].get("accent", [])]
    palette_lab = {
        key: _rgb_lab(_hex_rgb(value)) for key, value in palette.items()
    }
    dominant_key = design["color"]["dominant"]
    dominant_distance = (
        _lab_distance(lab_mean, palette_lab[dominant_key])
        if dominant_key in palette_lab else None
    )
    nearest = min(
        ((key, _lab_distance(lab_mean, value)) for key, value in palette_lab.items()),
        key=lambda item: item[1],
        default=(None, None),
    )
    measured_temperature = "warm" if lab_mean[2] > 5 else "cool" if lab_mean[2] < -5 else "neutral"

    flags: list[dict[str, Any]] = []

    def flag(code: str, severity: str, detail: str, **extra: Any) -> None:
        flags.append({"code": code, "severity": severity, "detail": detail, **extra})

    if placement_error > 0.22:
        flag("placement", "warn", f"主体重心离设计位置约 {placement_error:.2f}（归一化）",
             target=list(target), centroid=centroid)
    ws = design["composition"]["whitespace_ratio"]
    if abs(metrics["whitespace_fraction"] - ws) > 0.15:
        flag("whitespace", "warn",
             f"留白 {metrics['whitespace_fraction']:.2f} 与设计 {ws:.2f} 相差超过 0.15")
    if metrics["edge_density"] > 0.22:
        flag("crowding", "warn", f"边缘密度 {metrics['edge_density']:.3f} 偏高，可能拥挤")
    if metrics["edge_density"] < 0.012:
        flag("sparse", "info", f"边缘密度 {metrics['edge_density']:.3f} 偏低，可能过空")
    if focus_ratio < 1.35:
        flag("focus", "warn", f"最清晰区域仅 {focus_ratio:.2f}× 平均，视觉焦点可能不明确")
    if contrast < 30:
        flag("contrast", "info", f"明暗跨度 {contrast} 偏低")
    if design["lighting"]["contrast"] == "high" and contrast < 40:
        flag("contrast_intent", "warn", "设计要求高反差，实测跨度偏低")
    if design["lighting"]["contrast"] == "low" and contrast > 85:
        flag("contrast_intent", "warn", "设计要求低反差，实测跨度过高")
    direction = design["lighting"]["direction"]
    if direction == "side_left" and lr_delta < -6:
        flag("light_direction", "warn", f"设计为左侧光，但右侧更亮（左右差 {lr_delta}）")
    if direction == "side_right" and lr_delta > 6:
        flag("light_direction", "warn", f"设计为右侧光，但左侧更亮（左右差 {lr_delta}）")
    if direction == "diffuse" and abs(lr_delta) > 18:
        flag("light_direction", "info", f"设计为漫射光，左右亮度差 {lr_delta} 偏大")
    intended_temp = design["color"]["temperature"]
    if intended_temp in ("warm", "cool") and measured_temperature not in (intended_temp, "neutral"):
        flag("temperature", "warn", f"设计为{intended_temp}调，实测偏{measured_temperature}")
    if dominant_distance is not None and dominant_distance > 42:
        flag("palette", "warn", f"主色与风格色板距离 {dominant_distance}（Delta E 76）")
    if design["mise_en_scene"].get("modern_elements") == "risk":
        flag("modern_elements", "warn", "设计标记了现代物件风险，必须人工核对")
    if not design["depth"].get("layered_assets") and design["depth"].get("aerial_perspective"):
        flag("depth_layers", "info", "前中远景依靠空气透视；无独立图层，不能据此声称 2.5D")

    severity = "warn" if any(item["severity"] == "warn" for item in flags) else "ok"
    return {
        "path": str(path),
        "shot_id": (meta or {}).get("shot_id"),
        "variant_id": (meta or {}).get("variant_id"),
        "axis": (meta or {}).get("axis"),
        "metrics": metrics,
        "composition": {
            "centroid": centroid,
            "target": list(target),
            "placement_error": placement_error,
            "focus_ratio": focus_ratio,
            "crowding": metrics["edge_density"],
        },
        "lighting": {
            "mean": mean,
            "contrast_p5_p95": contrast,
            "highlight_fraction": highlight,
            "shadow_fraction": shadow,
            "left_mean": left,
            "right_mean": right,
            "lr_delta": lr_delta,
            "tb_delta": tb_delta,
        },
        "color": {
            "lab_mean": list(lab_mean),
            "nearest_palette": nearest[0],
            "nearest_distance": nearest[1],
            "dominant_distance": dominant_distance,
            "measured_temperature": measured_temperature,
            "saturation_mean": metrics["saturation_mean"],
            "design_colors": design_colors,
        },
        "depth": {"band_means": bands, "band_spread": band_spread},
        "risk_flags": flags,
        "risk_severity": severity,
        "aesthetic_status": "PENDING_HUMAN_REVIEW",
        "note": "自动指标只给风险提示，不能代替人工审美验收",
    }


def check_color_continuity(items: list[dict[str, Any]], threshold: float = 15.0) -> dict[str, Any]:
    """Adjacent-shot LAB/luma continuity; a large jump is a risk, not a verdict."""
    records = []
    for item in items:
        path = Path(item["path"])
        metrics = image_metrics(path)
        records.append({
            "id": item.get("id"),
            "path": str(path),
            "lab_mean": metrics["lab_mean"],
            "luma": metrics["mean"],
        })
    pairs = []
    for left, right in zip(records, records[1:]):
        distance = _lab_distance(tuple(left["lab_mean"]), tuple(right["lab_mean"]))
        pairs.append({
            "from": left["id"],
            "to": right["id"],
            "delta_e": distance,
            "luma_delta": round(right["luma"] - left["luma"], 2),
            "risk": distance > threshold,
        })
    return {
        "threshold_delta_e": threshold,
        "records": records,
        "pairs": pairs,
        "status": "RISK" if any(pair["risk"] for pair in pairs) else "OK",
    }


def check_dynamic_aesthetics(
    manifest_path: Path, aesthetic_plan_path: Path | None = None
) -> dict[str, Any]:
    """Read a motion manifest and check static stability + colour/light continuity."""
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = manifest.get("shots") or []
    first_frames = []
    stability = []
    for shot in shots:
        frames = {item["name"]: item for item in shot.get("sample_frames") or []}
        if "first" in frames and frames["first"].get("path"):
            first_frames.append({"id": shot.get("id"), "path": frames["first"]["path"]})
        region = shot.get("region_checks") or {}
        guards = {item["band"]: item["mean_abs_diff"] for item in region.get("structure_bands") or []}
        stability.append({
            "shot_id": shot.get("id"),
            "camera_move": (shot.get("camera") or {}).get("move"),
            "isolates_local_motion": region.get("isolates_local_motion"),
            "structure_max_diff": max(guards.values()) if guards else None,
            "local_layers": len(shot.get("layers") or []),
        })
    continuity = check_color_continuity(first_frames)
    flags = []
    focus_checks = []
    if aesthetic_plan_path is not None:
        from .aesthetics import POSITION_TARGET, load_plan

        plan = load_plan(aesthetic_plan_path)
        for item, shot in zip(stability, shots):
            shot_set = next((s for s in plan.shots if s.shot_id == item["shot_id"]), None)
            if shot_set is None:
                continue
            design = shot_set.variants[0].design.composition
            target = POSITION_TARGET[design.subject_position]
            camera = shot.get("camera") or {}
            focus = tuple(camera.get("focus") or (0.5, 0.5))
            error = round(((focus[0] - target[0]) ** 2 + (focus[1] - target[1]) ** 2) ** 0.5, 3)
            focus_checks.append({
                "shot_id": item["shot_id"],
                "assumed_variant": shot_set.variants[0].variant_id,
                "camera_move": camera.get("move"),
                "camera_focus": list(focus),
                "design_subject_position": design.subject_position,
                "target": list(target),
                "focus_error": error,
            })
            if camera.get("move") not in ("static", None) and error > 0.2:
                flags.append({"code": "camera_focus", "severity": "warn",
                              "detail": f"{item['shot_id']} 运镜焦点与设计主体位置偏差 {error}"})
    for item in stability:
        if item["isolates_local_motion"] and (item["structure_max_diff"] or 0) > 1.0:
            flags.append({"code": "static_structure", "severity": "warn",
                          "detail": f"{item['shot_id']} 静态机位结构带变化 {item['structure_max_diff']}/255"})
    if continuity["status"] == "RISK":
        flags.append({"code": "color_continuity", "severity": "warn",
                      "detail": "相邻镜头 LAB 距离超过阈值"})
    report = {
        "manifest": str(manifest_path),
        "shots": stability,
        "continuity": continuity,
        "composition_focus": focus_checks,
        "risk_flags": flags,
        "risk_severity": "warn" if flags else "ok",
        "aesthetic_status": "PENDING_HUMAN_REVIEW",
        "note": "动态美学只检查稳定性与连续性；转场空间关系仍需人工看片",
    }
    out = manifest_path.parent / "dynamic_aesthetic_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report"] = str(out)
    return report


# ---------------------------------------------------------------------------
# M3: motion quality gates
# ---------------------------------------------------------------------------

RIGID_THRESHOLDS = {
    "mean_diff_max": 6.0,
    "p95_diff_max": 22.0,
    "edge_shift_pct_max": 0.06,
}

TEMPORAL_THRESHOLDS = {
    "frame_jump_luma": 6.0,
    "frame_jump_ratio": 4.0,
    "tail_fraction": 0.25,
    "tail_drop_luma": 5.0,
    "tail_slope_luma_per_s": -0.8,
    "tail_monotonic": 0.8,
    "flicker_residual_std": 0.8,
    "flicker_oscillation": 0.30,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _ease_value(easing: str, progress: float) -> float:
    p = _clamp(progress, 0.0, 1.0)
    if easing == "linear":
        return p
    if easing == "ease_in":
        return p * p
    if easing == "ease_out":
        return 1.0 - (1.0 - p) * (1.0 - p)
    return 3.0 * p * p - 2.0 * p * p * p


def camera_box_at(camera: dict[str, Any], box: list[float], t: float) -> tuple[float, float, float, float]:
    """Map a source-normalized box to output-normalized coordinates at time ``t``.

    Mirrors the FFmpeg expressions in ``motion/camera.py``. This is what lets a
    locked-region check follow the subject through a pan or zoom instead of
    comparing a fixed rectangle against moving content.
    """
    move = str(camera.get("move") or "static")
    duration = max(1e-6, float(camera.get("duration_seconds") or 1.0))
    progress = _clamp(t / duration, 0.0, 1.0)
    ease = _ease_value(str(camera.get("easing") or "ease_in_out"), progress)
    source = camera.get("source_size") or [576, 1024]
    src_w, src_h = int(source[0]), int(source[1])

    if move == "static":
        return (box[0], box[1], box[2], box[3])

    if move in ("scroll_pan", "slow_lateral_track"):
        scaled_w = scaled_width(src_w, src_h, H)
        start = float(camera.get("pan_start_px") or 0.0)
        end = float(camera.get("pan_end_px") or 0.0)
        x = start + (end - start) * ease
        return ((box[0] * scaled_w - x) / W, box[1],
                (box[2] * scaled_w - x) / W, box[3])

    # push / pull: 2x canvas, centre crop, zoompan window
    scaled_w = scaled_width(src_w, src_h, H * 2)
    crop_x = (scaled_w - W * 2) / 2.0
    scale = H * 2 / src_h
    px0 = box[0] * scaled_w - crop_x
    px1 = box[2] * scaled_w - crop_x
    py0 = box[1] * H * 2
    py1 = box[3] * H * 2
    z0 = float(camera.get("scale_start") or 1.0)
    z1 = float(camera.get("scale_end") or 1.0)
    zoom = z0 + (z1 - z0) * ease
    focus = camera.get("focus") or [0.5, 0.5]
    fx, fy = float(focus[0]), float(focus[1])
    window_w = W * 2 / zoom
    window_h = H * 2 / zoom
    ox = fx * W * 2 - window_w / 2.0
    if move == "push_in_with_pan":
        ox += float(camera.get("push_pan_fraction") or 0.0) * W * 2 * (ease - 0.5)
    ox = _clamp(ox, 0.0, W * 2 - window_w)
    oy = _clamp(fy * H * 2 - window_h / 2.0, 0.0, H * 2 - window_h)
    return ((px0 - ox) / window_w, (py0 - oy) / window_h,
            (px1 - ox) / window_w, (py1 - oy) / window_h)


def _decode_gray_frames(path: Path, width: int = 270, height: int = 480) -> list[Image.Image]:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-vf", f"scale={width}:{height}:flags=area,format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise QualityError(proc.stderr.decode("utf-8", "replace")[-800:])
    size = width * height
    data = proc.stdout
    return [Image.frombytes("L", (width, height), data[i:i + size])
            for i in range(0, len(data) - size + 1, size)]


def _clamped_crop(frame: Image.Image, box: tuple[float, float, float, float],
                  inset: float = 0.08) -> Image.Image | None:
    x0, y0, x1, y1 = box
    dx = (x1 - x0) * inset
    dy = (y1 - y0) * inset
    width, height = frame.size
    px0 = int(round(_clamp(x0 + dx, 0.0, 1.0) * (width - 1)))
    px1 = int(round(_clamp(x1 - dx, 0.0, 1.0) * (width - 1)))
    py0 = int(round(_clamp(y0 + dy, 0.0, 1.0) * (height - 1)))
    py1 = int(round(_clamp(y1 - dy, 0.0, 1.0) * (height - 1)))
    if px1 - px0 < 3 or py1 - py0 < 3:
        return None
    return frame.crop((px0, py0, px1, py1))


def _edge_center(crop: Image.Image) -> tuple[float, float] | None:
    edges = crop.resize((96, 96), Image.BILINEAR).filter(ImageFilter.FIND_EDGES)
    mask = edges.point(lambda value: 255 if value > 24 else 0)
    # FIND_EDGES marks the crop border itself; ignore that 4 px frame so the
    # bbox describes the subject, not the box.
    inner = mask.crop((4, 4, 92, 92))
    bbox = inner.getbbox()
    if not bbox:
        return None
    bbox = (bbox[0] + 4, bbox[1] + 4, bbox[2] + 4, bbox[3] + 4)
    return ((bbox[0] + bbox[2]) / 2.0 / 96.0, (bbox[1] + bbox[3]) / 2.0 / 96.0)


def _p95(histogram: list[int]) -> int:
    total = sum(histogram)
    if total == 0:
        return 0
    target = total * 0.95
    running = 0
    for value, count in enumerate(histogram):
        running += count
        if running >= target:
            return value
    return 255


def _load_shot_manifest(shot_manifest: dict[str, Any] | Path | str,
                        video_path: Path) -> dict[str, Any]:
    if isinstance(shot_manifest, dict):
        data = shot_manifest
    else:
        data = json.loads(Path(shot_manifest).read_text(encoding="utf-8"))
    if "shots" in data:
        shots = data.get("shots") or []
        for shot in shots:
            output = str(shot.get("output") or "")
            if output and Path(output).name == video_path.name:
                return shot
        if shots:
            return shots[0]
    return data


def check_rigid_protection(
    shot_manifest: dict[str, Any] | Path | str,
    video_path: Path | str,
    *,
    fps: int = 24,
) -> dict[str, Any]:
    """Check that locked/hard_excluded regions stay rigid in the rendered clip.

    The region box is mapped through the camera transform for every frame, so
    the check works for pans and push-ins, not only static shots. Two signals:

    * frame-to-frame difference inside the tracked box (a warp or overlay leak);
    * edge-bbox centre drift relative to the first frame (subject displacement).

    Any region over threshold returns ``RIGID_OBJECT_VIOLATION``.
    """
    video = Path(video_path)
    if not video.is_file():
        return {"status": FAIL, "code": "RIGID_OBJECT_VIOLATION",
                "error": f"missing video: {video}"}
    shot = _load_shot_manifest(shot_manifest, video)
    regions = [region for region in (shot.get("regions") or [])
               if region.get("permission") in ("locked", "hard_excluded")]
    if not regions:
        return {"status": PASS, "code": "NO_LOCKED_REGIONS",
                "note": "镜头没有声明 locked/hard_excluded 区域，未执行刚体检查",
                "video": str(video)}
    camera = shot.get("camera") or {"move": "static", "duration_seconds": 1.0,
                                    "source_size": shot.get("source_size") or [576, 1024]}
    frames = _decode_gray_frames(video)
    if len(frames) < 2:
        return {"status": FAIL, "code": "RIGID_OBJECT_VIOLATION",
                "error": "video has fewer than 2 decoded frames", "video": str(video)}

    results = []
    for region in regions:
        raw_box = region.get("box") or {}
        if isinstance(raw_box, dict):
            normalized = [float(raw_box["x0"]), float(raw_box["y0"]),
                          float(raw_box["x1"]), float(raw_box["y1"])]
        else:
            normalized = [float(value) for value in raw_box]
        tracked = [_clamped_crop(frame, camera_box_at(camera, normalized, index / fps))
                   for index, frame in enumerate(frames)]
        tracked = [crop for crop in tracked if crop is not None]
        if len(tracked) < 2:
            results.append({"id": region.get("id"), "permission": region.get("permission"),
                            "violated": True, "reasons": ["region_outside_frame"],
                            "frames": len(tracked)})
            continue
        diffs = []
        histograms = []
        for previous, current in zip(tracked, tracked[1:]):
            a = previous.resize((64, 64), Image.BILINEAR)
            b = current.resize((64, 64), Image.BILINEAR)
            difference = ImageChops.difference(a, b)
            stat = ImageStat.Stat(difference)
            diffs.append(stat.mean[0])
            histograms.append(difference.histogram())
        centers = [_edge_center(crop) for crop in tracked]
        centers = [center for center in centers if center is not None]
        edge_shift = 0.0
        if len(centers) >= 2:
            first = centers[0]
            edge_shift = max(math.hypot(cx - first[0], cy - first[1])
                             for cx, cy in centers)
        reasons = []
        if sum(diffs) / len(diffs) > RIGID_THRESHOLDS["mean_diff_max"]:
            reasons.append("frame_difference")
        if diffs and max(diffs) > RIGID_THRESHOLDS["mean_diff_max"] * 2:
            reasons.append("frame_difference_spike")
        if histograms and _p95(histograms[-1]) > RIGID_THRESHOLDS["p95_diff_max"]:
            reasons.append("p95_difference")
        # The edge-bbox heuristic is meaningful for a compact rigid silhouette.
        # Soft background regions (moon, mist) use the frame-difference signal.
        if region.get("role") == "rigid_object" and edge_shift > RIGID_THRESHOLDS["edge_shift_pct_max"]:
            reasons.append("edge_drift")
        results.append({
            "id": region.get("id"),
            "permission": region.get("permission"),
            "role": region.get("role"),
            "frames": len(tracked),
            "mean_diff_avg": round(sum(diffs) / len(diffs), 3) if diffs else 0.0,
            "mean_diff_max": round(max(diffs), 3) if diffs else 0.0,
            "edge_shift_pct": round(edge_shift, 4),
            "edge_check_applied": region.get("role") == "rigid_object",
            "violated": bool(reasons),
            "reasons": reasons,
        })
    violated = any(item["violated"] for item in results)
    return {
        "status": FAIL if violated else PASS,
        "code": "RIGID_OBJECT_VIOLATION" if violated else "RIGID_PROTECTION_OK",
        "video": str(video),
        "camera_move": camera.get("move"),
        "thresholds": RIGID_THRESHOLDS,
        "regions": results,
    }


def _flicker_metrics(values: list[float], fps: float) -> dict[str, float]:
    half_window = max(3, int(round(fps * 0.5)))
    smoothed = []
    for index in range(len(values)):
        window = values[max(0, index - half_window):index + half_window + 1]
        smoothed.append(sum(window) / len(window))
    residual = [value - smooth for value, smooth in zip(values, smoothed)]
    residual_std = math.sqrt(sum(value * value for value in residual) / len(residual))
    steps = [residual[i] - residual[i - 1] for i in range(1, len(residual))]
    flips = sum(1 for a, b in zip(steps, steps[1:]) if a and b and (a > 0) != (b > 0))
    return {
        "residual_std": round(residual_std, 3),
        "oscillation": round(flips / max(1, len(steps) - 1), 3),
        "range": round(max(values) - min(values), 3),
        "frames": len(values),
    }


def _linear_slope(values: list[float], fps: float) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    numerator = sum((i - mean_x) * (value - mean_y) for i, value in enumerate(values))
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    return (numerator / denominator) * fps if denominator else 0.0


def _transition_windows(transition_manifest: dict[str, Any] | Path | str | None) -> list[tuple[float, float]]:
    """Known transition / cut windows from a motion or transition manifest.

    A jump inside a declared transition is expected; a jump at a declared hard
    cut is expected too. Everything else is still a temporal defect.
    """
    if transition_manifest is None:
        return []
    if isinstance(transition_manifest, (str, Path)):
        path = Path(transition_manifest)
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = transition_manifest
    if isinstance(data, list):
        windows = []
        for item in data:
            if isinstance(item, dict) and "start" in item:
                windows.append((float(item["start"]), float(item.get("end", item["start"]))))
        return windows
    if not isinstance(data, dict):
        return []
    shots = data.get("shots") or []
    if shots:
        durations = [float(shot.get("duration_seconds") or 0.0) for shot in shots]
        transitions = (data.get("sequence") or {}).get("transitions") or []
        by_before = {int(item.get("before_index")): item for item in transitions
                     if item.get("before_index") is not None}
        windows = []
        cumulative = 0.0
        for index, duration in enumerate(durations):
            if index > 0:
                item = by_before.get(index)
                length = float(((item or {}).get("spec") or {}).get("duration_s") or 0.0)
                if length > 0:
                    windows.append((cumulative, cumulative + length))
                else:
                    windows.append((max(0.0, cumulative - 0.05), cumulative + 0.05))
            cumulative = round(cumulative + duration, 3)
        return windows
    return []


def check_temporal_continuity(
    sequence_video_path: Path | str,
    *,
    fade_out_seconds: float = 0.0,
    fps: int = 24,
    transition_manifest: dict[str, Any] | Path | str | None = None,
) -> dict[str, Any]:
    """Detect brightness jumps, unexpected tail darkening and strobing.

    ``fade_out_seconds`` excludes a deliberate master fade from the tail check;
    sequence clips should leave it at 0 so a clamp fade is caught.
    """
    video = Path(sequence_video_path)
    if not video.is_file():
        return {"status": FAIL, "code": "TEMPORAL_MISSING", "error": f"missing video: {video}"}
    frames = _decode_gray_frames(video)
    if len(frames) < 4:
        return {"status": FAIL, "code": "TEMPORAL_TOO_SHORT",
                "error": "fewer than 4 decoded frames"}
    luma = [ImageStat.Stat(frame).mean[0] for frame in frames]
    diffs = [abs(b - a) for a, b in zip(luma, luma[1:])]
    baseline = median(diffs) if diffs else 0.0
    jumps = []
    for index, value in enumerate(diffs):
        local = diffs[max(0, index - 2):index + 3]
        if value >= TEMPORAL_THRESHOLDS["frame_jump_luma"] and \
                value > max(TEMPORAL_THRESHOLDS["frame_jump_ratio"] * max(baseline, 0.05), 5.0) and \
                value >= max(local):
            jumps.append({"frame": index + 1, "seconds": round((index + 1) / fps, 3),
                          "delta": round(value, 3)})

    fade_frames = min(len(luma) - 2, int(round(fade_out_seconds * fps)))
    analysis = luma[:len(luma) - fade_frames] if fade_frames > 0 else luma
    tail_fraction = TEMPORAL_THRESHOLDS["tail_fraction"]
    tail_start = int(len(analysis) * (1 - tail_fraction))
    tail = analysis[tail_start:]
    before = analysis[max(0, tail_start - len(tail)):tail_start]
    tail_result = None
    if tail and before:
        slope = _linear_slope(tail, fps)
        drop = sum(before) / len(before) - sum(tail) / len(tail)
        monotonic = sum(1 for a, b in zip(tail, tail[1:]) if b < a) / max(1, len(tail) - 1)
        tail_result = {
            "fade_out_seconds_excluded": round(fade_frames / fps, 3),
            "mean_before": round(sum(before) / len(before), 3),
            "mean_tail": round(sum(tail) / len(tail), 3),
            "drop_luma": round(drop, 3),
            "slope_luma_per_s": round(slope, 3),
            "monotonic_drop_ratio": round(monotonic, 3),
        }

    # Flicker is a high-frequency residual, not a non-linear trend. Compute it
    # per stable segment; declared transitions / cuts are excluded so a
    # legitimate brightness shift between shots is not called flicker.
    windows = _transition_windows(transition_manifest)
    cut_frames = {0, len(luma)}
    for start, end in windows:
        cut_frames.add(max(0, min(len(luma), int(round(start * fps)))))
        cut_frames.add(max(0, min(len(luma), int(round(end * fps)))))
    boundaries = sorted(cut_frames)
    segments = [luma[a:b] for a, b in zip(boundaries, boundaries[1:]) if b - a >= 8]
    if not segments:
        segments = [luma]
    metrics = [_flicker_metrics(segment, fps) for segment in segments]
    worst = max(metrics, key=lambda item: item["residual_std"])
    flicker = {
        **worst,
        "overall_range": round(max(luma) - min(luma), 3),
        "segments": metrics,
    }
    residual_std = worst["residual_std"]
    oscillation = worst["oscillation"]

    def _known(seconds: float) -> bool:
        return any(start - 0.08 <= seconds <= end + 0.08 for start, end in windows)

    exempted = [item for item in jumps if _known(item["seconds"])]
    active_jumps = [item for item in jumps if not _known(item["seconds"])]
    tail_failed = bool(tail_result) and tail_result["drop_luma"] >= TEMPORAL_THRESHOLDS["tail_drop_luma"] and tail_result["slope_luma_per_s"] <= TEMPORAL_THRESHOLDS["tail_slope_luma_per_s"] and tail_result["monotonic_drop_ratio"] >= TEMPORAL_THRESHOLDS["tail_monotonic"]
    flicker_failed = residual_std >= TEMPORAL_THRESHOLDS["flicker_residual_std"] and oscillation >= TEMPORAL_THRESHOLDS["flicker_oscillation"] and flicker["range"] >= 2.0
    codes = []
    if tail_failed:
        codes.append("TAIL_DARKENING")
    if active_jumps:
        codes.append("TEMPORAL_FRAME_JUMP")
    if flicker_failed:
        codes.append("TEMPORAL_FLICKER")
    return {
        "status": FAIL if codes else PASS,
        "code": codes[0] if codes else "TEMPORAL_OK",
        "codes": codes,
        "video": str(video),
        "frames": len(frames),
        "thresholds": TEMPORAL_THRESHOLDS,
        "luma": {"first": round(luma[0], 3), "mid": round(luma[len(luma) // 2], 3),
                 "last": round(luma[-1], 3), "min": round(min(luma), 3),
                 "max": round(max(luma), 3)},
        "frame_jumps": active_jumps,
        "frame_jumps_all": jumps,
        "exempted_jumps": exempted,
        "known_windows": [[round(a, 3), round(b, 3)] for a, b in windows],
        "tail": tail_result,
        "flicker": flicker,
    }


def check_motion_quality(
    manifest_path: Path | str,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Run rigid protection on every shot plus temporal continuity on the sequence."""
    manifest_path = Path(manifest_path).resolve()
    root = (root or _infer_root(manifest_path)).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = []
    for shot in manifest.get("shots") or []:
        output = Path(shot.get("output") or "")
        video = output if output.is_absolute() else root / output
        shots.append(check_rigid_protection(shot, video))
    sequence = manifest.get("sequence") or None
    temporal = None
    temporal_video: Path | None = None
    if sequence and sequence.get("sequence"):
        path = Path(sequence["sequence"])
        temporal_video = path if path.is_absolute() else root / path
    elif len(manifest.get("shots") or []) == 1:
        # A single-shot plan has no sequence; check the shot clip directly so a
        # clamp fade or strobing at the tail is still gated.
        output = Path((manifest["shots"][0]).get("output") or "")
        temporal_video = output if output.is_absolute() else root / output
    if temporal_video is not None:
        temporal = check_temporal_continuity(temporal_video, transition_manifest=manifest)
    failed = any(item["status"] == FAIL for item in shots)
    failed = failed or (temporal is not None and temporal["status"] == FAIL)
    report = {
        "status": FAIL if failed else PASS,
        "code": "MOTION_QUALITY_VIOLATION" if failed else "MOTION_QUALITY_OK",
        "manifest": str(manifest_path),
        "shots": shots,
        "temporal": temporal,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out = manifest_path.parent / "motion_quality_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report"] = str(out)
    return report


def _infer_root(manifest_path: Path) -> Path:
    for parent in manifest_path.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "config").is_dir():
            return parent
    return Path.cwd()


def check_build(manifest_path: Path, *, root: Path | None = None) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    root = (root or _infer_root(manifest_path)).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = manifest.get("outputs") or {}

    def resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (root / path)

    checks: dict[str, Any] = {"manifest": str(manifest_path), "root": str(root)}
    final = resolve(outputs["final"]) if outputs.get("final") else None
    if final is None or not final.is_file():
        checks["final"] = _result(False, path=str(final), error="manifest has no existing final")
    else:
        checks["final"] = check_video(final, expected_width=1080, expected_height=1920)
        if outputs.get("final_sha256"):
            checks["final"]["sha256_ok"] = _sha256(final) == outputs["final_sha256"]

    images = []
    for segment in manifest.get("segments") or []:
        source = segment.get("source")
        if not source:
            continue
        # R3 accepts both stills and pre-rendered clips; check each by its own
        # media type instead of assuming every segment is an image.
        if segment.get("type") == "video":
            images.append(check_video(resolve(source), expected_width=1080, expected_height=1920))
        else:
            images.append(check_image(resolve(source)))
    if images:
        checks["images"] = images
    mixed = outputs.get("mixed")
    if mixed:
        # The build-level check is decode/clipping only: a mixed track may have
        # long quiet tails. Volume/pause/pronunciation gates run per line in
        # ``check_audio_manifest``.
        checks["audio"] = check_audio(resolve(mixed), detect_silence=False)

    ok = checks["final"]["status"] == PASS
    ok = ok and all(item["status"] == PASS for item in images)
    ok = ok and checks["final"].get("sha256_ok", True)
    if "audio" in checks:
        ok = ok and checks["audio"]["status"] == PASS
    checks["status"] = PASS if ok else FAIL
    checks["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report_path = manifest_path.parent / "quality_report.json"
    report_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks["report"] = str(report_path)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", help="build_manifest.json of one render")
    parser.add_argument("--audio-manifest", help="audio_manifest.json for per-line audio QA")
    parser.add_argument("--timeline", default=None, help="timeline.json for subtitle/audio alignment")
    parser.add_argument("--aesthetic-motion", default=None,
                        help="motion_manifest.json for static stability + colour/light continuity")
    parser.add_argument("--aesthetic-plan", default=None,
                        help="optional aesthetic_plan.json to check camera focus vs design")
    parser.add_argument("--motion-manifest", default=None,
                        help="motion_manifest.json: rigid protection + temporal continuity")
    parser.add_argument("--root", default=None, help="project root (default: infer)")
    args = parser.parse_args()
    selected = [
        bool(args.manifest), bool(args.audio_manifest), bool(args.aesthetic_motion),
        bool(args.motion_manifest),
    ]
    if sum(selected) != 1:
        print(json.dumps({
            "ok": False,
            "error": "pass exactly one of --manifest / --audio-manifest / "
                     "--aesthetic-motion / --motion-manifest",
        }, ensure_ascii=False))
        return 2
    try:
        if args.audio_manifest:
            result = check_audio_manifest(
                Path(args.audio_manifest),
                root=Path(args.root) if args.root else None,
                timeline_path=Path(args.timeline) if args.timeline else None,
            )
        elif args.aesthetic_motion:
            result = check_dynamic_aesthetics(
                Path(args.aesthetic_motion),
                Path(args.aesthetic_plan) if args.aesthetic_plan else None,
            )
        elif args.motion_manifest:
            result = check_motion_quality(
                Path(args.motion_manifest),
                root=Path(args.root) if args.root else None,
            )
        else:
            result = check_build(
                Path(args.manifest),
                root=Path(args.root) if args.root else None,
            )
    except (OSError, ValueError, QualityError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    ok = result.get("status") in (PASS, "PARTIAL", "OK") or result.get("risk_severity") in ("ok",)
    print(json.dumps({
        "ok": ok,
        "status": result.get("status") or result.get("risk_severity"),
        "aesthetic_status": result.get("aesthetic_status"),
        "report": result.get("report"),
    }, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
