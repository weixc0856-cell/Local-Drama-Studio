# M0 视觉事故审计报告

> 执行日期：2026-11-04
> 环境：Windows 11 / Intel i7-13700K / 64 GB / Intel Arc A750 8 GB / FFmpeg 8.1 / Python 3.12
> 本轮未启动 ComfyUI、FLUX、Wan、LLM 或 CosyVoice；审计只读已有视频与原图。
> 状态口径：`docs/PRD.md` §0.2。自动指标通过不等于审美通过；根因结论必须同时有实测值和代码位置。

## 0. 结论

本轮审计覆盖 10 个样片、2 468 帧、102.8 s。问题可以明确分成五层，**不是单一链路的问题**。

> 说明：findings 中的 `CONFIRMED` / `PARTIAL` / `RULED_OUT` / `NOT_RUN` 是**审计判定**，不是 PRD §0.2 的能力状态；能力状态仍按 PRD 口径单独记录。

| 层 | 结论 | 代表证据 |
|---|---|---|
| 源图/生成 | 水墨 E2E 的第二镜头是彩色水彩；P1 项目从未使用 `ink_wash` | 源图平均色度 0.33 → 12.53；P1 风格快照 `style_p1_short` |
| Wan 图生视频 | 船体不单向漂移，而是围绕固定点抖动、面积呼吸 | 3 s 质心路径 35.5 px（270 宽），起止 188.16 → 189.05 |
| 确定性局部运动 | 水面是整层灰膜平移；云雾是整张底图的位移副本在振荡透明度 | `local.py` 的 `water_ripple` / `cloud_drift`；C2 全片帧差 0.059 |
| 转场合成 | 转场取的是上一镜头的**开头**，却插在**结尾**之后 | 边界帧差 28.04（水墨）/ 47.79（青绿） |
| 最终编码 | **排除**：编码前后 ΔE ≤ 0.20、\|Δluma\| ≤ 0.19 | preencode vs final 逐镜头对比 |

现有质量门 `dynamic_aesthetic_report.json` 对上述样片全部给出 `risk_flags: []`、`risk_severity: ok`、`continuity.status: OK`。
这正是“像素差值通过但视觉不自然”的直接证据。

## 1. 输入与工具

| 样片 | 类型 | 路径 | 时长 |
|---|---|---|---|
| `pipeline_a_c2` | 确定性合成（水墨孤舟，旧实现） | `experiments/pipeline_a/renders/build-20261103-224331/final_9x16.mp4` | 10.0 s |
| `pipeline_a_wan` | Wan I2V 基线 | `experiments/pipeline_a/wan_baseline/A_wan_1080.mp4` | 3.0 s |
| `pipeline_b_g3_scroll` | 青绿长卷横移 | `experiments/pipeline_b/renders_fix/build-20261103-220644/final_9x16.mp4` | 28.0 s |
| `e2e_ink_final` | 水墨 E2E 成片 | `experiments/mv/e2e_ink_wash/renders/build-20261104-005709/final_9x16.mp4` | 8.83 s |
| `e2e_ink_preencode` | 同上，淡入/字幕前 | 同目录 `segments/sequence.mp4` | 8.83 s |
| `e2e_court_final` | 青绿 E2E 成片 | `experiments/mv/e2e_court_green_fine_line/renders/build-20261104-005728/final_9x16.mp4` | 9.08 s |
| `e2e_court_preencode` | 同上，淡入/字幕前 | 同目录 `segments/sequence.mp4` | 9.08 s |
| `aesthetic_ink` | 最新确定性动画样片 | `experiments/aesthetic/ink/work/motion/build-20261104-065806/sequence/sequence.mp4` | 8.0 s |
| `aesthetic_court` | 最新确定性动画样片 | `experiments/aesthetic/court/work/motion/build-20261104-065818/sequence/sequence.mp4` | 8.0 s |
| `p1_short` | 工作台 P1 期数成片 | `projects/proj_p1_short/episodes/ep_p1_short/renders/build-20261104-005408-motion-ink/final_9x16.mp4` | 10.0 s |

工具：新增 `scripts/visual_audit.py`。它复用 `scripts/compare_motion.py` 的暗部统计，并用
`scripts/r2b_track_boat.py` 的连通域规则跟踪船体；不新增依赖（Pillow + FFmpeg + stdlib）。

