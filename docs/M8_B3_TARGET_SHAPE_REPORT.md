# M8-B(3) 目标形态：完整背景 + 独立舟层 + 独立前景

> 执行日期：2026-11-04
> 前置：[M8_B1_PLATE_SOURCE_REPORT.md](M8_B1_PLATE_SOURCE_REPORT.md)、[M8_B2_ASSET_LAYER_REPORT.md](M8_B2_ASSET_LAYER_REPORT.md)
> 状态口径：`docs/PRD.md` §0.2

## 0. 结论

**M8-B(3) = `PARTIAL`（技术通过，人工待审）。**

三个平面用三种不同来源拼在一起，跑一台相机，成立：

| 平面 | 来源 | 来源类型 |
|---|---|---|
| `bg` z=0 | 原图，仅船位由 FLUX 重绘（掩膜覆盖 2.0%） | `inpainted` |
| `mid` z=1 | 从原图抠出的孤舟＋倒影 | `original`（抠图） |
| `fg` z=2 | 独立生成的芦苇 RGBA（无任何背景） | `generated_asset` |

| 检查 | 结果 |
|---|---|
| 露洞（舟层） | 加权 0.246% 画面、硬露洞 2012 px（0.10%）、最大连续 53 px，峰值在 t=3.5 s |
| 露洞（前景层） | **不存在**——前景是新增图层，背景未被挖开 |
| 补底质量 | 露洞带下方现在是**画出来的水面**（FLUX），不是插值平滑（两版均值差 10/255） |
| 掩膜外保真 | 0.0000/255，原画其余部分逐像素不变 |
| 时间连续性 | 帧间最大亮度跳变 0.212/255，与 A/E/B 同一包络 |
| 成本 | 渲染 70.9 s（3 平面 × 144 帧）；资产与补底另计 30.8 s + 46.1 s |

它证明的不是"更好看"，而是**这套形状在工程上成立**：三种来源可以在同一台相机、同一 z 序下共存，且背景板可以是被重绘过的（不再要求"原图逐像素"），因为重绘只发生在掩膜内。

## 1. 与前面几步的关系

| 步骤 | 证明了什么 | 没证明什么 |
|---|---|---|
| M8-A（B/C） | 分层视差在观感上成立（人工判定 C 优于 A/B），优势来自分层 | 图层只能靠抠，抠完要补底 |
| M8-B(1) | 补底能做出同风格内容，但**只在小洞、均质区域**成立 | 大洞（前景主体）会变成重画 |
| M8-B(2) | 独立生成的前景资产可以无洞地叠在完整背景上 | 舟这一层仍是挖出来的 |
| **M8-B(3)** | **三种来源可以共存**，且背景允许局部重绘 | 青绿工笔、长卷横移、正式质量门 |

## 2. 由此确定的 `PlateSpec` 草案

```text
PlateSpec
  id            str            唯一，^[a-z][a-z0-9_]{1,31}$
  source        enum            original | inpainted | interpolated | generated_asset | generated_background
  path          str            plate 文件
  sha256        str            完整性
  z_order       int            0 为最远
  depth_alpha   float (0,1]    平面距离 / 背景距离；决定该层相机缩放
  coverage      enum           full_frame | partial
  anchor        Box|None       partial 层在 t=0（相机 scale=1）时的归一化范围
  provenance    dict           seed / steps / workflow_sha256 / mask_sha256 / key 参数 / 耗时
```

校验规则（全部可写进 Pydantic，无需新依赖）：

| 编号 | 规则 | 依据 |
|---|---|---|
| R1 | 恰好一层 `coverage=full_frame`，且 `z_order` 最小 | 背景必须完整，否则露洞 |
| R2 | `source=generated_asset` ⇒ `coverage=partial` 且 `anchor` 必填 | B(2)：资产是新增内容，必须给定位置 |
| R3 | `source ∈ {inpainted, interpolated}` 只允许出现在 `z_order=0` | B(1)：补底只在背景成立 |
| R4 | 每个 `locked` 区域必须完整落在单一 plate 的覆盖范围内 | 刚体不可被切开（沿用 M1 语义） |
| R5 | `depth_alpha` 随 `z_order` 严格递减；允许显式声明的例外 | A 的实验；例外如倒影、交错枝条 |
| R6 | 补底掩膜覆盖率 ≤ 4% 且落在单一材质内，否则拒绝该镜头的 2.5D | B(1)：船 2% 成功、树 9% 失败 |
| R7 | 必须测量并上报露洞（加权泄漏 + 硬露洞 + 最大连续宽度）；超阈值拒绝 | A 的 `uncovered_stats` 已实现原型 |
| R8 | 跨渲染器的 A/B 必须先证明几何一致（远景地标 ≤1 px） | A 报告 §10.1 |

