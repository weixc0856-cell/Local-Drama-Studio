"""Independent acceptance report for one film build.

This is a read-only evidence collector, not a renderer. It prints the numbers a
human needs before watching: media streams, black/freeze intervals, subtitle and
narration starts, dissolve cut points, per-shot pacing, Wan chain seams and the
audio mix. It never upgrades a technical PASS into a content PASS.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(path: Path) -> dict[str, Any]:
    proc = run(["ffprobe", "-v", "error", "-show_entries",
                "stream=index,codec_type,codec_name,width,height,r_frame_rate,duration:"
                "format=duration,size", "-of", "json", str(path)])
    return json.loads(proc.stdout or "{}")


def black_intervals(path: Path) -> list[dict[str, float]]:
    proc = run(["ffmpeg", "-hide_banner", "-v", "info", "-i", str(path),
                "-vf", "blackdetect=d=0.08:pix_th=0.10", "-an", "-f", "null", "-"])
    intervals = []
    for line in proc.stderr.splitlines():
        if "black_start" not in line:
            continue
        values = dict(re.findall(r"(black_start|black_end|black_duration):([0-9.]+)", line))
        intervals.append({key: float(value) for key, value in values.items()})
    return intervals


def freeze_intervals(path: Path, duration: float = 1.0) -> list[dict[str, float]]:
    proc = run(["ffmpeg", "-hide_banner", "-v", "info", "-i", str(path),
                "-vf", f"freezedetect=n=0.003:d={duration}", "-an", "-f", "null", "-"])
    intervals = []
    for line in proc.stderr.splitlines():
        if "freeze_start" not in line and "freeze_end" not in line:
            continue
        values = dict(re.findall(r"(freeze_start|freeze_end|freeze_duration):([0-9.]+)", line))
        if "freeze_start" in values:
            intervals.append({key: float(value) for key, value in values.items()})
    return intervals


def srt_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    events = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        start, end = [item.strip() for item in lines[1].split("-->")]
        events.append({"start": start, "end": end, "text": " ".join(lines[2:]).strip()})
    return events


def _markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    lines = [
        f"# 成片验收报告 · {report['project']}",
        "",
        f"- 构建：`{report['build']}`",
        f"- 成片：`{report['final']}`",
        f"- 时长：{report['media']['duration']} s；"
        f"{report['media']['video'].get('width')}×{report['media']['video'].get('height')}；"
        f"{report['media']['video'].get('r_frame_rate')} fps",
        f"- 技术状态：**{report['technical_status']}**（人工结论仍为 PENDING）",
        "",
        "## 自动检查",
        "",
        "| 检查 | 结果 |",
        "|---|---|",
    ]
    for key, value in checks.items():
        lines.append(f"| {key} | {'PASS' if value else 'REVIEW'} |")
    lines += ["", "## 旁白 / 字幕起点（ms）", ""]
    lines.append(f"- 时间轴：`{report['narration']['expected_starts_ms']}`")
    lines.append(f"- 字幕：`{report['narration']['subtitle_starts_ms']}`")
    lines += ["", "## 叠化切点", ""]
    for item in report["dissolve_cuts"]:
        lines.append(f"- {item['shot_id']} @ {item['start_ms']} ms")
    lines += ["", "## 逐镜节奏", "", "| 镜头 | 时长 ms | 旁白 ms | 尾静默 ms | 转场 |", "|---|---|---|---|---|"]
    for item in report["pacing"]:
        lines.append(f"| {item['shot_id']} | {item['duration_ms']} | {item['narration_ms']} | "
                     f"{item['tail_silence_ms']} | {item['transition_in']} |")
    lines += ["", "## Wan 续接与尾帧 QC", ""]
    chain = report.get("chain") or {}
    if chain.get("segments"):
        lines.append(f"- 段数 {chain['segments']}；总帧 {chain['frames']}；截掉污染帧 {chain['truncated_frames']}")
        for seam in chain.get("seams", []):
            lines.append(f"- 段 {seam['segment']} 接缝亮度差 {seam['luma_diff']} → {seam['status']}")
        for qc in chain.get("segment_qc", []):
            if qc.get("qc"):
                lines.append(f"- 段 {qc['segment']} 尾帧截断：{qc['qc']}")
    else:
        lines.append("- 暂无 chain_manifest（S01 未使用 Wan 续接或不在本项目）")
    lines += [
        "",
        "## 人工验收清单（必须在 1080×1920 实际尺寸播放）",
        "",
        f"- [ ] {chain.get('segments') or 0} 段 Wan 接缝处无跳变、无重复帧、无突然加速/减速",
        "- [ ] 无黑帧、环形伪影、金属/结构幻觉",
        "- [ ] 旁白与画面节奏匹配；无一句被切断或赶拍",
        "- [ ] 字幕起点与旁白起点一致；无错字、无英文残留",
        "- [ ] 叠化切点自然；没有 PPT 式硬切感",
        "- [ ] 环境声连续，不抢旁白；无爆音、无突然静音",
        "- [ ] 人物/建筑结构稳定；无面部、衣纹、屋顶形变",
        "- [ ] 整段播放时纹理不闪烁、边缘不跳动",
        "- [ ] 最终画面像一段连续动画，而不是图片切换",
        "",
        "人工结论：`PENDING`  ",
        "审片人：__________  日期：__________  备注：__________",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--build", required=True, help="renders/build-<time>")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    project = ROOT / "projects" / args.project
    build = (ROOT / args.build).resolve() if not Path(args.build).is_absolute() else Path(args.build)
    manifest_path = build / "build_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"missing {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    final = ROOT / manifest["outputs"]["final"]
    quality = json.loads((build / "quality_report.json").read_text(encoding="utf-8"))
    timeline = json.loads((build / "film_timeline.json").read_text(encoding="utf-8"))
    chain_path = project / "shots" / "S01" / "chain_manifest.json"
    chain = json.loads(chain_path.read_text(encoding="utf-8")) if chain_path.is_file() else None
    audio_manifest = json.loads((project / "assets" / "audio" / "audio_manifest.json").read_text(encoding="utf-8"))

    media = probe(final)
    streams = media.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    subtitles = next((s for s in streams if s.get("codec_type") == "subtitle"), {})

    srt = srt_events(build / "drama.srt")
    events = timeline.get("narration_events") or []
    starts_expected = [event["start_ms"] for event in events]
    starts_srt = []
    for event in srt:
        hour, minute, rest = event["start"].split(":")
        second, millis = rest.split(",")
        starts_srt.append(int(hour) * 3600000 + int(minute) * 60000 + int(second) * 1000 + int(millis))

    dissolves = [
        {"shot_id": entry["shot_id"], "start_ms": entry["start_ms"]}
        for entry in timeline["entries"] if entry.get("transition_in") == "dissolve"
    ]

    line_by_id = {line["id"]: line for line in audio_manifest.get("lines", [])}
    pacing = []
    for entry in timeline["entries"]:
        duration = entry["end_ms"] - entry["start_ms"]
        narration_ms = sum(round(line_by_id[item]["duration_seconds"] * 1000)
                           for item in entry["narration_ids"] if item in line_by_id)
        pacing.append({
            "shot_id": entry["shot_id"],
            "duration_ms": duration,
            "narration_ms": narration_ms,
            "tail_silence_ms": duration - narration_ms,
            "transition_in": entry.get("transition_in"),
        })

    blacks = black_intervals(final)
    unexpected_blacks = [
        item for item in blacks
        if not (item.get("black_start", 1) <= 0.05 and item.get("black_duration", 1) <= 0.6)
    ]
    checks = {
        "video_1080x1920": (video.get("width"), video.get("height")) == (1080, 1920),
        "fps_24": video.get("r_frame_rate") == "24/1",
        "audio_stream": bool(audio),
        "subtitle_stream": bool(subtitles),
        "subtitle_starts_match": starts_srt == starts_expected,
        "black_frames": len(unexpected_blacks) == 0,
        "no_freeze_over_1s": len(freeze_intervals(final)) == 0,
        "quality_check": quality.get("status") == "PASS",
        "wan_seams": (
            all(item.get("seam_status") == "PASS" for item in chain["segments"])
            if chain else True
        ),
    }

    report = {
        "project": args.project,
        "build": str(build.relative_to(ROOT)).replace("\\", "/"),
        "final": str(final.relative_to(ROOT)).replace("\\", "/"),
        "media": {
            "duration": (media.get("format") or {}).get("duration"),
            "video": {k: video.get(k) for k in ("codec_name", "width", "height", "r_frame_rate", "duration")},
            "audio": {k: audio.get(k) for k in ("codec_name", "duration")},
            "subtitle": {k: subtitles.get(k) for k in ("codec_name", "duration")},
            "size_bytes": (media.get("format") or {}).get("size"),
        },
        "audio_quality": quality.get("audio"),
        "narration": {
            "lines": len(audio_manifest.get("lines", [])),
            "expected_starts_ms": starts_expected,
            "subtitle_starts_ms": starts_srt,
            "events": events,
        },
        "dissolve_cuts": dissolves,
        "pacing": pacing,
        "black_intervals": blacks,
        "unexpected_black_intervals": unexpected_blacks,
        "freeze_intervals": freeze_intervals(final),
        "chain": {
            "segments": len(chain["segments"]) if chain else None,
            "frames": chain.get("frames") if chain else None,
            "truncated_frames": chain.get("truncated_frames") if chain else None,
            "seams": [{"segment": item["segment"], "luma_diff": item.get("seam_luma_diff"),
                       "status": item.get("seam_status")} for item in chain["segments"]] if chain else [],
            "segment_qc": [{"segment": item["segment"], "qc": item.get("qc")} for item in chain["segments"]] if chain else [],
        },
        "checks": checks,
        "technical_status": "PASS" if all(checks.values()) else "REVIEW",
        "human_review": "PENDING",
        "note": "自动指标只做筛查；成片是否成立必须人工在 1080x1920 实际尺寸看片。",
    }
    out = Path(args.out) if args.out else build / "acceptance_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = out.with_suffix(".md")
    markdown.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"report": str(out), "technical_status": report["technical_status"],
                      "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if report["technical_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
