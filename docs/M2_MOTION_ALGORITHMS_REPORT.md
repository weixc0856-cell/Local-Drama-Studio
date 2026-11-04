# M2 局部运动算法修正报告

> 执行日期：2026-11-04
> 环境：Windows 11 / i7-13700K / 64 GB / FFmpeg 8.1 / Python 3.12
> 本轮未启动 ComfyUI、FLUX、Wan、LLM 或 CosyVoice；渲染为 CPU + Pillow/FFmpeg。
> 状态口径：`docs/PRD.md` §0.2。**算法技术检查通过不等于人工审美通过。**

## 0. 结论

M2 完成。M0 的 F3（水面整层平移/太静）与 F4（云雾整层蒙雾）已从算法层修正；M1 的区域与主体保护契约保留并继续生效。

| 项 | 状态 | 证据 |
|---|---|---|
| 水面：透视衰减 + 低频行波 + 局部位移 | `PASS_STATIC` + 真实渲染 | 12 个新算法测试；远/中/近幅度单调；水面运动 1.218 → 2.309 |
| 倒影：水面相位 + 纵向拖尾 + 禁止横跳 | `PASS_STATIC` + 真实渲染 | 横向位移恒为 0；`|倒影| <= |水面|`；船体/倒影核心 alpha 0 |
| 植物：Y 轴非线性、底部严格 0 | `PASS_STATIC` + 像素级验证 | 底行像素与底图逐像素一致；顶部有衰减 |
| 云雾：平滑流动噪声、无整层平移 | `PASS_STATIC` + 真实渲染 | 静态 alpha；暗部结构差 0.151 → 0.048 |
| 风格默认值偏向“微动、静穆” | `PASS_STATIC` | `config/styles.yaml` 两种风格同步调整 |
| 人工看片 / 审美验收 | `PENDING` | 首/中/末帧切片已生成，等待人工 |

总能力状态保持 `PARTIAL`，直到人工看片。

## 1. 根因回顾（来自 M0）

- **F3 水面**：旧 `water_ripple` 生成一张全画面纹理，整层按 `amplitude*sin(2πft)` 平移；不是局部波动，且幅度极低（C2 水面 10 s 只变化 0.44 luma），既“太静”又“整层滑动”。
- **F4 云雾**：旧 `cloud_drift` 把整张底图作为 rgb 层，alpha 在 `opacity_min..opacity_max` 间振荡，再整层单向位移；云带与树冠重叠时形成缓慢蒙雾/提亮。
- **植物**：旧实现是线性 `(y1-y)/span` 权重，底部为 0，但顶部没有自然衰减，整段像刚性杠杆。
- **倒影**：旧实现与水面共用 `_water_ripple`，没有相位绑定、没有纵向拖尾，也没有横向约束。

## 2. 新算法

所有算法都是确定性的、无随机数、可在纯 Python 中复算。坐标约定：归一化 `x,y ∈ [0,1]`，**图像 y 向下增大**；水面远景是 y 较小的一侧（靠近地平线），近景是 y 较大的一侧。

### 2.1 水面 `water_ripple_v2`

```text
w(y)        = far + (1-far) * smoothstep((y-y0)/(y1-y0))      # 透视衰减
phase(x,y,t)= 2π f t - 2π (x/λx + y/(2.2 λx)) + 2π φ
dx          = A w(y) [0.70 sin(phase) + 0.30 sin(0.61 phase + 1.7)]
dy          = A w(y) r_v sin(phase + 0.9)
```

- `A` 为风格 `amplitude_px`，`λx = wavelength_px / 1080`，`r_v = vertical_ratio`。
- 只有两个不可公度的低频正弦，没有逐像素随机噪声，因此没有高频震颤。
- 远景观测幅度严格低于近景；远/中/近单调性由 `perspective_weight` 保证。
- 渲染方式改为**网格位移**：在 540×960 工作分辨率上用 20×28 网格做 Pillow MESH 变形，每帧生成 RGBA 序列；不再整层平移。

### 2.2 倒影 `reflection_distortion_v2`

```text
current   = dy_water(x,y,t)
lagged    = dy_water(x,y,t-lag)
dy_refl   = clamp(ratio * lagged, |·| <= |current|)
dx_refl   = 0
```

- 只做纵向位移，横向恒为 0，倒影不会脱离水体。
- 位移相位来自水面波，带 `reflection_lag_s` 延迟；瞬时幅度被钳制在水面当前位移以内。
- 渲染前对底图做**纵向拖尾**：5 个垂直偏移副本按 0.12/0.20/0.36/0.20/0.12 加权平均，再叠加纵向位移。
- 倒影层仍然通过 M1 的区域契约自动排除船体，水面层自动排除倒影。

