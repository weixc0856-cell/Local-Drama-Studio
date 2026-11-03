# R0 测试报告

> 执行日期：2026-11-02
> 主机：Windows 11 Pro 10.0.26300 / i7-13700K / 64 GB / Intel Arc A750 8 GB（驱动 32.0.101.9150）
> 原则：只记录实际执行结果；没有证据的项为 `NOT_RUN`。

## 汇总

| 项目 | 状态 | 说明 |
|---|---|---|
| R0-A 硬件与依赖 | `PASS_VERIFIED` | 见 §1，报告 `logs/doctor-20261102-185031.json` |
| R0-B ComfyUI + XPU | `PASS_VERIFIED` | 见 §2 |
| R0-C FLUX.2 静态图 | `PASS_VERIFIED` | 见 §3 |
| R0-D Wan2.2 视频 | `PASS_VERIFIED` | 见 §4 |
| R0-E 模型互斥/重载 | `PASS_VERIFIED` | 见 §5 |

---

## 1. R0-A：硬件与依赖（PASS_VERIFIED）

### 1.1 实际执行的命令

```powershell
scripts\doctor.ps1
```

### 1.2 结果

| 检查 | 状态 | 实测值 |
|---|---|---|
| Python | `PASS_VERIFIED` | 3.12.10，虚拟环境 `D:\Local-Drama-Studio\.venv` |
| 虚拟环境隔离 | `PASS_VERIFIED` | 根 `.venv`，未安装 torch |
| uv | `PASS_VERIFIED` | 0.10.8 |
| FFmpeg | `PASS_VERIFIED` | 8.1-full_build（gyan.dev） |
| ffprobe | `PASS_VERIFIED` | 8.1-full_build |
| 配置文件 | `PASS_VERIFIED` | settings/models/generation/audio 均可解析 |
| CPU | `PASS_VERIFIED` | i7-13700K，16C / 24T |
| 内存 | `PASS_VERIFIED` | 63.7 GiB |
| GPU | `PASS_VERIFIED` | Arc A750（32.0.101.9150）+ UHD 770（32.0.101.7092） |
| 磁盘 | `PASS_VERIFIED` | D: 剩余 428.2 GiB |
| ComfyUI 服务 | `NOT_RUN` | 8188 未监听（R0-B 前） |
| 项目 LLM 服务 | `NOT_RUN` | 8081 未监听（R4 前不要求） |
| CosyVoice 服务 | `NOT_RUN` | 50000 未监听（R6 前不要求） |
| ComfyUI 安装 | `NOT_RUN` | 当次执行时尚未安装 |
| PyTorch XPU | `NOT_RUN` | 当次执行时尚无独立运行时 |
| 模型配套文件 | `FAIL` | 当次执行时缺 Qwen3-4B / UMT5 / 两个 VAE |

汇总：`PASS_VERIFIED=11 / FAIL=2 / NOT_RUN=5`。两项 `FAIL` 是配套模型文件尚未下载，属于预期，不是硬件问题。

### 1.3 额外实测：端口冲突

```text
netstat: 127.0.0.1:8080 LISTENING (PID 7196)
curl http://127.0.0.1:8080/v1/models
→ 401 {"error":{"message":"Invalid API Key", ...}}
```

结论：8080 被另一个需要 API Key 的实例占用。项目 LLM 端点改为 **8081**，并在 `config/settings.yaml` 中固化。此发现已写入 `docs/ENVIRONMENT.md` 与 ADR-004。

### 1.4 项目环境

- 根 `.venv` 创建成功，`uv sync --python 3.12` 完成。
- `pytest`：11 项全部通过（配置加载、数据契约、状态汇总）。
- `drama doctor` 可运行，写 JSON 报告到 `logs/`。

---

## 2. R0-B：ComfyUI + PyTorch XPU（PASS_VERIFIED）

### 2.1 安装结果

```text
runtime/ComfyUI/.venv/Scripts/python.exe
ComfyUI 0.43.0（commit bb878b9ee35274e67931634ba9e8c338f8c06035，2026-11-01）
torch 2.15.0+xpu / torchvision 0.29.2+xpu / torchaudio 2.11.1+xpu
custom_nodes/ComfyUI-GGUF（gguf 0.19.0）
```

