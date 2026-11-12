"""Deterministic paper/silk texture.

Moved out of ``scripts/s2_build.py`` so production motion rendering and the S2
validation clips share one implementation. The texture is a neutral 128-grey
image blended with ``overlay`` at low opacity; it never carries colour.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from drama_studio.domain.motion.noise import noise_image

from drama_studio.domain.motion.spec import H, W


def make_texture(kind: str, path: Path, seed: int = 7, size: tuple[int, int] = (W, H)) -> dict:
    width, height = size
    rng = random.Random(seed)
    base = Image.new("L", (width, height), 128)
    if kind == "silk":
        low = noise_image((width // 8, height // 8), seed, 24).resize((width, height), Image.BICUBIC)
        base = Image.blend(base, low, 0.35)
        draw = ImageDraw.Draw(base)
        for y in range(0, height, 3):
            draw.line([(0, y), (width, y)], fill=128 + rng.choice((-8, -6, -4, 4, 6, 8)), width=1)
        for x in range(0, width, 3):
            draw.line([(x, 0), (x, height)], fill=128 + rng.choice((-8, -6, -4, 4, 6, 8)), width=1)
        base = base.filter(ImageFilter.GaussianBlur(0.6))
        base = Image.blend(base, noise_image((width // 4, height // 4), seed + 1, 28).resize((width, height), Image.BICUBIC), 0.30)
    elif kind == "raw_paper":
        blotch = noise_image((width // 16, height // 16), seed + 2, 40).resize((width, height), Image.BICUBIC)
        blotch = blotch.filter(ImageFilter.GaussianBlur(6))
        base = Image.blend(base, blotch, 0.40)
        draw = ImageDraw.Draw(base)
        for _ in range(900):
            x0, y0 = rng.randrange(width), rng.randrange(height)
            length = rng.randint(4, 18)
            angle = rng.uniform(-0.5, 0.5)
            x1 = x0 + length * math.cos(angle)
            y1 = y0 + length * math.sin(angle)
            draw.line([(x0, y0), (x1, y1)], fill=128 + rng.choice((-10, -8, -6, 6, 8, 10)), width=1)
        base = base.filter(ImageFilter.GaussianBlur(0.4))
        base = Image.blend(base, noise_image((width // 4, height // 4), seed + 3, 26).resize((width, height), Image.BICUBIC), 0.30)
    else:
        raise ValueError(f"unknown texture kind: {kind}")
    path.parent.mkdir(parents=True, exist_ok=True)
    # RGB (not L): blending a grey texture into an RGB frame makes FFmpeg
    # negotiate a grey intermediate and silently drop all colour.
    base.convert("RGB").save(path)
    return {"path": str(path), "kind": kind, "size": [width, height], "seed": seed}
