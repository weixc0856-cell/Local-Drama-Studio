"""Objective image measurements (colour, edges, luma).

Pure measurement: the caller supplies a path, the module returns numbers and
never decides whether an image is acceptable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat


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