`scripts/setup.ps1 -WithComfyUI` 退出码 0。ComfyUI 依赖安装时过滤了 `requirements.txt` 中的 torch 行，安装完成后复核 `torch.__version__ == 2.15.0+xpu`，未被 PyPI 的 CPU 版覆盖。

### 2.2 XPU 探测

```text
torch 2.15.0+xpu
xpu_available True
device_count 1
device 0 Intel(R) Arc(TM) A750 Graphics 7.75 GiB
```

证据：`logs/r0/R0-B-torch-probe.txt`

### 2.3 ComfyUI 运行状态

```text
GET /system_stats → 200
devices[0] = { type: xpu, index: 0, name: "xpu:0 Intel(R) Arc(TM) A750 Graphics",
               vram_total: 8321540096 }
GET / → 200
```

日志关键行：

```text
[INFO] pytorch version: 2.15.0+xpu
[INFO] Device: xpu:0 Intel(R) Arc(TM) A750 Graphics
[INFO] Using pytorch attention
[INFO] ComfyUI version: 0.43.0
```

证据：`logs/r0/R0-B-system-stats.json`、`logs/comfyui.err.log`

### 2.4 其他验证

- `extra_model_paths.yaml` 生效，`D:\AI\models` 顶层与 `text_encoders/`、`vae/` 子目录均可见。
- 首次映射同时写了 `unet_gguf`，触发 `Unknown file list already present on key unet_gguf` 警告；已移除冗余键并重启，警告消失。
- `scripts/start.ps1` 就绪探测最初使用 `Invoke-RestMethod`，受系统代理影响可能得到 502；已改为 `curl.exe`。
- `scripts/stop.ps1` 最初记录的是 venv launcher PID（子进程才是真实监听者），已改为按进程树 `taskkill /T` 停止，并实际验证可停止。

### 2.5 结论

`PASS_VERIFIED`：PyTorch XPU 在 A750 上可用，ComfyUI 以 `xpu:0` 启动并提供 API。**此时尚未证明任何 GGUF 模型可以推理**，那是 R0-C/R0-D。

---

## 3. R0-C：FLUX.2 klein 静态图（PASS_VERIFIED）

### 3.1 配置

| 项 | 值 |
|---|---|
| 扩散模型 | `flux-2-klein-4b-Q4_K_M.gguf`（2.60 GB，GGUF Q4_K_M） |
| 文本编码器 | `qwen_3_4b.safetensors`（8.04 GB，bf16，**CPU** 加载） |
| VAE | `flux2-vae.safetensors`（336 MB，XPU） |
| 采样 | 512×512，4 步，CFG 1.0，euler，`Flux2Scheduler` |
| 工作流 | `workflows/r0_flux_t2i_api.json`（API 格式） |
| 执行设备 | 扩散模型与 VAE：`xpu:0`；文本编码器：CPU（日志 `CLIP/text encoder model load device: cpu`） |

### 3.2 结果

| 轮次 | 耗时 | 峰值显存 | 产物 |
|---|---|---|---|
| 第 1 次（冷启动） | 99.5 s | 2.61 GiB | `logs/r0/R0-C-flux/flux_t2i_00001_.png` |
| 第 2 次（命中执行缓存） | 2.1 s | 2.60 GiB | `logs/r0/R0-C-flux-run2/flux_t2i_run2_00001_.png` |

- 图片 512×512 RGB，可正常解码，像素标准差约 30（非全黑/全白）。
- 相同 seed 的两次输出像素一致（逐通道 mean abs diff = 0），但第二次仅耗时 2.1 s：这是 ComfyUI **执行缓存命中**，不是冷启动确定性证明。重启后的冷启动复跑见 §5，那里像素同样完全一致，才是确定性证据。
- 文本编码器 7.67 GB 在 CPU 上加载，未挤占显存；这是 8 GB 卡能跑起来的关键。
- 采样设备为 XPU，未出现 CUDA 初始化或 CPU 回退。