**相机归属**：`PlateSpec` 不带相机参数。每层的变换由统一的 `CameraRig` 从 `depth_alpha` 与全局 `CameraSpec` 推出：

```
s_bg(t) = 1 / (1 - u(t))
s_i(t)  = 1 / (1 - u(t) / alpha_i)
screen  = clamp_window(focus, 1/s_i)   # 与生产 zoompan 逐字一致
```

这条公式是本轮唯一"发明"出来的数学，其余都是把已验证的行为固定下来。

## 3. 尚未实现（M8-B 的正式部分）

| 项 | 状态 | 说明 |
|---|---|---|
| `PlateSpec` / `PlateAnchor` / `ShotSpec.plates` / `depth_exceptions` 进 `motion/spec.py` | **`PASS_STATIC`** | 2026-11-04 落地：单测覆盖全部校验规则 |
| `render.py` 多平面渲染路径 | **`PASS_STATIC`** | 2026-11-04 落地：`motion/plates.py`（窗口规则与 `zoompan` 逐字一致）+ `_render_layered_shot`，**仅在 `shot.plates` 非空时进入**，单平面镜头走原路径不变；13 个单测 + 一次真实渲染（2 s / 48 帧 / 18 s，`check=PASS`，manifest 记录每层缩放 1.030 / 1.0434 / 1.0632） |
| `check_rigid_protection` 支持逐层相机 | **`PASS_STATIC`** | 2026-11-04 落地：区域用 `plate_id` 绑定图层，框按该层相机逐帧映射；分层镜头实测 `mean_diff 4.39`、`edge_shift 0.0052`（阈值 6.0 / 0.06） |
| 补底质量门 | **`PASS_STATIC`** | 2026-11-04 重写为成品判据：**露出比例 × 补底纹理能量比**。实测暴露 41.9%、能量比 0.685（>0.5）→ PASS；M8-A 的插值补底能量比 0.37 → 会 FAIL |
| R7 的补底质量 | **已进契约** | `exposure_of_repair_max 1%`、`energy_ratio_min 0.5`；按 M8-A/B(1) 两组实测标定 |
| 资产风格连续性检查（墨色/纸白/线宽） | `NOT_RUN` | B(2) L2 |
| `config/styles.yaml` 的 parallax 参数 | `NOT_RUN` | 两风格仍是 `allowed: false`；分层镜头目前不依赖该字段 |
| 工笔风格的资产与镜头 | `NOT_RUN` | 留 M8-D |
| 工作台任务与生产链路 | **`PASS_STATIC`** | `plates` 随 `regions.json` 一起下发，`build_motion_plan → motion_build.py → quality` 全链跑通，无需新增任务类型 |

## 4. 建议的落地顺序（若继续）

1. 先把 R1–R8 写成 `PlateSpec` + 单元测试，**不接渲染器**（纯契约，零风险）。
2. 再把实验渲染器里的三平面路径搬进 `render.py`，用一个镜头做回归，确保现有 `A` 类镜头输出逐像素不变。
3. 最后才扩 `check_rigid_protection` 与露洞门——它们会改变既有镜头的判定结果，必须单独一步并留回滚点。

## 5. 产物

| 内容 | 路径 |
|---|---|
| G 变体视频 | `experiments/m8_parallax/renders/G/g.mp4`（1080×1920 / 24 fps / 6.000 s / 144 帧） |
| 首末帧 | `experiments/m8_plates/inspect_G_0000.png`、`inspect_G_0143.png` |
| 七版对照图 | `experiments/m8_parallax/metrics/contact_sheet_ABC.png`（A/E/B/D/C/F/G） |
| 数据 | `experiments/m8_parallax/metrics/metrics.json`、`renders/G/render.json` |

复现：

```powershell
scripts\start.ps1
.venv\Scripts\python.exe scripts\m8_plates.py masks --dilate 12
.venv\Scripts\python.exe scripts\m8_plates.py inpaint --region boat --steps 6 --seed 8100
.venv\Scripts\python.exe scripts\m8_plates.py build --region boat
.venv\Scripts\python.exe scripts\m8_plates.py asset --steps 4 --seed 8100
scripts\stop.ps1
.venv\Scripts\python.exe scripts\m8_parallax.py render --variant G
.venv\Scripts\python.exe scripts\m8_parallax.py metrics
```

ComfyUI 已停止，8188 已释放。

## 6. 边界

- 未修改任何生产代码、配置、质量门；`PlateSpec` 仍只是本文档里的草案。
- 未做青绿工笔、长卷横移、BGM/音效。
- M8-A 的人工结论（C 优于 A/B）不变；B(1)/(2)/(3) 均为技术通过、**人工待审**。

## 11. 契约按成品修订（2026-11-04）

