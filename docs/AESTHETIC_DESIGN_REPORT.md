# 镜头美学设计系统集成报告

> 执行日期：2026-11-04
> 环境：i7-13700K / 64 GB DDR5 / Intel Arc A750 8 GB / ComfyUI 0.43.0 / FLUX.2 klein 4B Q4 / FFmpeg 8.1
> 状态口径：`docs/PRD.md` §0.2。**自动指标通过不等于审美通过；人工看片前一律不写 `PASS_VERIFIED`。**

## 1. 执行前审计

### 1.1 当前生产调用链（改动前）

```text
ContentPackage → ProductionScript（LLM）
  → build_jobs（scene_prompt/visual_prompt 直接进 FLUX）
  → FLUX 静态图 → static_quality（客观指标 + 人工检查表）
  → segments → r3_build → quality.check
```

### 1.2 已存在的美学相关字段

| 位置 | 字段 | 实际用途 |
|---|---|---|
| `config/styles.yaml` | `visual_language`、`positive_prompt`、`negative_prompt`、`material`、`line`、`detail`、`color_palette` | 风格提示与审计；前两项进入生成 |
| `config/styles.yaml` | `motion`、`compositing` | 2026-11-04 已由 `drama_studio.motion` 消费 |
| `ScriptShot` | `scene_prompt`、`visual_prompt`、`motion` | 自由文本；无构图/光影/色彩结构 |
| `static_quality.py` | 客观指标 + 两套人工检查表 | 空图/黑图/留白/边缘/饱和度；无“设计 vs 成图”对照 |
| `human_review.json` | 期数级接受/拒绝 | 没有镜头级美学结论 |

### 1.3 当前缺失

- 没有镜头级六维美学规格；`scene_prompt` 无法表达主体位置、光线方向、色彩关系、前中远景。
- 没有“设计 → Prompt”编译器；风格只靠拼接 `visual_language + positive_prompt`。
- 没有 A/B 候选与对照；无法知道质量提升来自哪个设计变量。
- 没有设计快照；“生成时用了什么规格”不可追溯。
- 静态质量门没有“设计与成图”的构图/光影/色彩风险提示。
- 没有镜头级美学人工结论。

### 1.4 复用与最小改动

复用：`ProductionScript`、`style_presets`、`build_jobs`/`r1_batch`、`static_quality`、`quality`、`motion`、工作台任务注册表。**没有新建第三套风格、Prompt 模板目录或独立质量系统。**

新增/修改文件见 §10。

## 2. 六个维度的数据结构

`src/drama_studio/aesthetics.py`：

| 维度 | 关键字段 |
|---|---|
| Composition | `shot_size`、`viewpoint`、`subject_position`、`visual_weight`、`foreground_occlusion`、`leading_lines`、`whitespace_ratio`、`depth_layers`、`density`、`strategies`、`safe_area` |
| Lighting | `key_light`、`direction`、`quality`、`intensity`、`contrast`、`rim_light`、`ambient`、`reflected`、`aerial_perspective`、`mist_scattering`、`time_weather`、`mood` |
| Color | `dominant`、`secondary`、`accent`、`temperature`、`saturation`、`value_range`、`continuity_group`、`style_range` |
| Depth | `foreground`、`midground`、`background`、`occlusion`、`aerial_perspective`、`sharpness_falloff`、`guides`、`layered_assets` |
| Mise en scène | `period`、`architecture`、`components`、`nature`、`costume`、`props`、`figure_pose`、`cultural_context`、`relationships`、`modern_elements` |
| Visual storytelling | `narrative_purpose`、`emotional_target`、`visual_subject`、`focal_point`、`entry_point`、`eye_path`、`connection_prev`、`connection_next`、`rhythm` |

构图策略包含三分法、中心、对称、框景、对角线、留白、纵向纵深、宏大尺度、边角、高远/深远/平远、散点透视、虚实相生；三远可组合，不是三选一。

### 2.1 共享数据与独立风格适配

- 共享：六维结构、`SharedAesthetic`（连续性组、色板键、情绪弧、视觉语法、约束）、A/B 机制、质量指标。
- 独立：每种风格在 `config/styles.yaml` 的 `aesthetic_profile` 中声明自己的构图偏好、默认主体位置、留白范围、光质/方向/反差、色彩键、饱和度范围、时代与建筑正向约束、情绪词汇。
- `aesthetics.py` 没有 `if style == ...`；两者都由配置驱动。测试断言两种风格的 continuity group、默认方向、默认色温不同。

