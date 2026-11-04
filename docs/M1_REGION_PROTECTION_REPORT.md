# M1 主体保护机制报告

> 执行日期：2026-11-04
> 环境：Windows 11 / i7-13700K / 64 GB / FFmpeg 8.1 / Python 3.12
> 本轮未启动 ComfyUI、FLUX、Wan、LLM、CosyVoice；渲染为 CPU + Pillow/FFmpeg。
> 状态口径：`docs/PRD.md` §0.2。本轮只做 M1（区域语义与运动权限），不改 M2 的局部运动算法。

## 0. 结论

M1 完成。区域语义、运动权限、主体排除与拒绝执行已进入数据契约和渲染链；旧格式仍可读取，但标记为 `legacy`。

| 项 | 状态 | 证据 |
|---|---|---|
| 区域角色 / 权限的数据契约 | `PASS_STATIC` | 16 个新单测；全量 `198 passed` |
| 锁定区域自动排除 | `PASS_STATIC` + 真实渲染 | 水面层 alpha 在船体/倒影核心为 0；manifest `protection.excluded_regions` |
| 拒绝执行并记录原因 | `PASS_STATIC` + 真实渲染 | `layers_skipped` 两条真实原因；结构违规导致 plan 拒绝 |
| 旧 `motion_regions.json` 兼容 | `PASS_STATIC` | legacy 解析测试；现有 182 个测试不回归 |
| 端到端能力 | `PARTIAL` | 已真实渲染保护样片，但运动自然度属 M2，人工看片 PENDING |

## 1. 改动前审计

- `motion_regions.json` 的实际格式是 `{"shots": {"shot_001": [layer, ...]}}`；只有 `mask` 和可选 `exclude_boxes`。
- 没有区域角色、没有权限、没有“主体必须被排除”的强制规则；排除框由作者手填，漏填不会报错。
- 水面、云雾、植物共用同一套 box/band + luma 门控；倒影只是另一个 `water_ripple` 图层。
- `render.py` 的 `_render_shot` 只跳过 `local_policy.enabled=False` 的图层，不校验遮罩有效性。
- 旧 `scripts/pipeline_ink.py` 已有 `boat_mask` / `reflection_mask` / `water_exclude_boxes`，但新 `motion/` 模块没有继承这些语义。

## 2. 数据契约

### 2.1 区域角色与权限

`src/drama_studio/motion/spec.py`：

| 角色 | 含义 | 允许的权限 |
|---|---|---|
| `rigid_object` | 船、人物、建筑、山体等刚性主体 | 只能 `locked` 或 `hard_excluded` |
| `fluid_surface` | 水面 | `controlled` / `allowed` |
| `reflection` | 倒影，必须 `follows` 一个 `rigid_object` | `controlled` / `allowed`（或 `locked` 表示不做倒影动态） |
| `vegetation` | 树、芦苇 | `controlled` / `allowed` |
| `atmosphere` | 云雾、墨雾 | `controlled` / `allowed` |
| `background` | 远山等背景结构 | `locked` / `hard_excluded` / `controlled` |
| `independent_overlay` | 花瓣、飞鸟等独立 RGBA 图层 | `controlled` / `allowed` |

权限语义：

- `locked`：主体不可被任何局部图层覆盖；与之相交的局部图层会自动扣除该区域。若某图层显式指向它，plan 直接拒绝。
- `hard_excluded`：与 `locked` 同样强制扣除；语义上表示“永远不参与局部运动”。二者都记录在 manifest，便于 M3 做保护区差异检查。
- `controlled`：只接受该区域声明的运动类型与幅度/频率上限；超限时该图层被拒绝并记录。
- `allowed`：不额外限制（仍受风格 `local_policy` 与全局幅度上限约束）。

角色默认运动类型（`ROLE_MOTION_TYPES`）：

```text
fluid_surface -> water_ripple
reflection    -> reflection_distortion
vegetation    -> leaf_sway / reed_sway
atmosphere    -> cloud_drift / ink_diffusion
background    -> cloud_drift / ink_diffusion
independent_overlay -> petal_drift / bird_motion
rigid_object  -> （无）
```

### 2.2 文件格式

同一个 `motion_regions.json` 支持两种镜头条目：

```json
{
  "shots": {
    "shot_001": {
      "regions": [
        {"id": "boat", "role": "rigid_object", "permission": "locked",
         "box": {"x0": 0.37, "y0": 0.47, "x1": 0.60, "y1": 0.59}},
        {"id": "reflection", "role": "reflection", "permission": "controlled",
         "box": {"x0": 0.36, "y0": 0.58, "x1": 0.62, "y1": 0.70},
         "follows": "boat", "max_amplitude_px": 2.0},
        {"id": "water", "role": "fluid_surface", "permission": "controlled",
         "box": {"x0": 0.0, "y0": 0.54, "x1": 1.0, "y1": 0.82},
         "max_amplitude_px": 4.0}
      ],
      "layers": [
        {"layer_id": "water", "motion_type": "water_ripple", "region_id": "water",
         "mask": {"kind": "band", "y0": 0.54, "y1": 0.82}, "amplitude": 2.5, "frequency": 0.1}
      ]
    }
  }
}
```

