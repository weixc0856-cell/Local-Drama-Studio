"""Cross-shot style consistency gate.

This is a *technical* consistency check, not a claim that every frame looks like
the same artwork. It measures three things across all completed stills:

* palette adherence to the style preset's ``color_palette``;
* pairwise mean-colour distance (CIELAB) between shots;
* luma / saturation / edge-density spread.

A technical ``OK`` is still only ``PARTIAL`` until a human records an aesthetic
review. A technical ``RISK`` is ``FAIL``. The report never writes
``PASS_VERIFIED`` from automated metrics alone.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image

from drama_studio.application.quality import _hex_rgb, _lab_distance, _rgb_lab, image_metrics
from drama_studio.domain.style.presets import StylePreset, load_style_presets


class StyleConsistencyError(RuntimeError):
    pass


def _palette_stats(path: Path, palette: dict[str, str]) -> dict[str, Any]:
    colors = [_rgb_lab(_hex_rgb(value)) for value in palette.values()]
    with Image.open(path) as raw:
        image = raw.convert("RGB")
        image.thumbnail((256, 256))
        lab = image.convert("LAB")
        lab_pixels = list((getattr(lab, "get_flattened_data", None) or lab.getdata)())
    nearest: list[float] = []
    hits = 0
    for pixel in lab_pixels[:: max(1, len(lab_pixels) // 8000)]:
        lab = (pixel[0] * 100.0 / 255.0, pixel[1] - 128.0, pixel[2] - 128.0)
        distance = min(_lab_distance(lab, color) for color in colors)
        nearest.append(distance)
        if distance <= 20.0:
            hits += 1
    total = len(nearest) or 1
    return {
        "palette_colors": len(colors),
        "mean_palette_distance": round(sum(nearest) / total, 2),
        "max_palette_distance": round(max(nearest), 2),
        "palette_coverage": round(hits / total, 4),
    }


def _shot_record(shot_id: str, path: Path, preset: StylePreset) -> dict[str, Any]:
    metrics = image_metrics(path)
    palette = _palette_stats(path, preset.color_palette)
    return {
        "shot_id": shot_id,
        "path": str(path),
        "lab_mean": metrics["lab_mean"],
        "luma": metrics["mean"],
        "saturation": metrics["saturation_mean"],
        "edge_density": metrics["edge_density"],
        "high_frequency_ratio": metrics["high_frequency_ratio"],
        **palette,
    }


def check_style_consistency(
    shots: list[tuple[str, Path]],
    *,
    style_id: str,
    root: Path | None = None,
    max_pair_delta_e: float = 18.0,
    max_palette_distance: float = 25.0,
    max_luma_range: float = 45.0,
    max_saturation_range: float = 0.35,
    max_edge_range: float = 0.12,
    review_status: str = "PENDING_HUMAN_REVIEW",
    review_note: str = "",
) -> dict[str, Any]:
    if len(shots) < 2:
        raise StyleConsistencyError("style consistency needs at least two shots")
    preset = load_style_presets(root).get(style_id)
    records = []
    for shot_id, path in shots:
        path = Path(path)
        if not path.is_file():
            raise StyleConsistencyError(f"{shot_id}: image not found: {path}")
        records.append(_shot_record(shot_id, path, preset))

    pairs = []
    for index, left in enumerate(records):
        for right in records[index + 1:]:
            pairs.append({
                "from": left["shot_id"],
                "to": right["shot_id"],
                "delta_e": _lab_distance(tuple(left["lab_mean"]), tuple(right["lab_mean"])),
            })
    max_pair = max(pairs, key=lambda item: item["delta_e"]) if pairs else None
    luma_values = [record["luma"] for record in records]
    saturation_values = [record["saturation"] for record in records]
    edge_values = [record["edge_density"] for record in records]
    flags: list[dict[str, Any]] = []
    if max_pair and max_pair["delta_e"] > max_pair_delta_e:
        flags.append({
            "code": "cross_shot_color",
            "detail": f"{max_pair['from']} ↔ {max_pair['to']} ΔE={max_pair['delta_e']} > {max_pair_delta_e}",
        })
    palette_worst = max(records, key=lambda item: item["mean_palette_distance"])
    if palette_worst["mean_palette_distance"] > max_palette_distance:
        flags.append({
            "code": "palette_distance",
            "detail": f"{palette_worst['shot_id']} mean palette ΔE={palette_worst['mean_palette_distance']} > {max_palette_distance}",
        })
    luma_range = round(max(luma_values) - min(luma_values), 2)
    if luma_range > max_luma_range:
        flags.append({"code": "luma_spread", "detail": f"luma range {luma_range} > {max_luma_range}"})
    saturation_range = round(max(saturation_values) - min(saturation_values), 4)
    if saturation_range > max_saturation_range:
        flags.append({
            "code": "saturation_spread",
            "detail": f"saturation range {saturation_range} > {max_saturation_range}",
        })
    edge_range = round(max(edge_values) - min(edge_values), 4)
    if edge_range > max_edge_range:
        flags.append({"code": "edge_spread", "detail": f"edge-density range {edge_range} > {max_edge_range}"})

    technical = "RISK" if flags else "OK"
    review = str(review_status or "PENDING_HUMAN_REVIEW").upper()
    if review not in ("PENDING_HUMAN_REVIEW", "APPROVED", "REJECTED"):
        raise StyleConsistencyError(
            f"review_status must be PENDING_HUMAN_REVIEW/APPROVED/REJECTED, got {review_status!r}")
    if technical == "RISK" or review == "REJECTED":
        overall = "FAIL"
    elif review == "APPROVED":
        overall = "PASS_VERIFIED"
    else:
        overall = "PARTIAL"

    return {
        "schema_version": "1.0",
        "style_id": preset.id,
        "style_name": preset.name,
        "shot_count": len(records),
        "shots": records,
        "pairs": pairs,
        "max_pair": max_pair,
        "spread": {
            "luma": luma_range,
            "saturation": saturation_range,
            "edge_density": edge_range,
        },
        "thresholds": {
            "max_pair_delta_e": max_pair_delta_e,
            "max_palette_distance": max_palette_distance,
            "max_luma_range": max_luma_range,
            "max_saturation_range": max_saturation_range,
            "max_edge_range": max_edge_range,
        },
        "flags": flags,
        "technical_status": technical,
        "aesthetic_status": review,
        "review_note": review_note,
        "overall_status": overall,
        "note": (
            "自动指标只检查跨镜头色彩/亮度/饱和度/边缘密度稳定性；"
            "风格语义、构图与“像不像同一套画”仍需人工审片。"
        ),
    }


def _parse_shot(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--shot must be SHOT_ID=PATH")
    shot_id, path = value.split("=", 1)
    if not shot_id.strip() or not path.strip():
        raise argparse.ArgumentTypeError("--shot must be SHOT_ID=PATH")
    return shot_id.strip(), Path(path.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-shot style consistency gate")
    parser.add_argument("--style", required=True)
    parser.add_argument("--shot", action="append", required=True, type=_parse_shot,
                        help="SHOT_ID=PATH; repeat for each shot")
    parser.add_argument("--review", default=None, help="human review JSON (aesthetic_status/note)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)

    review_status = "PENDING_HUMAN_REVIEW"
    review_note = ""
    if args.review:
        review_path = Path(args.review)
        if not review_path.is_file():
            print(json.dumps({"ok": False, "error": f"review not found: {review_path}"}, ensure_ascii=False))
            return 1
        data = json.loads(review_path.read_text(encoding="utf-8"))
        review_status = str(data.get("aesthetic_status") or review_status)
        review_note = str(data.get("note") or "")
    try:
        report = check_style_consistency(
            args.shot,
            style_id=args.style,
            root=Path(args.root) if args.root else None,
            review_status=review_status,
            review_note=review_note,
        )
    except (StyleConsistencyError, KeyError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": report["overall_status"] != "FAIL",
        "style_id": report["style_id"],
        "technical_status": report["technical_status"],
        "aesthetic_status": report["aesthetic_status"],
        "overall_status": report["overall_status"],
        "flags": len(report["flags"]),
        "out": str(out),
    }, ensure_ascii=False))
    return 0 if report["overall_status"] != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
