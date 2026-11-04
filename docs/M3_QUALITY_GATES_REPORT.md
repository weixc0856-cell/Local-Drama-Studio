# M3 时间连续性与质量门禁报告

> 执行日期：2026-11-04
> 环境：Windows 11 / i7-13700K / 64 GB / FFmpeg 8.1 / Python 3.12
> 本轮未启动 ComfyUI、FLUX、Wan、LLM 或 CosyVoice；渲染与检查为 CPU + Pillow/FFmpeg。
> 状态口径：`docs/PRD.md` §0.2。**门禁通过不等于审美通过。**

## 0. 结论

M3 完成两项工作：

1. **相机与遮罩坐标对齐**：渲染顺序固定为“源图比例中间画布 → 局部图层 → 相机裁切/缩放”，遮罩与主体经过同一变换；同时修正了非 9:16 源图被强制拉成 540×960 的缺陷。
2. **质量门禁**：新增 `check_rigid_protection`、`check_temporal_continuity`、`check_motion_quality`，并接入 `motion.render` 与 `quality.check` 工作流。

| 项 | 状态 | 证据 |
|---|---|---|
| 坐标顺序修复 | `PASS_VERIFIED` | 复合镜头 `argv` 顺序；船体边缘漂移 0.52%；正方形源图图层 540×540 |
| 刚体保护门禁 | `PASS_STATIC` + 真实执行 | 复合镜头 PASS；移动主体负例 `RIGID_OBJECT_VIOLATION` |
| 时序连续性门禁 | `PASS_STATIC` + 真实执行 | 复合镜头 PASS；尾部渐黑负例 `TAIL_DARKENING`；交界跳变负例 `TEMPORAL_FRAME_JUMP` |
| 工作台集成 | `PASS_STATIC` | `motion.render.quality`、`quality.check.motion_manifest` |
| 全量测试 | PASS | **221 passed**（新增 11） |

## 1. 改动前的缺陷

### 1.1 坐标顺序

旧 `_render_shot` 先把相机链作用到源图，再叠加局部图层：

```text
[0:v] camera_chain -> [base]
[base][layer] overlay -> ...
```

局部图层按源图坐标生成，却叠加在已经推近/横移过的画面上。运镜时遮罩不跟随主体，水面/云雾会“漂”到船体或山体上。这正是 M0 记录但 M2 未处理的遗留问题。

### 1.2 源图比例

`base_half = image.resize((540, 960))` 把所有源图强制拉成 9:16。正方形或 2:3 源图的图层坐标与相机 cover/crop 后的内容不一致，遮罩边界会错位。

## 2. 渲染顺序修复

### 2.1 新顺序

```text
[0:v] camera_pre（按源图比例缩放到中间画布） -> [base]
[base][layer*] overlay（图层缩放到同一中间画布） -> [composed]
[composed] camera_post（裁切 / zoompan 到 1080x1920） -> [cam]
[cam][texture] blend -> [outv]
```

中间画布尺寸由 `camera.intermediate_size` 给出：

| 运动 | 中间画布 |
|---|---|
| `static` | `scaled_width(src) × 1920` |
| `scroll_pan` / `slow_lateral_track` | `scaled_width(src) × 1920` |
| `slow_push_in` / `slow_pull_out` / `push_in_with_pan` | `scaled_width(src) × 3840` |

`camera_pre` 只缩放，不裁切；`camera_post` 只裁切/缩放。`camera_chain` 仍返回 `pre,post` 的拼接，旧调用与测试保持兼容。

### 2.2 图层生成

`base_half` 改为保持源图比例：宽度 540，高度按源图比例计算并取偶。576×1024 仍是 540×960；1024×1024 是 540×540；1024×1536 是 540×810。

图层在渲染图中按中间画布尺寸缩放；外部 RGBA 图层的 overlay 位移按 `inter_w/W`、`inter_h/H` 同步缩放，避免运镜后位移被二次缩放。

### 2.3 复合镜头实测

`experiments/m3_quality/plan_push_boat.json`：