证据：

```text
logs/r0/R0-C-flux/run.json
logs/r0/R0-C-flux/history.json
logs/r0/R0-C-flux/workflow.submitted.json
logs/r0/R0-C-flux-run2/run.json
logs/comfyui.err.log
```

### 3.3 结论

`PASS_VERIFIED`：FLUX.2 klein 4B Q4 + Qwen3-4B 编码器 + FLUX.2 VAE 在 A750 上可完成 512×512 出图，约 100 秒/张（冷启动）。质量足以进入 R1 的角色/场景资产实验。未测试 1024×1024，也未测试图像编辑/参考图一致性，这些留给 R1/R5。

---

## 4. R0-D：Wan2.2 TI2V 视频（PASS_VERIFIED）

### 4.1 配置

| 项 | 值 |
|---|---|
| 扩散模型 | `Wan2.2-TI2V-5B-Q4_K_M.gguf`（3.43 GB） |
| 文本编码器 | `umt5_xxl_fp8_e4m3fn_scaled.safetensors`（6.27 GB，ComfyUI 自动放 CPU） |
| VAE | `wan2.2_vae.safetensors`（1.31 GB，XPU） |
| 分辨率/帧数 | 512×512，33 帧（4n+1），24fps |
| 采样 | `uni_pc` / `simple`，shift 8.0，CFG 5.0 |
| 工作流 | `workflows/r0_wan_t2v_api.json`、`workflows/r0_wan_i2v_api.json` |

日志确认：Wan 模型 3.36 GB 加载到 XPU，VAE 1.34 GB 加载到 XPU，UMT5 `CLIP/text encoder model load device: cpu`。

### 4.2 结果

| 实验 | 步数 | 耗时 | 峰值显存 | 技术结果 | 画面质量 |
|---|---|---|---|---|---|
| T2V | 10 | 316.4 s | 4.79 GiB | 33 帧，MP4 可解码 | 偏暗、动作弱，可用性低 |
| I2V（FLUX 首帧） | 10 | 329.5 s | 5.11 GiB | 33 帧，MP4 可解码 | **末帧严重彩虹伪影** |
| I2V（同参数复测） | 20 | 590.9 s | 4.99 GiB | 33 帧，MP4 可解码 | 干净，人物抬手接电话，与首帧一致 |

产物：

```text
logs/r0/R0-D-wan-t2v/wan_t2v.mp4                      512x512 24fps 1.375s
logs/r0/R0-D-wan-i2v/wan_i2v.mp4                      512x512 24fps 1.375s（10 步，有伪影）
logs/r0/R0-D-wan-i2v-20steps/wan_i2v_20steps.mp4      512x512 24fps 1.375s（20 步，正常）
```

FFmpeg 全帧解码 `ffmpeg -v error -i <mp4> -f null -` 退出码 0，`ffprobe` 均为 33 帧 / 24fps / 1.375s。

### 4.3 关键发现

1. **10 步不可用**：同一 I2V 工作流，10 步在末帧产生大面积彩虹伪影；20 步完全消失。这不是 Q4 量化或 XPU 故障，而是采样步数不足。默认步数已改为 20。
2. **文本编码器自动 offload**：即使 `CLIPLoader` 未指定 CPU，ComfyUI 在 8 GB 卡上也会把 UMT5 放到 CPU；显存峰值约 5 GiB。
3. **模型自动卸载**：每个 prompt 结束后显存回到 7.75 GiB 空闲，无需手动 `/free`。
4. 512×512 不是 Wan 的原生训练分辨率，画面与提示词匹配度一般；这属于 R2 调参范围，不是 R0 的验收项。

### 4.4 结论

`PASS_VERIFIED`：Wan2.2 TI2V-5B Q4 在 A750 上可完成 T2V 与 I2V，512×512×33 帧，20 步约 10 分钟/段，峰值显存约 5 GiB，成片可解码。R0 不评价画质；R2 需要重新标定分辨率、步数与提示词。

---

## 5. R0-E：模型互斥与重载（PASS_VERIFIED）

### 5.1 实际执行的切换序列

