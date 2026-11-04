# M8-0 项目状态审计（只读）

> 执行日期：2026-11-04
> 范围：M8「高质量动态表现与 2.5D 分层视差」的前置审计。**本轮不修改任何生产代码、配置、质量门或工作流**。
> 状态口径：`docs/PRD.md` §0.2（`PASS_VERIFIED` / `PASS_STATIC` / `PARTIAL` / `NOT_RUN` / `BLOCKED`），另加本阶段专用的 `PENDING_HUMAN_REVIEW`。
> 判断原则：配置文件里出现过、或节点名存在，都不等于能力成立。凡是本轮没有实际执行过的，一律不写通过。

## 0. 结论

| 项 | 状态 | 依据 |
|---|---|---|
| 工作区干净可冻结 | `PASS_VERIFIED` | HEAD `06f91e4`，`main`，`git status` 无改动、无未跟踪文件 |
| 测试基线 | `PASS_VERIFIED` | `.venv\Scripts\python.exe -m pytest` → `246 passed` |
| M1–M4、M6、M7 | `PASS_VERIFIED`（技术 + 人工，见各自报告） | 见 §2 |
| M5 Wan 运动遮罩 | `NOT_RUN (UNSUPPORTED_WORKFLOW)` | [M5_WAN_MOTION_MASK_REPORT.md](M5_WAN_MOTION_MASK_REPORT.md) |
| 2.5D 分层视差 | `NOT_RUN` | `parallax.allowed=false`；`layered_parallax` 在渲染入口显式拒绝 |
| 人工审美项 | `PENDING_HUMAN_REVIEW` | [AESTHETIC_DESIGN_REPORT.md](AESTHETIC_DESIGN_REPORT.md)、[S2_TEST_REPORT.md](S2_TEST_REPORT.md) |

**一句话**：项目已有相机、区域权限、刚体保护、局部微动、FFmpeg 合成与三层质量门；2.5D 是唯一被**显式预留并显式关闭**的能力。M8-A 因此是"点亮一个已声明但被拒绝的分支"，不是新建系统。

## 1. Git 与基线

| 项 | 值 |
|---|---|
| 分支 | `main` |
| HEAD | `06f91e4` `feat(pipeline): complete M1-M7 motion refactor, semantic protection, and smooth recitation pipeline` |
| 工作区 | 干净（`git status --porcelain` 空），无未跟踪文件 |
| 约定 | 本轮不执行 `git reset` / `git clean` / `commit` / `push` |

`experiments/`、`runtime/`、`logs/`、`.venv/` 均在 `.gitignore` 内：实验产物不进入版本库，符合"生成证据本地留存"的仓库边界。

## 2. 阶段状态（只依据各报告与实盘）

| 阶段 | 状态 | 证据位置 |
|---|---|---|
| M1 区域语义与运动权限 | `PASS_STATIC` + 真实渲染 | [M1_REGION_PROTECTION_REPORT.md](M1_REGION_PROTECTION_REPORT.md) |
| M2 局部运动算法 | `PASS_STATIC` + 真实渲染 | [M2_MOTION_ALGORITHMS_REPORT.md](M2_MOTION_ALGORITHMS_REPORT.md) |
| M3 相机/遮罩坐标对齐 + 质量门 | 已接入 `motion.render` 与 `quality.check` | [M3_QUALITY_GATES_REPORT.md](M3_QUALITY_GATES_REPORT.md) |
| M4 转场 | 已固化 | [M4_TRANSITIONS_REPORT.md](M4_TRANSITIONS_REPORT.md) |
| M5 Wan 运动遮罩 | `NOT_RUN (UNSUPPORTED_WORKFLOW)` | [M5_WAN_MOTION_MASK_REPORT.md](M5_WAN_MOTION_MASK_REPORT.md) |
| M6 发音/吟诵 | 已交付（5 条谐音转 `verified`） | [M6_PRONUNCIATION_REPORT.md](M6_PRONUNCIATION_REPORT.md) |
| M7 双风格成片 | 水墨 `PASS_VERIFIED`（技术 + 人工） | [M7_FINAL_DELIVERY_REPORT.md](M7_FINAL_DELIVERY_REPORT.md) |
| S1 双风格规范与配置 | `PASS_STATIC` | [VISUAL_STYLE_SPEC.md](VISUAL_STYLE_SPEC.md) |
| S2 双风格样片 | `PARTIAL`（技术通过，人工待审） | [S2_TEST_REPORT.md](S2_TEST_REPORT.md) |
| 静态质量门（管线） | `PARTIAL`（山石纹理重复） | [PIPELINE_AB_VALIDATION.md](PIPELINE_AB_VALIDATION.md) |
| 镜头美学 A/B | `PARTIAL` + `PENDING_HUMAN_REVIEW` | [AESTHETIC_DESIGN_REPORT.md](AESTHETIC_DESIGN_REPORT.md) |