### 2.3 植物 `sway_v2`

```text
p      = (y1-y)/(y1-y0)                  # 0 在根部，1 在顶端
w(p)   = smoothstep(p)^exponent * (1 - top_decay*smoothstep((p-0.75)/0.25))
offset = A w(p) sin(2π f t + 2π φ + 14.4 y)
```

- 根部 `w(0)=0`，像素位移严格为 0；底部行与底图逐像素一致（有测试）。
- 顶部按 `top_decay` 收敛，最大位移出现在上中部，避免刚性杠杆。
- 仍用逐行 affine，保持 CPU 成本低。

### 2.4 云雾 `cloud_drift_v2`

```text
flow  = sin(2π(1.15x + 0.55y) + 0.65 sin(2π(0.45x - 0.35y) + 1.1))
angle = 2π t / period + 2π φ
dx    = A sin(angle + 1.9 flow)
dy    = 0.32 A sin(0.83 angle + 1.4 flow + 0.9)
```

- 空间相位由两个低频正弦调制，形成平滑连续流动；没有整层平移、没有逐帧随机噪声。
- alpha 是静态的（不再有 `opacity_min/max` 振荡），因此没有亮度泵动/蒙雾提亮。
- 网格 18×24；只改变云雾遮罩内的内容。

## 3. 配置变更

`config/styles.yaml` 的 `motion.local_policy`（两种风格同步）：

| 字段 | 水墨 | 工笔 | 作用 |
|---|---|---|---|
| water `amplitude_px` / `period_s` | 2.2 / 13.0 | 2.4 / 11.0 | 更低频、更克制 |
| water `wavelength_px` | 320 | 340 | 更长波长，减少波纹密度 |
| `vertical_ratio` | 0.26 | 0.24 | 纵向位移小于横向 |
| `perspective_far_scale` | 0.12 | 0.14 | 远景幅度衰减到 12%/14% |
| reflection `amplitude_px` / `smear_px` | 1.2 / 3.0 | 1.4 / 3.0 | 独立、纵向拖尾 |
| `reflection_ratio` / `reflection_lag_s` | 0.55 / 0.2 | 0.55 / 0.2 | 倒影 <= 水面，相位延迟 |
| cloud `amplitude_px` / `period_s` | 14 / 24 | 11 / 22 | 平滑、慢速 |
| leaf/reed `amplitude_px` | 1.1 / 1.7 | 1.0 / 1.5 | 微动 |
| `sway_exponent` / `top_decay` | 1.5/0.25, 1.35/0.2 | 1.4/0.2, 1.3/0.2 | 非线性摆动、顶部收敛 |
| 所有新局部层 `opacity` | 1.0 | 1.0 | 位移层替换遮罩内像素，羽化边缘负责融合 |

新增 `LocalPolicy` 字段：`wavelength_px`、`vertical_ratio`、`perspective_far_scale`、`reflection_ratio`、`reflection_lag_s`、`smear_px`、`sway_exponent`、`top_decay`。旧配置仍可加载（字段有默认值）。

## 4. 测试

```text
.venv\Scripts\python.exe -m pytest
210 passed, 1 warning in 10.41s
```

新增 `tests/test_motion_algorithms.py`（12 个），覆盖任务要求的三条硬断言：

| 要求 | 测试 | 结果 |
|---|---|---|
| 植物底部像素位移严格为 0 | `sway_weight(1.0)=0`、`sway_offset(1.0,t)=0`；渲染后底行与底图逐像素一致 | 通过 |
| 倒影位移幅度 <= 水面，且无突变孤立点 | 3×3×120 个 (x,y,t) 采样断言 `|dy_ref| <= |dy_water|`、`dx=0`；80 个时刻的相邻/二阶差分上界 | 通过 |
| 水面远景幅度单调衰减 | `perspective_weight` 全区间单调；远/中/近 `max_t|dy|` 严格递增；远景观测值等于解析包络 | 通过 |

其他覆盖：水面场无高频成分、云雾流场平滑且非刚性平移、云雾 alpha 静态、算法标识写入 manifest、位移场处处有限。

## 5. 真实渲染与前后对比

### 5.1 水墨小舟（4.0 s，静态机位）

