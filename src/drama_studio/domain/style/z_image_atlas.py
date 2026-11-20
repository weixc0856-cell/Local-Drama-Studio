"""Z-Image Turbo Visual Style Atlas & 7-Dimension Prompt Engine.

Implements the official Tongyi-MAI Z-Image Turbo prompting methodology:
1. Natural language long-form descriptive paragraphs instead of comma tag spam (no 8k/masterpiece).
2. Zero Negative Prompt paradigm: 少步蒸馏 DiT (8-step forward) does not use traditional negative prompts.
   Negative constraints are encoded as positive natural descriptions (e.g., 'a clean empty background without graphic overlays').
3. Strict text preservation: Any on-screen text must be enclosed in double quotes (e.g., "COFFEE").
4. 7-Dimension Structural Architecture:
   (1) Subject (2) Scene (3) Composition (4) Lighting (5) Medium & Style (6) Color & Texture (7) Constraints.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

from drama_studio.config import find_project_root


class ZImageDimensions(BaseModel):
    subject: str = Field(..., description="Subject identity, role, attire, action")
    scene: str = Field(..., description="Spatial setting, environment, background")
    composition: str = Field(..., description="Framing, camera angle, perspective, rule-of-thirds")
    lighting: str = Field(..., description="Light source, direction, quality, shadows")
    medium_style: str = Field(..., description="Artistic medium, camera format, rendering technique")
    color_texture: str = Field(..., description="Color grading, palette, tactile surface qualities")
    constraints: str = Field(..., description="Boundary controls, clean aesthetics, positive-framed negatives")


class ZImageStyle(BaseModel):
    id: str
    code: str
    category: str
    name: str
    name_en: str
    application: str
    dimensions: ZImageDimensions
    positive_prompt: str
    postprocess: str = Field("", description="Optional delivery fix, e.g. 'grayscale'")


class ZImageStyleAtlas:
    """Registry and manager for Z-Image Turbo visual styles."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            root = find_project_root()
            config_path = root / "config" / "z_image_styles.yaml"
        self.config_path = Path(config_path)
        self._raw_data: dict = {}
        self._categories: dict[str, dict] = {}
        self._styles: dict[str, ZImageStyle] = {}
        self.reload()

    def reload(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Z-Image styles config not found at: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._raw_data = data
        self._categories = data.get("categories", {})
        raw_styles = data.get("styles", {})
        parsed: dict[str, ZImageStyle] = {}

        for sid, sdata in raw_styles.items():
            dims = sdata.get("dimensions", {})
            parsed[sid] = ZImageStyle(
                id=sdata.get("id", sid),
                code=str(sdata.get("code", "")),
                category=sdata.get("category", "A"),
                name=sdata.get("name", sid),
                name_en=sdata.get("name_en", sid),
                application=sdata.get("application", ""),
                dimensions=ZImageDimensions(
                    subject=dims.get("subject", ""),
                    scene=dims.get("scene", ""),
                    composition=dims.get("composition", ""),
                    lighting=dims.get("lighting", ""),
                    medium_style=dims.get("medium_style", ""),
                    color_texture=dims.get("color_texture", ""),
                    constraints=dims.get("constraints", ""),
                ),
                positive_prompt=sdata.get("positive_prompt", "").strip(),
                postprocess=(sdata.get("postprocess") or "").strip(),
            )
        self._styles = parsed

    def get_style(self, style_id: str) -> ZImageStyle:
        sid = style_id.lower().strip()
        if sid in self._styles:
            return self._styles[sid]
        # Allow lookup by code (e.g., '01', '12')
        for s in self._styles.values():
            if s.code == sid or s.code == sid.zfill(2):
                return s
        raise KeyError(f"Style '{style_id}' not found in Z-Image Visual Style Atlas. Available: {list(self._styles.keys())}")

    def list_styles(self, category: Optional[str] = None) -> list[ZImageStyle]:
        styles = list(self._styles.values())
        if category:
            cat = category.upper().strip()
            styles = [s for s in styles if s.category.upper() == cat]
        return sorted(styles, key=lambda x: (x.category, x.code))

    def list_categories(self) -> dict[str, dict]:
        return self._categories

    def count(self) -> int:
        return len(self._styles)


class ZImagePromptCompiler:
    """Compiles 7-dimension structured parameters into optimal Z-Image Turbo prompts."""

    # Words that degrade or conflict with Z-Image Turbo DiT natural language parsing
    BANNED_TAGS = {
        "masterpiece", "8k", "best quality", "ultra-detailed", "hyper-detailed",
        "extremely detailed", "highres", "photorealistic", "ultra realistic",
        "trending on artstation", "unreal engine 5"
    }

    @classmethod
    def clean_noisy_tags(cls, text: str) -> str:
        """Strip traditional SD1.5/SDXL tag spam to allow natural DiT comprehension."""
        cleaned = text
        for tag in cls.BANNED_TAGS:
            pattern = re.compile(rf"\b{re.escape(tag)}\b,?", re.IGNORECASE)
            cleaned = pattern.sub("", cleaned)
        # Normalize redundant commas and spaces
        cleaned = re.sub(r",\s*,+", ",", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
        return cleaned

    @classmethod
    def format_text_in_prompt(cls, text: str) -> str:
        """Ensure designated on-screen text uses double quotes as required by Z-Image Turbo."""
        # Find single quoted words that look like labels and normalize to double quotes
        def _replace_quotes(match):
            content = match.group(1).strip()
            return f'"{content}"'
        return re.sub(r"\'([A-Z0-9\s\-]+)\'", _replace_quotes, text)

    def compile(
        self,
        style: ZImageStyle,
        *,
        subject: Optional[str] = None,
        scene: Optional[str] = None,
        composition: Optional[str] = None,
        lighting: Optional[str] = None,
        medium_style: Optional[str] = None,
        color_texture: Optional[str] = None,
        constraints: Optional[str] = None,
        text_quote: Optional[str] = None,
    ) -> str:
        """Synthesize 7 dimensions into an official-grade Z-Image Turbo prompt.
        
        Args:
            style: The base ZImageStyle reference.
            subject: Overriding or custom subject description.
            scene: Overriding or custom scene description.
            composition: Overriding composition.
            lighting: Overriding lighting.
            medium_style: Overriding medium/aesthetic.
            color_texture: Overriding color/material texture.
            constraints: Extra constraints or positive-negative boundaries.
            text_quote: Accurate text that MUST appear inside the image (enclosed in "").
        """
        dims = style.dimensions

        def pick(override: Optional[str], fallback: str) -> str:
            return (override or fallback).strip().rstrip(" .")

        eff_subject = pick(subject, dims.subject)
        eff_scene = pick(scene, dims.scene)
        eff_comp = pick(composition, dims.composition)
        eff_light = pick(lighting, dims.lighting)
        eff_medium = pick(medium_style, dims.medium_style)
        eff_color = pick(color_texture, dims.color_texture)
        eff_constraints = pick(constraints, dims.constraints)

        # Scene clauses in the registry may already carry a preposition ("beside a window").
        # Only prepend one when it is missing, so we never emit "set in beside a window".
        prepositions = ("in ", "on ", "at ", "beside ", "inside ", "above ", "below ", "against ",
                        "along ", "among ", "within ", "beneath ", "under ", "near ", "across ",
                        "through ", "between ", "over ", "before ", "behind ")
        scene_clause = eff_scene if eff_scene.lower().startswith(prepositions) else f"in {eff_scene}"

        article = "An" if eff_medium[:1].lower() in "aeiou" else "A"
        lead_sentence = f"{article} {eff_medium} of {eff_subject}, {scene_clause}."

        # Remaining dimensions read as descriptive clauses, matching the official recipe style
        # ("Medium close-up composition, relaxed expression, realistic skin texture.").
        fragments = [eff_comp, eff_light, eff_color]
        body = ". ".join(f[0].upper() + f[1:] for f in fragments if f)
        body = f"{body}." if body else ""

        constraint_parts = []
        if eff_constraints:
            constraint_parts.append(eff_constraints[0].upper() + eff_constraints[1:])
        if text_quote:
            clean_text = text_quote.replace('"', '').strip()
            constraint_parts.append(
                f'The text "{clean_text}" is clearly and accurately rendered in the composition'
            )
        boundary_sentence = ". ".join(constraint_parts) + "." if constraint_parts else ""

        raw_prompt = " ".join(p for p in (lead_sentence, body, boundary_sentence) if p).strip()
        cleaned_prompt = self.clean_noisy_tags(raw_prompt)
        formatted_prompt = self.format_text_in_prompt(cleaned_prompt)
        if formatted_prompt and not formatted_prompt.endswith((".", '"')):
            formatted_prompt += "."

        return formatted_prompt


class ZImageBenchmarkSuite:
    """Pre-configured benchmark control suite for systematic style evaluation."""

    # Standardized neutral subjects for fair, cross-style comparison
    CANONICAL_SUBJECTS = {
        "portrait": "a young East Asian woman with natural facial features and a minimalist tailored outfit",
        "landscape": "a serene mountain valley with ancient winding pines, rocky cliffs, and a quiet river",
        "architecture": "a monumental courtyard pavilion with harmonious geometry and refined structural proportions",
        "object": "an elegant handcrafted ceramic vase with subtle organic textures and delicate glaze",
        "vehicle": "a sleek modern electric coupe with liquid aerodynamic body lines and precision paneling",
    }

    # Recommended first-pass evaluation list (14 diverse styles covering core categories)
    DEFAULT_EVAL_STYLES = [
        "editorial_fashion",
        "street_documentary",
        "black_white_noir",
        "vintage_film",
        "scifi_cinematic",
        "wuxia_cinema",
        "chinese_ink_wash",
        "gongbi_flower_bird",
        "song_aesthetics",
        "shinkai_scenery",
        "stylized_3d_animation",
        "luxury_product",
        "swiss_style",
        "watercolor",
    ]

    RUBRIC_CRITERIA = [
        ("Distinctiveness", "风格辨识度", "一眼能否清晰识别目标风格核心视觉特征"),
        ("Purity", "风格纯度", "是否保持纯净艺术语言，无冲突风格元素杂糅"),
        ("Detail Quality", "细节质量", "纹理、皮肤孔隙、材质折射、线条是否自然扎实"),
        ("Composition", "构图审美", "是否有明确视觉中心、空间纵深与光影层次"),
        ("Usability", "商业可用性", "是否可直接进入短剧分镜、海报设计或工业交付"),
    ]

    def __init__(self, atlas: Optional[ZImageStyleAtlas] = None) -> None:
        self.atlas = atlas or ZImageStyleAtlas()
        self.compiler = ZImagePromptCompiler()

    def generate_benchmark_matrix(
        self,
        style_ids: Optional[list[str]] = None,
        canonical_subject_key: str = "portrait"
    ) -> list[dict[str, Any]]:
        """Generate evaluation matrix with controlled subjects."""
        target_ids = style_ids or self.DEFAULT_EVAL_STYLES
        matrix = []
        base_subject = self.CANONICAL_SUBJECTS.get(canonical_subject_key, self.CANONICAL_SUBJECTS["portrait"])

        for sid in target_ids:
            try:
                style = self.atlas.get_style(sid)
                compiled_prompt = self.compiler.compile(
                    style=style,
                    subject=base_subject
                )
                matrix.append({
                    "style_id": style.id,
                    "code": style.code,
                    "category": style.category,
                    "name": style.name,
                    "name_en": style.name_en,
                    "base_subject_key": canonical_subject_key,
                    "base_subject": base_subject,
                    "default_prompt": style.positive_prompt,
                    "compiled_prompt": compiled_prompt,
                    "di_forward_steps": 8,
                    "guidance_scale": 0.0,
                    "sampler": "euler",
                    "scheduler": "simple",
                })
            except KeyError:
                continue

        return matrix


DIMENSION_FIELDS = (
    "subject", "scene", "composition", "lighting",
    "medium_style", "color_texture", "constraints",
)


class ZImageVocabulary:
    """Reusable 7-dimension phrase bank (config/z_image_style_vocabulary.yaml).

    The style atlas holds finished recipes; this holds the ingredients, so a new
    style can be assembled from objective visual phrases instead of tag spam.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            config_path = find_project_root() / "config" / "z_image_style_vocabulary.yaml"
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Z-Image vocabulary config not found at: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._dims: dict[str, dict[str, dict]] = data.get("dimensions", {}) or {}
        unknown = set(self._dims) - set(DIMENSION_FIELDS)
        if unknown:
            raise ValueError(f"Unknown vocabulary dimensions: {sorted(unknown)}")

    def dimensions(self) -> list[str]:
        return [d for d in DIMENSION_FIELDS if d in self._dims]

    def entries(self, dimension: str) -> dict[str, dict]:
        if dimension not in self._dims:
            raise KeyError(f"Dimension '{dimension}' not in vocabulary. Available: {self.dimensions()}")
        return self._dims[dimension]

    def get(self, dimension: str, entry_id: str) -> str:
        entries = self.entries(dimension)
        if entry_id not in entries:
            raise KeyError(f"Entry '{entry_id}' not in dimension '{dimension}'. Available: {list(entries)}")
        return entries[entry_id]["en"]

    def resolve(self, spec: str) -> dict[str, str]:
        """Resolve "lighting:low_key_neon,composition:intimate_close_up" into overrides."""
        out: dict[str, str] = {}
        for chunk in spec.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if ":" not in chunk:
                raise ValueError(f"Bad vocab term '{chunk}'; expected dimension:entry_id")
            dim, entry = (p.strip() for p in chunk.split(":", 1))
            out[dim] = self.get(dim, entry)
        return out

    def count(self) -> int:
        return sum(len(v) for v in self._dims.values())


def compile_style_mix(
    atlas: ZImageStyleAtlas,
    base_style_id: str,
    borrow_style_id: str,
    borrow_dimensions: List[str],
    *,
    compiler: Optional[ZImagePromptCompiler] = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Cross-style combination experiment (e.g. Song aesthetics + luxury commercial lighting).

    Keeps ONE primary medium unless medium_style is explicitly borrowed, which is the
    only safe way to mix visual languages without producing conflicting style soup.
    """
    base = atlas.get_style(base_style_id)
    borrow = atlas.get_style(borrow_style_id)
    bad = [d for d in borrow_dimensions if d not in DIMENSION_FIELDS]
    if bad:
        raise ValueError(f"Unknown dimensions {bad}; valid: {list(DIMENSION_FIELDS)}")

    merged = {d: getattr(base.dimensions, d) for d in DIMENSION_FIELDS}
    for d in borrow_dimensions:
        merged[d] = getattr(borrow.dimensions, d)
    text_quote = overrides.pop("text_quote", None)
    for k, v in overrides.items():
        if k in DIMENSION_FIELDS and v:
            merged[k] = v

    compiler = compiler or ZImagePromptCompiler()
    prompt = compiler.compile(style=base, text_quote=text_quote, **merged)
    return {
        "base_style": base.id,
        "borrow_style": borrow.id,
        "borrowed_dimensions": list(borrow_dimensions),
        "dimensions": merged,
        "prompt": prompt,
        "medium_conflict_warning": (
            "medium_style borrowed: verify the result keeps a single coherent art medium"
            if "medium_style" in borrow_dimensions else None
        ),
    }
