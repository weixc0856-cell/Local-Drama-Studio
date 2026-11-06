"""Generate the 12 Visual Style Packs under config/style_packs/.

Idempotent: rewrites every pack file. Reference images are never generated.
Run: .venv\\Scripts\\python.exe scripts\\gen_style_packs.py
"""

from __future__ import annotations

import pathlib

import yaml

BASE = pathlib.Path(__file__).resolve().parents[1] / "config" / "style_packs"

STYLES = [
    dict(id="retro.collage", group="retro", name="拼贴艺术",
         summary="剪贴、撕纸边、照片碎片与印刷纹理的层叠构图。",
         identity="retro paper collage art",
         medium="cut paper, torn edges, vintage photo fragments, screen-print texture",
         materials=["paper fibre", "torn edges", "halftone print", "aged photograph"],
         composition=["asymmetric layered layout", "overlapping fragments", "deliberate empty paper gaps"],
         lighting="flat even light with local shadows between layers", temperature="neutral", contrast="medium",
         palette=[("paper cream", "#E8DCC8"), ("ink black", "#1B1B1B"), ("vermilion", "#C0392B"),
                  ("cobalt", "#2E5E9E"), ("olive", "#6B7A3A")],
         sat=(0.10, 0.60), edge=(0.06, 0.25),
         camera=["dolly_in", "tracking", "static"], lens=50, dof="layered",
         motion=["paper layer parallax", "edge tearing", "fragment reassembly"],
         secondary=["paper flutter", "print grain shift"],
         preserve=["torn paper edges", "visible print texture"],
         avoid=["photoreal depth of field", "smooth digital gradients", "3D rendering"],
         anchors=["every element reads as a cut paper piece", "visible torn edges and print grain",
                  "layers cast small local shadows"]),
    dict(id="retro.synthwave", group="retro", name="合成波",
         summary="霓虹网格、镀铬反射与 80 年代未来主义。",
         identity="1980s synthwave retro-futurism",
         medium="neon light, chrome surfaces, grid horizon, scan lines",
         materials=["chrome", "neon tube", "glossy plastic", "film grain"],
         composition=["strong central vanishing point", "symmetrical geometry", "low horizon"],
         lighting="neon key light, magenta and cyan rim", temperature="cool", contrast="high",
         palette=[("magenta", "#FF2E88"), ("cyan", "#00E5FF"), ("violet", "#6C2BD9"),
                  ("deep navy", "#0B1026"), ("chrome", "#C9D6E3")],
         sat=(0.35, 0.80), edge=(0.04, 0.18),
         camera=["dolly_in", "orbit", "tracking"], lens=24, dof="deep",
         motion=["grid advancing", "neon pulse", "light band sweep"],
         secondary=["cloud drift", "scan line flicker"],
         preserve=["grid geometry", "neon colour separation"],
         avoid=["daylight realism", "warm earth palette", "hand-drawn texture"],
         anchors=["neon magenta and cyan light sources", "grid receding to a central vanishing point",
                  "chrome reflections"]),
    dict(id="retro.pop_art", group="retro", name="波普艺术",
         summary="漫画网点、粗黑轮廓与大色块的商业图像语言。",
         identity="pop art comic print",
         medium="halftone dots, bold black outlines, flat ink colour",
         materials=["newsprint", "halftone screen", "flat ink"],
         composition=["graphic panel layout", "repeated motifs", "exaggerated subject scale"],
         lighting="flat commercial lighting, no soft gradients", temperature="neutral", contrast="high",
         palette=[("red", "#E02B20"), ("yellow", "#FFD400"), ("blue", "#0057B8"),
                  ("black", "#111111"), ("white", "#FFFFFF")],
         sat=(0.40, 0.90), edge=(0.05, 0.20),
         camera=["static", "pan"], lens=50, dof="flat",
         motion=["graphic pop-in", "repeated motif movement", "panel transition"],
         secondary=["halftone shimmer"],
         preserve=["bold outlines", "flat colour fields"],
         avoid=["photographic depth of field", "soft airbrush shading", "texture noise"],
         anchors=["thick black contour lines", "flat unmodulated colour blocks",
                  "visible halftone dot pattern"]),
    dict(id="retro.y2k", group="retro", name="Y2K 千禧",
         summary="金属、镭射、透明 PVC 与未来科技质感。",
         identity="Y2K chrome futurism",
         medium="liquid metal, holographic film, transparent PVC, lens flare",
         materials=["mirror chrome", "iridescent film", "clear plastic", "pearl finish"],
         composition=["floating product space", "streamlined geometry", "macro detail"],
         lighting="hard specular highlights, coloured bounce", temperature="cool", contrast="high",
         palette=[("silver", "#C0C6CF"), ("hot pink", "#FF69B4"), ("ice blue", "#A8E6FF"),
                  ("lime", "#C6FF00"), ("pearl", "#F5F0FA")],
         sat=(0.20, 0.70), edge=(0.03, 0.15),
         camera=["orbit", "dolly_in"], lens=85, dof="shallow",
         motion=["metal rotation", "reflection sweep", "liquid morph"],
         secondary=["flare drift"],
         preserve=["specular reflections", "transparent material refraction"],
         avoid=["matte paper texture", "earth tones", "hand-painted brushwork"],
         anchors=["mirror chrome surfaces with sharp highlights", "iridescent holographic film",
                  "transparent PVC with visible refraction"]),
    dict(id="oriental.modern_chinese", group="oriental", name="国风新中式",
         summary="东方传统元素与现代设计语言融合。",
         identity="modern Chinese aesthetic",
         medium="refined digital painting with traditional motifs",
         materials=["silk", "lacquer", "stone", "ink wash accents"],
         composition=["generous negative space", "symmetry with offset focal point", "layered depth"],
         lighting="soft ambient, low contrast", temperature="neutral", contrast="medium",
         palette=[("azurite", "#2E5E75"), ("malachite", "#4E7A5E"), ("cinnabar", "#9A3B32"),
                  ("ochre", "#8C5A3B"), ("dai", "#3A3F4B")],
         sat=(0.05, 0.30), edge=(0.04, 0.15),
         camera=["dolly_in", "crane", "tilt"], lens=35, dof="deep",
         motion=["mist drift", "water flow", "robe sway"],
         secondary=["tree sway", "cloud drift"],
         preserve=["negative space", "traditional motifs"],
         avoid=["neon colour", "3D plastic surfaces", "heavy photoreal texture"],
         anchors=["restrained azurite and cinnabar accents", "visible negative space",
                  "traditional architectural motifs"]),
    dict(id="oriental.gongbi", group="oriental", name="工笔国风",
         summary="铁线描、矿物颜料、绢本设色。",
         identity="Chinese gongbi fine-line painting",
         medium="silk ground, iron-wire contours, mineral pigments",
         materials=["silk", "mineral pigment", "fine ink line"],
         composition=["precise decorative layout", "balanced negative space", "clear hierarchical detail"],
         lighting="soft even light, no dramatic shadow", temperature="cool", contrast="low",
         palette=[("azurite", "#2E5E75"), ("malachite", "#4E7A5E"), ("cinnabar", "#B23A2E"),
                  ("pale ochre", "#C8A56A"), ("silk", "#E3D6BE")],
         sat=(0.08, 0.35), edge=(0.10, 0.30),
         camera=["tracking", "dolly_in", "static"], lens=50, dof="deep",
         motion=["petal fall", "bird flight", "robe sway"],
         secondary=["leaf tremble"],
         preserve=["fine contours", "mineral pigment layering"],
         avoid=["loose watercolour bleeding", "photoreal rendering", "heavy contrast"],
         anchors=["crisp iron-wire outlines", "flat mineral pigment layers", "visible silk ground"]),
    dict(id="oriental.ink_wash", group="oriental", name="水墨风",
         summary="墨分五色、宣纸渗化、大面积留白。",
         identity="traditional Chinese ink wash painting",
         medium="raw xuan paper, diluted ink, dry brush",
         materials=["rice paper fibre", "wet ink", "dry brush"],
         composition=["large negative space", "layered distance", "asymmetrical balance"],
         lighting="atmospheric, low contrast", temperature="neutral", contrast="low",
         palette=[("ink black", "#1B1A17"), ("mid ink", "#7A756D"), ("pale ink", "#C2BDB2"),
                  ("xuan", "#EDE4D3"), ("cinnabar", "#9A4A3A")],
         sat=(0.0, 0.15), edge=(0.02, 0.10),
         camera=["dolly_in", "dolly_out", "tracking", "crane", "static"], lens=35, dof="deep",
         motion=["ink diffusion", "mist drift", "water flow"],
         secondary=["branch sway"],
         preserve=["brushwork", "negative space", "paper grain"],
         avoid=["photoreal smoke", "3D volumetric fog", "crisp CGI edges"],
         anchors=["visible xuan paper grain", "brush strokes dissolving into blank paper",
                  "large unpainted areas"]),
    dict(id="artistic.japanese_soft", group="artistic", name="日系小清新",
         summary="明亮、清透、治愈的生活感动画。",
         identity="soft Japanese animated film background",
         medium="hand-painted animation background, pastel palette",
         materials=["gouache background", "soft paper texture", "natural light"],
         composition=["layered environment", "rich atmospheric perspective", "open sky"],
         lighting="bright summer daylight, soft shadows", temperature="warm", contrast="low",
         palette=[("sky blue", "#A8D8EA"), ("leaf green", "#A8C686"), ("soft pink", "#F6C6C9"),
                  ("warm white", "#FFF7E6"), ("dusk violet", "#B7A9C9")],
         sat=(0.05, 0.30), edge=(0.03, 0.12),
         camera=["tracking", "dolly_in", "pan"], lens=35, dof="medium",
         motion=["wind in leaves", "hair sway", "cloud drift"],
         secondary=["water shimmer"],
         preserve=["character design", "soft light"],
         avoid=["heavy contrast", "photoreal skin", "dark palette"],
         anchors=["soft pastel sky", "gentle light with visible atmosphere",
                  "hand-painted background shapes"]),
    dict(id="artistic.surrealism", group="artistic", name="超现实主义",
         summary="梦境、悖论、尺度错位与非欧空间。",
         identity="surrealist dreamscape",
         medium="painterly impossible space, dream logic",
         materials=["smooth paint", "sand", "still water"],
         composition=["impossible scale relationship", "floating objects", "non-euclidean space"],
         lighting="dreamlike directional light", temperature="neutral", contrast="medium",
         palette=[("dusk blue", "#3B4A6B"), ("sand", "#D8C3A5"), ("ember", "#C2543B"),
                  ("pale sky", "#CFE0E8"), ("deep teal", "#1F4E5F")],
         sat=(0.05, 0.40), edge=(0.03, 0.12),
         camera=["orbit", "dolly_in", "crane"], lens=24, dof="deep",
         motion=["floating objects", "space morph", "time reversal"],
         secondary=["cloud drift"],
         preserve=["dream logic", "scale paradox"],
         avoid=["ordinary realism", "cluttered detail", "flat lighting"],
         anchors=["objects floating without support", "impossible scale relationships",
                  "calm dreamlike light"]),
    dict(id="artistic.impasto_oil", group="artistic", name="油画厚涂",
         summary="颜料堆叠、刮刀笔触与画布肌理。",
         identity="impasto oil painting",
         medium="thick oil paint, palette knife, canvas weave",
         materials=["oil paint", "canvas", "palette knife"],
         composition=["strong volume and light", "weighted colour blocks"],
         lighting="directional light revealing paint relief", temperature="warm", contrast="medium",
         palette=[("ochre", "#C08A3E"), ("deep umber", "#5A3E2B"), ("sap green", "#4F6B3A"),
                  ("ivory", "#EFE6D2"), ("crimson", "#8E2F3A")],
         sat=(0.15, 0.50), edge=(0.05, 0.22),
         camera=["dolly_in", "tracking"], lens=85, dof="shallow",
         motion=["paint stroke emergence", "light across ridges"],
         secondary=["canvas grain shift"],
         preserve=["paint relief", "visible knife strokes"],
         avoid=["flat digital shading", "clean vector edges", "photo texture"],
         anchors=["thick raised paint ridges", "visible palette knife strokes", "canvas weave texture"]),
    dict(id="artistic.impressionism", group="artistic", name="印象派",
         summary="瞬间光线、松散笔触与空气感。",
         identity="impressionist painting",
         medium="broken brushwork, light-dappled colour",
         materials=["oil on canvas", "short visible strokes"],
         composition=["outdoor air and light", "soft dissolving forms"],
         lighting="changing natural light", temperature="warm", contrast="medium",
         palette=[("lavender", "#B9A7D6"), ("butter", "#F2D98C"), ("river blue", "#8FB8D9"),
                  ("rose", "#E7A3A8"), ("fresh green", "#9DBF8E")],
         sat=(0.10, 0.45), edge=(0.03, 0.15),
         camera=["pan", "dolly_in"], lens=50, dof="medium",
         motion=["light shift", "water reflection", "leaf shadow"],
         secondary=["cloud drift"],
         preserve=["broken brushwork", "light atmosphere"],
         avoid=["sharp outlines", "flat colour fields", "photo realism"],
         anchors=["short broken brush strokes", "colours shifting with light",
                  "forms dissolving at the edges"]),
    dict(id="artistic.ukiyo_e", group="artistic", name="浮世绘",
         summary="木版套色、平涂色块与清晰轮廓。",
         identity="Japanese ukiyo-e woodblock print",
         medium="woodblock colour, flat pigment, washi paper",
         materials=["washi paper", "woodblock ink", "flat pigment"],
         composition=["flat decorative layout", "clear outline", "strong silhouette"],
         lighting="flat, no realistic shading", temperature="neutral", contrast="medium",
         palette=[("indigo", "#1F3A5F"), ("vermilion", "#C1442E"), ("rice", "#EFE3CC"),
                  ("ochre", "#B98A4A"), ("charcoal", "#2B2B2B")],
         sat=(0.10, 0.40), edge=(0.08, 0.25),
         camera=["tracking", "static", "pan"], lens=50, dof="flat",
         motion=["wave motion", "cloud band drift", "layer parallax"],
         secondary=["figure step"],
         preserve=["flat colour fields", "clear contours", "washi texture"],
         avoid=["photoreal depth of field", "soft gradients", "3D volume"],
         anchors=["flat woodblock colour areas", "clear dark outlines", "visible washi paper texture"]),
]