每个样片输出：

- 全片与逐镜头亮度、帧差、切点；
- 逐区域亮度时间序列（去趋势残差、方向反转率、单调漂移率）；
- 船体连通域质心路径、面积呼吸、剪影亮度；
- 区域变化覆盖率（区分“局部运动”与“整层滑动”）；
- 逐镜头 Lab 均值、镜头间 ΔE 与色度比；
- 尾部亮度斜率；
- 首/中/末帧对照、区域裁切对照、异常帧对照、亮度时间轴。

权威结果：原 `experiments/audit/M0/visual_failure_audit.json`（含 10 条 findings 与全部实测）；该目录已在 2026-11-06 的本地清理中删除，结论保留在本文。
生成该结果的原始 run 为 `experiments/audit/M0/run-20261104-071740/`（已删除）；更早的 run 只是阈值迭代中间产物，不作为证据。

## 2. 逐项根因

### F1 跨镜头从水墨跳变到彩色水彩 — CONFIRMED（源图层）

- 源图平均色度：`e2e_ink` shot_001 = 0.33，shot_002 = 12.53。
- preencode 序列镜头间：ΔE 15.36，色度比 55.3，亮度差 −23.5。
- 该差异在淡化、字幕、封装之前就存在，因此不是运动、转场或编码造成。
- `p1_short` 的 4 个镜头同样全是彩色水彩：风格快照是 `style_p1_short`（“低饱和青绿与暖金”），
  不是 `ink_wash` 或 `court_green_fine_line`。
- 现有门禁只在单图上查留白/边缘/饱和度，没有跨镜头风格一致性检查。

对照：`aesthetic_ink` 两个镜头源图色度 1.41 / 0.79，画风一致；问题在 E2E 夹具与 P1 风格选择，不在两种核心风格本身。

### F2 船体漂移、悬浮 — CONFIRMED（Wan 基线）

Wan 3 s 输出中的船体：

| 指标 | 值 |
|---|---|
| 质心路径长度 | 35.48 px（270 宽审计帧；约合 1080 宽 142 px） |
| 起止质心 | 188.16 → 189.05（几乎回到原点） |
| 面积比范围 | 0.062–0.072（极差 0.0095，相对波动约 14%） |
| 剪影亮度变化 | 1.46 luma |

结论：不是单向漂移，而是围绕固定位置的高频抖动 + 船体面积呼吸。观感就是“漂浮/没坐进水里”。

对照确定性 C2：船体质心 10 s 只走 7.92 px（0.29 %/s），面积比稳定在 0.067–0.079，并且旧实现有
`boat_mask` / `reflection_mask` / `water_exclude_boxes`。因此该缺陷属于 Wan，不属于 FFmpeg/Pillow 链路。
当前 9 个 E2E/确定性样片中没有 Wan 段，不能把“船漂”算到确定性动画头上。

### F3 水面缺少自然动态、整片水面机械平移 — CONFIRMED（确定性）

- `water_ripple` 生成一张**全画面**纹理（均值 128 ± 10），用 box/band + luma 门控得到静态 alpha，
  再把**整层**按 `amplitude*sin(2πft)` 水平平移（`local.py:135-156, 166-210`）。
- alpha 没有船体、倒影、岸线排除；计划里也从未填 `exclude_boxes`。
- 叠加发生在 camera 变换**之后**（`render.py:216-235`），遮罩坐标不跟随推近/横移，内容与遮罩会错位。
- 实测：C2 全片帧差 0.059 luma，水面区域 10 s 只变化 0.44 luma（太静）；
  `aesthetic_ink` 水面区域变化覆盖率 0.388、亮度极差 1.37 luma（4 s 推近镜头），两项都不足以构成可见的自然波动。
- 回归点：旧 `scripts/pipeline_ink.py:365-392` 有水面排除框和船体/倒影遮罩，新模块没有继承。

### F4 树丛异常爆光、时间闪烁 — PARTIAL（确认提亮，不确认高频闪烁）

- `tree_left` 10 s 内抬升 5.29 luma（+0.67 luma/s），但去趋势残差 0.33、方向反转率 0.55，
  **没有达到高频闪烁判据**。