### 2.2 A/B 变体约束

`ShotAestheticSet` 在 Pydantic 层强制：

- 恰好 A/B 两版；
- 两版 `changed_axis` 相同；
- 除该维度外，其余五个维度逐字段相等；
- 该维度确实不同。

因此“只改变一个主要美学变量”不是文档约定，而是数据结构不变量。注意：不变量约束的是**设计规格**；生成像素仍受 FLUX 随机性与语义理解影响，所以 A/B 必须看片，不能只凭 Prompt 差异或单一指标下结论。

### 2.3 为什么不是让 Qwen 直接生成一套设计

本轮不让 LLM 直接产出“唯一正确”的美学规格再送 FLUX：那样无法判断质量提升来自哪个变量。默认路径是：

1. `aesthetic_profile` 提供风格边界；
2. `designs.json` 提供人工场景设计（可编辑、可审查）；
3. 系统只为选定的一个维度生成 A/B 两版；
4. 生成后比较指标与人工看片，再沉淀规则。

LLM 可以以后用来起草 `designs.json`，但必须经过同样的 A/B 与人工验证，不能绕过。

## 3. Prompt Compiler 与 FLUX 负向能力

### 3.1 工作流核查

`workflows/r0_flux_t2i_api.json`：

- 节点 4：正向 `CLIPTextEncode({{positive_prompt}})`；
- 节点 5/6：空文本 → `ConditioningZeroOut`；
- 节点 10：`CFGGuider`，`cfg=1.0`；
- 工作流里**没有** `{{negative_prompt}}` 占位符。

结论：当前 FLUX.2 配置的负向条件被清零且 CFG=1.0，负向提示词**不是有效控制**。编译器因此：

- 记录 `negative_prompt`（审计用），`negative_supported=false`；
- 主要约束写成明确正向描述（时代、形制、构件、空间关系、禁用现代物件以正向方式表达）。

### 3.2 编译顺序

固定为：主体与关系 → 构图/主体位置 → 环境与空间 → 光线方向与质量 → 色彩关系 → 艺术风格 → 材质细节 → 正向约束。

每个镜头/版本输出 `prompts/<shot>_<variant>.json`，包含分节文本、完整 Prompt、负向记录、`spec_sha256`、`prompt_sha256`、`negative_supported`。**真正送进模型的是 `positive_prompt` 字符串**（由 `params/*.json` 替换工作流占位符）；`prompts/*.json` 只是审计记录，不会被 ComfyUI 当作结构化 Prompt 解析。

### 3.3 冻结与追溯

`production.build_aesthetic_jobs` 为每次运行写新的 `snapshot-<时间>/`：

```text
snapshot-<time>/
├─ A/ B/                     # 两套冻结规格
│  ├─ aesthetic_plan.json
│  ├─ aesthetic/*.json       # 质量门可直接读取的 shot design
│  ├─ params/*.json
│  ├─ prompts/*.json
│  ├─ jobs_A|B.json
│  └─ provenance.json        # style/workflow/plan 哈希、seed/尺寸/步数/CFG
└─ images/<shot>/A|B/        # FLUX 输出
```

同一目录再次写入会直接失败；人工改设计必须生成新 snapshot。`aesthetic.compare` 会记录工作 plan 与 snapshot `plan_sha256`；不一致时写入 warning，避免用错设计解释成图。

## 4. 生产调用链差异

```text
改动前：ProductionScript → FLUX
改动后：ProductionScript
          → aesthetic.plan（六维设计 + A/B + snapshot + jobs）
          → comfy.batch（A、B 各一次 FLUX）
          → aesthetic.compare（风险指标 + 联系表 + 人工审核包）
          → aesthetic.review（人工结论，新增文件）
          → static_quality（设计 vs 成图风险）
          → motion.plan → motion.render → quality --aesthetic-motion
          → segments → r3_build → quality
```

工作台新增：`aesthetic.plan`、`aesthetic.compare`、`aesthetic.review`。图像生成仍走既有 `comfy.batch`，没有新的 GPU 路径。

## 5. 四组测试镜头

基线图只作为对照，不代表已通过；生成结果来自本轮 FLUX。

