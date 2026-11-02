# 环境说明

> 核实日期：2026-11-02。以下"已核实"项均由本机命令实际执行得到，不是推断。

## 1. 已核实硬件与系统

| 项目 | 实测值 | 证据来源 |
|---|---|---|
| CPU | 13th Gen Intel Core i7-13700K，16C / 24T | `Get-CimInstance Win32_Processor` |
| 内存 | 63.7 GiB（68,393,086,976 B） | `Get-CimInstance Win32_ComputerSystem` |
| 独显 | Intel Arc A750 Graphics，驱动 **32.0.101.9150** | `Get-CimInstance Win32_VideoController` |
| 核显 | Intel UHD Graphics 770，驱动 32.0.101.7092 | 同上 |
| 系统 | Windows 11 Pro 10.0.26300 | `win32` 平台 |
| WSL | 已安装 Ubuntu（当前未用于本项目） | `wsl --status` |
| 项目盘 D: | 剩余 428.2 GiB | `shutil.disk_usage` |
| 系统盘 C: | 剩余 396.2 GiB | 同上 |

注意：`Win32_VideoController.AdapterRAM` 是 32 位字段，对 A750 显示为 4 GiB，**不能作为显存依据**。显存容量必须以 `torch.xpu.get_device_properties()` 或 ComfyUI `/system_stats` 的实测为准。

## 2. 已核实软件

| 工具 | 版本 | 路径 |
|---|---|---|
| Python（系统） | 3.12.10 | `C:\Users\99236\AppData\Local\Programs\Python\Python312\python.exe` |
| uv | 0.10.8 | `C:\Users\99236\.local\bin\uv.exe` |
| FFmpeg / ffprobe | 8.1-full_build（gyan.dev） | WinGet 安装目录 |
| Git | 2.53.0.windows.2 | — |
| 项目 `.venv` | Python 3.12.10 | `D:\Local-Drama-Studio\.venv` |

FFmpeg 8.1 构建包含 `libass`、`libx264`、`libx265`、`libvpl`（Intel QSV）、`libplacebo`，满足字幕烧录、H.264 合成与硬件解码需求。

## 3. 已有 AI 运行时（D:\AI）

### 3.1 llama.cpp 服务

- 入口：`D:\AI\start_server.bat`（交互式，单选菜单）
- 后端：SYCL（`bin-sycl\`，b12024）/ Vulkan（`bin\`）
- 接口：OpenAI 兼容 `http://127.0.0.1:8080/v1`
- 模型：`Qwen3-30B-A3B`、`Qwen3-Coder-30B-A3B`、`Qwen3VL-30B-A3B`、`Qwen3-8B`、`Qwen3.5-4B`、`DeepSeek-R1-8B`
- **2026-11-02 实测：8080 被另一个需要 API Key 的实例占用（`GET /v1/models` 返回 401）**。因此本项目的 LLM 端点默认改为 **8081**，由项目自己的实例提供；不要依赖 8080 上的未知实例。

### 3.2 CosyVoice

- 目录：`D:\AI\CosyVoice-Runtime`
- 独立 Python 3.10 venv，CPU 推理，端口 **50000**
- 两种模式共用端口，同一时刻只能启动一个：
  - `start_cosyvoice.bat` → CosyVoice2-0.5B，zero-shot 克隆，24 kHz
  - `start_cosyvoice_sft.bat` → CosyVoice-300M-SFT，预置音色，22.05 kHz
- 2026-11-02 实测：服务未启动（50000 未监听）。

### 3.3 模型仓库

`D:\AI\models`（顶层文件不能移动，原因见 §5）：

| 文件 | 大小 | 状态 |
|---|---|---|
| `Wan2.2-TI2V-5B-Q4_K_M.gguf` | 3.43 GB | ✅ 已有 |
| `flux-2-klein-4b-Q4_K_M.gguf` | 2.60 GB | ✅ 已有 |
| `Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf` | 18.56 GB | ✅ 已有 |
| `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` | 18.56 GB | ✅ 已有 |
| `Qwen3VL-30B-A3B-Instruct-Q4_K_M.gguf` | 18.56 GB | ✅ 已有 |
| `Qwen3-8B-Q4_K_M.gguf` | 5.03 GB | ✅ 已有 |
| `Qwen3.5-4B_Q4_k_m.gguf` | 2.71 GB | ✅ 已有 |
| `DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf` | 4.92 GB | ✅ 已有 |
| `mmproj-Qwen3VL-30B-A3B-Instruct-F16.gguf` | 1.08 GB | ✅ 已有 |

## 4. 双虚拟环境边界

