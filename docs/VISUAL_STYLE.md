# 09 · 视觉风格引擎与 LoRA 规范指南 (V2.1)

> 状态：`DECISION / APPROVED` (2026-11-18 升级重构)  
> 历史废弃说明：原 23 套纯文本提示词风格包（包含 `advertising` 6 套、`oriental`、`retro`、`artistic` 等，基于 Wishful Prompting / 许愿式开发）全面归档废弃。纯靠 Prompt 堆砌修饰词在量化底模上无法稳定控脸、控材质，且无法排版复杂中文，易导致“大头娃娃”或乱码。新体系转为 **“物理 LoRA 注入 + 分工解耦：AI 负责光影材质与留白底图 + 确定性工程节点负责排版与 VFX 调度”**。

---

## 1. 核心架构：双 LoRA 黄金法则与显存边界

在 8GB 显存安全线（`--profile safe8g`，Intel Arc A750 + FLUX.3 Klein Q4_K_M）下，**最多同时挂载 2 个 LoRA，总权重严格控制在 1.20 ~ 1.40 之间**，实现角色一致性、高级画风与商业质感的稳定平衡。

```text
[UnetLoaderGGUF (FLUX.3 Klein 底模)] 
       │
       ▼
[槽位 A: 角色/主体 LoRA (0.70 ~ 0.80)] ───► 锁定面容骨相、发际线神态 或 核心产品形态 (空镜时置空)
       │
       ▼
[槽位 B: 美学/光影/材质 LoRA (0.45 ~ 0.65)] ─► 注入商业布光、宣纸水墨或特定微观材质 (全片/全系统一)
       │
       ▼
[KSampler (16~20 步, CFG 1.0)] ──────────► 干净视觉底图 (预留排版负空间 Negative Space)
       │
       ▼
[确定性工程层 (Python Pillow / r3_build)] ──► 矢量 Logo、高精度中文排版、网格线与时间轴特效调度
```

### 槽位职责与边界

| 槽位 | 控制目标 | 推荐权重 | 生命周期与触发策略 |
|---|---|---|---|
| **槽位 A：角色/主体 LoRA** | 锁定人物面部骨相神态 或 商业主体结构 | **0.70 ~ 0.80** | 绑定 `character_bible`；仅在主体镜头启用，**风景空镜/纯景深自动置空**以节省显存。 |
| **槽位 B：美学/光影/材质 LoRA** | 注入全片统一的艺术媒介、影棚布光或特定微观材质 | **0.45 ~ 0.65** | 绑定 `style_pack`；作为画风与质感铺底，不抢主体特征。 |
| **构图与留白** | **提示词强制预留负空间** | — | FLUX 原生具备优异的空间理解力，通过 `clean negative space on top/bottom for typography` 约束生成留白。 |

> [!CAUTION] 权重红线与防打架机制
> - **严禁同时挂载 3 个以上 LoRA**：多 LoRA 动态合并会引发 XPU 显存抖动，导致 Out-Of-Memory 或大幅拖慢推理；
> - **总权重上限守门**：$\text{Strength}_{\text{A}} + \text{Strength}_{\text{B}} \le 1.40$。超过上限会导致画面过锐、边缘噪点黑边或塑料假面感。

---

## 2. 广告设计、海报与视觉特效：4 类高价值 LoRA 规范

在商业广告、海报视觉包装场景中，LoRA 仅负责“局部材质、美学光影与特定视觉元素”，严禁用于硬磕排版：

| LoRA 细分类型 | 核心作用与解决痛点 | 典型应用场景 | 推荐权重 |
|---|---|---|---|
| **1. 商业产品摄影棚光影 LoRA**<br>*(Studio Lighting)* | 注入软箱高光、金属拉丝反射、玻璃焦散、暗调奢华光影，彻底消除廉价塑料感。 | 3C 数码、美妆护肤、酒水茶饮、汽车工业主视觉。 | `0.55 ~ 0.70` |
| **2. 平面排版与网格构图 LoRA**<br>*(Poster Layout / Grid)* | 强制画面形成瑞士网格（Swiss Grid）、极简留白（Negative Space）与几何张力。 | 活动主视觉海报（KV）、电商首图、杂志封面底图。 | `0.50 ~ 0.65` |
| **3. 材质与微观肌理 LoRA**<br>*(Material / Macro Texture)* | 精准强化液态水花飞溅（Splash）、磨砂玻璃、丝绸流动、碳纤维等物理微观纹理。 | 饮品飞溅、精华液拉丝质感、微距工业细节。 | `0.50 ~ 0.65` |
| **4. 粒子与能量特效 LoRA**<br>*(VFX / Particle / Elemental)* | 生成金色粒子流、烟雾弥漫、雷电火焰、赛博全息光斑等非实体视觉元素。 | 国风片头包装、高燃转场背景、发布会宣传底图。 | `0.55 ~ 0.75` |

