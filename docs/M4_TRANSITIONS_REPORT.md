# M4 转场与时序时间轴修复报告

> 执行日期：2026-11-04
> 环境：Windows 11 / i7-13700K / 64 GB / FFmpeg 8.1 / Python 3.12
> 本轮未启动 ComfyUI、FLUX、Wan、LLM 或 CosyVoice；渲染与检查为 CPU + Pillow/FFmpeg。
> 状态口径：`docs/PRD.md` §0.2。技术检查通过不等于人工审美通过。

## 0. 结论

M4 完成三件事：

1. **修复 F8 时间倒错**：转场左侧从上一镜头的**尾部 handle** 截取，起始时间戳严格大于 0；不再从 `-ss 0` 重放开头。
2. **固化水墨转场算法**：`alphamerge + overlay`，显式拒绝 `maskedmerge`；转场前后做色彩差异检查并在 manifest 中预警。
3. **时序门禁对接**：`check_temporal_continuity` 接受 transition manifest，转场/已知切点处豁免 `TEMPORAL_FRAME_JUMP`；频闪按稳定片段计算，不再被合法转场误伤。

| 项 | 状态 | 证据 |
|---|---|---|
| Handle 截取与断言 | `PASS_VERIFIED` | 真实 2 镜头序列；`left_start=3.852`；0 起点被拒绝 |
| 四种转场帧率/色彩稳定 | `PASS_VERIFIED` | 探针 4/4 通过；24 fps；无黑帧；无 `maskedmerge` |
| 色彩差异预警 | `PASS_STATIC` + 真实执行 | 同风格 ΔE 5.94 无预警；跨风格测试触发 `style_jump` |
| 序列总时长 | `PASS_VERIFIED` | 8.833 s vs plan 8.832 s（误差 0.001 s） |
| 时序门禁豁免 | `PASS_STATIC` + 真实执行 | 硬切负例无 manifest 报错、有 manifest 通过 |
| 全量测试 | PASS | **231 passed**（新增 10） |

## 1. 根因（M0 F8）

旧 `render_transition` 对左侧输入使用：

```text
-ss 0 -t <transition> -i <left clip>
```

而时间轴是：

```text
body0 [0, shot0.duration]  →  transition  →  body1 [trans, shot1.duration]
```

`body0` 已经播到上一镜头的结尾，转场却从上一镜头的**开头**重新开始，于是发生：

```text
上一镜结尾 → 上一镜开头 → 下一镜开头 → 下一镜第 1 秒
```

M0 实测边界帧差 28.04（水墨）/ 47.79（青绿）。纯色静态探针无法发现，因为首尾帧颜色相同。

## 2. 修复内容

### 2.1 Handle 截取

`src/drama_studio/motion/transition.py`：

- `render_transition(..., left_start=None, right_start=0.0)` 先探测左右片段时长；
- `left_start` 默认 `left_clip_duration - transition_duration`，即尾部 handle；
- 断言 `left_start > 0`，否则抛出 `transition left handle must start after 0`；
- 断言 `[left_start, left_start + duration]` 落在左片段内；
- `assemble_sequence` 显式传入 `left_start = 上一镜头计划时长`（handle 的起点），`right_start = 0`；
- 转场记录写入 `timing`：`left_start / left_duration / left_clip_duration / right_start / right_duration / right_clip_duration`。

真实序列（`experiments/m4_transitions/renders/build-20261104-093009/`）：

| 项 | 值 |
|---|---|
| 上一镜头计划时长 | 3.852 s |
| 左片段时长 | 5.052 s |
| 转场左起点 | **3.852 s** |
| 转场右起点 | 0.000 s |
| 转场时长 | 1.200 s |
| 转场文件帧数 | 29 |

### 2.2 帧量化与总时长

- `_trim` 与 `render_transition` 同时使用 `-t` 与 `-frames:v round(duration × fps)`，避免 ceil 产生额外帧；
- `assemble_sequence` 拼接后 ffprobe 实测时长，误差超过 1 帧 + 0.02 s 直接失败；
- `scripts/motion_build.py` 新增 `--expected-seconds`，在构建后再次校验。

真实序列：

```text
plan total      8.832 s
measured        8.833 s
error           0.001 s
frames          212
```

计划由 `--align-audio` 从 `audio_manifest.json` 生成，再追加 1.5 s 尾部留白；最终音频时间轴按同一总时长补齐。

### 2.3 水墨算法冻结

- 非 crossfade 使用 `alphamerge + overlay`；
- 命令拼接后检查 `maskedmerge`，出现即抛错；
- manifest 记录 `algorithm: alphamerge_overlay`（crossfade 为 `xfade`）；
- `make_masks` 的距离场 + 多尺度噪声 + 平滑 LUT 未改变。

### 2.4 色彩差异预警

`colour_check` 采样转场两侧中点帧，计算 Lab 均值、ΔE76 与色度比：

- ΔE > 12 或色度比 > 1.5 → `warning: style_jump`；
- 结果写入每个 transition 记录的 `colour` 字段；
- 真实同风格序列：ΔE 5.937、色度比 0.419、无预警；
- 跨风格测试：灰度 vs 绿色 → 触发 `style_jump`。

