# 09 · VISUAL_STYLE_SPEC — 双核心东方美学规范

> 文档状态：`DECISION`（S1 规范落地，2026-11-03）。
> 本文件是产品两种核心视觉风格的唯一规范来源；可执行配置见 `config/styles.yaml`，校验与导出见 `src/drama_studio/style_presets.py`。
> 能力状态使用 `docs/PRD.md` §0.2 词典。**规范存在不等于已经生成、验证或进入成片。**

## 0. 定位与边界

产品视觉方向从本文件起收敛为**两种核心美学**，不再以增加风格数量为发展方向：

| id | 风格 | 一句话定位 |
|---|---|---|
| `court_green_fine_line` | 宋代院体青绿工笔 | 让宋代画卷以细腻、克制的方式动起来 |
| `ink_wash` | 东方写意水墨 | 让墨色、留白和意境在时间中自然流动 |

规则：

1. Drama Studio 仍是通用内容生产系统。两种风格是**系统支持的核心视觉配置**，不是某一首诗、某一幅画或某一部作品的专用程序。
2. 两种风格共享同一套数据契约、调度、生成、配音、字幕、合成与质量门；不建设两套生产架构。
3. 作品通过配置选择风格（`style id` + 期数 `style_snapshot`），不改业务代码。
4. 当前不预设第三种或第四种风格。新增风格必须另立阶段，并先证明现有两种仍可稳定生产。
5. 本文档不写具体作品的剧情、分镜或台词；风格提示词只描述视觉语言。

### 0.1 与既有文档的关系

| 内容 | 权威文档 |
|---|---|
| 产品定位、范围、验收 | `docs/PRD.md` |
| 视觉/声音/字幕/母版通用规范 | `docs/CONTENT_SPEC.md` |
| **两种核心风格的差异与动画路线** | 本文件 |
| 风格配置字段 | `config/styles.yaml` + `style_presets.py` |
| 实测性能与模型限制 | `docs/TECH_STACK.md`、`docs/R2_TEST_REPORT.md`、`docs/R3_TEST_REPORT.md` |

`docs/CONTENT_SPEC.md` §2 的色板与镜头语言是 R1 建立的水墨/自然纪实基线，对应水墨管线（管线 A）的近似方向；工笔管线（管线 B）的色板与细节要求以本文件为准。

---

## 1. 两种风格的共享与差异

管线命名（2026-11-03 起，避免与阶段编号混淆）：

| 管线 | 风格 | 风格 id |
|---|---|---|
| 管线 A | 东方写意水墨 | `ink_wash` |
| 管线 B | 宋代院体青绿工笔 | `court_green_fine_line` |

两条管线共享底层设施（ComfyUI、FLUX/Wan、FFmpeg、调度、存储、日志），但提示词、静态质量检查表、素材分层与动画策略相互独立；不得合并成一个大提示词再靠少量参数切换。

| 配置类别 | 院体青绿工笔 | 写意水墨 | 配置字段 |
|---|---|---|---|
| 画面材质 | 绢本、细腻纸本 | 生宣、纸本 | `material.kind` / `material.prompt` |
| 主色调 | 石青、石绿、赭石、泥金 | 墨黑、灰、少量赭石与淡彩 | `color_palette` |
| 线条 | 细密、清晰、结构明确 | 概括、虚实变化 | `line.style` / `line.prompt` |
| 画面细节 | 高 | 适度，允许抽象 | `detail.level` / `detail.prompt` |
| 构图 | 山水层次、长卷、院体秩序 | 留白、虚实、意境 | `composition` |
| 主要运动 | 长卷横移、缓慢推近 | 墨迹渗染、雾气、水流 | `motion.primary` |
| 局部微动 | 飞鸟、云雾、水面、枝叶 | 墨迹、云烟、飞鸟、水面 | `motion.local` |
| 主要合成 | 纹理、分层、视差、运镜 | 灰度遮罩、墨迹扩散、叠加 | `compositing.primitives` |

共同约束：

- 帧率 24 fps，母版 1080×1920。
- 相机运动以固定、缓慢横移、缓慢推近为主；禁止快速摇镜与手持晃动。
- 不把单张图片的平移宣称为 2.5D 视差；没有可靠分层或深度图时不得使用。
- 不依赖 Wan 完成主体位移或复杂人物动作（R2-B H3 已证明不可靠）。

---

## 2. 管线 B · 宋代院体青绿工笔（`court_green_fine_line`）

### 2.1 审美方向

宋代院体绘画、青绿山水与工笔花鸟的公共审美范式。方向参考（只用于人工判断，不写入生成提示词）：宋代青绿长卷、院体花鸟与楼阁界画。

