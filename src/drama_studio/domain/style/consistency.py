"""Objective style consistency checks (VISUAL_STYLE_ENGINE §7)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat

from drama_studio.quality import image_metrics
from drama_studio.domain.style.schemas import StylePack

SAT_TOLERANCE = 0.06
EDGE_TOLERANCE = 0.03
PALETTE_DISTANCE_WARN = 45.0
LUMA_DRIFT_WARN = 12.0
SAT_DRIFT_WARN = 0.08


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    code: str
    message: str


def hex_to_lab(value: str) -> tuple[float, float, float]:
    rgb = tuple(int(value.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    pixel = Image.new("RGB", (1, 1), rgb).convert("LAB").getpixel((0, 0))
    return (pixel[0] * 100.0 / 255.0, pixel[1] - 128.0, pixel[2] - 128.0)


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _letterboxed(path: Path) -> bool:
    with Image.open(path) as raw:
        gray = raw.convert("L")
    width, height = gray.size
    band = max(1, height // 20)
    top = ImageStat.Stat(gray.crop((0, 0, width, band))).mean[0]
    bottom = ImageStat.Stat(gray.crop((0, height - band, width, height))).mean[0]
    return min(top, bottom) < 8


def check_image(path: Path, pack: StylePack) -> list[Issue]:
    issues: list[Issue] = []
    metrics = image_metrics(path)
    sat = metrics["saturation_mean"]
    sat_lo, sat_hi = pack.color.saturation_range
    if not (sat_lo - SAT_TOLERANCE <= sat <= sat_hi + SAT_TOLERANCE):
        issues.append(Issue("warning", "saturation_out_of_range",
                            f"{path.name}: saturation {sat:.3f} outside {sat_lo}-{sat_hi}"))
    edge = metrics["edge_density"]
    edge_lo, edge_hi = pack.color.edge_density_range
    if not (edge_lo - EDGE_TOLERANCE <= edge <= edge_hi + EDGE_TOLERANCE):
        issues.append(Issue("warning", "edge_density_out_of_range",
                            f"{path.name}: edge density {edge:.3f} outside {edge_lo}-{edge_hi}"))
    if _letterboxed(path):
        issues.append(Issue("error", "letterbox", f"{path.name}: black bars detected"))
    anchors = [hex_to_lab(anchor.hex) for anchor in pack.color.anchors]
    if anchors:
        mean_lab = tuple(metrics["lab_mean"])
        nearest = min(_distance(mean_lab, anchor) for anchor in anchors)
        if nearest > PALETTE_DISTANCE_WARN:
            issues.append(Issue("warning", "palette_far_from_anchors",
                                f"{path.name}: mean LAB is {nearest:.1f} from the nearest anchor"))
    return issues


def check_sequence(paths: list[Path], pack: StylePack) -> list[Issue]:
    issues: list[Issue] = []
    previous = None
    for path in paths:
        metrics = image_metrics(path)
        current = (metrics["lab_mean"][0], metrics["saturation_mean"])
        if previous is not None:
            luma_delta = abs(current[0] - previous[0])
            sat_delta = abs(current[1] - previous[1])
            if luma_delta > LUMA_DRIFT_WARN:
                issues.append(Issue("warning", "luma_drift",
                                    f"{path.name}: luma jumps {luma_delta:.1f} from the previous shot"))
            if sat_delta > SAT_DRIFT_WARN:
                issues.append(Issue("warning", "saturation_drift",
                                    f"{path.name}: saturation jumps {sat_delta:.3f} from the previous shot"))
        previous = current
    return issues