| 轮次 | 序列 | 结果 |
|---|---|---|
| 1 | FLUX 512（冷启动，97.7 s）→ Wan I2V 33 帧 | 自动卸载 FLUX、加载 Wan，无 OOM |
| 2 | 重启 ComfyUI → FLUX 冷启动（95.0 s）→ Wan T2V 20 步（529.3 s） | 无 OOM；冷启动 FLUX 与首轮**像素完全一致** |
| 3 | Wan → FLUX（seed 43，强制重算，99.1 s） | 正常出图，画面随 seed 变化 |

每一轮都确认同一时刻只有一个扩散模型驻留；观测到的峰值显存为 5.11 GiB（I2V），未接近 7.75 GiB 上限。

### 5.2 `/free` 与自动释放

```text
Wan 生成结束后的 /free：  请求前 7.75 GiB 空闲 → 请求后 7.75 GiB（已自动卸载）
FLUX 生成结束后的空闲：   5.16 GiB（约 2.6 GB 模型留在缓存中）
```

- ComfyUI 在 prompt 结束后会自动卸载大模型；手动 `POST /free` 返回 200，但通常已无对象可释放。
- FLUX 的 2.6 GB 会短暂留在显存缓存中，不影响下一次加载 Wan（Wan 需要约 3.4 GB + VAE 1.3 GB，仍有余量）。
- 因此**不需要**为了切换模型重启 ComfyUI；重启仅用于清空执行缓存/故障恢复。

### 5.3 启停脚本验证

- `scripts/stop.ps1`：按进程树 `taskkill /T` 停止，实际验证可停掉 venv launcher 及其子进程。
- `scripts/start.ps1`：用 `curl.exe` 探测 `/system_stats`，重启后服务恢复。
- 仍有一个小问题：后台运行时 PowerShell 的输出缓冲会让启动脚本看起来“卡住”，但服务实际已就绪；这属于脚本输出体验，不影响功能（见 §6）。

### 5.4 结论

`PASS_VERIFIED`：在 A750 8 GB 上，FLUX.2 与 Wan2.2 可以反复切换，无需手工控制模型加载；峰值显存约 5 GiB，未出现 OOM。冷启动固定 seed 的输出像素一致，生成具备可复现性。

---

## 6. 结论

### 6.1 实际验证结果

| 项 | 结果 |
|---|---|
| PyTorch XPU | torch 2.15.0+xpu，A750 7.75 GiB，`is_available=True` |
| ComfyUI | 0.43.0，`xpu:0` 启动，API/Web 正常 |
| FLUX.2 klein 4B Q4 | 512×512 出图成功，约 95-100 s/张，峰值 2.6 GiB |
| Wan2.2 TI2V 5B Q4 | T2V 与 I2V 均成功，512×512×33 帧，20 步约 9-10 分钟，峰值约 5 GiB |
| 模型切换 | 3 轮 FLUX↔Wan，无 OOM，峰值 5.11 GiB |
| 可复现性 | 重启后冷启动、相同 seed、像素完全一致 |
| 技术质量 | 所有 MP4 为 H.264 512×512 / 24fps / 1.375s，全帧解码退出码 0 |
| 内容质量 | 10 步 Wan 不可用（彩虹伪影）；20 步正常。512×512 下提示词匹配度一般 |

### 6.2 未解决问题

1. **长片段未测**：只测了 33 帧（1.375 s）。要覆盖 3-5 秒镜头需要 73/121 帧，显存与耗时未知，必须作为 R2 的第一项实验。
2. **非原生分辨率未测**：512×512 是方形低分辨率，Wan 原生是 1280×704。832×480 / 640×480 是否更稳、是否 OOM，未验证。
3. **人物一致性未测**：FLUX 的参考图/图像编辑能力（klein image-edit）尚未实验，这是 R5 的核心风险。
4. **Q4 质量上限未知**：fp16 版 9.31 GB 超出 8 GB 显存，无法直接对比；Q4 是否是画质瓶颈，需要 R1/R2 用更多步数和更好提示词评估。
5. **LLM 与 TTS 未接入**：8081 的剧本服务、50000 的 CosyVoice 都没有在 R0 中启动验证。
6. **口型同步不存在**：首阶段不承诺，分镜需用旁白/背影/侧脸/特写规避。
7. **启动脚本输出缓冲**：后台运行 `start.ps1` 时 PowerShell 管道缓冲会让命令看起来未返回；服务本身已就绪。后续可改为写日志文件 + 独立探针，不阻塞调用方。

