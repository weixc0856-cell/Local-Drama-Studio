# S2 双核心风格技术验证报告

> 执行日期：2026-11-03
> 环境：Intel Arc A750 8 GB / ComfyUI 0.43.0 / FLUX.2 klein 4B Q4_K_M / FFmpeg 8.1
> 规范：[VISUAL_STYLE_SPEC.md](VISUAL_STYLE_SPEC.md)（S2 阶段）
> 状态口径：`docs/PRD.md` §0.2。**技术检查通过不等于风格验收通过；人工看片未完成前标 `PARTIAL`。**

## 1. 结论

| 项 | 状态 | 说明 |
|---|---|---|
| S2-工笔 长卷片段 | `PARTIAL` | 20.0 s / 1080×1920 / 24 fps；横移、纹理、解码、黑帧、抽样帧全部技术通过；风格审美待人工看片 |
| S2-水墨 显现片段 | `PARTIAL` | 20.0 s / 1080×1920 / 24 fps；柔边遮罩、渗染、纸纹、留白、解码、黑帧、抽样帧全部技术通过；风格审美待人工看片 |
| 确定性动画原语 | `PARTIAL` | 长卷横移、水墨遮罩、墨迹渗染、纸纹已在实验链路真实执行；线描显现、2.5D 视差未做 |
| Wan 局部动态 | `NOT_RUN` | 本轮刻意不调用 Wan，先验证静帧 + 确定性动画 |
| 双风格接入完整链路（S3） | `NOT_RUN` | S2 阶段 8080 被外部实例占用，LLM 链路未执行；本轮结束时 8080 已空闲，仍待人工审查后再进入 S3 |

两段片段都是 **静帧 + 确定性 FFmpeg 合成**，没有使用 Wan。这样先把最可控、最便宜的路线验证清楚，再决定是否需要视频模型补充局部动态。

## 2. 生成输入

| 风格 | 源图 | seed | 尺寸 | 耗时 | 峰值显存 | SHA-256 |
|---|---|---|---|---|---|---|
| `court_green_fine_line` | `experiments/s2a/runs/A1/A1_court_green_00001_.png` | 5201 | 1024×1024 | 49.1 s | 2.73 GiB | `5db5f7bd…380b2b` |
| `ink_wash` | `experiments/s2b/runs/B1/B1_ink_wash_00001_.png` | 5202 | 576×1024 | 16.1 s | 3.11 GiB | `d8d7755e…510ccad5` |

- 工作流：`workflows/r0_flux_t2i_api.json`（已验收的 FLUX.2 文生图）。
- 参数：4 步 / CFG 1.0；完整 prompt、seed、工作流哈希见各自 `job.json`。
- 1024×1024 是本项目第一次在 FLUX 上使用；本轮 1 次成功，记录为新增实测点，不据此承诺稳定性。
- 风格、提示词与色板来自 `config/styles.yaml`（SHA-256 `c03c99f6…af95b5`）。

## 3. S2-工笔 · 宋代院体青绿工笔

### 3.1 片段

- 产物：`experiments/s2a/renders/build-20261103-210443/final_9x16.mp4`
- 20.000 s / 1080×1920 / 24 fps / H.264 yuv420p / AAC 48 kHz 单声道（静音轨）
- 大小 5,182,706 B；视频 SHA-256 `7d229ae2…e80cd1`
- 构建 manifest：`experiments/s2a/renders/build-20261103-210443/build_manifest.json`

### 3.2 做法

1. 1024×1024 静帧按高度放大到 1920（Lanczos），得到 1920×1920 画布。
2. 1080×1920 裁切窗口在 20 s 内从 x=0 线性移动到 x=840；输出空间约 **42 px/s**。裁切不缩放，逐帧没有拉伸。
3. 程序生成 1080×1920 绢纹纹理（低頻噪声 + 3 px 经纬线 + 细颗粒），以 `overlay` 0.12 叠加。
4. 首/中/末帧抽样、全片解码、黑帧检测均在构建时执行。

### 3.3 验收核对

| 验收项 | 结果 | 证据 |
|---|---|---|
| 绢本质感 | 技术通过，审美待审 | `texture_silk.png`（SHA-256 `10d61b03…90fc6`）以 0.12 叠加；抽样帧可见细颗粒 |
| 青绿设色 | 技术通过，审美待审 | 抽样帧保持石青/石绿/赭石色相，未出现灰度或高饱和偏色 |
| 线条细节 | 技术通过，审美待审 | 建筑、树木、水纹在首/中/末帧均保留 |
| 长卷横移 | `PASS` | 裁切窗口 0→840 px，线性、恒定速度 |
| 镜头运动平稳 | `PASS` | 无缩放、无逐帧重采样；`decode_returncode=0` |
| 无明显拉伸/结构破坏 | `PASS`（技术） | 裁切而非缩放；首/中/末帧结构一致 |
| 1080×1920 / 24 fps / 15-30 s | `PASS` | ffprobe：20.000 s、1080×1920、24/1 |
| 无黑帧 | `PASS` | `blackdetect` 0 段 |
| 人工看片 | **PENDING** | 需要人工确认“像不像院体青绿工笔” |

抽样帧：

- `experiments/s2a/renders/build-20261103-210443/frames/frame_first.png`
- `experiments/s2a/renders/build-20261103-210443/frames/frame_mid.png`
- `experiments/s2a/renders/build-20261103-210443/frames/frame_last.png`

## 4. S2-水墨 · 东方写意水墨

### 4.1 片段