- 前：`experiments/m1_regions/renders/build-20261104-084709/shot_001.mp4`（M1 旧算法）
- 后：`experiments/m2_algorithms/ink_boat/renders/build-20261104-090123/shot_001.mp4`
- 计划：`experiments/m2_algorithms/ink_boat/plan.json`（6 区域 + 4 图层）
- 首/中/末对照：`experiments/m2_algorithms/ink_boat/compare_first_mid_last.png`
- 船体/水面局部：`experiments/m2_algorithms/ink_boat/crop_boat_sheet.png`

| 指标（首→中，0–255） | 前 | 后 |
|---|---|---|
| 船体结构差 | 0.044 | **0.009** |
| 倒影结构差 | 0.174 | **0.035** |
| 山体暗部差 | 0.000 | **0.000** |
| 云雾暗部差 | 0.151 | **0.048** |
| 水面运动 | 1.218 | **2.309** |
| 全片帧差均值 | 0.493 | **0.994** |
| 水面残差（去趋势） | 0.049 | **0.048** |
| 云雾残差（去趋势） | 0.051 | **0.221** |

解读：

- 船体与倒影更稳（0.009 / 0.035），山体暗部完全不变（0.000）。
- 水面运动更明显但仍是低频（残差 0.048，无高频闪烁）。
- 云雾残差升高是“流动”本身，不是闪烁；暗部结构差从 0.151 降到 0.048。
- `upper_structure` 带包含云雾区域，因此该带的盒均值会随云雾流动上升；这不是山体泄漏，暗部隔离指标为 0.000。

### 5.2 P1 shot_003（2.112 s，静态机位）

- 前：`projects/proj_p1_short/episodes/ep_p1_short/work/motion/build-20261104-005126/shot_003.mp4`（旧算法，含 0.7 s handle；统计时截到 2.112 s）
- 后：`experiments/m2_algorithms/p1_shot_003/renders/build-20261104-090146/shot_003.mp4`
- 计划：`experiments/m2_algorithms/p1_shot_003/plan.json`（5 区域 + 3 图层；水面显式排除芦苇，远景岸线 hard_excluded）
- 首/中/末对照：`experiments/m2_algorithms/p1_shot_003/compare_first_mid_last.png`

| 指标（首→中，0–255） | 前 | 后 |
|---|---|---|
| 天空结构差 | 0.002 | **0.000** |
| 远水 | 0.036 | **0.175** |
| 近水 | 1.383 | **0.982** |
| 左芦苇 | 1.468 | **0.636** |
| 右芦苇 | 2.171 | **0.860** |
| 全片帧差均值 | 0.397 | **0.341** |

解读：

- 近水运动仍明显，远水保持很小；远/近比约 1:5.6，透视衰减成立。
- 芦苇摆动下降约 55%，符合“微动、静穆”的默认值；底部严格不动。
- 远水比旧算法略高（0.036 → 0.175），因为旧算法几乎不动；仍在“微动”范围内，不是整层平移。

## 6. 限制 / 未执行

- **相机变换与遮罩坐标**：局部层仍按源图坐标生成、在 camera 变换之后叠加；推近/横移镜头里遮罩不跟随内容。本轮样片为静态机位，未暴露；M3 的时间/结构检查或 M4 需要处理。
- **倒影与主体的空间对应**：M2 绑定了相位、幅度上限和纵向拖尾，但没有做光流/像素级对应；极端大位移时仍可能看到倒影与船体错位。
- **区域仍是人工矩形**：保护范围取决于作者画的框；M3 需要独立保护区差异检查。
- **未做人工审美验收**：所有切片等待看片；能力保持 `PARTIAL`。
- 未改 M3 质量门、M4 转场、M5 Wan、M6 发音。
- 未新增依赖、未训练 LoRA、未启动 GPU。

## 7. 资源与 Git

- 渲染：水墨小舟 4 层 × 96 帧，P1 shot_003 3 层 × 51 帧；CPU + Pillow/FFmpeg，约 1–2 分钟/次；GPU 0、无网络。
- 测试：10.4 s。
- 未提交、未推送、未 reset、未 clean；HEAD 仍为 `651c7dd`。

## 8. 待人工看片

1. 水墨小舟：水面是否“平缓阻尼”，船体/倒影是否稳定，云雾是否不再蒙雾。
2. P1 shot_003：远水/近水层次是否自然，芦苇摆动是否过小或过僵。
3. 倒影纵向拖尾强度（`smear_px=3.0`）是否合适。
4. 风格默认值是否“过静”；如需更大动态，只调 `styles.yaml`，不改算法。
5. 确认后进入 **M3 时间连续性与质量门禁**。
