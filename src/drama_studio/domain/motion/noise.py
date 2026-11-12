"""Deterministic value noise.

Pillow's ``Image.effect_noise`` is not seedable, so two builds with the same
recorded parameters could differ. This tiny generator is seeded by an integer
and has no dependency beyond ``math``; the result is reproducible on any machine
(floating-point sine is stable for the ranges used here).
"""

from __future__ import annotations

import math

from PIL import Image


def noise_image(size: tuple[int, int], seed: int = 0, sigma: float = 40.0) -> Image.Image:
    width, height = max(1, size[0]), max(1, size[1])
    image = Image.new("L", (width, height), 128)
    pixel = image.load()
    base = float(seed % 100000) * 37.719
    for y in range(height):
        for x in range(width):
            value = math.sin(x * 12.9898 + y * 78.233 + base) * 43758.5453
            fraction = value - math.floor(value)
            pixel[x, y] = max(0, min(255, int(round(128.0 + (fraction - 0.5) * 2.0 * sigma))))
    return image