| 环境 | 路径 | Python | 允许安装 | 禁止 |
|---|---|---|---|---|
| 调度环境 | `D:\Local-Drama-Studio\.venv` | 3.12 | typer / rich / pydantic / pyyaml / httpx / websockets / pysubs2 / pillow / pytest | torch、comfyui、模型推理依赖 |
| 生成环境 | `D:\Local-Drama-Studio\runtime\ComfyUI\.venv` | 3.12 | PyTorch XPU、ComfyUI requirements、ComfyUI-GGUF | 业务代码依赖 |
| 现有 TTS 环境 | `D:\AI\CosyVoice-Runtime\venv` | 3.10 | 保持不变 | 本项目不向其安装任何东西 |
| 系统 Python | `C:\...\Python312` | 3.12 | 不使用 | 不安装任何项目依赖 |

创建方式：

```powershell
uv sync --python 3.12                      # 调度环境
scripts\setup.ps1 -WithComfyUI             # 生成环境（独立 venv）
```

2026-11-02 实际安装并核实：

| 组件 | 版本 |
|---|---|
| torch | 2.15.0+xpu |
| torchvision | 0.29.2+xpu |
| torchaudio | 2.11.1+xpu |
| ComfyUI | 0.43.0（commit `bb878b9ee35274e67931634ba9e8c338f8c06035`） |
| ComfyUI-GGUF | 随仓库 HEAD，`gguf==0.19.0` |

`doctor` 的 `PyTorch XPU` 行会重新探测，以实际输出为准。

## 5. 模型目录与 ComfyUI 映射

### 硬约束

`D:\AI\start_server.bat` 第 40 行只扫描 `%MODELS_DIR%\*.gguf`（顶层），因此：

- **不能**把 `flux-2-klein-4b-Q4_K_M.gguf`、`Wan2.2-TI2V-5B-Q4_K_M.gguf` 移入子目录；
- 新增的编码器/VAE 放在子目录，ComfyUI 同时映射顶层与子目录。

### 目标布局

```text
D:\AI\models\
├─ flux-2-klein-4b-Q4_K_M.gguf              # 已有，保持在顶层
├─ Wan2.2-TI2V-5B-Q4_K_M.gguf               # 已有，保持在顶层
├─ Qwen3-*.gguf                              # 已有
├─ text_encoders\
│  ├─ qwen_3_4b.safetensors                 # FLUX.2 klein 配套（待下载）
│  └─ umt5_xxl_fp8_e4m3fn_scaled.safetensors# Wan2.2 配套（待下载）
└─ vae\
   ├─ flux2-vae.safetensors                 # FLUX.2 VAE（待下载，不是 FLUX.1 的）
   └─ wan2.2_vae.safetensors                # Wan2.2 VAE（待下载）
```

### ComfyUI 映射

`config/comfyui_extra_model_paths.yaml` 会被 `setup.ps1` 复制到 `runtime/ComfyUI/extra_model_paths.yaml`：

```yaml
ai_shared:
  base_path: D:/AI/models
  diffusion_models: |
    .
    diffusion_models
  unet_gguf: |
    .
    diffusion_models
  text_encoders: text_encoders
  vae: vae
```

同时映射 `diffusion_models` 与 `unet_gguf`，兼容不同版本的 ComfyUI-GGUF 读取目录名。

### 待下载配套文件

| 用途 | 文件名 | 目标目录 | 备注 |
|---|---|---|---|
| FLUX.2 文本编码器 | `qwen_3_4b.safetensors` | `text_encoders\` | 必须是 **4B**，不能用 Qwen3-8B 代替 |
| FLUX.2 VAE | `flux2-vae.safetensors` | `vae\` | 不能用 FLUX.1 VAE |
| Wan2.2 文本编码器 | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `text_encoders\` | — |
| Wan2.2 VAE | `wan2.2_vae.safetensors` | `vae\` | TI2V-5B 专用 |

来源以 ComfyUI 官方 FLUX.2 klein / Wan2.2 教程给出的仓库为准；HuggingFace 访问受限时可设 `HF_ENDPOINT=https://hf-mirror.com`。**下载完成不等于推理成功**，必须走 R0-C/R0-D。

`config/models.yaml` 为每个文件记录了**精确字节数**；`doctor` 会拒绝缺失或未下载完的文件（例如把 2.4 GB 的 partial 文件误判为可用）。如果实际下载的文件名或大小不同，修改配置，不要改文件名去凑配置。

## 6. 端口分配