### 6.3 能不能在 A750 上跑

**能，且两个模型都实际跑通了。** 但它是“能产出”的级别，不是“高性能视频工作站”：

- 图像：可用，约 100 秒/张。
- 视频：可用，约 9-10 分钟 / 1.375 秒片段（20 步）。
- 显存：峰值约 5 GiB，切换模型不需要重启。
- 关键限制：分辨率低、片段短、生成慢。

### 6.4 哪些环节需要 CPU offload

| 环节 | 设备 | 说明 |
|---|---|---|
| FLUX 文本编码器（Qwen3-4B，7.67 GB） | **CPU** | 工作流中显式 `device: cpu`，否则 8 GB 装不下 |
| Wan 文本编码器（UMT5，6.4 GB） | **CPU** | ComfyUI 在 8 GB 卡上自动 offload |
| FLUX UNet + VAE | XPU | 峰值约 2.6 GiB |
| Wan UNet + VAE | XPU | 峰值约 5 GiB |
| Wan 扩散模型本身 | XPU，无需 offload | 512×512×33 帧已验证；更长/更大分辨率待测 |

### 6.5 是否值得继续

**值得，但必须把目标锁死在“30-45 秒、3-5 个镜头、3-5 秒/镜头”的实验片上。**

按实测外推（未测 121 帧，仅作预算）：

- 33 帧 ≈ 1.375 s，20 步 ≈ 9-10 分钟。
- 73 帧（约 3 s）理论上 ≈ 20-22 分钟/镜头。
- 121 帧（约 5 s）理论上 ≈ 33-36 分钟/镜头。
- 45 秒成片若用 9 个 5 秒镜头 ≈ 5-6 小时纯生成；加 FLUX 首帧、失败重试、配音与剪辑，约 **7-10 小时/集**，属于“挂机过夜”而不是交互式创作。
- 如果 121 帧 OOM，则退到 3 秒镜头、更多镜头数，预算仍在 3-5 小时量级。

这个成本对于“自动化实验室”是可接受的；对于“每天产出多条短视频”则不够。后续若要提高吞吐，优先考虑更小分辨率/更短镜头/更强显卡，而不是继续堆节点。

### 6.6 R1 的具体建议

1. **先做角色定妆，不碰视频。** 用 512×512 生成角色四视图/半身像，再试 768×768，记录耗时与显存；以 768 能稳定跑为上限。
2. **把 FLUX.2 klein 的 image-edit 工作流纳入 R1**：官方模板 `image_flux2_klein_image_edit_4b_distilled.json` 是人物一致性的关键，不要等 R5 才试。
3. **固化工作流与元数据**：`workflows/flux_character_api.json` + `.meta.json`（模型 sha256、ComfyUI commit、seed、参数、验收状态）。
4. **H1 人工门必须保留**：自动只做技术检查（尺寸、非空、可解码），不做“像不像同一个人”的自动判定。
5. **R2 第一件事不是生成成片，而是测 73/121 帧与 640×480/832×480 的显存与耗时**；结果决定镜头时长和整条流水线的时间预算。
6. **Wan 固定 20 步、uni_pc/simple、shift 8**；10 步只用于排错，不进入生产。
7. **LLM 用 8081 的 CPU-only 实例**，避免和 ComfyUI 抢显存；先验证它能否稳定输出通过 Pydantic 的 JSON，再谈提示词质量。
8. **不要现在更新 ComfyUI/节点**：当前 commit `bb878b9` 与 GGUF `6ea2651` 已通过验证，升级必须重跑 R0。
9. **保持双 venv 与模型仓库边界**：R1 不要往根 `.venv` 装 torch，也不要把模型复制进项目。