预警是 manifest 提示，不直接让构建失败；是否接受跨风格由编辑决定。

## 3. 时序门禁对接

`src/drama_studio/quality.py`：

- `check_temporal_continuity(..., transition_manifest=None)`；
- 从 motion manifest 推导已知窗口：
  - 有转场：`[累计时长, 累计时长 + 转场时长]`；
  - 无转场（硬切）：`[切点 ± 0.05 s]`；
- 落在窗口内的帧间跳变计入 `exempted_jumps`，不再报 `TEMPORAL_FRAME_JUMP`；
- 频闪按稳定片段分别计算（滑动平均去趋势），取最差片段；转场段单独成段，单调亮暗不会被判为频闪；
- `check_motion_quality` 自动把 motion manifest 传给时序检查。

真实 2 镜头序列：

| 项 | 值 |
|---|---|
| 已知窗口 | `[3.852, 5.052]` |
| 帧间跳变 | 无 |
| 频闪残差（最差段） | 2.773（转场段）；振荡率 0.074 → 不判频闪 |
| 序列最大帧差 | **5.38 luma @ 4.33 s** |
| 边界帧差（3.79→3.83 s） | **3.7 luma** |
| 时序结论 | PASS |

对照 M0 的 28.04 / 47.79，边界硬跳已消失。

## 4. 测试证据

```text
.venv\Scripts\python.exe -m pytest
231 passed, 1 warning in 22.12s
```

新增 `tests/test_motion_transitions.py`（10 个）：

| 测试 | 结果 |
|---|---|
| 左侧 handle 从尾部截取（4 s 片段、0.5 s 转场 → 起点 3.5 s；首帧为黄色段而非红色开头） | 通过 |
| `left_start=0` 被拒绝 | 通过 |
| 四种转场输出 24 fps、时长、无黑帧、起止色、混合色、无 `maskedmerge` | 4/4 通过 |
| 跨风格转场触发 `style_jump` | 通过 |
| 硬切携带 transition manifest 时不再误报 | 通过 |
| 转场窗口 `[1.0, 1.4]` 被识别 | 通过 |
| 序列总时长等于 plan total | 通过 |

真实探针（`scripts/transition_probe.py`）：

- 输出：`experiments/m4_transitions/probe/build-20261104-093236/transition_manifest.json`
- crossfade / ink_dissolve / ink_reveal / ink_spread 全部 `ok: true`
- 检查项：`duration_ok`、`fps_ok`、`no_black`、`starts_left`、`ends_right`、`mid_is_mixed`、`colour_planes_stable`、`no_maskedmerge`

## 5. 真实 2 镜头序列

- 计划：`experiments/m4_transitions/work/motion_shots.json`
  - shot_001 3.852 s（白天孤舟）
  - shot_002 4.980 s（月夜孤舟）
  - `ink_dissolve` 1.2 s
  - 音频对齐 + 1.5 s 尾部留白
- 成片：`experiments/m4_transitions/renders/build-20261104-093009/sequence/sequence.mp4`
- Manifest：同目录 `motion_manifest.json`
- 门禁：同目录 `motion_quality_report.json`（总体 PASS）
- 边界对照：`experiments/m4_transitions/transition_boundary_sheet.png`

刚体门禁：

| 镜头 | 区域 | 帧差均值 | 帧差峰值 | 边缘漂移 | 结论 |
|---|---|---|---|---|---|
| shot_001 | boat | 2.088 | 6.157 | 1.04% | PASS |
| shot_001 | shore_buildings | 1.794 | 8.508 | 0.52% | PASS |
| shot_002 | boat | 2.302 | 10.596 | 0.00% | PASS |
| shot_002 | moon/background | 0.205 | 0.799 | 边缘检查不适用 | PASS |

## 6. 限制 / 未执行

- 色彩预警是 advisory，不阻断；跨风格是否可用仍需人工判断。
- 时序门禁豁免的是**已声明**的转场/切点；未声明的硬切仍会报 `TEMPORAL_FRAME_JUMP`，这是有意的。
- 转场时长按帧量化；序列总时长可能有 ≤1 帧的舍入误差（本次 0.001 s）。
- `make_masks` 的缓动曲线未改；水墨溶解在约 88% 处完成显现，属于现有风格行为。
- 探针使用纯色片段，只验证技术项，不代表审美。
- 未改 M5 Wan、M6 发音、M7 验收。

## 7. 资源与 Git

- 2 镜头序列：9 个局部图层，约 212 帧，CPU + Pillow/FFmpeg，约 3–5 分钟；探针 4 个转场约 10 s。
- 测试：22.1 s；GPU 0、无网络。
- 未提交、未推送、未 reset、未 clean；HEAD 仍为 `651c7dd`。

## 8. 待人工审查

1. 2 镜头序列的转场观感（`transition_boundary_sheet.png`）。
2. 色彩预警阈值（ΔE 12 / 色度比 1.5）是否合适。
3. 时序门禁“未声明硬切仍报错”的策略是否接受。
4. 转场时长 1.2 s、尾部留白 1.5 s 是否符合节奏。
5. 确认后进入 **M5 Wan 图生视频独立实验**（先核验工作流是否真的支持运动遮罩；不支持则标 `NOT_RUN`）。
