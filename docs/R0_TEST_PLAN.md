# R0 可行性验证计划

> 目标：在 Intel Arc A750 8GB 上，确认 **PyTorch XPU → ComfyUI → GGUF 模型 → 实际推理** 这条链路是否成立。
> R0 只验证环境与模型，不开发短剧业务功能。R0 完成后停止，不提前进入 R1。

## 0. 状态定义

| 状态 | 含义 |
|---|---|
| `PASS_VERIFIED` | 实际执行成功，有产物与日志可复核 |
| `PASS_LIMITED` | 能跑，但依赖 CPU offload / 降参数 / 有明显限制，必须写明限制 |
| `FAIL` | 实际执行失败，保留错误日志 |
| `NOT_RUN` | 前置条件不满足，未执行（**不得写成 PASS**） |

硬性约束：

1. 模型下载成功 ≠ 推理成功。
2. ComfyUI 启动成功 ≠ 模型兼容。
3. 不虚构运行结果；没有证据的一律 `NOT_RUN`。
4. 不用 CPU 推理冒充 GPU 推理；若实际走 CPU，必须标 `PASS_LIMITED` 并注明。
5. 失败时保留日志，最多自动重试 2 次。
6. 不擅自升级其他项目依赖，不修改 `D:\AI` 现有脚本。

---

## 1. 公共前置

```powershell
cd D:\Local-Drama-Studio
uv sync --python 3.12
scripts\doctor.ps1
```

证据目录：

```text
logs/r0/
├─ R0-A-doctor.json
├─ R0-B-torch-probe.txt
├─ R0-B-system-stats.json
├─ R0-C-image-*.png / *.json
├─ R0-D-*.mp4 / *.json
├─ R0-E-reload-*.log
└─ R0-comfyui-*.log
```

每次测试记录：时间、命令、退出码、耗时、产物路径、峰值显存、系统内存。

---

## 2. R0-A：硬件与依赖检测

### 步骤

1. `scripts\doctor.ps1`，保存 JSON 报告。
2. 记录 Python、uv、FFmpeg、ffprobe、CPU、内存、GPU、驱动、磁盘。
3. 记录 8080 / 8081 / 8188 / 50000 端口的实际监听状态。

### 验收

- Python 3.12.x、uv、FFmpeg、ffprobe 均为 `PASS_VERIFIED`。
- 能读出 Arc A750 型号与驱动版本。
- 8080 上若被其他实例占用，必须记录（预期 401），并确认项目改用 8081。

### 不需要

- 此阶段不要求 torch / ComfyUI / 模型齐全。

---

## 3. R0-B：ComfyUI 独立运行环境

### 步骤

```powershell
scripts\setup.ps1 -WithComfyUI
scripts\doctor.ps1
scripts\start.ps1
```

验证：

1. `runtime/ComfyUI/.venv/Scripts/python.exe` 存在，且**不等于**根 `.venv` 的解释器。
2. `torch.__version__`、`torch.xpu.is_available()`、`torch.xpu.device_count()`。
3. `GET http://127.0.0.1:8188/system_stats` 返回设备信息。
4. 浏览器可访问 `http://127.0.0.1:8188`。
5. ComfyUI 日志中没有 `CUDA` 相关初始化或回退提示。

### 验收

- `PASS_VERIFIED`：`torch.xpu.is_available() == True`，`device_count >= 1`，设备名为 Arc A750，`/system_stats` 显示 XPU 设备。
- `PASS_LIMITED`：能启动但设备识别为 CPU，或需要额外 offload。
- `FAIL`：torch 无法导入、XPU 不可用、ComfyUI 无法启动。
- `NOT_RUN`：安装未完成。

### 证据

- `logs/r0/R0-B-torch-probe.txt`
- `logs/r0/R0-B-system-stats.json`
- `logs/comfyui.log`、`logs/comfyui.err.log`

---

## 4. R0-C：FLUX.2 klein 4B 静态图

### 前置

补齐配套文件（见 ENVIRONMENT §5）：

```text
D:\AI\models\text_encoders\qwen_3_4b.safetensors
D:\AI\models\vae\flux2-vae.safetensors
```

### 步骤

1. 在 ComfyUI 中加载 `flux-2-klein-4b-Q4_K_M.gguf`（`Unet Loader (GGUF)`）。
2. 加载 Qwen3-4B 文本编码器与 FLUX.2 VAE。
3. 使用官方 klein 参数：**4 步、CFG 1.0、euler/simple、无负面提示词**。
4. 分辨率 512×512，seed 固定 42，生成 1 张。
5. 保存工作流为 **API 格式**：`workflows/flux_character_api.json`。
6. 记录：加载耗时、生成耗时、峰值显存、系统内存、图片路径。
7. 再次以相同参数生成，验证可重复。