### 2.1 `PENDING_HUMAN_REVIEW` 清单（M8 不得绕过）

- 镜头美学 A/B：8 张实图、自动指标与联系表已生成，人工美学结论 `PENDING_HUMAN_REVIEW`。
- 动态美学：`quality --aesthetic-motion` 两段 `risk_severity=ok`，人工 PENDING。
- S2 水墨/工笔：云气速度、水面幅度、纸纹强度、"像不像写意水墨 / 院体青绿"待人工看片。
- 管线 A/B 样片：人工看片 PENDING。

这些项的结论不因 M8 而改变；M8-A 只是新增一组对照样片供同一批人工审片。

## 3. 代码实盘：2.5D 相关的真实实现

### 3.1 相机的真实能力

`src/drama_studio/motion/camera.py` 实现 `static` / `slow_push_in` / `slow_pull_out` / `scroll_pan` / `slow_lateral_track` / `push_in_with_pan`，全部为 `t` 或 `on` 的确定性表达式。链路为 `camera_pre`（缩放到源图比例中间画布）→ 局部图层合成 → `camera_post`（裁切 / zoompan）。这条链路保证遮罩与主体经过同一变换（M3 的工作）。

`CameraMove` 字面量里还有第七项 `layered_parallax`。

### 3.2 `layered_parallax` 的声明、关闭位置与调用链

| 环节 | 位置 | 现状 |
|---|---|---|
| 类型声明 | `style_presets.py` `CameraMove` | 合法值 |
| 文本识别 | `motion/spec.py` `_classify_motion`（含"视差 / parallax"） | 会解析出 `layered_parallax` |
| 相机解析 | `motion/spec.py` `resolve_camera` | 不在任何 style 的 `allowed` 列表中 → 回落为默认并记录 `fallback_reason` |
| 渲染入口 | `motion/render.py:159` | 显式 `raise ValueError("layered_parallax needs explicit background/foreground layers; this shot has none")` |
| 风格策略 | `config/styles.yaml` 两种风格 | `compositing.parallax.allowed: false`，`requires: 可靠的图层分层或深度图；单张图片平移不算 2.5D 视差` |
| 状态描述 | `docs/VISUAL_STYLE_SPEC.md` | 能力表 `2.5D Parallax = NOT_RUN` |

结论：2.5D 在**类型系统里已经存在**，在**策略里被禁止**，在**渲染器里被拒绝**。三处一致，不存在"半实现"。

### 3.3 区域契约与刚体保护的真实实现

- `RegionSpec`：7 种 `role`（`rigid_object` / `fluid_surface` / `reflection` / `vegetation` / `atmosphere` / `background` / `independent_overlay`）× 4 种 `permission`（`locked` / `hard_excluded` / `controlled` / `allowed`）。校验器强制：`rigid_object` 只能 lock/exclude；`reflection` 必须 `follows` 一个 `rigid_object`；`controlled` 只能接受该 role 允许的运动类型。
- `local.effective_exclusions`：`locked` / `hard_excluded` 区域会**自动从任何与它相交的局部图层 alpha 中扣除**；`reflection` 区域自动从非倒影图层中扣除。
- `quality.check_rigid_protection`：把区域框按**单一全局相机**逐帧映射后追踪，三路信号（帧间差、p95 差、边缘 bbox 漂移），阈值 `mean_diff_max=6.0` / `p95_diff_max=22.0` / `edge_shift_pct_max=0.06`。
- `quality.check_motion_quality`：逐镜头刚体检查 + 整段时序连续性。