### 2.2 视觉要求

1. **材质**：绢本质感，细密绢纹、纸本肌理与适度历史沉淀感；不得做成塑料或照片质感。
2. **设色**：石青、石绿、赭石、泥金等传统矿物色；色板见 `color_palette`，不得高饱和青橙调色。
3. **线条**：游丝描、铁线描一类的细密、克制、清晰线条；轮廓结构明确。
4. **构图**：空间层次与远近关系清楚；近景—中景—远景三层；地平线不居中。
5. **细节**：建筑、树木、山石、人物、花鸟具有相对明确的结构与细节。
6. **留白**：克制使用，保留空间呼吸感；不追求满屏堆砌。
7. **运动**：长卷横移、缓慢推近、局部景物微动；不追求现代影视式大幅镜头运动。

### 2.3 提示词落点

`visual_language` 与 `positive_prompt` 必须自包含材质、线条、细节与构图要求（当前生成链路只消费这两个字段）。`material` / `line` / `detail` 是审计字段，不单独拼接。

核心目标：画面具有宋代院体绘画的精致、秩序与细节，并通过适度运镜让静态画卷产生生命感。

### 2.4 禁止项

- 现代建筑、电线、霓虹、塑料/金属质感、游戏 CG 发光粒子。
- 照片写实、过度磨皮、整体过曝。
- 快速摇镜、手持晃动、为运动而运动。
- 让 Wan 承担人物动作或精确主体位移。

### 2.5 工笔静态缺陷检查（进入动画前）

| 检查项目 | 主要问题 |
|---|---|
| 线条 | 断裂、粗细机械、结构错乱 |
| 建筑 | 透视错误、屋顶和结构变形 |
| 山石 | 重复纹理、设色溢出 |
| 水纹 | 机械同心圆、规则闭合环线、数字矢量感 |
| 树木 | 枝干逻辑错误、重复树冠 |
| 人物 | 五官、服饰、比例异常 |
| 花鸟 | 结构错误、细节混乱 |
| 色彩 | 荧光感、过度饱和、数字渐变 |
| 材质 | 塑料感、过重纹理 |
| 整体 | 细节堆砌、缺少传统画面秩序 |

规则：发现明显缺陷先局部修复或重生成，不直接把有问题的图送入 I2V；当前没有局部 inpaint 工作流，修复手段限于重生、换 seed、调整提示词或裁切。检查记录写入 `static_quality.json`，不能只凭“模型成功出图”判定通过。

### 2.6 S2-工笔 验收标准

在 15-30 秒验证片段上检查：

- 绢本/纸本纹理可见但不过噪，主体线条与细节未被纹理压过。
- 色板落在本风格 `color_palette` 范围内；无高饱和偏色。
- 至少一段长卷横移；横移稳定，无抖动、无拉伸、无结构破坏。
- 首帧、中帧、末帧各抽样检查；全片解码退出码 0；无黑帧。
- 1080×1920 / 24 fps / H.264；时长 15-30 秒。
- 人工看片结论单独记录，不因技术检查通过而自动通过。

---

## 3. 管线 A · 东方写意水墨（`ink_wash`）

### 3.1 审美方向

传统中国山水水墨画的公共审美范式：生宣纸上的墨色渗化、水分扩散、墨色流动与留白。方向参考（只用于人工判断，不写入生成提示词）：传统水墨山水长卷与水墨动画的空气感。

### 3.2 视觉要求

1. **材质**：生宣、熟宣及纸本肌理；墨迹在纤维上自然洇开。
2. **墨色**：墨分五色，浓淡、干湿、虚实有层次。
3. **渗染**：墨迹自然扩散、晕染、叠加，边缘有变化。
4. **留白**：留白是构图的一部分，不是空白背景。
5. **形态**：不要求所有物体边缘清晰，允许局部虚化、概括和抽象。
6. **色彩**：以墨黑灰为主，可少量使用赭石、淡花青等辅助色。
7. **运动**：以墨迹扩散、雾气、水面、云烟、飞鸟等局部变化为主。

### 3.3 提示词落点

`visual_language` 与 `positive_prompt` 必须明确写出“生宣、墨分五色、自然渗化、留白、非黑白滤镜”。仅在普通图片上叠加黑白或水墨滤镜不算达成目标。

### 3.4 禁止项

- 黑白滤镜式处理、阈值化硬边缘、矢量插画感。
- 满屏实景、没有留白、所有边缘都清晰。
- 以 Wan 生成复杂人物动作或主体位移。
- 用亮度直方图“看起来像水墨”代替人工判断。

### 3.5 水墨静态缺陷检查（进入动画前）