### 验收

- `PASS_VERIFIED`：生成 PNG 可正常打开；尺寸 512×512；两次均成功；耗时与显存有记录；执行设备为 XPU。
- `PASS_LIMITED`：可出图但文本编码器或 VAE 在 CPU、或单张耗时超过 10 分钟。
- `FAIL`：GGUF 加载失败、算子不支持、OOM、黑图/全白图。
- `NOT_RUN`：配套文件缺失。

### 证据

- `logs/r0/R0-C-image-01.png`、`-02.png`
- `logs/r0/R0-C-run.json`（prompt_id、耗时、显存、模型 sha256）
- `/history/{prompt_id}` 原文
- `workflows/flux_character_api.json`

---

## 5. R0-D：Wan2.2 TI2V 5B 视频

### 前置

```text
D:\AI\models\text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors
D:\AI\models\vae\wan2.2_vae.safetensors
```

### 步骤

1. **先做 T2V**：512×512，33 帧（4n+1），24fps，10 步起步，seed 42。10 步若出现明显伪影，用 20 步复核（2026-11-02 实测：10 步不可用，20 步正常）。
2. 保存 API 工作流：`workflows/wan_t2v_api.json`。
3. 用 R0-C 的图片做 **I2V**：同分辨率、同帧数。
4. 保存 API 工作流：`workflows/wan_i2v_api.json`。
5. 检查输出 MP4：`ffprobe` 帧率/帧数/时长；`ffmpeg -v error -i out.mp4 -f null -` 全帧解码。
6. 记录峰值显存、耗时、是否触发 VAE 分块解码或 offload。

### 验收

- `PASS_VERIFIED`：T2V 与 I2V 各成功一次；MP4 可播放；时长 ≈ 33/24 ≈ 1.375 秒（允许编码误差）；全帧解码无错误；设备为 XPU。
- `PASS_LIMITED`：需要降帧/降分辨率/CPU offload 才能完成，或 I2V 失败但 T2V 成功。
- `FAIL`：两类都失败、VAE 解码 OOM、输出损坏。
- `NOT_RUN`：配套文件缺失或 ComfyUI 不可用。

### 明确不做

- 不要求 720p、121 帧、整段连续生成。
- 不以画质作为 R0 验收标准。

---

## 6. R0-E：模型互斥、释放与重载

### 步骤

1. 记录空闲显存。
2. 加载 FLUX，生成 1 张图，记录显存。
3. `POST /free {"unload_models": true, "free_memory": true}`，记录释放后显存。
4. 加载 Wan，生成 1 段 33 帧视频，记录显存。
5. 再次 `/free`，重新加载 FLUX 并生成 1 张图。
6. 重复步骤 2-5 两轮，共 3 轮。
7. 全程确认：**任何时刻只有一个生成模型被加载**。

### 验收

- `PASS_VERIFIED`：3 轮全部成功；每轮切换后显存回落到基线附近；无进程重启；无 OOM。
- `PASS_LIMITED`：需要重启 ComfyUI 才能稳定切换。
- `FAIL`：切换后 OOM、崩溃、或必须重启整机。

### 证据

- `logs/r0/R0-E-reload-<n>.log`
- 每轮 `/system_stats` 快照

---

## 7. 执行顺序与停止条件

```text
R0-A ──► R0-B ──► R0-C ──► R0-D ──► R0-E ──► 报告
                  │
                  └─ 配套文件缺失时停在 NOT_RUN，不伪造结果
```

立即停止并写报告的情况：

- XPU 不可用且无法在合理时间内解决。
- 两个 GGUF 在 A750 上都加载失败。
- Wan VAE 在最低参数下持续 OOM 且无可行降级路径。
- 需要修改 `D:\AI` 现有脚本或升级其他项目依赖才能继续。

---

## 8. 交付物

- `docs/R0_TEST_REPORT.md`：每项 PASS_VERIFIED / PASS_LIMITED / FAIL / NOT_RUN，附证据路径。
- `logs/r0/` 下的原始日志与产物。
- `workflows/*_api.json`（成功验证过的那一份）。
- 结论：能否在 A750 上运行、哪些环节需要 offload、是否值得继续 R1-R7、R1 的具体建议。

---

## 9. R0 完成后不做什么

- 不开发 R1-R7 业务功能。
- 不下载额外模型，除非 R0 报告中明确列出并说明原因。
- 不把临时实验脚本固化成正式模块；先写进报告，等对应阶段再实现。
