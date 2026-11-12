"""Compare A/B aesthetic variants for each shot and write a human-review packet.

The comparison is deliberately a *metric hint*, not an aesthetic verdict. It
builds a contact sheet, reports risk indicators per variant, and leaves the
decision at ``PENDING_HUMAN_REVIEW``.

Example::

    .venv\\Scripts\\python.exe scripts\\aesthetic_compare.py ^
        --plan experiments/aesthetic/ink/work/aesthetic/aesthetic_plan.json ^
        --images experiments/aesthetic/ink/work/aesthetic/snapshots/snapshot-.../images ^
        --out experiments/aesthetic/ink/work/aesthetic/compare
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from drama_studio.domain.aesthetics import design_for_quality, load_plan
from drama_studio.config import find_project_root
from drama_studio.application.quality import check_aesthetic_risk, check_image
from drama_studio.domain.style.presets import load_style_presets

ROOT = find_project_root()
THUMB = (360, 640)
LABEL_H = 34


def _font(size: int = 20) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        ROOT / "assets" / "fonts" / "source-han-sans-cn" / "SourceHanSansCN-Regular.otf",
        ROOT / "assets" / "fonts" / "source-han-sans-cn" / "SourceHanSansCN-Medium.otf",
    ]
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    return ImageFont.load_default()


def _newest(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    files = sorted(
        (p for p in directory.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}),
        key=lambda p: p.stat().st_mtime,
    )
    return files[-1] if files else None


def _thumb(path: Path) -> Image.Image:
    with Image.open(path) as raw:
        image = raw.convert("RGB")
    image.thumbnail(THUMB, Image.LANCZOS)
    canvas = Image.new("RGB", THUMB, (24, 24, 24))
    canvas.paste(image, ((THUMB[0] - image.width) // 2, (THUMB[1] - image.height) // 2))
    return canvas


def _sheet(rows: list[tuple[str, Path, Path]], out: Path) -> None:
    font = _font()
    width = THUMB[0] * 2 + 12
    height = (THUMB[1] + LABEL_H) * len(rows) + 8 * (len(rows) - 1)
    sheet = Image.new("RGB", (width, height), (16, 16, 16))
    draw = ImageDraw.Draw(sheet)
    for index, (label, left, right) in enumerate(rows):
        top = index * (THUMB[1] + LABEL_H + 8)
        draw.text((6, top + 4), f"{label}  A", fill=(235, 235, 235), font=font)
        draw.text((THUMB[0] + 18, top + 4), "B", fill=(235, 235, 235), font=font)
        sheet.paste(_thumb(left), (0, top + LABEL_H))
        sheet.paste(_thumb(right), (THUMB[0] + 12, top + LABEL_H))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


CONTRAST_TARGET = {"low": 30, "medium": 60, "high": 90}


def _hint(risk_a: dict, risk_b: dict, design_a: dict, design_b: dict) -> dict:
    """Which variant is closer to its *own* design on each measurable axis."""
    def lower(value):
        return value if value is not None else 999

    scores = {
        "placement": (risk_a["composition"]["placement_error"], risk_b["composition"]["placement_error"]),
        "focus": (risk_a["composition"]["focus_ratio"], risk_b["composition"]["focus_ratio"]),
        "palette": (risk_a["color"]["dominant_distance"], risk_b["color"]["dominant_distance"]),
        "contrast": (
            abs(risk_a["lighting"]["contrast_p5_p95"]
                - CONTRAST_TARGET[design_a["lighting"]["contrast"]]),
            abs(risk_b["lighting"]["contrast_p5_p95"]
                - CONTRAST_TARGET[design_b["lighting"]["contrast"]]),
        ),
    }
    result = {}
    for key, (a, b) in scores.items():
        if key == "focus":
            result[key] = "A" if a > b else "B"
        else:
            result[key] = "A" if lower(a) < lower(b) else "B"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare A/B aesthetic variants")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--images", required=True, help="root with <shot_id>/<A|B>/*.png")
    parser.add_argument("--out", required=True)
    parser.add_argument("--manual", default=None, help="optional human review JSON")
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    plan_path = plan_path if plan_path.is_absolute() else ROOT / plan_path
    plan = load_plan(plan_path)
    preset = load_style_presets(ROOT).get(plan.style_id)
    images_root = Path(args.images)
    images_root = images_root if images_root.is_absolute() else ROOT / images_root
    out_dir = Path(args.out)
    out_dir = out_dir if out_dir.is_absolute() else ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    manual = {}
    if args.manual:
        path = Path(args.manual)
        path = path if path.is_absolute() else ROOT / path
        manual = json.loads(path.read_text(encoding="utf-8")).get("shots", {})

    rows = []
    shots_payload = []
    missing = []
    for shot_set in plan.shots:
        variants = {}
        risks = {}
        for variant in shot_set.variants:
            path = _newest(images_root / shot_set.shot_id / variant.variant_id)
            if path is None:
                missing.append(f"{shot_set.shot_id}/{variant.variant_id}")
                variants[variant.variant_id] = {"variant_id": variant.variant_id, "missing": True}
                continue
            design = design_for_quality(shot_set, variant.variant_id)
            risk = check_aesthetic_risk(
                path, design["design"], preset.color_palette,
                meta={"shot_id": shot_set.shot_id, "variant_id": variant.variant_id,
                      "axis": shot_set.axis},
            )
            risks[variant.variant_id] = risk
            variants[variant.variant_id] = {
                "variant_id": variant.variant_id,
                "label": variant.label,
                "rationale": variant.rationale,
                "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
                "image_check": check_image(path),
                "risk_severity": risk["risk_severity"],
                "risk_flags": risk["risk_flags"],
                "whitespace_fraction": risk["metrics"]["whitespace_fraction"],
                "composition": risk["composition"],
                "lighting": risk["lighting"],
                "color": risk["color"],
                "depth": risk["depth"],
            }
        if len(risks) == 2:
            a, b = variants["A"], variants["B"]
            deltas = {
                "placement_error": round(a["composition"]["placement_error"] - b["composition"]["placement_error"], 3),
                "whitespace_fraction": round(
                    a.get("whitespace_fraction", 0.0) - b.get("whitespace_fraction", 0.0), 4
                ),
                "focus_ratio": round(a["composition"]["focus_ratio"] - b["composition"]["focus_ratio"], 2),
                "contrast": round(a["lighting"]["contrast_p5_p95"] - b["lighting"]["contrast_p5_p95"], 1),
                "dominant_distance": round(
                    (a["color"]["dominant_distance"] or 0) - (b["color"]["dominant_distance"] or 0), 2
                ),
            }
            design_a = design_for_quality(shot_set, "A")["design"]
            design_b = design_for_quality(shot_set, "B")["design"]
            hint = _hint(risks["A"], risks["B"], design_a, design_b)
            left = ROOT / a["path"]
            right = ROOT / b["path"]
            rows.append((shot_set.shot_id, left, right))
        else:
            deltas = {}
            hint = {}
        human = manual.get(shot_set.shot_id) or {
            "status": "PENDING",
            "checklist": {
                key: {"status": "PENDING", "note": ""}
                for key in ("composition", "lighting", "color", "depth", "mise_en_scene", "storytelling")
            },
        }
        shots_payload.append({
            "shot_id": shot_set.shot_id,
            "axis": shot_set.axis,
            "scene_subject": shot_set.scene_subject,
            "variants": variants,
            "deltas": deltas,
            "metric_hint": hint,
            "human_review": human,
        })

    sheet = out_dir / "contact_sheet.png"
    if rows:
        _sheet(rows, sheet)

    plan_sha = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    warnings = []
    provenance = images_root.parent / "A" / "provenance.json"
    snapshot_plan_sha = None
    if provenance.is_file():
        snapshot_plan_sha = json.loads(provenance.read_text(encoding="utf-8")).get("plan_sha256")
        if snapshot_plan_sha and snapshot_plan_sha != plan_sha:
            warnings.append(
                "当前 plan 与生成 snapshot 的 plan_sha256 不一致；对照可能使用了不同版本的设计"
            )
    payload = {
        "stage": "aesthetic.compare",
        "style_id": plan.style_id,
        "plan": str(plan_path),
        "plan_sha256": plan_sha,
        "snapshot_plan_sha256": snapshot_plan_sha,
        "warnings": warnings,
        "images_root": str(images_root),
        "contact_sheet": sheet.relative_to(ROOT).as_posix() if sheet.is_relative_to(ROOT) else str(sheet),
        "shots": shots_payload,
        "missing": missing,
        "status": "PENDING_HUMAN_REVIEW" if not missing else "INCOMPLETE",
        "note": "metric_hint 只表示哪一版更接近自身设计指标；不是审美结论。人工看片后才可给出结论。",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    report = out_dir / "comparison.json"
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# A/B 美学对照（自动指标）",
        "",
        f"- 风格：`{plan.style_id}`",
        f"- 计划：`{plan_path.relative_to(ROOT).as_posix() if plan_path.is_relative_to(ROOT) else plan_path}`",
        f"- 状态：`{payload['status']}`（人工看片前不构成审美结论）",
        "",
        "| 镜头 | 变量 | A | B | 指标提示 |",
        "|---|---|---|---|---|",
    ]
    for shot in shots_payload:
        hint = ", ".join(f"{key}:{value}" for key, value in shot["metric_hint"].items()) or "—"
        lines.append(
            f"| {shot['shot_id']} | {shot['axis']} | "
            f"{shot['variants'].get('A', {}).get('label', 'missing')} | "
            f"{shot['variants'].get('B', {}).get('label', 'missing')} | {hint} |"
        )
    lines += ["", f"联系表：`{payload['contact_sheet']}`", ""]
    (out_dir / "comparison.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "ok": not missing,
        "report": report.relative_to(ROOT).as_posix() if report.is_relative_to(ROOT) else str(report),
        "contact_sheet": payload["contact_sheet"],
        "status": payload["status"],
        "missing": missing,
    }, ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