| 检查项目 | 主要问题 |
|---|---|
| 飞鸟 | 排列机械、形态错误、数量不合理 |
| 山石 | 皴法重复、纹理条纹化 |
| 树木 | 树冠重复、枝干结构不自然 |
| 水面 | 缺少纸性、数字渐变明显 |
| 倒影 | 透视不合理、镜像过于机械 |
| 云烟 | 轮廓过硬、与山体脱节 |
| 远景 | 过度锐化、缺乏虚实变化 |
| 整体材质 | 塑料感、数码感、纹理覆盖过重 |
| 构图 | 留白不足、主体拥挤、空间层次混乱 |

规则同工笔：明显缺陷先修复；没有局部 inpaint 时通过重生/换 seed/调提示词处理；检查记录写入 `static_quality.json`。

### 3.6 S2-水墨 验收标准

在 15-30 秒验证片段上检查：

- 墨色至少可分为 4 个可区分的浓淡层次（抽样帧灰度分布 + 人工确认）。
- 宣纸纹理存在但不影响主体可读性；留白占构图的可辨认比例。
- 至少一次墨迹显现/渗染转场；遮罩边缘柔化，无单帧硬边。
- 局部动态（雾、水、飞鸟、墨迹）自然，无主体结构变形。
- 首帧、中帧、末帧各抽样检查；全片解码退出码 0；无黑帧。
- 1080×1920 / 24 fps / H.264；时长 15-30 秒。
- 人工看片结论单独记录。

---

## 4. 配置边界

### 4.1 唯一配置来源

`config/styles.yaml` 定义两个预设。字段分三层：

| 层 | 字段 | 是否写入 `workspace.db` | 当前消费方 |
|---|---|---|---|
| 生成层 | `visual_language`、`positive_prompt`、`negative_prompt` | 是（`styles` 实体与期数快照） | `script.generate` → `script_engine.compose_visual_prompt` |
| 审计层 | `material`、`line`、`detail`、`color_palette`、`lighting`、`camera_language`、`composition`、`character_design`、`environment_design` | 是（结构化字段与色板） | 人工核对与工作台展示；不单独进入提示词 |
| 动画/合成层 | `motion`、`compositing` | 否 | `drama_studio.motion`：镜头运动、局部微动、转场；2026-11-04 已接入生产链路 |
| 美学设计层 | `aesthetic_profile` | 否 | `drama_studio.aesthetics`：六维设计、A/B 变体、Prompt 编译；2026-11-04 已接入 |

`STYLE_ENTITY_FIELDS` 必须与 `workspace.store.STYLE_FIELDS` 完全一致，由测试保证；配置层独有字段不得混入 SQLite。

### 4.2 选择风格的方式

1. 预设定义在 `config/styles.yaml`，id 稳定：`court_green_fine_line`、`ink_wash`。
2. 需要把预设落成工作台风格实体时，显式导出：

   ```powershell
   .venv\Scripts\python.exe -m drama_studio.style_presets
   .venv\Scripts\python.exe -m drama_studio.style_presets --id ink_wash --entity
   ```

3. 通过工作台/API 用该 payload 创建 `styles` 实体，并在期数上绑定；绑定即冻结 `style_snapshot`。当前 Web API 的创建入口不接收自定义 style id，会分配 `style_<time>_<hex>`；若需要保留预设 id，走 `WorkspaceStore.create_style({"id": ..., **payload})`，或等 S3 接入任务入口时补齐。无论哪种方式，期数快照都保存完整的预设字段。
4. `script.generate` 使用期数快照，不使用代码常量，也不读取 `assets/visual_style/` 的历史实验文件。

**不自动导入**：工作台启动时不会把预设写入 `projects/workspace.db`。数据库只保存用户创建的事实（PRD §4.4、§6.3）。

### 4.3 变更控制

- 修改预设提示词或字段必须同时更新本文件与 `config/styles.yaml`，并重新跑一次静态测试。
- 一旦某期绑定了快照，后续修改全局预设不得改变该期；需要换风格时显式重新绑定并写新快照。
- 不引用不存在的参考资产或来源文件；`load_style_presets()` 会校验路径。
- 不把具体作品名、作者名、诗词句子写入 `config/styles.yaml`、通用代码或测试。

### 4.4 明确不做

- 不引入插件系统、风格 DSL、工作流引擎或第二套配置体系。
- 不为每种风格复制工作流 JSON 或 FFmpeg 命令。
- 不新增 LoRA、模型或大量风格参数；先证明现有 FLUX/Wan 能力边界。
- 不在代码里写 `if style == "..."`。

---

## 5. 视觉生产技术路线

### 5.1 图像生成（沿用 FLUX）