旧格式 `"shot_001": [layer, ...]` 继续可用，解析为 `regions=[]`、`model=legacy`，并在 `motion_plan.meta.json` 的 `regions_model` 中标明。

## 3. 执行规则

### 3.1 自动排除（`local.effective_exclusions`）

对每个局部图层，以下区域会被自动从 alpha 中扣除：

1. 与该图层 mask 相交的 `locked` / `hard_excluded` 区域；
2. 所有 `reflection` 区域（除非当前图层就是 `reflection_distortion` 倒影层）；
3. 图层显式声明的 `exclude_regions`；
4. 图层所属区域自身声明的 `exclude_regions`。

图层自己的区域不会被自己扣除。`mask.exclude_boxes`（旧字段）仍然生效，并在语义区域之前应用。

### 3.2 拒绝执行

| 情形 | 结果 | 记录 |
|---|---|---|
| 图层显式指向 `locked/hard_excluded` 区域 | plan 校验失败，退出码 1 | `区域 boat 是 locked，禁止在其上运行动画` |
| `reflection` 没有 `follows` | plan 校验失败 | `reflection 区域必须 follows 一个 rigid_object 区域` |
| `reflection` 使用 `water_ripple` | plan 校验失败 | `不在区域 ... 允许的类型` |
| `reflection_distortion` 未绑定 reflection 区域 | plan 校验失败 | `必须绑定一个 reflection 区域` |
| 图层缺少 `mask` | plan 校验失败 | Pydantic 缺字段 |
| 扣除后 alpha 覆盖率 < 0.2% | 该图层跳过，镜头继续渲染 | `layers_skipped[].reason = mask_fully_excluded` |
| 幅度/频率超过区域上限 | 该图层跳过，镜头继续渲染 | `amplitude_exceeds_region_cap` / `frequency_exceeds_region_cap` |
| mask 面积 < 0.05% | 该图层跳过 | `mask_area_too_small` |

### 3.3 船体与倒影

- 船体是 `rigid_object + locked`；水面层自动扣除船体。
- 倒影是独立的 `reflection + controlled`，必须 `follows: boat`，只能使用 `reflection_distortion`，并有自己的幅度/频率/相位。
- 水面层与其它非倒影层自动扣除倒影区域，因此倒影不会被水面层的规则驱动。
- 倒影层会自动扣除与它相交的船体区域，避免倒影覆盖船体。

### 3.4 风格配置

`config/styles.yaml` 为两种风格新增 `reflection_distortion` 的 `local_policy`（此前缺失，倒影层会被 `render._render_shot` 拒绝）：

| 风格 | amplitude_px | period_s | opacity | feather_px |
|---|---|---|---|---|
| `court_green_fine_line` | 2.0 | 6.5 | 0.18 | 40 |
| `ink_wash` | 1.5 | 7.0 | 0.16 | 45 |

## 4. 修改文件

新增：

- `tests/test_motion_regions.py`（16 个测试）

修改：

- `src/drama_studio/motion/spec.py`：`RegionSpec`、`RegionRole`、`RegionPermission`、`ROLE_MOTION_TYPES`、`boxes_intersect`、`ShotSpec.regions`、`LocalMotionSpec.region_id/exclude_regions`、plan 级契约校验。
- `src/drama_studio/motion/local.py`：`LayerRefused`、`effective_exclusions`、区域排除、覆盖/上限检查、`alpha_coverage`、`protection` 元数据。
- `src/drama_studio/motion/render.py`：捕获 `LayerRefused` 写入 `layers_skipped`；manifest 增加 `regions` 与 `region_model`。
- `src/drama_studio/production.py`：`_load_regions` 支持 legacy / semantic 两种格式；`build_motion_plan` 写入 `regions`；meta 增加 `regions_model`。
- `config/styles.yaml`：两种风格新增 `reflection_distortion` 策略。
- `docs/VISUAL_STYLE_SPEC.md`、`docs/README.md`：文档索引与契约说明。

## 5. 真实执行证据

全部路径相对于仓库根目录。

### 5.1 测试

```text
.venv\Scripts\python.exe -m pytest
198 passed, 1 warning in 7.51s
```

新增 16 个 M1 测试覆盖：角色/权限校验、锁定区域拒绝、倒影 follows、倒影运动类型、未知区域、缺 mask、自动排除、alpha 核心为 0、倒影不被自己排除、全覆盖拒绝、幅度上限拒绝、legacy 兼容、未知字段拒绝。

### 5.2 真实渲染（保护通过）

```powershell
.venv\Scripts\python.exe scripts\motion_build.py `
  --plan experiments\m1_regions\plan_ink.json `
  --out experiments\m1_regions\renders
```