| 端口 | 服务 | 当前状态 | 说明 |
|---|---|---|---|
| 8188 | ComfyUI | 运行中（R0 验证时） | `scripts/start.ps1` 启动 |
| 8081 | 项目 LLM（llama.cpp） | 未监听 | 建议 CPU-only 启动，避免抢显存 |
| 8080 | 其他定时任务的 LLM | 监听中，需 API Key | **不要**依赖，也不要随意结束 |
| 50000 | CosyVoice | 未监听 | 用 `D:\AI\CosyVoice-Runtime` 启动 |

## 7. 显存预算（R0 实测）

| 场景 | 权重 | 实测显存峰值 | 结论 |
|---|---|---|---|
| FLUX.2 klein 4B Q4 @512×512 | 2.60 GB | **2.61 GiB** | 文本编码器放 CPU；出图约 95-100 s/张 |
| Wan2.2 TI2V 5B Q4 @512×512×33 | 3.43 GB | **5.11 GiB**（I2V） | UMT5 自动放 CPU；20 步约 9-10 分钟 |
| 空闲（Wan 结束后） | — | 7.75 GiB 空闲 | ComfyUI 自动卸载模型 |
| 空闲（FLUX 结束后） | — | 5.16 GiB 空闲 | 约 2.6 GB 留在缓存，仍可加载 Wan |
| Qwen3-30B-A3B（LLM） | 18.56 GB | 未在 R0 测试 | 与 ComfyUI **不可共存**，建议 CPU-only |
| CosyVoice | — | 未在 R0 测试 | CPU 推理，不占显存 |

补充实测结论：

### R1 补充实测（FLUX 16:9 / 参考图编辑）

| 场景 | 耗时 | 峰值显存 | 结论 |
|---|---|---|---|
| FLUX 768×432 文生图 | 70-102 s | 2.60-2.84 GiB | 16:9 可直接生成 |
| FLUX 768×432 参考图编辑 | 72-83 s | 2.79-2.84 GiB | `ReferenceLatent + VAEEncode` 可用 |
| R1 批量 11 个任务 | — | — | 0 失败、0 重试 |

**Wan 视频的分辨率约束**：`Wan22ImageToVideoLatent` 的 width/height 必须能被 32 整除。
R1 关键帧是 768×432（432/32=13.5），不能直接作为 I2V 输入；R2 必须先缩放到
**1024×576**（16:9，32 的倍数）或 832×480，再生成视频。

- Wan 在 10 步时末帧出现彩虹伪影，20 步正常；生产默认 20 步。
- 长片段（73/121 帧）与非方形分辨率尚未实测，R2 第一项任务就是补这组数据。
- 以上数字来自 `logs/r0/R0-C-*`、`logs/r0/R0-D-*`、`logs/r0/R0-E-*` 的 `run.json`。

## 8. 明确不要动的东西

- `D:\AI\start_server.bat` 及其 `.bak-*` 备份
- `D:\AI\bin-sycl\`、`bin\`、`bin-old\`
- `D:\AI\models\` 顶层的任何 `.gguf`
- `D:\AI\CosyVoice-Runtime\venv\`、`app\` 中的两处本地补丁
- 其他项目（`D:\CourseStudio`、`D:\Project\*` 等）的虚拟环境与依赖
- 系统 Python 的 site-packages
- 8080 上不属于本项目的进程

## 9. 已知风险

| 风险 | 影响 | 应对 |
|---|---|---|
| XPU 后端缺少 GGUF 反量化算子 | ComfyUI-GGUF 报错或退回 CPU | R0-C/D 实测；失败则记录，不盲目换整套环境 |
| Wan VAE 解码 OOM | 512×512 也可能失败 | 降低帧数 / 分块解码 / `--lowvram`，逐项验证 |
| Qwen3-4B 编码器体积大 | 加载慢、挤占显存 | ComfyUI 自动 offload；必要时 GGUF 量化编码器 |
| ComfyUI / 节点 API 变动 | 工作流字段失效 | 锁定 commit；工作流与版本一起登记 |
| 驱动过旧 | XPU 不可用 | 驱动 32.0.101.9150 已较新；不满足时再升级 |
| HuggingFace 访问受限 | 配套文件下载失败 | `HF_ENDPOINT` 镜像；校验 sha256 |
| 8080 端口冲突 | 请求被错误实例接走 | 项目固定 8081，doctor 报告实际监听者 |
| Windows 控制台编码 | 中文乱码 | CLI 非 TTY 时强制 UTF-8；脚本带 BOM |

## 10. 环境复现命令

```powershell
# 调度环境
uv sync --python 3.12
.venv\Scripts\python.exe -m pytest

# 诊断
scripts\doctor.ps1

# 生成引擎
scripts\setup.ps1 -WithComfyUI
scripts\start.ps1
scripts\stop.ps1
```