- 引擎与工作流不变：ComfyUI + FLUX.2 klein 4B GGUF，API 格式工作流，占位符按 JSON 树替换。
- 竖屏静帧 576×1024（R3-A 已验证）；16:9 实验 768×432（R1 已验证）。
- 风格差异通过 `visual_language` + `positive_prompt` + `negative_prompt` 实现；参考图条件使用现有 `ReferenceLatent` 工作流，不新增模型。
- 每次生成保留 prompt、seed、模型/工作流哈希、尺寸、耗时与输出哈希。

### 5.2 视频生成（Wan 只做局部补充）

- Wan2.2 TI2V 5B，20 步，`uni_pc/simple`，CFG 5，分辨率可被 32 整除，默认 73 帧（3.04 秒）。
- 只用于云雾、水面、飞鸟、花瓣、墨迹等局部动态；**不承担**人物动作、精确主体位移或长镜头连续运动。
- 不是每个镜头都必须经过 Wan。静帧 + 确定性动画是默认路线。
- 不为使用视频模型而牺牲画面质量或跨帧一致性；Wan 失败时退回静帧 + 确定性动画并记录降级。

### 5.3 确定性动画能力

以下能力是 S2 与首批管线验证的重点。A–D、云气/水面/孤舟图层、局部微动与转场已在实验/生产链路真实执行（技术通过，人工审美待审）；E（线描显现）与 2.5D 尚未执行；Wan 局部动态未在本轮执行。

| 代号 | 能力 | 目标 | 实现方向（FFmpeg 优先） | 状态 |
|---|---|---|---|---|
| A | Scroll Pan 长卷横移 | 模拟长卷展开，横向缓慢移动 + 局部推近 | 源图宽于输出，`crop` 窗口随时间平移；必要时叠加轻微缩放 | `PARTIAL`（S2-工笔） |
| B | Ink Matte 水墨遮罩 | 灰度遮罩控制画面显现，边缘柔化、渐进变化 | 灰度遮罩 + `alphamerge` + `overlay`（`maskedmerge` 会混色度，已排除）+ `gblur` 柔化 | `PARTIAL`（S2-水墨） |
| C | Ink Diffusion 墨迹渗染 | 墨色扩散、叠墨、边缘自然变化 | 噪声/湍流遮罩随时间扩展 + 模糊 + 曲线控制，不使用二值阈值 | `PARTIAL`（S2-水墨） |
| D | Paper Texture 纸本纹理 | 绢本/宣纸纹理叠加，强度克制 | 纹理图 `blend`/`overlay` 低不透明度叠加 | `PARTIAL`（S2-工笔/水墨） |
| E | Line Reveal 线描显现 | 线稿或边缘逐步显现，服务工笔 | 底图边缘提取生成遮罩，随时间推进显现；必须与底图对齐 | `NOT_RUN` |
| F | Local Motion 局部微动 | 云雾、流水、植物、飞鸟、花瓣、墨迹 | 确定性图层 + FFmpeg overlay/alphamerge；Wan 只作补充 | `PARTIAL`（水面/植物/云雾/墨迹已执行；花瓣/飞鸟需独立 RGBA 素材） |
| G | Cloud Motion 云气横移 | 山腰云气独立层缓慢横移，山体冻结 | 模糊亮度遮罩生成云层，图层平移 ±24 px/14 s | `PARTIAL`（管线 A） |
| H | Water Motion 水面微动 | 仅水面极弱位移，保持倒影逻辑 | 水面图层 ±4 px/8 s，排除舟体包围盒 | `PARTIAL`（管线 A） |
| I | Boat Micro-move 孤舟微移 | 极慢、极小的关键帧位移 | 羽化舟体贴片平移 8 px/20 s + ±1.5 px 起伏 | `PARTIAL`（管线 A） |
| J | Layering 分层 | 云/水/舟/主体独立图层 | 每样片 `layers.json` 手工定义；不是通用分割模型 | `PARTIAL`（管线 A） |
| — | 2.5D Parallax | 分层视差 | 推拉用径向缩放、横移用平移窗口 + 逐层 1/α；参数见 `config/styles.yaml` `compositing.parallax` | `PARTIAL`（两风格各一镜技术通过，人工待审） |
| — | Slow push-in | 缓慢推近 | 现有 `zoompan`，R3 已使用 | `PASS_VERIFIED`（R3；S2-水墨 复用） |

### 5.3.1 S2 动态升级（2026-11-04）

在 S2 已验证的横移/遮罩/纸纹之上，新增并接入生产链路：