- 产物：`experiments/s2b/renders/build-20261103-210408/final_9x16.mp4`
- 20.000 s / 1080×1920 / 24 fps / H.264 yuv420p / AAC 48 kHz 单声道（静音轨）
- 大小 2,748,519 B；视频 SHA-256 `3a607c3c…2481a84`
- 构建 manifest：`experiments/s2b/renders/build-20261103-210408/build_manifest.json`

### 4.2 做法

1. 576×1024 静帧放大到 2160×3840 后做 1.00→1.03 的极缓慢推近（20 s），作为局部动态；没有 Wan。
2. 生成 480 帧 270×480 灰度遮罩：3 个种子点（两处山体与中部云雾）出发的距离场 + 低频噪声扰动，每帧用 256 级 LUT 推进阈值；无二值阈值，边缘保持柔和。
3. FFmpeg 将遮罩放大到 1080×1920 并 `gblur=sigma=6`，与底图 `alphamerge`，叠在 `#EDE4D3` 纸色背景上。
4. 程序生成宣纸纹理（低频斑纹 + 900 条纤维 + 细颗粒），以 `overlay` 0.14 叠加。
5. 墨迹显现约在片长 82% 处完成，之后保持成画。

### 4.3 验收核对

| 验收项 | 结果 | 证据 |
|---|---|---|
| 墨色浓淡层次 | 技术通过，审美待审 | 末帧灰度分布覆盖 8 个 32 级区间（≥1% 像素），满足“≥4 层”的量化下限 |
| 宣纸质感 | 技术通过，审美待审 | `texture_raw_paper.png`（SHA-256 `87ae05e3…3033004`）以 0.14 叠加；抽样帧可见细纹 |
| 留白 | `PASS`（技术） | 末帧 L≥240 像素占 75.7%，源图 76.8%，构图留白未被填满 |
| 自然渗染 | 技术通过，审美待审 | 遮罩 LUT + 高斯模糊，无硬边；3 s / 6 s 过渡帧可见柔和扩散 |
| 墨迹显现与转场 | `PASS`（技术） | 首帧只有山体种子点，3 s 形成墨团，6 s 大部分山体显现，16.4 s 完成 |
| 局部动态自然、不变形 | `PASS`（技术） | 仅 1.03 倍缓慢推近；无 Wan、无主体位移 |
| 1080×1920 / 24 fps / 15-30 s | `PASS` | ffprobe：20.000 s、1080×1920、24/1 |
| 无黑帧 | `PASS` | `blackdetect` 0 段 |
| 人工看片 | **PENDING** | 需要人工确认“像不像写意水墨”，以及显影速度/幅度是否合适 |

抽样帧：

- `experiments/s2b/renders/build-20261103-210408/frames/frame_first.png`（0.5 s，纸面 + 墨种）
- `experiments/s2b/renders/build-20261103-210408/frames/frame_03s.png`
- `experiments/s2b/renders/build-20261103-210408/frames/frame_06s.png`
- `experiments/s2b/renders/build-20261103-210408/frames/frame_mid.png`
- `experiments/s2b/renders/build-20261103-210408/frames/frame_last.png`

## 5. 复现

```powershell
# 1) 启动 ComfyUI（谁启动谁停止）
scripts\start.ps1

# 2) 生成两张风格静帧
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments/s2a/jobs.json --timeout 1800
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments/s2b/jobs.json --timeout 1800

# 3) 构建 20 秒片段（每次写入新的 build-<时间> 目录）
.venv\Scripts\python.exe scripts\s2_build.py --style court_green_fine_line `
  --source experiments/s2a/runs/A1/A1_court_green_00001_.png --duration 20 --out experiments/s2a/renders
.venv\Scripts\python.exe scripts\s2_build.py --style ink_wash `
  --source experiments/s2b/runs/B1/B1_ink_wash_00001_.png --duration 20 --out experiments/s2b/renders

# 4) 停止 ComfyUI
scripts\stop.ps1
```

`scripts/s2_build.py` 只做三件事：生成纹理/遮罩、调用一次 FFmpeg、写 manifest + 抽样帧 + 黑帧检查。没有引入新依赖，也没有新建动画框架。

## 6. 限制与未做

1. **没有使用 Wan**。本轮只验证静帧 + 确定性动画；云雾/水面/飞鸟的真实局部动态仍属 `NOT_RUN`。
2. **线描显现（Line Reveal）未做**；2.5D 视差未做。
3. 纹理是程序生成的中性纹理，不是扫描的绢/宣纸素材；不涉及第三方授权，但也不能替代真实材质素材。
4. 两段片段只有静音 AAC 轨，没有旁白/BGM；本轮只验收视觉。
5. 1080×1920 来自 1024 或 576 源的 Lanczos 放大，不是原生 1080p。
6. 1024×1024 FLUX 只跑了 1 次，不能据此承诺稳定吞吐。
7. **人工审美未完成**：在 PRD §17.2 的 H 类人工门之外，S2 需要一次明确的人工看片结论。看完后：
   - 通过：把对应项从 `PARTIAL` 升为 `PASS_VERIFIED`，并记录人工结论与日期。
   - 不通过：保留 `PARTIAL`，记录问题（显影速度、纹理强度、色相、横移幅度等），调整后重跑。

## 7. 对规范的反馈

- 色板、材质、动画原语与配置边界在真实执行中可用；`config/styles.yaml` 的 `motion` / `compositing` 字段足以描述本轮两种做法。
- 水墨遮罩的“种子点 + 距离场 + 噪声 + LUT”路线不需要新依赖，也不需要 Wan；可作为 S3 之前的默认转场方案候选。
- 横移速度、遮罩软度、纹理强度目前是实验参数，尚未固化为风格规范中的硬阈值；等人工看片结论后再决定是否写入 `VISUAL_STYLE_SPEC.md`。
