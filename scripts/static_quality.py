"""Static image quality gate for the two visual pipelines.

This is deliberately split in two:

* objective metrics (blank/black, whitespace, edge density, high-frequency
  ratio, saturation) are computed by the script;
* semantic defects (mechanical birds, repeated rock hatching, digital water,
  deformed boat, etc.) can only be judged by looking at the image. They are
  recorded in an optional ``--manual`` JSON, so the gate cannot silently pass
  on a model-success alone.

Usage:

    .venv\\Scripts\\python.exe scripts\\static_quality.py ^
        --image experiments/pipeline_a/static/IA4/IA4_ink_landscape_00001_.png ^
        --style ink_wash --out experiments/pipeline_a/static/IA4/static_quality.json

The manual JSON shape is::

    {"checks": {"birds": {"status": "PASS", "note": "无飞鸟"}, ...}}
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat

from drama_studio.config import find_project_root
from drama_studio.style_presets import load_style_presets

ROOT = find_project_root()

# The two pipelines keep separate checklists. This is data, not a shared
# visual rule: each style is reviewed against its own failure modes.
CHECKLISTS: dict[str, list[dict]] = {
    "ink_wash": [
        {"key": "birds", "label": "飞鸟", "issues": "排列机械 / 形态错误 / 数量不合理"},
        {"key": "rocks", "label": "山石", "issues": "皴法重复 / 纹理条纹化"},
        {"key": "trees", "label": "树木", "issues": "树冠重复 / 枝干结构不自然"},
        {"key": "water", "label": "水面", "issues": "缺少纸性 / 数字渐变明显"},
        {"key": "reflection", "label": "倒影", "issues": "透视不合理 / 镜像过于机械"},
        {"key": "clouds", "label": "云烟", "issues": "轮廓过硬 / 与山体脱节"},
        {"key": "distant", "label": "远景", "issues": "过度锐化 / 缺乏虚实变化"},
        {"key": "material", "label": "整体材质", "issues": "塑料感 / 数码感 / 纹理覆盖过重"},
        {"key": "composition", "label": "构图", "issues": "留白不足 / 主体拥挤 / 空间层次混乱"},
    ],
    "court_green_fine_line": [
        {"key": "lines", "label": "线条", "issues": "断裂 / 粗细机械 / 结构错乱"},
        {"key": "architecture", "label": "建筑", "issues": "透视错误 / 屋顶和结构变形"},
        {"key": "rocks", "label": "山石", "issues": "重复纹理 / 设色溢出"},
        {"key": "water", "label": "水纹", "issues": "机械同心圆 / 规则闭合环线 / 数字矢量感"},
        {"key": "trees", "label": "树木", "issues": "枝干逻辑错误 / 重复树冠"},
        {"key": "figures", "label": "人物", "issues": "五官、服饰、比例异常"},
        {"key": "flowers_birds", "label": "花鸟", "issues": "结构错误 / 细节混乱"},
        {"key": "color", "label": "色彩", "issues": "荧光感 / 过度饱和 / 数字渐变"},
        {"key": "material", "label": "材质", "issues": "塑料感 / 过重纹理"},
        {"key": "overall", "label": "整体", "issues": "细节堆砌 / 缺少传统画面秩序"},
    ],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metrics(path: Path) -> dict:
    with Image.open(path) as raw:
        image = raw.convert("RGB")
    width, height = image.size
    # Metrics are scale-independent; 512 px keeps the gate fast.
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
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Static quality gate for a pipeline still")
    parser.add_argument("--image", required=True)
    parser.add_argument("--style", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--manual", help="JSON with semantic check results")
    args = parser.parse_args(argv)

    path = (ROOT / args.image).resolve()
    if not path.is_file():
        raise SystemExit(f"image not found: {path}")
    preset = load_style_presets(ROOT).get(args.style)
    checklist = CHECKLISTS.get(preset.id)
    if checklist is None:
        raise SystemExit(f"no static checklist for style: {preset.id}")

    objective = metrics(path)
    blocking = objective["width"] < 512 or objective["height"] < 512
    blank = objective["stddev"] < 1.5
    black = objective["mean"] < 4.0 and objective["stddev"] < 3.0
    objective_passed = not (blocking or blank or black)

    checks = [
        {**item, "status": "PENDING", "note": ""}
        for item in checklist
    ]
    if args.manual:
        manual = json.loads((ROOT / args.manual).read_text(encoding="utf-8"))
        by_key = manual.get("checks") or {}
        for check in checks:
            entry = by_key.get(check["key"])
            if entry:
                check["status"] = str(entry.get("status", "PENDING"))
                check["note"] = str(entry.get("note", ""))

    statuses = {check["status"] for check in checks}
    if not objective_passed or "FAIL" in statuses:
        overall = "FAIL"
    elif "PENDING" in statuses:
        overall = "PENDING"
    elif "PARTIAL" in statuses:
        overall = "PARTIAL"
    else:
        overall = "PASS_STATIC"

    out = (ROOT / args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "image": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(path),
        "style_id": preset.id,
        "style_name": preset.name,
        "objective": objective,
        "objective_passed": objective_passed,
        "blank": blank,
        "black": black,
        "manual_checks": checks,
        "overall_status": overall,
        "note": "PASS_STATIC 只表示静态图过门；动态效果与最终审美仍需人工看片",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"image": payload["image"], "objective_passed": objective_passed,
                      "overall": overall, "checks": {c["key"]: c["status"] for c in checks}},
                     ensure_ascii=False))
    return 0 if overall in ("PASS_STATIC", "PARTIAL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