- **镜头运动**：`static / slow_push_in / slow_pull_out / scroll_pan / push_in_with_pan / slow_lateral_track`，支持三次缓动、焦点、起止缩放、方向；参数由 `motion.camera` 决定，结果写入 `motion_manifest.json`。
- **2026-11-04 A/B 基线**：`config/styles.yaml` 的 `production_baselines` 记录工笔 `shot_001=A/shot_002=A`、水墨 `shot_001=B/shot_002=A`，含完整 prompt、sha256 与人工理由。
- **局部微动**：`water_ripple / cloud_drift / leaf_sway / reed_sway / ink_diffusion / reflection_distortion`；每个图层必须有显式区域与排除框，静态结构带差值可独立检查。
- **Wan 运动遮罩（2026-11-04，M5）**：项目 Wan2.2 TI2V 5B 工作流没有 `mask` / `motion_mask` 输入；`Wan22ImageToVideoLatent` 的内部 `noise_mask` 只作用于起始图，不是空间运动遮罩。M5 = `NOT_RUN (UNSUPPORTED_WORKFLOW)`，Wan 不得宣称主体保护或运动遮罩；主力管线保持“静态首帧 + 确定性局部微动”。详见 [`M5_WAN_MOTION_MASK_REPORT.md`](M5_WAN_MOTION_MASK_REPORT.md)。
- **声学层谐音替换（2026-11-04，M6）**：`source_text / display_text / tts_text / acoustic_text` 四层分离；只为已确认的 G2P 缺口配置 `tts_alias`，只改 `acoustic_text`，字幕与原文逐字不变；5 条谐音（碣石/潇湘/扁舟/似霰/青枫浦）已完成音频验证与人工复核，状态为 `verified`；ASR 用拼音 TONE3 编辑距离判定，全篇 18/18、探针 12/12。2026-11-04 人工听感驳回 2/2/3 硬切与 220 ms 数字静音后，改为整句/整联推理 + 破折号气口，行间停顿 800–1000 ms；不再生成段级 WAV。详见 [`M6_PRONUNCIATION_REPORT.md`](M6_PRONUNCIATION_REPORT.md)。
- **转场时间轴（2026-11-04，M4）**：转场左侧从上一镜头的尾部 handle 截取（`left_start > 0`），不再从 0 重放开头；`body + transition + body` 的总时长按帧量化并断言等于 plan total；水墨转场固定使用 `alphamerge + overlay`，禁止 `maskedmerge`；转场前后做 ΔE/色度差异检查，跨风格时在 manifest 预警。时序门禁接受 transition manifest，在已声明转场/切点处豁免帧间跳变。详见 [`M4_TRANSITIONS_REPORT.md`](M4_TRANSITIONS_REPORT.md)。
- **渲染顺序（2026-11-04，M3）**：固定为“源图比例中间画布 → 局部图层合成 → 相机裁切/缩放 → 纸纹”；遮罩与主体经过同一相机变换，非 9:16 源图不再被强制拉成 540×960。门禁：`check_rigid_protection`（锁定区域多帧差 + 边缘漂移）与 `check_temporal_continuity`（帧间突变、尾部变暗、频闪），详见 [`M3_QUALITY_GATES_REPORT.md`](M3_QUALITY_GATES_REPORT.md)。
- **局部运动算法（2026-11-04，M2）**：水面改为透视衰减的低频行波 + 网格位移；倒影只做纵向、绑定水面相位并加纵向拖尾；植物按 Y 轴非线性权重、根部严格 0；云雾改为平滑流动噪声，取消整层平移与透明度振荡。参数全部在 `config/styles.yaml` 的 `motion.local_policy`（`wavelength_px`、`vertical_ratio`、`perspective_far_scale`、`reflection_ratio`、`reflection_lag_s`、`smear_px`、`sway_exponent`、`top_decay`）。详见 [`M2_MOTION_ALGORITHMS_REPORT.md`](M2_MOTION_ALGORITHMS_REPORT.md)。
- **区域语义与权限（2026-11-04，M1）**：`motion_regions.json` 的镜头条目可写 `{regions, layers}`。角色为 `rigid_object / fluid_surface / reflection / vegetation / atmosphere / background / independent_overlay`，权限为 `locked / hard_excluded / controlled / allowed`。`locked/hard_excluded` 区域会从所有与其相交的局部图层中自动扣除；`reflection` 必须 `follows` 一个 `rigid_object`，且只能使用 `reflection_distortion`；非倒影层会自动排除倒影区域；扣除后 alpha 覆盖率低于 0.2% 时该图层被拒绝并记录原因。旧格式（镜头 → 图层列表）仍可读取，但标记为 `legacy`，不提供主体保护。详见 [`M1_REGION_PROTECTION_REPORT.md`](M1_REGION_PROTECTION_REPORT.md)。
- **转场**：`crossfade / ink_dissolve / ink_reveal / ink_spread`；水墨转场使用距离场 + 噪声遮罩，无二值阈值；转场只消耗上一镜头尾部 handle，序列总时长不变。
- **风格隔离**：两种风格的运动策略、局部类型、转场类型均在各自 `motion` 配置中声明；通用代码不写 `if style == ...`。