M8-B 的第一版契约有三条规则是"为了迁就实现"而不是"为了保证成品"，已全部改掉：

| 原规则 | 问题 | 现规则 |
|---|---|---|
| 受保护区域不得与更近图层重叠（parse error） | 逼着把船的锁定区从"船+倒影"缩成"船体"，是为了让检查通过而改镜头 | 允许重叠；刚体门**只测可见像素**，被遮挡比例上报，可见不足 25% 记为 `subject_not_assessable` |
| 补底掩膜覆盖率 ≤ 4%（parse error） | 掩膜多大与观众看到什么无关 | 删掉硬上限；改为**露出比例 × 补底纹理能量比**，判"看见时像不像画" |
| 露洞宽度阈值（行内最长连续 ≥80 px 即失败） | 量的是几何，不是观感；同一软掩膜两次重采样就会误报 | 删掉；改测补底纹理连续性，覆盖率只作信息记录 |

此外修掉一个渲染器缺陷：局部图层原用"整数像素 resize + paste"，逐帧按整像素跳，慢推镜会抖。改为按各自仿射做**亚像素采样**（`motion/plates.place`），刚体门的帧差均值从 4.96 降到 4.55（同镜头同时在景的其它因素不变）。

修订后，同一镜头**不再需要为了过检而改设计**：船体 `rigid_object/locked`、倒影 `reflection/controlled/follows` 两个区域各按语义声明，全部检查通过。

### 11.1 刚体门改为自归一化判据（2026-11-04）

上一版刚体门用绝对阈值（帧差均值 6.0、尖峰 12.0），这两个数是在静态机位镜头上标定的。分层镜头一上来就暴露两个问题：

1. **窗口是整像素取窗**。区域框逐帧按整像素裁切，主体高对比边缘每帧跳一格，测到的帧差是量化噪声而不是形变。改为按该层相机做**亚像素采样**（固定 96×96），帧差均值从 **4.55 → 1.40**，尖峰从 **11.93 → 2.01**。
2. **绝对值本身不是判据**。"主体变了多少"要和"这个镜头本来变了多少"比。新增 `motion_energy`（全帧逐帧平均变化）与 `subject_to_energy` 比值：`relative_floor 2.0` + `subject_to_energy_max 1.5`。刚性主体在移动机位上应当**比整帧变化得更少**。

实测（同一镜头两种时长）：

| 时长 | 主体帧差均值 | 全帧变化 | 比值 | 结论 |
|---|---|---|---|---|
| 2 s（48 帧） | 1.404 | 2.794 | **0.503** | PASS |
| 6 s（144 帧） | 0.662 | 1.385 | **0.478** | PASS |

（同一缩放范围内，镜头越长每帧位移越小，所以 6 s 的帧差反而低于 2 s。此前担心的"6 s 会顶到绝对阈值"不成立。）

3. **边缘漂移判据在分层镜头上停用**。实测：把第 0 帧与第 24 帧的窗口做 ±3 px 对齐搜索，最佳位移是 **(0, 0)** ——主体在平面锁定窗口里根本没动；`edge_shift 0.12` 全部来自 96×96 上边缘 bbox 的量化与弱边阈值抖动。分层镜头改由"主体变化 / 全帧变化"比值承担，`edge_check_applied=false` 并写明理由；单平面镜头保留该判据（它在那里被验证过）。

## 12. M8-D 第一步：分层相机支持横移（2026-11-04）

长卷横移与推拉是两种相机，旧的分层渲染只实现了推拉（窗口按 `1/s` 收缩）。横移是窗口平移，且近层要走得更远：

```
x0_i(t) = pan_start + (pan(t) - pan_start) / depth_alpha
```

t=0 时各层对齐；镜头一动，近层按 `1/alpha` 倍位移。**窗口不做 clamp**——近层走出自己的画板就是缺陷，应该被门看见，而不是被边界悄悄挡住。

| 项 | 状态 | 证据 |
|---|---|---|
| 横移相机（`pan_window` / `CameraState` / `background_pan`） | `PASS_STATIC` | 8 个单测：静止对齐、近层 1/alpha、不 clamp、相机跨度跟随 plan |
| 生产渲染接入 | `PASS_STATIC` | 合成宽幅图（1600×1024）走 `render_plan`：`camera=scroll_pan`、`check=PASS` |
| 逐层窗口实测 | — | manifest 记录：背景窗口 0.300→0.340，近景窗口 0.300→**0.3667**（= 0.04/0.6），精确为 1/α |
| **青绿工笔素材与整镜** | `NOT_RUN` | 仓库内没有任何宽幅静帧；横移需要 `scaled_width > 1080`，必须先生成宽幅静帧与独立前景资产 |