| # | 管线 | 基线 | 变量 | A | B |
|---|---|---|---|---|---|
| 1 | 水墨大远景 | `experiments/aesthetic/ink/baseline/shot_001.png` | 构图 | 主体居中、对称、留白 38% | 主体右三分、留白 51%、前景遮挡 |
| 2 | 水墨月夜/云雾 | `.../ink/baseline/shot_002.png` | 光影 | 月夜漫射、低反差 | 逆光、轮廓光、反差提高 |
| 3 | 青绿大场景 | `.../court/baseline/shot_001.png`（G3） | 色彩 | 石青主调、冷 | 石绿主调、暖、赭石辅助 |
| 4 | 青绿建筑细节 | `.../court/baseline/shot_002.png`（G3 局部裁切） | 构图 | 既定右三分、框景 | 反向左三分、更多留白 |

设计文件：`experiments/aesthetic/<style>/work/designs.json`。计划：`.../work/aesthetic/aesthetic_plan.json`。

编译后的完整 Prompt 在 `snapshots/snapshot-20261104-064902-*/{A,B}/prompts/`。水墨 shot_001 A 开头：

```text
主体：远山、江面与孤舟；主体关系：孤舟与远山形成尺度对照、近岸疏树引导视线；
场景：远山、江面、孤舟与近岸坡石；竖屏9:16构图；大远景，高角度俯视；主体位于画面中心；
构图策略：中心构图、对称构图、纵向纵深、高远、平远、虚实相生、计白当黑；留白约38%…
```

青绿 shot_001 A 开头：

```text
主体：楼阁、江流与群山；主体关系：楼阁嵌入山体、江流引导视线；场景：宋代楼阁、江流、松树与群山；
竖屏9:16构图；大远景，高角度俯视；主体位于画面中心；构图策略：对称构图、宏大尺度、高远、深远、散点透视、纵向纵深；
留白约18%；……主色：石青（#2E5E75）；辅助色：石绿（#4E7A5E）、绢底（#E3D6BE）……
```

## 6. 静态质量与 A/B 指标

每张生成图都有 `static_quality.json`：客观项通过，人工检查表 `PENDING`，`aesthetic_status=PENDING_HUMAN_REVIEW`。

风险指标（注意：是提示，不是审美结论）：

| 镜头 | 版本 | 主体位置误差 | 留白 | 焦点比 | 反差 p5–p95 | 主色 ΔE | 实测冷暖 | warn 数 |
|---|---|---:|---:|---:|---:|---:|---|---:|
| ink shot_001 | A | 0.206 | 0.468 | 2.01 | 198 | 12.5 | neutral | 1 |
| ink shot_001 | B | 0.287 | 0.509 | 2.16 | 200 | 12.4 | neutral | 2 |
| ink shot_002 | A | 0.265 | 0.335 | 2.14 | 220 | 16.9 | neutral | 2 |
| ink shot_002 | B | 0.255 | 0.333 | 2.15 | 228 | 18.1 | neutral | 1 |
| court shot_001 | A | 0.103 | 0.090 | 1.45 | 190 | 38.7 | warm | 1 |
| court shot_001 | B | 0.105 | 0.073 | 1.38 | 193 | 23.6 | warm | 0 |
| court shot_002 | A | 0.144 | 0.125 | 1.28 | 223 | 32.1 | neutral | 2 |
| court shot_002 | B | 0.052 | 0.285 | 1.76 | 210 | 40.2 | neutral | 1 |

指标提示（`metric_hint`）：

| 镜头 | 更接近自身设计的版本 |
|---|---|
| ink shot_001 | placement A / focus B / palette B / contrast A |
| ink shot_002 | placement B / focus B / palette A / contrast B |
| court shot_001 | placement A / focus A / palette B / contrast A |
| court shot_002 | placement B / focus B / palette A / contrast B |

这些提示不构成“哪版更好”的结论。例如 court shot_001 的 A 更接近设计位置/焦点，B 更接近设计色板；最终取舍必须看片。

联系表：

- `experiments/aesthetic/ink/work/aesthetic/compare/contact_sheet.png`
- `experiments/aesthetic/court/work/aesthetic/compare/contact_sheet.png`
- `comparison.json` / `comparison.md` 同目录；`human_review` 全部 `PENDING`。

人工观察（仅记录，不作验收）：水墨两版整体偏水彩质感，与 `ink_wash` 目标存在风格漂移风险；青绿建筑细节的框景/反向偏置差异明显；青绿大场景 A/B 色差偏细，需要看片确认。

## 7. 动态能力接入

用各风格 A 版本生成两镜头序列（4 s + 4 s，含转场）：