实测证据与逐项状态见 [`MOTION_VOICE_UPGRADE_REPORT.md`](MOTION_VOICE_UPGRADE_REPORT.md)。人工看片前，相关能力一律 `PARTIAL`。

质量原则：

- 墨水遮罩与渗染必须避免硬边缘；宁可降低幅度，也不做阈值化效果。
- 纸纹是辅助层，不得改变主体色彩与可读性。
- 线描显现不得出现与底图错位的“PPT 叠加”，也不宣传为真实绘画过程模拟。
- 局部动态必须限制运动范围，避免主体结构变形。

### 5.3.2 镜头美学设计（2026-11-04）

每个镜头在 FLUX 之前拥有六维规格：构图、光影、色彩、空间、场景设计、视觉叙事。共享数据结构，风格差异来自各自的 `aesthetic_profile`；通用代码不写 `if style == ...`。

- **构图**：景别、视角、主体位置、重心、前景遮挡、引导线、留白、分层、疏密、安全区；策略可组合三分法/中心/对称/框景/对角线/留白/纵深/宏大/边角/高远/深远/平远/散点/虚实相生。
- **光影**：主光、方向、光质、强度、反差、轮廓光、环境光、反射、空气透视、雾中散射、时间天气；不把丁达尔/金光/轮廓光当默认。
- **色彩**：主色/辅助色/点缀色、冷暖、饱和、明度、连续性组、风格范围；自动检查只给 LAB 距离/饱和度风险，不判定审美。
- **空间**：前中远景、遮挡、空气透视、虚实、引导、是否有可靠图层；没有图层就不声称 2.5D。
- **场景设计**：时代、建筑形制、构件、自然、服饰、器物、姿态、文化语境、物体关系；历史文化准确性与艺术质量分开检查。
- **视觉叙事**：叙事目的、情绪目标、视觉主体、焦点、进入点、视线路径、前后镜头衔接、节奏。

**A/B 候选**：同一镜头生成两版，除一个维度外其余逐字段相同（Pydantic 不变量强制）。生成后写联系表与风险指标，最终结论留给人工。

**Prompt 编译**：主体/关系 → 构图 → 环境空间 → 光线 → 色彩 → 风格 → 材质 → 正向约束。当前 FLUX.2 工作流把负向条件 `ConditioningZeroOut` 且 CFG=1.0，负向提示词不作为控制，改用正向约束并在 provenance 中记录 `negative_supported=false`。

**冻结**：每次生成写新的 `snapshot-<时间>/`，保存设计、编译 Prompt、参数、工作流/风格哈希；不覆盖旧版本。

状态：数据结构与编译 `PASS_STATIC`；真实 A/B 生成、静态/动态风险检查 `PARTIAL`；人工审美 `PENDING_HUMAN_REVIEW`。证据见 [`AESTHETIC_DESIGN_REPORT.md`](AESTHETIC_DESIGN_REPORT.md)。

### 5.4 合成与母版

- 沿用 `scripts/r3_build.py` 的 FFmpeg 链路：分段 → 拼接 → 混音 → 字幕 → 1080×1920 母版 → manifest/解码校验。
- 新增动画原语应作为现有合成模块内的分段构建方式扩展，不另起动画框架，不引入 Node/Remotion/MoviePy。
- 每个构建写入独立目录，不覆盖历史成片；manifest 记录输入、参数、哈希与 ffprobe/解码结果。
- 1080×1920 仍由 576×1024 源经 Lanczos 放大，不冒充原生 1080p。

---

## 6. 硬件与资源约束

- Intel i7-13700K / 64 GB DDR5 / Intel Arc A750 8 GB；不以下一代显卡为前提。
- GPU 租户互斥：FLUX、Wan、GPU 模式 LLM 不同时运行；同一时间一个生成任务。
- 视频模型只承担必要的局部动态；优先保证静帧质量与确定性动画。
- 不提前承诺 2K/4K/60 fps 或特定生成耗时；所有性能结论以本机日志、参数与资源监测为依据。
- 多模态上下文按现有 64K 上限规划，超长上下文不是默认方案。

---

## 7. 实施阶段与状态

### S1 · 双风格规范落地（本轮）