**对 M8 的直接含义**：`check_rigid_protection` 的输入是"一个相机 + 若干区域框"。多图层各自不同相机时，这套假设不成立。M8-A 因此**不调用也不修改**它，另写独立检查（见 3.4）；正式扩展留到 M8-B。

### 3.4 现有可复用的测量与合成工具

| 工具 | 作用 | M8-A 是否复用 |
|---|---|---|
| `motion/texture.make_texture` | 生宣/绢本纸纹，FFmpeg `blend=overlay` 叠加 | 复用（A/B/C 同强度 0.14） |
| `motion/local.mesh_warp` | 网格位移场（Pillow MESH） | 复用（C 的水面/倒影） |
| `motion/local.water_displacement` / `reflection_displacement` | 透视衰减低频行波 / 倒影垂直位移 | 复用（C 与生产同款算法） |
| `quality.check_video` / `check_image` | 尺寸、时长、解码、黑帧 | 复用（A 由生产渲染器内部调用） |
| `scripts/visual_audit.py` | 逐帧 luma、闪烁、暗物轨迹、切点 | 未调用（指标不同，见报告 §4） |
| `scripts/compare_motion.py` | 两版本同镜头对照 | 未调用 |

### 3.5 依赖边界（实盘）

| 环境 | 内容 | 结论 |
|---|---|---|
| 根 `.venv`（Python 3.12.10） | 无 numpy / torch / cv2 / scipy；有 pillow 13.0.0、pypinyin 0.55.0 | 一切分层与合成只能用 Pillow + FFmpeg |
| `runtime/ComfyUI/.venv` | torch 2.15.0+xpu、torchvision、numpy 2.5.4、scipy；无 cv2 / onnxruntime | `src/` 不得导入（不变量 #1） |
| `runtime/ComfyUI/custom_nodes` | 仅 `ComfyUI-GGUF` | 无第三方深度/分割节点 |

## 4. ComfyUI 引擎实盘（DA3 / VACE / TrackToVideo）

引擎：ComfyUI `0.43.0`，`runtime/ComfyUI` HEAD `bb878b9e`（2026-11-02），本轮**未启动**（8188 未监听）。

| 能力 | 节点是否存在 | 输入/输出实盘 | 权重是否具备 |
|---|---|---|---|
| Depth Anything 3 | 是：`LoadDA3Model` / `DA3Inference` / `DA3Render` / `DA3GeometryToMesh` / `DA3GeometryToPointCloud` | `DA3Inference` 输入 `da3_model, image, resolution, resize_method, mode(mono/multiview)`；单目输出 `depth`（必有）、`confidence`、`sky`（按 head 类型） | **否**：`D:\AI\models` 无 `geometry_estimation` 目录，`config/comfyui_extra_model_paths.yaml` 也未映射该类别 |
| Wan VACE（`control_masks`） | 是：`WanVaceToVideo` | 输入 `positive, negative, vae, width, height, length, batch_size, strength, control_video?, control_masks?, reference_image?`；内部把 mask 拆成 reactive/inactive 两路 latent | **否**：需要 VACE 版权重，现有 `Wan2.2-TI2V-5B-Q4_K_M.gguf` 不适用 |
| Wan 轨迹控制 | 是：`WanTrackToVideo`、`WanMoveTracksFromCoords`、`GenerateTracks`、`WanMoveConcatTrack`、`WanMoveVisualizeTracks` | `WanTrackToVideo` 输入含 `tracks`(JSON) 与 `start_image`，把轨迹编码成 motion latent | **未验证**：节点存在，但 5B TI2V 权重是否接受该条件未实测 |
| Wan 首尾帧 / Fun Inpaint | 是：`WanFirstLastFrameToVideo`、`WanFunInpaintToVideo`、`Wan22FunControlToVideo` | 与 TI2V 同一模型的其它条件路径 | 权重可用性未验证 |

**对 M8 的直接含义**：接入遮罩/轨迹能力的瓶颈是**权重与实测**，不是节点缺失。安装 `ComfyUI-WanVideoWrapper` 不会补上这个缺口，反而引入与锁定引擎版本冲突的风险。M8-C 的正确形态是"引擎内节点的权重与性能评估"，与 M5 的结论一致。

