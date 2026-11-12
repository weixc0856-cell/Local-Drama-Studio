"""Detect and drop polluted tails in Wan frame runs.

Wan 2.2 5B can hold a clean shot for a while and then hallucinate a large
structure (a dark ring, a feather-like blob) in the last frames. Feeding that
frame into the next chained segment propagates the artifact. This module keeps
the longest clean prefix and records where and why it stopped.

The detector is deliberately simple and explainable: a sudden increase in dark
pixels, a large drop in mean luminance, or a jump in edge density relative to
the first frames. It is a screen, not an aesthetic judgement.
"""

from __future__ import annotations

import statistics
from pathlib import Path

from PIL import Image
from typing import Any

from ..quality import image_metrics

MIN_FRAMES = 4
BLACK_ABS = 0.008
BLACK_DELTA = 0.006
LUMA_DROP = 2.5
LUMA_DRIFT = 8.0
EDGE_RATIO = 1.25
BAND_FRAC = 0.12
BAND_ABS = 0.003
BAND_DELTA = 0.002
BRIGHT_ABS = 0.002
BRIGHT_DELTA = 0.001


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _band_dark(path: Path, frac: float = BAND_FRAC) -> tuple[float, float]:
    """Dark-pixel fraction in the top and bottom bands.

    Wan artifacts often enter from a frame edge before the global black fraction
    moves. A 0.7% top band is invisible to a whole-frame threshold but visible
    once the clip is enlarged to 1080x1920.
    """
    with Image.open(path) as raw:
        image = raw.convert("L")
        width, height = image.size
        band = max(1, int(height * frac))
        result = []
        for box in ((0, 0, width, band), (0, height - band, width, height)):
            crop = image.crop(box)
            histogram = crop.histogram()
            total = sum(histogram) or 1
            result.append(sum(histogram[:48]) / total)
        return result[0], result[1]


def _bright_fraction(path: Path) -> float:
    with Image.open(path) as raw:
        histogram = raw.convert("L").histogram()
        total = sum(histogram) or 1
        return sum(histogram[245:]) / total


def select_clean_prefix(frames: list[Path]) -> tuple[list[Path], dict[str, Any] | None]:
    if len(frames) <= MIN_FRAMES:
        return frames, None
    metrics = [image_metrics(frame) for frame in frames]
    bands = [_band_dark(frame) for frame in frames]
    bright = [_bright_fraction(frame) for frame in frames]
    baseline = metrics[: min(10, len(metrics))]
    base_black = _median([m["black_fraction"] for m in baseline])
    base_luma = _median([m["lab_mean"][0] for m in baseline])
    base_edge = _median([m["edge_density"] for m in baseline])
    base_top = _median([band[0] for band in bands[: min(10, len(bands))]])
    base_bottom = _median([band[1] for band in bands[: min(10, len(bands))]])
    base_bright = _median(bright[: min(10, len(bright))])
    for index, metric in enumerate(metrics):
        if index < MIN_FRAMES:
            continue
        black = metric["black_fraction"]
        luma = metric["lab_mean"][0]
        edge = metric["edge_density"]
        reasons = []
        if black > max(BLACK_ABS, base_black + BLACK_DELTA):
            reasons.append(f"black_fraction {black:.3f} > {max(BLACK_ABS, base_black + BLACK_DELTA):.3f}")
        if base_luma - luma > LUMA_DROP:
            reasons.append(f"luma drop {base_luma - luma:.2f}")
        if abs(luma - base_luma) > LUMA_DRIFT:
            reasons.append(f"luma drift {luma - base_luma:+.2f}")
        if base_edge and edge > base_edge * EDGE_RATIO:
            reasons.append(f"edge density {edge:.3f} > {base_edge * EDGE_RATIO:.3f}")
        top, bottom = bands[index]
        top_limit = max(BAND_ABS, base_top + max(BAND_DELTA, base_top * 0.20))
        bottom_limit = max(BAND_ABS, base_bottom + max(BAND_DELTA, base_bottom * 0.20))
        if top > top_limit:
            reasons.append(f"top band dark {top:.3f} > {top_limit:.3f}")
        if bottom > bottom_limit:
            reasons.append(f"bottom band dark {bottom:.3f} > {bottom_limit:.3f}")
        bright_limit = max(BRIGHT_ABS, base_bright + BRIGHT_DELTA)
        if bright[index] > bright_limit:
            reasons.append(f"bright blob {bright[index]:.4f} > {bright_limit:.4f}")
        if reasons:
            return frames[:index], {
                "cut_index": index,
                "raw_frames": len(frames),
                "clean_frames": index,
                "reason": "; ".join(reasons),
                "band_top": round(bands[index][0], 4),
                "band_bottom": round(bands[index][1], 4),
            }
    return frames, None