- 产物：`experiments/m1_regions/renders/build-20261104-084709/`
- 4 个图层全部渲染，`layers_skipped: []`。
- manifest `protection`：

| 图层 | 角色/权限 | 自动排除 | alpha 覆盖率 |
|---|---|---|---|
| water | fluid_surface / controlled | boat, reflection | 0.02954 |
| reflection | reflection / controlled | boat | 0.01571 |
| cloud | atmosphere / controlled | — | 0.23718 |
| trees | vegetation / controlled | — | 0.09329 |

- 水面层 alpha：船体核心最大 0，倒影核心最大 0，全图均值 7.533/255。
- 人眼对照：`experiments/m1_regions/protection_overview.png`（源图区域框 / 水面 alpha / 倒影 alpha / 渲染首帧）。

### 5.3 拒绝执行（运行期）

```powershell
.venv\Scripts\python.exe scripts\motion_build.py `
  --plan experiments\m1_regions\plan_refusal.json `
  --out experiments\m1_regions\renders
```

- 产物：`experiments/m1_regions/renders/build-20261104-084723/`
- 有效图层 `cloud` 正常渲染，镜头 `PASS`。
- `layers_skipped`：

```json
[
  {"layer_id": "water_blocked", "reason": "mask_fully_excluded",
   "details": {"coverage": 0.0, "min": 0.002}},
  {"layer_id": "water_overcap", "reason": "amplitude_exceeds_region_cap",
   "details": {"region": "water", "amplitude": 8.0, "cap": 4.0}}
]
```

### 5.4 拒绝执行（结构违规）

```powershell
.venv\Scripts\python.exe scripts\motion_build.py `
  --plan experiments\m1_regions\plan_invalid_target.json `
  --out experiments\m1_regions\renders
```

- 退出码 1；日志：`experiments/m1_regions/logs/invalid_target.err`
- 错误：`shot_001/water: 区域 boat 是 locked，禁止在其上运行动画`

### 5.5 生产链路

```powershell
.venv\Scripts\python.exe -m drama_studio.production --motion-plan `
  --script experiments\mv\e2e_ink_wash\work\production_script.json `
  --images experiments\mv\e2e_ink_wash\work\assets\images `
  --audio experiments\mv\e2e_ink_wash\work\audio_manifest.json `
  --out experiments\m1_regions\work\motion_shots.json `
  --style ink_wash --regions experiments\m1_regions\regions_e2e_ink.json --align-audio
```

- 输出：`experiments/m1_regions/work/motion_shots.json`（2 镜头 / 7.332 s / 1 转场）
- `motion_plan.meta.json`：`regions_file` 已记录，`regions_model = {"shot_001": "semantic", "shot_002": "semantic"}`
- shot_001 的 5 个区域与 4 个图层均绑定 `region_id`。

### 5.6 旧格式兼容（真实渲染）

```powershell
.venv\Scripts\python.exe scripts\motion_build.py `
  --plan experiments\m1_regions\plan_legacy.json `
  --out experiments\m1_regions\renders
```

- 产物：`experiments/m1_regions/renders/build-20261104-084900/`
- `region_model = "legacy"`，2 个图层正常渲染，`layers_skipped: []`
- `protection`：`region_id=None`、`excluded_regions=[]`（旧格式不提供主体保护）
- 这说明新契约没有破坏现有计划；生产新样片才需要语义区域。

## 6. 未执行 / 边界

- 未改 M2 的水面/云雾/植物算法；本轮只保证“不能越过主体”，不保证“运动自然”。M0 的 F3/F4 缺陷仍在。
- 未改 M4 转场；M0 的 F8（`-ss 0`）仍在。
- 未验证 Wan 能力；M5 仍为 `NOT_RUN`。
- 未做人工审美验收；M1 能力状态最多 `PARTIAL`。
- 未把已有实验的 `motion_regions.json` 全部迁移到语义格式；legacy 仍可读，但不会获得主体保护。生产新样片应使用语义格式。
- 区域边界仍是人工矩形，不是分割模型；矩形画错时保护范围也会错。M3 需要把“保护区差异”作为独立检查。

## 7. 资源与 Git

- 渲染为 CPU + Pillow/FFmpeg；两次单镜头渲染共约 20 s；无 GPU、无网络。
- 未提交、未推送、未 reset、未 clean；HEAD 仍为 `651c7dd`。

## 8. 待人工审查

1. 区域角色/权限的命名与默认运动类型是否接受。
2. `locked` 与 `hard_excluded` 是否保留两个状态（当前行为相同，语义不同）。
3. 倒影只允许 `reflection_distortion` 是否过严（M2 若要改倒影算法，需要在此处扩展）。
4. 拒绝策略：结构违规拒绝整个 plan，运行期违规只跳过图层；是否接受这一分级。
5. 确认后进入 **M2 局部运动修正**。