## 5. 实验素材盘点

| 素材 | 路径 | 规格 | provenance |
|---|---|---|---|
| 孤舟水墨静帧（本轮 M8-A 首选） | `experiments/m7_final/ink/work/images/shot_001/out.png` | 576×1024 RGB，834 236 B，sha256 `861de8fd…32cc9` | 原始生成：`experiments/aesthetic/ink/work/aesthetic/snapshots/snapshot-20261104-064902-104/images/shot_001/A/shot_001_A_00001_.png`；同哈希副本另见 `experiments/m4_transitions/work/images/shot_001/out.png`；生成参数见该快照 `A/provenance.json`（seed_base 8100、576×1024、steps 4、cfg 1.0、`workflows/r0_flux_t2i_api.json`） |
| 水墨山水（旧） | `experiments/pipeline_a/static/IA4/IA4_ink_landscape_00001_.png` | 576×1024 | `job.json` / `history.json` 同目录 |
| 工笔样片 | `experiments/aesthetic/court/baseline/shot_00{1,2}.png` | 576×1024 | 同快照结构 |

画面结构（M8-A 分层依据）：远景雾山与天光、中景岸线与木构、近景孤舟＋桅杆＋倒影、最前景左右两株枯树与土坡山石。

## 6. 风险清单

| 编号 | 风险 | 影响 | 本轮处置 |
|---|---|---|---|
| R1 | 项目无分割模型，图层只能手工或几何构造 | 2.5D 的收益上限由"图层从哪来"决定，不由深度精度决定 | M8-A 用手写盒子 + 亮度阈值 + 逐行补底 |
| R2 | 平坦画面抠层必然在背景留洞 | 补不干净就会出现色块或重复纹理 | 补底用相邻真实水面的逐行插值；可见范围量化上报 |
| R3 | `check_rigid_protection` 假设单一全局相机 | 多图层直接套用会全量误判 | M8-A 不调用、不修改；另做独立检查 |
| R4 | 逐像素深度 warp 与刚体门数值冲突 | 船头船尾被赋予不同缩放即触发 `edge_shift` | M8-A 完全不用深度，用分层刚性变换 |
| R5 | 根 `.venv` 无 numpy | 一切度量必须用 Pillow 或 FFmpeg | 全部实现走 Pillow |
| R6 | 焦点 `y=0.48` 使 zoompan 窗口在低位被 clamp | 各图层 clamp 释放时刻不同，产生瞬时相对跳变 | 实测并量化（见 M8-A 报告 §4.5） |
| R7 | 只有 8 GB A750 且 GPU 租户互斥 | DA3 在 XPU 上的耗时/显存未知 | M8-A 不启动 ComfyUI；DA3 留到 M8-C 单点实测 |
| R8 | 人工审美仍是 `PENDING_HUMAN_REVIEW` | 技术通过不等于可上线 | M8-A 明确以人工看片为最终判据 |

## 7. M8-A 的边界（本轮不做）

- 不修改 `RegionSpec` / 新增 `PlateSpec` / `ParallaxSpec` 正式契约。
- 不改造 `render.py`，不修改 `check_rigid_protection` 的全局逻辑。
- 不在 `workspace/tasks.py` 注册新任务类型。
- 不下载 DA3 / VACE 权重，不安装 `MoviePy` / `DiffSynth-Studio` / `ComfyUI-WanVideoWrapper`。
- 不修改两种风格的正式生产配置与质量门。

## 8. 本轮实际写入

| 类型 | 路径 | 说明 |
|---|---|---|
| 新增实验工具 | `scripts/m8_parallax.py` | `layers` / `render --variant A\|B\|C` / `metrics` 三个子命令；不导入 `runtime/ComfyUI`，只读导入 `drama_studio` |
| 实验产物 | `experiments/m8_parallax/` | plan、layers、renders、metrics、inspect（`.gitignore` 内） |
| 文档 | 本文件、[M8_A_PARALLAX_REPORT.md](M8_A_PARALLAX_REPORT.md) | — |

生产代码 `src/`、`config/`、`workflows/`、`tests/` 本轮零改动（`git status` 可核）。