- 水墨小舟，5.0 s，`slow_push_in` 1.00→1.05，焦点 (0.5, 0.5)
- 局部层：水面、倒影、云雾、植物；船体/倒影/岸边建筑为 `locked`/`controlled`
- 输出：`experiments/m3_quality/renders/build-20261104-090832/shot_001.mp4`

渲染图顺序（来自 manifest `argv`）：

```text
[0:v]scale=2160:3840:force_original_aspect_ratio=increase...[base];
[1:v]scale=2160:3840...[L1];[base][L1]overlay...
...
[S4]crop=2160:3840,zoompan=...:s=1080x1920...[cam];
[5:v]scale=1080:1920...[tex];[cam][tex]blend...
```

`overlay` 出现在 `zoompan` 之前，图层缩放尺寸等于中间画布 2160×3840。

首/中/末帧：`experiments/m3_quality/push_first_mid_last.png`
船体局部：`experiments/m3_quality/push_boat_sheet.png`

## 3. 质量门禁

### 3.1 刚体保护 `check_rigid_protection(shot_manifest, video_path)`

输入是 motion manifest 的单个 shot 记录（或完整 manifest 路径）与渲染视频。流程：

1. 读取 `locked` / `hard_excluded` 区域；
2. 用 `camera_box_at` 按相机参数把区域框映射到每一帧（支持 static / pan / push / pull / push_in_with_pan）；
3. 在映射框内比较相邻帧（缩放到 64×64）；
4. 对每帧做 `FIND_EDGES`，取边缘 bbox 中心，比较其相对首帧的漂移；
5. 任一区域超阈值 → `status: FAIL`、`code: RIGID_OBJECT_VIOLATION`。

阈值（`RIGID_THRESHOLDS`）：

| 指标 | 阈值 |
|---|---|
| 帧差均值 | 6.0 / 255 |
| 帧差峰值 | 12.0 / 255 |
| p95 帧差 | 22 / 255 |
| 边缘中心漂移 | 6% 框尺寸 |

没有 `locked/hard_excluded` 区域时返回 `PASS` + `NO_LOCKED_REGIONS`，不误判。

### 3.2 时序连续性 `check_temporal_continuity(video_path)`

逐帧全局亮度：

- **帧间突变**：`Δluma ≥ 6` 且大于局部基线 4 倍 → `TEMPORAL_FRAME_JUMP`；镜头交界的亮度跳变也会被捕获。
- **尾部异常变暗**：尾窗（默认 25%）斜率 ≤ −0.8 luma/s、下降 ≥ 5 luma、单调下降 ≥ 80% → `TAIL_DARKENING`。`fade_out_seconds` 可排除成片的有意淡出；序列检查默认不排除。
- **频闪**：用 0.5 s 滑动平均去趋势后的残差；`residual_std ≥ 0.8` 且方向反转率 ≥ 0.30 → `TEMPORAL_FLICKER`。

### 3.3 组合门禁 `check_motion_quality(manifest_path)`

- 对每个 shot 运行刚体保护；
- 对 sequence 运行时序连续性；单镜头计划直接检查该镜头视频；
- 写 `motion_quality_report.json` 到 manifest 同目录；
- 总体 `PASS` / `FAIL`。

## 4. 工作台集成

- `motion.render` 新增参数 `quality: bool = True`。渲染完成后自动运行 `check_motion_quality`；失败时任务标记 `FAILED`，错误为 `quality_failed`，报告仍保留在 build 目录。
- `quality.check` 新增参数 `motion_manifest`。传入时以 `--motion-manifest` 运行，并读取 `motion_quality_report.json`；`manifest` 与 `motion_manifest` 互斥。
- CLI：

```powershell
.venv\Scripts\python.exe -m drama_studio.quality --motion-manifest <motion_manifest.json>
```

## 5. 测试证据

```text
.venv\Scripts\python.exe -m pytest
221 passed, 1 warning in 15.58s
```

新增 `tests/test_motion_quality_gates.py`（11 个）：