合成验证用的是画出来的色块（`experiments/m8_parallax/pan_check/`），**只证明几何，不证明观感**。

由此得到的青绿工笔约束：

- 长卷镜头必须**从一开始就按宽幅出图**（高度 1920 时宽度 > 1080），不能事后裁剪；
- 近层的安全边距 = `(1/alpha - 1) × 总横移量`；`alpha=0.6`、横移 120 px 时，近层比背景多走 80 px，画板两侧各需 ≥40 px 余量；
- 独立前景资产在横移下会**滑出画框**，这是正常视差，不算缺陷；但全幅切图滑出自己的画板就是缺陷。

## 13. M8-D 第二步：青绿工笔长卷整镜（2026-11-04）

素材（均本机生成，记录在 `experiments/m8_plates/runs/*/run.json`）：

| 件 | 规格 | 说明 |
|---|---|---|
| 宽幅静帧 | 1600×1024，59.5 s | 宋代院体青绿，石青石绿，层叠远山、江岸楼阁、近景坡石松树 |
| 独立前景 | 487×673 RGBA，20.0 s | 石绿松枝折枝，纯白绢底 → 颜色键出 alpha（覆盖 21.0%） |

成镜：`bg`（full_frame, α=1.0）+ `pine`（generated_asset, α=0.55）→ `scroll_pan` 6 s。
`check=PASS`，`MOTION_QUALITY_OK`（补底 `NO_REPAIR`、无锁定区域、时序 PASS）。

逐层窗口实测（manifest）：背景 `0.290 → 0.350`，前景 `0.290 → 0.399`；Δ 0.06 vs 0.109 = **1/0.55**，与设计一致。首末帧对照里松枝明显左移、背景岸线几乎不动。

### 13.1 两个被真实素材打出来的缺陷

**一、亮度键对青绿资产失效。** 石绿是浅色矿物颜料压在近白绢上，按"深墨"取 alpha 只能留下最黑的几笔（覆盖率 0.1%）。改为**按与纸色的距离取 alpha**（纸色取四边中位数），覆盖率 21.0%，松针与枝干完整。这条正是 B2 报告 L3 预警的情形，现在有了实现与实测。

**二、宽幅板下的窗口跨度算错。** 9:16 画框只覆盖宽幅板宽度的 `1080/3000 = 0.36`，而我最初按 1.0 计算窗口跨度，横移一帧就把窗口推出板外——成片右侧出现整块黑边。窗口改为 **(x0, y0, span_x, span_y)** 四元组后修正。

第二条影响面更大：**任何宽幅板的分层横移都会黑边**，而窄板（9:16）不会暴露它。这正是"只有真实素材才会打到"的缺陷，与合成色块验证无关。

### 13.2 状态

`PARTIAL`（技术通过，人工待审）。青绿资产与画面的风格是否一致、长卷节奏是否成立，仍需人工看片；M8-D 的"两套风格策略"才刚有第一镜。

## 14. 收口：视差策略进 `config/styles.yaml`（2026-11-04）

此前 `compositing.parallax` 只有 `allowed: false` 与一句说明，**没有任何消费者**——典型死配置。现在它是一条会被渲染器执行的策略：

| 字段 | 含义 | 消费者 |
|---|---|---|
| `allowed` | 风格是否允许分层镜头 | `motion.plates.enforce_policy` → 渲染器拒绝 |
| `camera_moves` | 允许的分层镜头类型 | 同上 |
| `max_plates` | 图层上限 | 同上 + `build_motion_plan` |
| `depth_alpha_min/max` | 内层深度系数区间（背景固定 1.0，不参与） | `enforce_policy` + `build_motion_plan` |
| `background_margin` | 背景窗口两侧必须留出的画板比例 | 渲染前逐帧预检，越界直接拒绝 |

两种风格的取值都来自本阶段实测，不是拍脑袋：

```yaml
ink_wash:                  court_green_fine_line:
  allowed: true              allowed: true
  camera_moves:              camera_moves:
    [slow_push_in,             [scroll_pan, slow_lateral_track,
     slow_pull_out]             slow_push_in]
  max_plates: 3              max_plates: 3
  depth_alpha: 0.45–0.85     depth_alpha: 0.50–0.75
  background_margin: 0.0     background_margin: 0.05
```

差异的理由：水墨这一镜是推拉（窗口只缩不平移，没有走出画板的风险，余量取 0）；青绿是横移，近层按 1/α 多走，窗口会平移，必须留边。

另外新增门 `check_plate_bounds`：从计划几何独立复核背景窗口是否始终落在画板内——这正是宽幅板黑边那个缺陷的守门人，且不依赖渲染器。

状态：`PASS_STATIC`（策略有消费者、有单测、两个风格各一镜在新策略下重渲通过）。