- 机制：`cloud_drift` 的 rgb 层是整张底图；alpha 序列把静态遮罩乘以 0.8–1.0 的透明度振荡，
  再把整层单向位移 30 px。云带 `0.46–0.63` 与树冠 `0.55–0.72` 重叠，树顶被位移的模糊副本反复覆盖。
- 4 s 短镜头里是轻微蒙雾；10 s 里累积成可见提亮。
- 因此“闪烁”这一描述在现有样片上不成立，确认的是“缓慢爆光/蒙雾漂移”。修复时仍应同时消除两者。

### F5 青绿动态不足 — CONFIRMED（aesthetic 样片）/ RULED_OUT（pipeline_b 长卷）

- `aesthetic_court` shot_001 帧差 1.77（3–6% 缓推），shot_002 帧差 0.854、`motion=static`、
  `local_motion=[]`。后半段基本是静止图。
- `pipeline_b` G3 长卷以 30 px/s 横移，帧差 6.09，运动是真实的。
- 结论：问题在镜头编排（第二镜头没有运动），不是“青绿风格不能动”。

### F6 青绿尾部异常变暗 — CONFIRMED（内容/构图），排除编码与淡出

G3 长卷：

| 指标 | 值 |
|---|---|
| 中段峰值亮度 | 155.0 |
| 末帧亮度 | 147.2 |
| 尾窗下降 | 4.72 luma |
| 尾窗斜率 | −0.82 luma/s |
| 单调下降比例 | 93.4% |
| 是否含 fade | 否（该 build 无 fade，`r3_build` 的 0.9 s fade-out 未参与） |

横移窗口在结尾露出源图右侧更暗的山体与建筑；源图本身右侧更暗。

`aesthetic_court` 的“尾部变暗”是另一个原因：第二个镜头整体暗 15.9 luma
（源图 Lab L* 60.77 vs 67.61），crossfade 之后整段变暗。现有连续性检查只算 ΔE（7.2），
亮度差没有进门禁。

编码前后逐镜头 ΔE ≤ 0.20、\|Δluma\| ≤ 0.19，排除编码/gamma 问题。**不得用统一 LUT 或改 gamma 掩盖**。

### F7 像素差值通过但视觉不自然 — CONFIRMED（门禁缺口）

- 两份 `dynamic_aesthetic_report.json` 均为 `risk_flags: []`、`risk_severity: ok`、
  `continuity.status: OK`（ΔE 4.69 / 7.74）。
- 同一批视频实测：镜头亮度差 15.9 luma、转场边界帧差 28–48、水层是整张纹理叠加、云雾蒙雾。
- 根因：门禁只查空白/黑帧、解码、时长、单帧结构带差和 ΔE ≤ 15；没有时间连续性、闪烁、
  硬保护区域、尾部亮度、转场方向检查。
- 转场探针用纯色静态片段，结构上无法发现“取了错误片段”。

### F8 转场开始/结束位置错误 — CONFIRMED（转场合成）

`src/drama_studio/motion/transition.py`：

- `render_transition` 对左侧输入使用 `-ss 0`（第 103 行 crossfade、第 120 行 ink），
  取的是上一镜头的**开头**；
- 转场被插在上一镜头的**结尾**之后；
- `body_i` 又从 `transition_in.duration_s` 开始截取（第 158–163 行），右镜头从 0 开始。

实际时间线变成：`上一镜结尾 → 上一镜开头 → 下一镜开头 → 下一镜第 1 秒`。

左侧应取上一镜头渲染时预留的尾部 handle（`-ss = shot.duration_seconds`, `-t = transition.duration_s`），而不是 `-ss 0`。右镜头取 0 与 body_i 跳过头部是一致的，不需要改。

实测边界：

| 样片 | 边界帧差 | 说明 |
|---|---|---|
| `aesthetic_ink` | frame 95→96 = 28.04 luma | 推近 4 s 后突然回到第 0 帧 |
| `e2e_court` | frame 101→102 = 47.79 luma（4.208→4.250 s） | 横移 4.2 s 后突然回到起点 |

