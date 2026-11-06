# 视觉风格引擎（Visual Style Engine）

> 状态：`DECISION` / 2026-11-06 立项。
> 定位：12 种风格不是 12 组提示词，而是 12 套可独立加载的视觉生产规范。
> 与 `FILM_PRODUCTION_GUIDE.md` 的关系：本文定义「风格」如何约束图像与视频；后者定义「镜头」如何组织成作品。

## 1. 三层架构

| 层 | 回答的问题 | 载体 |
|---|---|---|
| Style Identity | 这是什么视觉流派 | `style.yaml` |
| Style Execution | 图怎么生成、视频怎么运动 | `image_prompt.yaml` / `video_prompt.yaml` / `camera_profile.yaml` / `motion_profile.yaml` / `lighting_profile.yaml` / `color_profile.yaml` / `material_profile.yaml` |
| Style Consistency | 跨镜头是否还是同一部作品 | `negative_constraints.yaml` + 引用参考板 + 一致性检查 |

## 2. Style Pack 目录

```
config/style_packs/<group>/<name>/
├── style.yaml
├── image_prompt.yaml
├── video_prompt.yaml
├── camera_profile.yaml
├── motion_profile.yaml
├── lighting_profile.yaml
├── color_profile.yaml
├── material_profile.yaml
├── negative_constraints.yaml
└── reference_board/README.md
```

新增风格只增加一个目录并注册，**不改核心引擎**。

## 3. 12 种风格

### 复古潮流（retro）

| id | 名称 | 核心 |
|---|---|---|
| `retro.collage` | 拼贴艺术 | 剪贴、撕纸边、层叠、多色彩体系 |
| `retro.synthwave` | 合成波 | 霓虹、网格、80 年代未来主义 |
| `retro.pop_art` | 波普艺术 | 网点、粗黑轮廓、大色块 |
| `retro.y2k` | Y2K 千禧 | 金属、镭射、透明 PVC |

### 东方美学（oriental）

| id | 名称 | 核心 |
|---|---|---|
| `oriental.modern_chinese` | 国风新中式 | 传统元素 + 现代设计、青朱赭黛 |
| `oriental.gongbi` | 工笔国风 | 铁线描、矿物颜料、绢本 |
| `oriental.ink_wash` | 水墨风 | 墨分五色、宣纸、留白 |

### 艺术绘画（artistic）

| id | 名称 | 核心 |
|---|---|---|
| `artistic.japanese_soft` | 日系小清新 | 明亮、清透、治愈、生活感 |
| `artistic.surrealism` | 超现实主义 | 梦境、尺度错位、非欧空间 |
| `artistic.impasto_oil` | 油画厚涂 | 颜料堆叠、刮刀笔触、画布肌理 |
| `artistic.impressionism` | 印象派 | 瞬间光线、松散笔触、空气感 |
| `artistic.ukiyo_e` | 浮世绘 | 木版套色、平涂、清晰轮廓 |

## 4. 双模型约束：风格必须同时作用于 FLUX 与 Wan

只约束关键帧不够。Wan 若使用通用电影提示词，水墨会变成写实云雾、工笔会丢失线描、浮世绘会出现写实景深。

规则：

1. `image_prompt.yaml` 的 identity / medium / material 必须进入关键帧提示词。
2. `video_prompt.yaml` 的 motion vocabulary / preserve 必须进入 Wan 提示词。
3. `camera_profile.yaml` 的运动与景深策略按风格选择；**不是所有风格都适合浅景深**（浮世绘、波普应保持平面化）。
4. 风格禁止项以**正向锚点**表达（FLUX.2/3 无负向条件，CFG 1.0）；`negative_constraints.yaml` 只供校验器与人工清单使用。

## 5. Prompt Compiler

编译顺序固定：

```
Subject → Scene layers → Style Identity → Medium/Material →
Composition → Camera → Lighting → Motion → Continuity → Positive anchors
```

规则：

- 十六进制色值**不进入提示词**，只进入 `color_profile.yaml` 供校验；提示词使用色名与相对描述。
- 同一镜头的人物/服装描述必须逐字复用，不做同义替换。
- 多参考图输入遵循“锚点包”：3–4 张人物、3–4 张场景、2–3 张材质/光线；参考图按位置命名并写明角色。
- 保持单镜头运动主次：1 个主运动 + ≤2 个次要运动。

## 6. 参考板（Reference Board）

每种风格至少需要 12–20 张经人工审核的内部参考样本，覆盖六类：

| 类型 | 用途 |
|---|---|
| 整体风格 | 方向判断 |
| 色彩 | 固定色板 |
| 材质 | 纸张/颜料/金属/塑料 |
| 构图 | 主体与空间关系 |
| 光线 | 明暗与反射 |
| 动态 | 运动方式（可用短视频或序列帧） |

参考素材的版权分三种场景分别确认：内部研究、模型输入、公开发布。三者不自动互相授权。

## 7. 一致性检查

自动层（程序化）：

- 主色与 `color_profile.yaml` 锚点的 LAB 距离。
- 饱和度 / 明度区间。
- 边缘密度 / 高频比例区间（区分线描、平涂、厚涂、水墨）。
- 黑边与画幅检查。
- 相邻镜头的色彩与亮度漂移。

人工层（不可替代）：

- 材质是否保持（宣纸、绢、画布、网点、木版）。
- 笔触/线描是否在运动中消失。
- 是否出现该风格不该有的写实元素。
- 运动是否符合风格（例如水墨不该出现硬边三维烟雾）。

CLIP/嵌入相似度只作筛选，不作为“复刻了工笔/水墨”的证据。

## 8. 项目绑定

每个项目只选一个主风格：

```json
{"visual": {"style_id": "oriental.ink_wash", "style_version": "1.0.0"}}
```

- 期数绑定后冻结；改风格必须新版本，不覆盖历史产物。
- 多风格混合与渐变只允许显式声明权重与使用范围，默认关闭。
- 风格 id 不得写死在代码里；代码只认注册表。

## 9. 开发优先级

| 批次 | 风格 | 验证的技术能力 |
|---|---|---|
| P0 | 新中式、工笔、水墨 | 传统绘画风格的连续性与材质 |
| P1 | 日系、超现实、油画、印象派、浮世绘 | 绘画媒介与运动一致性 |
| P2 | 拼贴、合成波、波普、Y2K | 平面设计、多层合成 |

先做 P0 三种并跑通一部《登鹳雀楼》，再补 P1/P2。

## 10. 本机边界

- 关键帧：FLUX.3 576×1024，约 2–2.5 分钟/张。
- 视频：Wan2.2 TI2V 5B，121 帧约 60–70 分钟/镜。
- 单风格 8 镜短片约 8–10 小时生成，不含重试与审片。
- 参考板图片不进入 Git；只提交 manifest 与授权说明。

## 11. 验收

| 项 | 目标 |
|---|---|
| 风格数量 | 12 种全部可加载、可版本化 |
| 配置 | 每个 Pack 通过 Schema 校验 |
| 提示词 | 每种风格有独立编译规则，且同时覆盖图像与视频 |
| 校验 | 色板/饱和度/边缘/漂移可程序化检查 |
| 项目绑定 | 单主风格 + 冻结；混合需显式声明 |
| 扩展 | 新增第 13 种风格不改核心引擎 |

**12 种风格不是 12 个滤镜，而是 12 套完整的视觉生产规范。**
