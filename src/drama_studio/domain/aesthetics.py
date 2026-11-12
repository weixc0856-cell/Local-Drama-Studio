"""Shot aesthetic design: six dimensions, A/B variants, style adapter, prompt compiler.

Design (this module) answers *how the frame is organised*; the style preset
answers *which artistic language expresses it*. There is no style-id branch
here: both styles are driven by ``preset.aesthetic_profile`` plus the existing
material/line/detail fields.

The prompt compiler follows the FLUX.2 order that matters: subject and
relations first, then composition, environment, light, colour, style, material.
The current workflow zeroes the negative conditioning (CFG 1.0), so negatives
are recorded but not treated as control; explicit positive constraints are used
instead.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from drama_studio.domain.style.presets import AestheticProfile, ColorTemperature, CompositionStrategy, LightingKey, ShotSize, StylePreset, SubjectPosition, ValueRange

Axis = Literal["composition", "lighting", "color", "depth", "mise_en_scene", "storytelling"]
Viewpoint = Literal["eye_level", "low", "high", "aerial", "oblique"]
Density = Literal["sparse", "moderate", "dense"]
LightDirection = Literal["front", "side_left", "side_right", "back", "top", "diffuse"]
LightQuality = Literal["soft", "hard", "mixed"]
Level = Literal["low", "medium", "high"]
Sharpness = Literal["shallow", "medium", "deep"]

POSITION_TARGET: dict[str, tuple[float, float]] = {
    "center": (0.50, 0.50),
    "left_third": (0.34, 0.50),
    "right_third": (0.66, 0.50),
    "lower_left": (0.32, 0.68),
    "lower_right": (0.68, 0.68),
    "upper_center": (0.50, 0.32),
}

SHOT_SIZE_ZH = {
    "extreme_wide": "大远景",
    "wide": "远景",
    "medium": "中景",
    "close": "近景",
    "detail": "细节特写",
}
VIEWPOINT_ZH = {
    "eye_level": "平视",
    "low": "低角度仰视",
    "high": "高角度俯视",
    "aerial": "高空俯瞰",
    "oblique": "斜角观察",
}
POSITION_ZH = {
    "center": "画面中心",
    "left_third": "左三分线",
    "right_third": "右三分线",
    "lower_left": "左下角",
    "lower_right": "右下角",
    "upper_center": "上方居中",
}
STRATEGY_ZH = {
    "rule_of_thirds": "三分法",
    "center": "中心构图",
    "symmetry": "对称构图",
    "frame_in_frame": "框景",
    "diagonal": "对角线构图",
    "negative_space": "大面积留白",
    "vertical_depth": "纵向纵深",
    "monumental_scale": "宏大尺度",
    "corner_placement": "边角取景",
    "high_distance": "高远",
    "deep_distance": "深远",
    "level_distance": "平远",
    "scattered_perspective": "散点透视",
    "void_solid": "虚实相生、计白当黑",
}
LIGHT_KEY_ZH = {
    "moon": "月光",
    "sun_low": "低角度日光",
    "sun_high": "高位日光",
    "overcast": "阴天散射光",
    "candle": "烛火光",
    "none": "无明显主光",
}
LIGHT_DIR_ZH = {
    "front": "正面光",
    "side_left": "左侧光",
    "side_right": "右侧光",
    "back": "逆光",
    "top": "顶光",
    "diffuse": "漫射光",
}
QUALITY_ZH = {"soft": "柔和", "hard": "硬朗", "mixed": "软硬混合"}
LEVEL_ZH = {"low": "低", "medium": "中", "high": "高"}
TEMPERATURE_ZH = {"warm": "暖", "cool": "冷", "neutral": "中性", "split": "冷暖对比"}
VALUE_ZH = {
    "high_key": "高调明亮",
    "middle": "中间调",
    "low_key": "低调沉暗",
    "full": "全调层次",
}
SATURATION_ZH = {"low": "低饱和", "moderate": "中等饱和", "high": "高饱和"}
DENSITY_ZH = {"sparse": "疏", "moderate": "适中", "dense": "密"}
SHARPNESS_ZH = {"shallow": "浅景深", "medium": "中等景深", "deep": "远景仍清晰"}


class CompositionDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_size: ShotSize
    viewpoint: Viewpoint
    subject_position: SubjectPosition
    visual_weight: Literal["centered", "asymmetric", "balanced", "diagonal"]
    foreground_occlusion: bool = False
    leading_lines: list[str] = Field(default_factory=list, max_length=4)
    whitespace_ratio: float = Field(ge=0.0, le=0.9)
    depth_layers: int = Field(ge=1, le=3)
    density: Density
    strategies: list[CompositionStrategy] = Field(min_length=1, max_length=6)
    safe_area: bool = True


class LightingDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_light: LightingKey
    direction: LightDirection
    quality: LightQuality
    intensity: Level
    contrast: Level
    rim_light: bool = False
    ambient: str = Field(min_length=1, max_length=80)
    reflected: bool = False
    aerial_perspective: bool = True
    mist_scattering: bool = True
    time_weather: str = Field(min_length=1, max_length=80)
    mood: str = Field(min_length=1, max_length=60)


class ColorDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominant: str = Field(min_length=1, max_length=20)
    secondary: list[str] = Field(default_factory=list, max_length=4)
    accent: list[str] = Field(default_factory=list, max_length=4)
    temperature: ColorTemperature
    saturation: Literal["low", "moderate", "high"]
    value_range: ValueRange
    continuity_group: str = Field(min_length=1, max_length=40)
    style_range: bool = True


class DepthDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    foreground: str = Field(min_length=1, max_length=120)
    midground: str = Field(min_length=1, max_length=120)
    background: str = Field(min_length=1, max_length=120)
    occlusion: str = Field(default="", max_length=120)
    aerial_perspective: bool = True
    sharpness_falloff: Sharpness
    guides: list[str] = Field(default_factory=list, max_length=4)
    layered_assets: bool = False


class MiseEnSceneDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(min_length=1, max_length=40)
    architecture: str = Field(min_length=1, max_length=200)
    components: list[str] = Field(default_factory=list, max_length=10)
    nature: list[str] = Field(default_factory=list, max_length=10)
    costume: str = Field(default="", max_length=120)
    props: list[str] = Field(default_factory=list, max_length=10)
    figure_pose: str = Field(default="", max_length=120)
    cultural_context: str = Field(default="", max_length=160)
    relationships: list[str] = Field(default_factory=list, max_length=8)
    modern_elements: Literal["none", "risk"] = "none"


class StorytellingDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narrative_purpose: str = Field(min_length=1, max_length=160)
    emotional_target: str = Field(min_length=1, max_length=80)
    visual_subject: str = Field(min_length=1, max_length=160)
    focal_point: str = Field(min_length=1, max_length=120)
    entry_point: str = Field(min_length=1, max_length=120)
    eye_path: str = Field(min_length=1, max_length=160)
    connection_prev: str = Field(default="", max_length=160)
    connection_next: str = Field(default="", max_length=160)
    rhythm: str = Field(min_length=1, max_length=60)


class ShotDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    composition: CompositionDesign
    lighting: LightingDesign
    color: ColorDesign
    depth: DepthDesign
    mise_en_scene: MiseEnSceneDesign
    storytelling: StorytellingDesign


class ShotVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: Literal["A", "B"]
    label: str = Field(min_length=1, max_length=80)
    rationale: str = Field(min_length=1, max_length=240)
    changed_axis: Axis
    design: ShotDesign


class ShotAestheticSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_id: str = Field(pattern=r"^shot_\d{3}$")
    scene_subject: str = Field(min_length=2, max_length=400)
    axis: Axis
    variants: list[ShotVariant] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def _only_one_axis_changes(self) -> "ShotAestheticSet":
        a, b = self.variants
        if {a.variant_id, b.variant_id} != {"A", "B"}:
            raise ValueError("variants must be exactly A and B")
        if a.changed_axis != self.axis or b.changed_axis != self.axis:
            raise ValueError("both variants must declare the same changed_axis")
        left = a.design.model_dump(exclude={self.axis})
        right = b.design.model_dump(exclude={self.axis})
        if left != right:
            raise ValueError(
                f"{self.shot_id}: A/B differ outside {self.axis}; only one axis may change"
            )
        if a.design.model_dump()[self.axis] == b.design.model_dump()[self.axis]:
            raise ValueError(f"{self.shot_id}: A/B do not differ on {self.axis}")
        return self


class SharedAesthetic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continuity_group: str
    palette_keys: list[str]
    emotional_arc: list[str]
    visual_grammar: list[str]
    constraints: list[str]


class AestheticPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    style_id: str
    style_sha256: str
    style_config_sha256: str
    script_sha256: str
    shared: SharedAesthetic
    shots: list[ShotAestheticSet] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_and_shared(self) -> "AestheticPlan":
        ids = [shot.shot_id for shot in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate shot_id in aesthetic plan")
        for shot in self.shots:
            for variant in shot.variants:
                if variant.design.color.continuity_group != self.shared.continuity_group:
                    raise ValueError(
                        f"{shot.shot_id}/{variant.variant_id}: continuity_group "
                        f"{variant.design.color.continuity_group!r} does not match shared "
                        f"{self.shared.continuity_group!r}"
                    )
        return self

    def variant(self, shot_id: str, variant_id: str) -> ShotVariant:
        for shot in self.shots:
            if shot.shot_id == shot_id:
                for variant in shot.variants:
                    if variant.variant_id == variant_id:
                        return variant
                raise KeyError(f"{shot_id}: no variant {variant_id}")
        raise KeyError(f"unknown shot {shot_id}")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _text(shot: Any) -> str:
    if isinstance(shot, dict):
        return " ".join(str(shot.get(key) or "") for key in ("scene_prompt", "visual_prompt", "motion"))
    return " ".join(str(getattr(shot, key, "") or "") for key in ("scene_prompt", "visual_prompt", "motion"))


def _infer_shot_size(text: str, profile: AestheticProfile) -> ShotSize:
    if any(token in text for token in ("细节", "特写", "detail")):
        return "detail"
    if any(token in text for token in ("大远景", "宏大", "长卷")):
        return "extreme_wide"
    if any(token in text for token in ("中景",)):
        return "medium"
    return "wide"


def _infer_lighting_key(text: str, profile: AestheticProfile) -> LightingKey:
    if any(token in text for token in ("月", "夜")):
        return "moon"
    if any(token in text for token in ("夕", "日落", "黄昏")):
        return "sun_low"
    if any(token in text for token in ("晨", "朝", "日出")):
        return "sun_low"
    if any(token in text for token in ("雾", "云", "阴")):
        return "overcast"
    return profile.lighting.default_key


def infer_base_design(shot: Any, preset: StylePreset) -> ShotDesign:
    """Default six-dimension design; a caller can override any part with JSON."""
    profile = preset.aesthetic_profile
    text = _text(shot)
    shot_size = _infer_shot_size(text, profile)
    key = _infer_lighting_key(text, profile)
    lo, hi = profile.composition.whitespace_range
    whitespace = round((lo + hi) / 2.0, 2)
    dominant = profile.color.dominant_keys[0]
    secondary = profile.color.secondary_keys[:2]
    accent = profile.color.accent_keys[:1]
    return ShotDesign(
        composition=CompositionDesign(
            shot_size=shot_size,
            viewpoint="eye_level",
            subject_position=profile.composition.default_subject_position,
            visual_weight="balanced",
            foreground_occlusion=False,
            leading_lines=[],
            whitespace_ratio=whitespace,
            depth_layers=profile.depth.default_layers,
            density="moderate",
            strategies=profile.composition.preferred_strategies[:3],
            safe_area=True,
        ),
        lighting=LightingDesign(
            key_light=key,
            direction=profile.lighting.default_direction,
            quality=profile.lighting.default_quality,
            intensity="medium",
            contrast=profile.lighting.default_contrast,
            rim_light=False,
            ambient="柔和环境光",
            reflected=False,
            aerial_perspective=profile.depth.aerial_perspective,
            mist_scattering=key in ("moon", "overcast"),
            time_weather="清晨薄雾" if key == "overcast" else "夜色清朗" if key == "moon" else "天光柔和",
            mood=profile.storytelling.emotion_vocabulary[0],
        ),
        color=ColorDesign(
            dominant=dominant,
            secondary=secondary,
            accent=accent,
            temperature=profile.color.default_temperature,
            saturation="moderate",
            value_range=profile.color.value_range,
            continuity_group=profile.color.continuity_group,
            style_range=True,
        ),
        depth=DepthDesign(
            foreground="前景坡石与枝叶",
            midground="主体山体与水面" if "水" in text else "主体景物",
            background="远山与云雾",
            occlusion="前景枝叶轻微遮挡，不压主体",
            aerial_perspective=profile.depth.aerial_perspective,
            sharpness_falloff=profile.depth.sharpness_falloff,
            guides=["水面", "坡岸"],
            layered_assets=False,
        ),
        mise_en_scene=MiseEnSceneDesign(
            period=profile.mise_en_scene.period,
            architecture=profile.mise_en_scene.architecture_positive,
            components=[],
            nature=[],
            costume="",
            props=[],
            figure_pose="",
            cultural_context="",
            relationships=[],
            modern_elements="none",
        ),
        storytelling=StorytellingDesign(
            narrative_purpose="建立空间与情绪",
            emotional_target=profile.storytelling.emotion_vocabulary[0],
            visual_subject="画面主体",
            focal_point="主体",
            entry_point="近景引导线",
            eye_path="由近及远，沿引导线进入主体",
            connection_prev="承接上一镜的空间方向",
            connection_next="为下一镜保留视线出口",
            rhythm=profile.storytelling.default_rhythm,
        ),
    )


def _opposite_side(position: SubjectPosition) -> SubjectPosition:
    return {
        "center": "right_third",
        "left_third": "right_third",
        "right_third": "left_third",
        "lower_left": "lower_right",
        "lower_right": "lower_left",
        "upper_center": "right_third",
    }[position]


def _bump_contrast(level: Level) -> Level:
    return {"low": "medium", "medium": "high", "high": "high"}[level]


def build_variants(
    base: ShotDesign,
    axis: Axis,
    preset: StylePreset,
    notes: dict[str, Any] | None = None,
) -> list[ShotVariant]:
    """Create A/B that differ on exactly one dimension."""
    profile = preset.aesthetic_profile
    notes = notes or {}

    if axis == "composition":
        lo, hi = profile.composition.whitespace_range
        a_comp = base.composition.model_copy(update={
            "subject_position": base.composition.subject_position,
            "visual_weight": "centered" if base.composition.subject_position == "center" else "balanced",
            "whitespace_ratio": round(min(hi, max(lo, base.composition.whitespace_ratio)), 2),
            "density": base.composition.density,
            "strategies": list(dict.fromkeys(["center", *base.composition.strategies]))
            if base.composition.subject_position == "center" else list(base.composition.strategies),
        })
        b_strategies = [
            item for item in dict.fromkeys([
                "rule_of_thirds", "negative_space", "diagonal", *base.composition.strategies
            ]) if item not in ("center", "symmetry")
        ]
        b_comp = base.composition.model_copy(update={
            "subject_position": _opposite_side(base.composition.subject_position),
            "visual_weight": "asymmetric",
            "whitespace_ratio": round(lo + (hi - lo) * 0.85, 2),
            "density": "sparse",
            "foreground_occlusion": True,
            "strategies": b_strategies[:6],
        })
        a = base.model_copy(update={"composition": a_comp})
        b = base.model_copy(update={"composition": b_comp})
        label_a = "稳定中心" if base.composition.subject_position == "center" else "既定偏置"
        label_b = "偏置留白" if base.composition.subject_position == "center" else "反向偏置"
        why_a = (
            "主体居中，秩序稳定，视线直接落在主体上"
            if base.composition.subject_position == "center"
            else "保持既定主体位置，作为对照基线"
        )
        why_b = "主体移到另一侧，扩大留白并加入引导线，制造张力与进入路径"
    elif axis == "lighting":
        a_light = base.lighting.model_copy(update={
            "direction": "diffuse",
            "quality": "soft",
            "contrast": "low",
            "rim_light": False,
            "mist_scattering": True,
        })
        b_light = base.lighting.model_copy(update={
            "direction": "back",
            "quality": "soft",
            "contrast": _bump_contrast(base.lighting.contrast),
            "rim_light": True,
            "mist_scattering": True,
            "mood": "含蓄而有轮廓",
        })
        a = base.model_copy(update={"lighting": a_light})
        b = base.model_copy(update={"lighting": b_light})
        label_a, label_b = "漫射平光", "逆光轮廓"
        why_a = "漫射光压低反差，保持墨色/矿物色的层次与含蓄"
        why_b = "逆光与轮廓光拉开主体与背景，增加空气透视和戏剧性"
    elif axis == "color":
        dominant = base.color.dominant
        alternatives = [key for key in profile.color.dominant_keys if key != dominant]
        if not alternatives:
            raise ValueError(f"{preset.id}: colour A/B needs at least two dominant palette keys")
        alt = alternatives[0]
        accent = profile.color.accent_keys[0] if profile.color.accent_keys else base.color.accent[0]
        a_color = base.color.model_copy(update={
            "dominant": dominant,
            "temperature": profile.color.default_temperature,
            "saturation": "moderate",
        })
        b_color = base.color.model_copy(update={
            "dominant": alt,
            "secondary": list(dict.fromkeys(
                [key for key in [accent, *base.color.secondary] if key != alt]
            ))[:3],
            "accent": list(dict.fromkeys([*base.color.accent, accent]))[:3],
            "temperature": "warm" if profile.color.default_temperature in ("cool", "neutral") else "cool",
            "saturation": "moderate",
        })
        a = base.model_copy(update={"color": a_color})
        b = base.model_copy(update={"color": b_color})
        label_a, label_b = f"{dominant}主调", f"{alt}主调"
        why_a = f"以{dominant}为主，保持风格既定色相与连续性"
        why_b = f"改用{alt}为主并加入{accent}，比较另一组矿物色关系"
    elif axis in ("depth", "mise_en_scene", "storytelling"):
        raise ValueError(f"axis {axis} has no built-in A/B library; supply explicit variants")
    else:
        raise ValueError(f"unknown aesthetic axis: {axis}")

    return [
        ShotVariant(
            variant_id="A",
            label=str(notes.get("A", {}).get("label") or label_a),
            rationale=str(notes.get("A", {}).get("rationale") or why_a),
            changed_axis=axis,
            design=a,
        ),
        ShotVariant(
            variant_id="B",
            label=str(notes.get("B", {}).get("label") or label_b),
            rationale=str(notes.get("B", {}).get("rationale") or why_b),
            changed_axis=axis,
            design=b,
        ),
    ]


def generate_plan(
    script: Any,
    preset: StylePreset,
    *,
    axes: dict[str, str] | None = None,
    designs: dict[str, Any] | None = None,
    style_config_sha256: str = "",
) -> AestheticPlan:
    """Build an A/B plan for every shot in the ProductionScript.

    ``designs`` is an authored JSON keyed by shot id; it may contain a full
    ``design`` (validated as ShotDesign), an ``axis``, ``scene_subject`` and
    variant labels/rationales. Without it, a deterministic base design is
    inferred from the shot text and the style profile.
    """
    axes = axes or {}
    designs = designs or {}
    shots = []
    for shot in (script.get("shots") if isinstance(script, dict) else script.shots):
        shot_id = shot.get("shot_id") if isinstance(shot, dict) else shot.shot_id
        override = designs.get(shot_id) or {}
        if "design" in override:
            base = ShotDesign.model_validate(override["design"])
        else:
            base = infer_base_design(shot, preset)
            if "design_patch" in override:
                patch = override["design_patch"]
                merged = base.model_dump()
                for dimension, values in patch.items():
                    merged[dimension] = {**merged[dimension], **values}
                base = ShotDesign.model_validate(merged)
        axis = str(override.get("axis") or axes.get(shot_id) or "composition")
        scene_subject = str(override.get("scene_subject") or _text(shot) or "画面主体")
        variants = build_variants(base, axis, preset, override.get("variants"))
        shots.append(
            ShotAestheticSet(
                shot_id=shot_id,
                scene_subject=scene_subject,
                axis=axis,
                variants=variants,
            )
        )

    profile = preset.aesthetic_profile
    line_texts = [
        line.get("text") if isinstance(line, dict) else line.text
        for line in (script.get("lines") if isinstance(script, dict) else script.lines)
    ]
    shared = SharedAesthetic(
        continuity_group=profile.color.continuity_group,
        palette_keys=list(dict.fromkeys(
            profile.color.dominant_keys + profile.color.secondary_keys + profile.color.accent_keys
        )),
        emotional_arc=[text for text in line_texts if text][:6],
        visual_grammar=profile.composition.preferred_strategies,
        constraints=profile.mise_en_scene.positive_constraints,
    )
    script_payload = script.model_dump() if hasattr(script, "model_dump") else script
    return AestheticPlan(
        style_id=preset.id,
        style_sha256=str(getattr(script, "style_sha256", "") or ""),
        style_config_sha256=style_config_sha256,
        script_sha256=canonical_sha256(script_payload),
        shared=shared,
        shots=shots,
    )


class CompiledPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_id: str
    variant_id: str
    style_id: str
    sections: dict[str, str]
    prompt: str
    negative_prompt: str
    negative_supported: bool
    positive_constraints: list[str]
    spec_sha256: str
    prompt_sha256: str


def _palette_hex(preset: StylePreset, key: str) -> str:
    return preset.color_palette[key]


def compile_prompt(
    shot_set: ShotAestheticSet,
    variant: ShotVariant,
    preset: StylePreset,
    *,
    negative_supported: bool = False,
) -> CompiledPrompt:
    """Compile one variant into an ordered FLUX prompt + audit record."""
    d = variant.design
    comp, light, color = d.composition, d.lighting, d.color
    depth, mise, story = d.depth, d.mise_en_scene, d.storytelling
    profile = preset.aesthetic_profile

    strategies = "、".join(STRATEGY_ZH[s] for s in comp.strategies)
    palette_keys = set(preset.color_palette)
    used_colors = [color.dominant, *color.secondary, *color.accent]
    missing = sorted(set(used_colors) - palette_keys)
    if missing:
        raise ValueError(f"{shot_set.shot_id}/{variant.variant_id}: color keys not in style palette: {missing}")
    subject = "；".join(part for part in [
        f"主体：{story.visual_subject}",
        f"主体关系：{'、'.join(mise.relationships)}" if mise.relationships else "",
        f"场景：{shot_set.scene_subject}",
    ] if part)
    composition = "；".join(part for part in [
        "横屏16:9构图",
        f"{SHOT_SIZE_ZH[comp.shot_size]}，{VIEWPOINT_ZH[comp.viewpoint]}",
        f"主体位于{POSITION_ZH[comp.subject_position]}",
        f"构图策略：{strategies}",
        f"留白约{round(comp.whitespace_ratio * 100)}%",
        DENSITY_ZH[comp.density],
        "前景轻微遮挡，主体结构完整" if comp.foreground_occlusion else "前景不遮挡主体",
        f"视觉引导：{'、'.join(comp.leading_lines)}" if comp.leading_lines else "视觉引导由山势、水面与坡岸自然形成",
        "字幕安全区不压主体" if comp.safe_area else "",
    ] if part)
    environment = "；".join(part for part in [
        f"前景：{depth.foreground}",
        f"中景：{depth.midground}",
        f"远景：{depth.background}",
        f"空间：{depth.occlusion}" if depth.occlusion else "",
        "空气透视，远近虚实分明" if depth.aerial_perspective else "空间关系依靠结构层次",
        f"自然环境：{'、'.join(mise.nature)}" if mise.nature else "",
        f"建筑：{mise.architecture}",
        f"建筑构件：{'、'.join(mise.components)}" if mise.components else "",
    ] if part)
    lighting = "；".join(part for part in [
        f"主光：{LIGHT_KEY_ZH[light.key_light]}",
        f"方向：{LIGHT_DIR_ZH[light.direction]}",
        f"光质：{QUALITY_ZH[light.quality]}，强度{LEVEL_ZH[light.intensity]}，明暗反差{LEVEL_ZH[light.contrast]}",
        "轮廓光只勾边缘，不泛光" if light.rim_light else "不使用强烈轮廓光",
        f"环境光：{light.ambient}",
        "水面/地面有柔和反射光" if light.reflected else "",
        "空气透视与雾中散射" if light.mist_scattering else "",
        f"时间天气：{light.time_weather}",
        f"情绪：{light.mood}",
    ] if part)
    color_parts = [
        f"主色：{color.dominant}（{_palette_hex(preset, color.dominant)}）",
        f"辅助色：{'、'.join(f'{key}（{_palette_hex(preset, key)}）' for key in color.secondary)}" if color.secondary else "",
        f"点缀色：{'、'.join(f'{key}（{_palette_hex(preset, key)}）' for key in color.accent)}" if color.accent else "",
        f"冷暖：{TEMPERATURE_ZH[color.temperature]}",
        f"{SATURATION_ZH[color.saturation]}，{VALUE_ZH[color.value_range]}",
        f"色彩连续性组：{color.continuity_group}",
        "颜色落在风格既定范围内，不偏色" if color.style_range else "",
    ]
    colour = "；".join(part for part in color_parts if part)
    style = "；".join(part for part in [preset.visual_language, preset.positive_prompt] if part)
    material = "；".join(part for part in [
        preset.material.prompt,
        preset.line.prompt,
        preset.detail.prompt,
    ] if part)

    constraints = list(dict.fromkeys([
        *profile.mise_en_scene.positive_constraints,
        f"画面中的建筑与器物均为{mise.period}形制",
        *[f"主体关系：{item}" for item in mise.relationships],
    ]))
    sections = {
        "subject": subject,
        "composition": composition,
        "environment": environment,
        "lighting": lighting,
        "color": colour,
        "style": style,
        "material": material,
    }
    prompt = "；".join([f"{value}" for value in sections.values() if value] + constraints)
    negative = preset.negative_prompt
    spec = variant.model_dump()
    return CompiledPrompt(
        shot_id=shot_set.shot_id,
        variant_id=variant.variant_id,
        style_id=preset.id,
        sections=sections,
        prompt=prompt,
        negative_prompt=negative,
        negative_supported=negative_supported,
        positive_constraints=constraints,
        spec_sha256=canonical_sha256(spec),
        prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    )


def write_plan(plan: AestheticPlan, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(plan.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_plan(path: Path) -> AestheticPlan:
    return AestheticPlan.model_validate(json.loads(path.read_text(encoding="utf-8")))


def design_for_quality(shot_set: ShotAestheticSet, variant_id: str) -> dict[str, Any]:
    """Plain dict handed to quality checks (no Pydantic dependency there)."""
    variant = next(v for v in shot_set.variants if v.variant_id == variant_id)
    return {
        "shot_id": shot_set.shot_id,
        "variant_id": variant_id,
        "axis": shot_set.axis,
        "scene_subject": shot_set.scene_subject,
        "design": variant.design.model_dump(),
        "label": variant.label,
        "rationale": variant.rationale,
    }
