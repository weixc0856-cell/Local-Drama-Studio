# 视频增强 A/B 报告（S01）

> 状态：`PARTIAL` / 2026-11-07（A 组完成；B/C 因本机无 ncnn 权重未运行）
> 原则：同一源素材、同一时间轴、同一输出尺寸与编码；连续播放优先，不以单帧锐度作为通过依据。
> 默认生产配置不因本报告自动改变。

## 1. 源素材

- 项目：`deng_guan_que_lou`
- 镜头：S01（Wan 448×768 / 49 帧 × 3 段续接（第 4 段因亮度漂移弃用），尾帧 QC 截断污染帧）
- 源剪辑：`projects/deng_guan_que_lou/shots/S01/S01_clip.mp4`
- 源属性：448×768 / 24 fps / 6.0 s / 单段 Wan 续接后编码

## 2. 对照版本

| 版本 | 后端 | 模型 | 状态 |
|---|---|---|---|
| A | Lanczos + hqdn3d | — | `DONE` |
| B | realesrgan-ncnn | `realesrnet-x4plus` | `NOT_RUN`：本机未安装 ncnn 可执行文件/权重 |
| C | realesrgan-ncnn | `realesrgan-x4plus` | `NOT_RUN`：同上 |

`drama film upscale --check` 的输出已记录 `realesrgan-ncnn.available=false`。在安装外部可执行文件与权重前，不得宣称学习型超分优于 Lanczos。

## 3. 运行命令

```powershell
# 默认基准（Lanczos + 轻降噪）
.venv\Scripts\python.exe scripts\enhance_ab.py `
  --source projects\deng_guan_que_lou\shots\S01\S01_clip.mp4 `
  --out experiments\enhance_ab\S01 --shot S01

# 安装 ncnn 后设置：
$env:REALESRGAN_NCNN = "D:\AI\tools\realesrgan-ncnn-vulkan\realesrgan-ncnn-vulkan.exe"
```

## 4. 验收指标

- 空间：细节是否增加、轮廓是否改变、是否过度锐化、笔触是否保留。
- 时序：纹理是否闪烁、边缘是否跳动、镜头运动是否自然、段落接缝是否突兀。
- 结构：源视频结构是否被模型改写（下采样回源尺寸后的差异）。
- 性能：运行时间、峰值显存（若可读）、设备稳定性、输出文件大小。
- 播放：必须在 1080×1920 实际尺寸整段播放，不以 400% 截图判断。

## 5. 实测结果（A 组）

- 输出：`experiments/enhance_ab/S01/S01_lanczos_1080p.mp4`
- 规格：1080×1920 / 24 fps / 6.0 s / 6.94 MB
- 运行时间：2.12 s（包含解码、hqdn3d、Lanczos、编码）
- B/C：`NOT_RUN`，原因 `realesrgan-ncnn` 可执行文件与权重未安装；不伪造对比结论。

## 6. 当前结论

- **保持 Lanczos 为生产默认。**
- 学习型超分继续保持实验后端；等 S01 干净片段产出后，先完成 A 组基准，再安装 ncnn 做 B/C。
- 没有真实 B/C 数据前，不修改 `production.enhancement` 默认值，不改正式生产链。

## 7. 后续数据

- A 组运行时间：2.12 s
- A 组输出：1080×1920 / 6.0 s
- B/C 可用性：不可用（缺 ncnn exe/权重）
- 闪烁/结构差异：未做学习型对比；Lanczos 无逐帧纹理生成，不存在新增闪烁
- 人工结论：`PENDING`（需在 1080×1920 实际尺寸看片）