def dump(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> int:
    for style in STYLES:
        base = BASE / style["group"] / style["id"].split(".")[1]
        dump(base / "style.yaml", {
            "schema_version": "1.0", "id": style["id"], "name": style["name"],
            "group": style["group"], "version": "1.0.0", "status": "SPEC_DRAFT",
            "summary": style["summary"], "layers": ["identity", "execution", "consistency"],
        })
        dump(base / "image_prompt.yaml", {
            "schema_version": "1.0", "identity": style["identity"], "medium": style["medium"],
            "materials": style["materials"], "composition": style["composition"],
            "prompt_order": ["subject", "medium", "composition", "lighting", "material", "camera"],
            "positive_anchors": style["anchors"],
        })
        dump(base / "video_prompt.yaml", {
            "schema_version": "1.0", "motion_vocabulary": style["motion"],
            "secondary_limit": 2, "preserve": style["preserve"], "avoid": style["avoid"],
        })
        dump(base / "camera_profile.yaml", {
            "schema_version": "1.0", "allowed_moves": style["camera"],
            "preferred_lens_mm": style["lens"], "dof_strategy": style["dof"],
        })
        dump(base / "motion_profile.yaml", {
            "schema_version": "1.0", "primary_motions": style["motion"],
            "secondary_motions": style["secondary"], "secondary_limit": 2,
        })
        dump(base / "lighting_profile.yaml", {
            "schema_version": "1.0", "key": style["lighting"],
            "temperature": style["temperature"], "contrast": style["contrast"],
        })
        dump(base / "color_profile.yaml", {
            "schema_version": "1.0",
            "anchors": [{"name": name, "hex": value} for name, value in style["palette"]],
            "saturation_range": list(style["sat"]),
            "edge_density_range": list(style["edge"]), "value_range": [0.1, 0.95],
            "note": "Hex values are for validation only; they never enter a prompt.",
        })
        dump(base / "material_profile.yaml", {
            "schema_version": "1.0", "materials": style["materials"],
            "texture_cues": style["preserve"],
        })
        dump(base / "negative_constraints.yaml", {
            "schema_version": "1.0", "forbidden": style["avoid"],
            "note": "For validator and human checklist only; prompts use positive anchors.",
        })
        board = base / "reference_board"
        board.mkdir(parents=True, exist_ok=True)
        (board / "README.md").write_text(
            f"# {style['name']} 参考板\n\n"
            "需要 12–20 张经人工审核的内部参考图，覆盖六类：\n\n"
            "- 整体风格\n- 色彩\n- 材质\n- 构图\n- 光线\n- 动态（可用短视频或序列帧）\n\n"
            "参考图不进入 Git；只提交 `manifest.json`（文件名、来源、授权、用途）与授权说明。\n"
            "版权分三种场景分别确认：内部研究、模型输入、公开发布。\n",
            encoding="utf-8",
        )
    print(f"wrote {len(STYLES)} style packs under {BASE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