---

## 3. 必须纠偏：海报与特效中“绝对不要指望 LoRA”的 3 件事

在商业广告与影视后期工作流中，以下 3 个环节若依赖 LoRA 属于严重的工程错配，必须由外部确定性节点接管：

### 1. 商业海报的“精准中文与多行文案排版” → 交给 Python Pillow / HTML 渲染层
- **事实**：FLUX 原生对简单英文短词尚可理解，但对**复杂中文汉字、小字号价格标签、多行文案**必然产生笔画粘连或乱码；
- **确定性工程解**：
  1. AI 层（FLUX + 构图 LoRA）仅负责生成**带干净负空间（Negative Space）的高质感纯图**；
  2. 确定性排版层（Python `PIL.ImageDraw` / SVG / Remotion）读取设计系统模板，将矢量 Logo、中文标题（思源黑体/等线）、副标题、英文注解精准叠加上去，实现**100% 零乱码、可批量替换文案**。

### 2. 具体商业产品的“Logo 与工业结构 100% 还原” → 交给 ControlNet 或后期贴图
- **事实**：通用“产品摄影 LoRA”会擅自修改特定品牌耳机的转轴弧度、化妆品瓶身专属凹槽或 Logo 字母；
- **确定性工程解**：通过真实白底产品图提取 ControlNet Canny/Depth 边缘约束，或先用 AI 生成影棚光影背景，再通过 Alpha 遮罩将真实产品合成融入。

### 3. “视觉特效调度（VFX Scheduling）” → 属于时间轴引擎，不属于静态 LoRA
- **事实**：LoRA 是静态权重补丁，无法控制时间轴上“第 1.5 秒震屏 + 粒子爆发 + 字幕卡点”的时序调度；
- **确定性工程解**：
  1. **动态素材层**：利用特效 LoRA 批量出黑底粒子/火焰图，或程序化生成透明序列帧；
  2. **时序调度层**：在 `storyboard.json` 中配置 VFX 事件轨道，由 `r3_build` 调用 FFmpeg `filter_complex`（`screen/add` 混合模式、震屏、闪白、色散）按毫秒级音频节拍完成精确合成。

---

## 4. 人物画幅与防“大头娃娃”解剖学规范

在古典人物（如林黛玉、薛宝钗等闺秀角色）生成中，为杜绝二次元平涂导致的“大头娃娃（Chibi/Doll）”与窄肩失真，确立以下硬性解剖学约束：

```text
❌ 严禁引入的致畸关键词与 LoRA：
- 关键词禁令：anime girl, chibi, oversized eyes, baby face, cute doll, 3d figurine, shoujo manga
- LoRA 禁令：严禁在写实/半写实古风人物上叠加日系赛璐璐/少女漫平涂 LoRA (如 chinese_manhua_v1)

✅ 必须注入的解剖与构图锚点：
- 景别约束：waist-up portrait, medium shot (半身/中景，严禁面部大特写 headshot)
- 比例约束：natural adult bone structure, proportional head-to-shoulder ratio, graceful natural shoulders, realistic anatomical features
- 姿态构图：three-quarter profile view, looking gracefully to the side, leaning near carved lattice window
```

---

## 5. 工作流文件与调用规范

- **单 LoRA 基础工作流**：[workflows/flux3_lora_t2i_api.json](file:///d:/Local-Drama-Studio/workflows/flux3_lora_t2i_api.json)
- **双 LoRA 组合工作流**：[workflows/flux3_dual_lora_t2i_api.json](file:///d:/Local-Drama-Studio/workflows/flux3_dual_lora_t2i_api.json)
- **排版合成引擎**：[scripts/r4_poster_typeset.py](file:///d:/Local-Drama-Studio/scripts/r4_poster_typeset.py)