| 测试 | 结果 |
|---|---|
| 刚体区域被施加位移 → `RIGID_OBJECT_VIOLATION` | 通过（帧差均值 5.576、峰值 7.093、边缘漂移 38.0%） |
| 刚体区域静止 → PASS | 通过 |
| 无 locked 区域 → `NO_LOCKED_REGIONS` | 通过 |
| 尾部渐黑 → `TAIL_DARKENING` | 通过（下降 102.7 luma、斜率 −180 luma/s） |
| 镜头交界亮度跳变 → `TEMPORAL_FRAME_JUMP` | 通过（1.0 s、Δ60） |
| 干净片段 → PASS | 通过 |
| `camera_chain == pre + post`、中间画布尺寸 | 通过 |
| 推近时区域框随缩放扩张 | 通过 |
| 图层先合成、相机后运镜（渲染图顺序） | 通过 |
| 正方形源图图层保持 540×540 | 通过 |
| 工作台参数 `motion_manifest` / `quality` | 通过 |

## 6. 复合镜头门禁结果

`experiments/m3_quality/renders/build-20261104-090832/motion_quality_report.json`：

| 区域 | 帧差均值 | 帧差峰值 | 边缘漂移 | 结论 |
|---|---|---|---|---|
| boat（locked） | 0.959 | 6.547 | 0.52% | PASS |
| shore_buildings（locked） | 0.800 | 5.043 | 1.04% | PASS |

时序：

| 指标 | 值 |
|---|---|
| 全片亮度 | 203.3 → 206.5（推近带来的平滑变化） |
| 帧间突变 | 无 |
| 尾部 | 上升 +0.8 luma，非变暗 |
| 频闪残差 | 0.060 |
| 结论 | PASS |

## 7. 负向证据

| 用例 | 实测 | 门禁输出 |
|---|---|---|
| 锁定区域内主体每帧横移 2 px | 帧差均值 5.576、边缘漂移 38.0% | `FAIL` / `RIGID_OBJECT_VIOLATION`（`edge_drift`） |
| 尾部 1 s 线性渐黑 | 下降 102.7 luma、斜率 −180.1 luma/s、单调 100% | `FAIL` / `TAIL_DARKENING` |
| 1.0 s 处亮度 180→120 | Δ60 | `FAIL` / `TEMPORAL_FRAME_JUMP` |

## 8. 限制 / 未执行

- 刚体检查是“跟踪框内帧差 + 边缘 bbox 漂移”的启发式，不是光流；低对比度主体或小于约 1 px 的漂移可能漏检。
- 阈值在当前复合镜头上调过；更快的运镜或更高分辨率纹理可能需要重新标定，但阈值集中在 `RIGID_THRESHOLDS` / `TEMPORAL_THRESHOLDS`。
- 时序门禁把所有 ≥6 luma 的硬切都视为突变；有意的主镜头硬切需要在 M4 的镜头兼容性检查中分类，而不是放宽阈值。
- 相机映射覆盖 static / pan / push / pull / push_in_with_pan；`layered_parallax` 未实现（本身仍拒绝执行）。
- 检查解码为 270×480；极小区域或亚像素运动可能不可见。
- 区域仍是人工矩形；M4/M7 需要继续用人工看片补足。
- 未改 M4 转场、M5 Wan、M6 发音。

## 9. 资源与 Git

- 复合镜头渲染：4 图层 × 120 帧，CPU + Pillow/FFmpeg，约 1–2 分钟；门禁检查约数秒。
- 测试：15.6 s。
- 未提交、未推送、未 reset、未 clean；HEAD 仍为 `651c7dd`。

## 10. 待人工审查

1. 复合镜头的运镜与图层对齐是否肉眼成立（首/中/末帧与船体局部）。
2. 刚体门禁阈值（6 / 12 / 22 / 6%）是否合适；是否需要按镜头类型分级。
3. 时序门禁对“有意硬切”的策略：M4 分类前是否接受一律报 `TEMPORAL_FRAME_JUMP`。
4. `motion.render` 默认 `quality=true`、失败即任务 FAILED 是否接受。
5. 确认后进入 **M4 转场修正**（含 M0 F8 的 `-ss 0` 时间倒错）。