| 项 | 状态 | 证据 |
|---|---|---|
| 两种风格写入正式规范 | `PASS_STATIC` | 本文件 |
| 配置预设 `config/styles.yaml` | `PASS_STATIC` | 严格 Pydantic 加载；id/字段/路径校验；测试 |
| 配置与工作台风格实体字段对齐 | `PASS_STATIC` | `STYLE_ENTITY_FIELDS` == `workspace.store.STYLE_FIELDS` 测试 |
| 两种风格真实生成 | `PARTIAL` | 水墨 4 张候选（选用 IA4）+ 工笔 1 张；无批量样本 |

### S2 · 视觉技术验证（2026-11-03 已执行，待人工看片）

分别完成两个独立片段，先验证技术栈能否达到目标，再谈完整生产。执行结果见 [`S2_TEST_REPORT.md`](S2_TEST_REPORT.md)。

| 项 | 状态 | 证据 |
|---|---|---|
| S2-工笔 20 s 长卷片段 | `PARTIAL` | `experiments/s2a/renders/build-20261103-210443/`；横移/纹理/解码/黑帧/抽样帧技术通过，人工审美 PENDING |
| S2-水墨 20 s 显现片段 | `PARTIAL` | `experiments/s2b/renders/build-20261103-210408/`；柔边遮罩/渗染/纸纹/留白/解码/黑帧/抽样帧技术通过，人工审美 PENDING |
| 管线 A 水墨分层样片（20 s） | `PARTIAL` | `experiments/pipeline_a/renders/build-20261103-212100/`；云气/水面/孤舟/纸纹技术通过，静态门 `PARTIAL`（山石），人工 PENDING |
| 管线 B 工笔长卷样片（28 s） | `PARTIAL` | `experiments/pipeline_b/renders/build-20261103-212022/`；30 px/s 横移，静态门 `PARTIAL`（山石），人工 PENDING |
| Wan 局部动态 | `NOT_RUN` | 本轮刻意只用静帧 + 确定性动画 |
| 线描显现 / 2.5D | `NOT_RUN` | 未实现 |

首批管线验证的完整记录见 [`PIPELINE_AB_VALIDATION.md`](PIPELINE_AB_VALIDATION.md)。

片段与证据要求（两段相同）：

- 产物路径、`ffprobe` 输出、全片解码退出码、抽样帧（首/中/末）与人工看片结论。
- 生成参数、seed、模型/工作流哈希。
- 片段放在新目录（`experiments/s2a/`、`experiments/s2b/`），不覆盖既有实验与成片。
- 未达标的项保持 `PARTIAL`/`NOT_RUN`，不得写成 `PASS_VERIFIED`。
- 人工看片通过后才能把对应项升为 `PASS_VERIFIED`；不通过则记录问题并重跑。

约束：

- 不新增模型、LoRA 或依赖；先验证现有 FLUX/Wan/FFmpeg。
- 如果某类动画无法达到目标，应缩小效果范围或改用更简单的镜头设计，而不是引入新框架。
- S2 用于确认能力边界，不直接扩展成新的生产子系统。

### S2+ · 动态与声音能力（2026-11-04 已执行，待人工看片）

| 项 | 状态 | 证据 |
|---|---|---|
| 缓动镜头运动（推/拉/横移/推近带横移） | `PARTIAL` | `experiments/mv/renders/build-20261104-003418/`；参数与首中末帧 |
| 局部微动（水/植物/云雾/墨迹） | `PARTIAL` | P1 `motion/build-20261104-005126/`；静态结构带 0.0014–0.0633/255 |
| 四种转场 | `PARTIAL` | `experiments/mv/transition/build-20261104-004956/`；无黑帧、时长准确 |
| 双风格 E2E | `PARTIAL` | `experiments/mv/e2e_ink_wash/`、`experiments/mv/e2e_court_green_fine_line/`；画质 PASS，人工 PENDING |
| 标准朗诵 / 古典吟诵 | `PARTIAL` | `experiments/mv/e2e_*/work/`、`experiments/mv/voice_modes/work/`；ASR 辅助 |
| 真正吟唱 | `NOT_RUN`（不支持） | 接口无音高/旋律控制 |

### S3 · 接入完整生产链路

前置：S2 两种风格均达到验收。

- S3 不再用单一状态概括，按三件事分别评价：
  1. **独立规范与配置**：`PASS_STATIC`（本文件 + `config/styles.yaml` + 测试）。
  2. **每种风格的技术生产验证**：`PASS_VERIFIED`（技术样片）——2026-11-04 两套 2 镜头夹具走通 `motion.plan → motion.render → segments(sequence) → r3_build → quality`，两种风格画质 PASS；M7 记录人工审片。M7 只证明各风格有一个 2 镜头技术样片，不等于完整作品跨镜头一致性。
  3. **作品级风格锁定 + 跨镜头一致性**：锁定机制 `PARTIAL`；正式跨镜头一致性验证 `NOT_RUN`。当前期数有 `style_id/style_snapshot`、`ProductionScript` 有 `style_id/style_sha256`，但 `motion.plan`/`aesthetic.plan` 可 `--style` 覆盖，`comfy.batch` 不校验，DB 风格与 YAML preset 脱节，改风格直接替换 snapshot，无跨镜头风格门。