| 风格 | 序列 | 转场 | 静态结构带最大差 | 相邻镜头 ΔE / 亮度差 |
|---|---|---|---:|---|
| ink_wash | `.../ink/work/motion/build-20261104-065806/sequence/sequence.mp4` | ink_dissolve 1.0 s | 0.2953（静态镜头） | 4.69 / −10.23 |
| court_green_fine_line | `.../court/work/motion/build-20261104-065818/sequence/sequence.mp4` | crossfade 0.8 s | 0.0013（静态镜头） | 7.74 / −17.54 |

`quality --aesthetic-motion --aesthetic-plan` 输出 `dynamic_aesthetic_report.json`：两段 `risk_severity=ok`，`aesthetic_status=PENDING_HUMAN_REVIEW`。运镜焦点与设计主体位置：ink shot_001 focus_error 0.02、court shot_001 0.00（均 < 0.2，无 warning）；静态镜头不参与运镜焦点判定。运镜镜头的结构带差值包含运镜位移，报告明确标注不能单独归因于局部微动。转场是否破坏空间关系仍需人工看片。

## 8. 生成耗时与资源

| 项 | 实测 |
|---|---|
| 8 张 576×1024 / 4 步 / CFG 1.0 | 143.2 s 总计 |
| 稳态单张 | 16.09–16.13 s |
| 首张（含模型加载） | 30.5 s |
| 峰值显存 | 3.04 GiB（A750 8 GB） |
| 模型 | FLUX.2 klein 4B Q4_K_M，文本编码器 CPU |
| 运行方式 | ComfyUI 8188，串行；生成后已停止，端口空闲 |

未启动 LLM、Wan、CosyVoice；无新增依赖；仓库中未发现现成 LUT 使用，本轮未引入全片固定 LUT。

## 9. 状态与未完成

| 能力 | 状态 |
|---|---|
| 六维美学数据结构与校验 | `PASS_STATIC`（schema + 182 项测试） |
| 风格适配 profile | `PASS_STATIC` |
| Prompt 编译器 | `PARTIAL`（真实生成；因果优劣待人工） |
| A/B 生成与对照 | `PARTIAL`（8 张实图 + 指标 + 联系表；人工 PENDING） |
| 静态美学风险检查 | `PARTIAL`（风险提示；非审美结论） |
| 动态美学检查 | `PARTIAL`（连续性/静态保护；人工 PENDING） |
| 人工美学结论 | `PENDING_HUMAN_REVIEW` |
| 正式作品应用 | `NOT_RUN` |

未完成：

- 四组 A/B 的人工看片结论；未选“胜出版本”。
- 水墨成图的风格漂移（偏水彩）需要人工确认，可能需要改提示词或参考图策略；本轮不擅自定论。
- 构图指标是边缘重心代理，不是主体分割；焦点/景深是统计代理。
- 历史文化准确性无法自动判定；`mise_en_scene` 只记录设计与风险标记。
- 色彩连续性阈值 15（ΔE 76）是初始值，需用更多样片校准。
- 2.5D 视差、线描显现、正式作品双版本未开始。

## 10. 修改文件

新增：

- `src/drama_studio/aesthetics.py`
- `scripts/aesthetic_plan.py`、`scripts/aesthetic_compare.py`
- `tests/test_aesthetics.py`
- `docs/AESTHETIC_DESIGN_REPORT.md`

修改：

- `src/drama_studio/style_presets.py`（`aesthetic_profile` 模型与校验）
- `config/styles.yaml`（两套 `aesthetic_profile`）
- `src/drama_studio/production.py`（`build_aesthetic_jobs`）
- `src/drama_studio/quality.py`（`image_metrics`、`check_aesthetic_risk`、`check_color_continuity`、`check_dynamic_aesthetics`、CLI）
- `scripts/static_quality.py`（共享 metrics + `--aesthetic`）
- `src/drama_studio/workspace/tasks.py`、`src/drama_studio/web/js/pages/tasks.js`
- `tests/test_style_presets.py`、`tests/test_workspace_api.py`、`tests/test_workspace_motion_tasks.py`
- `docs/VISUAL_STYLE_SPEC.md`、`docs/PRODUCTION_WORKFLOW.md`、`docs/CONTENT_SPEC.md`、`docs/README.md`、`CLAUDE.md`

## 11. Git

- HEAD：`651c7dd`
- 未提交、未推送、未 reset、未 clean
- `experiments/` 与 `projects/` 为本地证据目录（已 gitignore），历史产物未覆盖
- ComfyUI 已停止；8080 / 8188 / 50000 / 8765 均空闲