转场技术探针（`transition_probe.py`）使用纯色静态片段，首尾帧颜色相同，故“起始=左、结束=右”会通过，
无法暴露该缺陷。这也解释了为什么报告里转场“全部通过”但看片不自然。

### F9 编码前后亮度/色彩 — RULED_OUT

| 样片 | 镜头 | ΔE | Δluma |
|---|---|---|---|
| 水墨 | shot_001 | 0.10 | −0.11 |
| 水墨 | shot_002 | 0.09 | −0.19 |
| 青绿 | shot_001 | 0.15 | −0.09 |
| 青绿 | shot_002 | 0.20 | −0.02 |

统计时已排除 `final_9x16` 的 0.9 s 淡出。编码不是本轮视觉问题的来源。

### F10 发音 — NOT_RUN（M6）

M0 只做视觉审计。发音问题留给 M6，按任务要求重新核对 `不胜愁` 的 `胜`（不得标为 shēng），
并把 `碣石 / 潇湘 / 扁舟 / 似霰 / 青枫浦` 作为候选逐条做音频验证。

## 3. 人工查看入口

所有路径相对于 `experiments/audit/M0/run-20261104-071740/`：

| 内容 | 路径 |
|---|---|
| Wan 船体抖动 | `samples/pipeline_a_wan/region_boat.png` |
| 确定性 C2 船体（对照，稳定） | `samples/pipeline_a_c2/region_boat.png` |
| 水层（整张纹理叠加） | `samples/aesthetic_ink/region_water.png` |
| 树冠蒙雾/提亮 | `samples/pipeline_a_c2/region_tree_left.png` |
| 水墨跨镜头风格跳变 | `samples/e2e_ink_final/shot_001_first_mid_last.png`、`shot_002_first_mid_last.png` |
| 青绿尾部变暗 | `samples/pipeline_b_g3_scroll/shot_001_first_mid_last.png` |
| 青绿第二镜头整体偏暗 | `samples/aesthetic_court/shot_002_first_mid_last.png` |
| 转场边界回跳 | `transition_evidence/ink_around_cut.png`、`transition_evidence/court_around_cut.png` |
| 亮度时间轴 | 各 `samples/<id>/luma_timeline.png` |
| 转场前后原始帧 | `transition_evidence/ink_3.80.png` … `ink_4.20.png` |

## 4. 未执行 / 不声称

- 未启动 ComfyUI、FLUX、Wan、LLM、CosyVoice；没有新的生成结果。
- 未判断审美好坏；所有结论只到“技术/结构缺陷”层。
- 未修改任何原始视频、原图或已有实验目录。
- 未验证 Wan 工作流是否真的支持运动遮罩/主体保护；这属于 M5，当前标记 `NOT_RUN`。
- 未新增依赖，未训练 LoRA，未引入 ControlNet。

## 5. 下一步（等待人工审查）

M0 完成后停止。人工确认根因分层后，按顺序进入：

1. **M1** 区域语义与运动权限：复用 `motion_regions.json`，加 `rigid_object / fluid_surface / reflection / vegetation / atmosphere / background / independent_overlay` 与 `locked / hard_excluded / controlled / allowed`。
2. **M2** 重做局部运动：水面改为局部低频扰动并强制排除主体；云雾取消整层位移；植物只动枝叶；墨迹只用于明确区域。
3. **M3** 扩展现有质量门：硬保护区、动态区运动范围、时间连续性、异常亮度、局部爆光、尾部亮度、转场前后连续性、编码前后一致性。
4. **M4** 转场：先修 `-ss 0` 的时间倒错，再加镜头兼容性检查。
5. **M5** Wan 独立实验：先核验工作流能力，不支持就明确 `NOT_RUN`。
6. **M6** 发音校正。
7. **M7** 双风格代表性镜头验收。

## 6. 资源与 Git

- 审计为 CPU + FFmpeg/Pillow；GPU 显存占用 0；无网络请求。
- 单次审计 run 约 1–2 分钟（CPU）；本轮共 5 次 run（阈值与分析窗口迭代）。
- 未提交、未推送、未 reset、未 clean。HEAD 仍为 `651c7dd`。
- 新增：`scripts/visual_audit.py`、`experiments/audit/M0/`（本地证据，`experiments/` 不入库）。