- 两种风格都必须**通过配置选择**，不能靠改代码切换。
- 同一期数在绑定风格后冻结快照；不同风格生成不同提示词且可追溯。
- 成片满足 PRD §20 的产品级验收（1080×1920、字幕、manifest、不覆盖历史、授权可查）。

---

## 8. 状态矩阵

| 能力 | 状态 | 说明 |
|---|---|---|
| 双风格规范与配置（S1） | `PASS_STATIC` | 本文件 + `config/styles.yaml` + 测试 |
| 工笔风格真实生成 | `PARTIAL` | S2-工笔 1 张 1024×1024 + 管线 B 28 s 样片；技术通过，人工审美 PENDING |
| 水墨风格真实生成 | `PARTIAL` | 4 张候选，选用 IA4 576×1024 + 管线 A 20 s 样片；技术通过，人工审美 PENDING |
| 长卷横移（Scroll Pan） | `PARTIAL` | S2-工笔 20 s + 管线 B 28 s 真实执行；仅实验链路 |
| 水墨遮罩（Ink Matte） | `PARTIAL` | S2-水墨 20 s 真实执行；仅实验链路 |
| 墨迹渗染（Ink Diffusion） | `PARTIAL` | S2-水墨 噪声 + LUT 柔边遮罩；人工审美 PENDING |
| 纸本纹理（Paper Texture） | `PARTIAL` | S2-工笔/水墨 程序纹理叠加；非扫描素材；未比较混合方式 |
| 云气横移（Cloud Motion） | `PARTIAL` | 管线 A 云层 ±24 px/14 s；山体静态区域差异 0.002/255；人工 PENDING |
| 水面微动（Water Motion） | `PARTIAL` | 管线 A 水面 ±4 px/8 s，排除舟体；人工 PENDING |
| 孤舟微移（Boat Micro-move） | `PARTIAL` | 管线 A 刚性舟体贴片 8 px/20 s；人工 PENDING |
| 分层（Layering） | `PARTIAL` | 每样片手工 `layers.json`；不是通用分割 |
| 线描显现（Line Reveal） | `NOT_RUN` | 未实现/未验证 |
| 局部微动（Wan 局部） | `PARTIAL` | Wan I2V 推近已验证；局部遮罩合成未验证 |
| 2.5D 视差 | `PARTIAL` | 水墨推拉 + 青绿横移各一镜；补底/遮挡/边界三门已接入 |
| 缓慢推近 | `PASS_VERIFIED` | R3（zoompan）；S2-水墨 复用 |
| 镜头缓动（确定性） | `PARTIAL` | 三轴缓动、焦点、起止缩放已执行；人工看片 PENDING |
| 局部微动（确定性图层） | `PARTIAL` | 水面/植物/云雾/墨迹已执行；静态结构带可量化；人工 PENDING |
| 水墨/叠化转场 | `PARTIAL` | 四种类型探针全过；双风格 E2E 已使用；人工 PENDING |
| 双风格链路（S3 分解） | `PASS_STATIC` / `PASS_VERIFIED`（技术样片）/ `PARTIAL` / `NOT_RUN` | ① 规范/配置；② 各风格 2 镜头技术样片（M7）；③ 作品级锁定 `PARTIAL`；跨镜头一致性正式验证 `NOT_RUN` |
| 六维美学数据结构 | `PASS_STATIC` | `aesthetics.py` + 两套 `aesthetic_profile` + 测试 |
| Prompt 编译器 | `PARTIAL` | 8 张真实生成；因果与审美待人工 |
| A/B 美学对照 | `PARTIAL` | 4 组镜头、8 张图、联系表、风险指标；人工 PENDING |
| 静态/动态美学风险检查 | `PARTIAL` | 指标与连续性；不是审美结论 |
| 镜头级美学人工结论 | `PENDING_HUMAN_REVIEW` | 未给出 |

---

## 9. 非目标

- 不追求模型数量、风格数量或“特效堆叠”。
- 不做风格插件市场、复杂参数系统或独立动画引擎。
- 不用 AI 视频模型模拟真实绘画过程。
- 不承诺原生 1080p/2K/4K、60 fps 或实时生成。
- 不把一次成功样片当作风格稳定性的结论。
