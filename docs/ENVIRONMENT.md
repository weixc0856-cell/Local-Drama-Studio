# 02 · 环境与技术栈

> 状态：`DECISION` / 2026-11-12 由 `ENVIRONMENT.md` 与 `TECH_STACK.md` 合并。
> 以下"已核实"项均由本机命令实际执行得到，不是推断；冻结不等于所有组件都通过生产验证。
> 原始文档归档在 `D:\DramaStudio\archive\docs\2026-11-12\`（见 [ARCHIVE.md](ARCHIVE.md)）。

## 1. 冻结原则

1. 不继续扩大技术栈；新增组件必须有明确业务需求、技术依据和实际验证。
2. 不升级 PyTorch / ComfyUI / 工作流节点，除非重新跑对应阶段验收。
3. 模型权重不进 Git，统一放在 `models`。
4. 根 `.venv` 不安装 torch；生成环境独立在 `runtime/ComfyUI/.venv`。
5. 新增依赖必须说明必要性；v1.0 后仅因工作台新增 `fastapi` / `uvicorn`（ADR-014）。

## 2. 已核实硬件与系统

| 项 | 实测值 |
|---|---|
| CPU | 13th Gen Intel Core i7-13700K，16C / 24T |
| 内存 | 63.7 GiB |
| 独显 | Intel Arc A750 8 GB，驱动 32.0.101.9150 |
| 核显 | Intel UHD Graphics 770 |
| 系统 | Windows 11 Pro 10.0.26300 |
| 推理后端 | PyTorch XPU（无 CUDA） |

注意：`Win32_VideoController.AdapterRAM` 对 A750 显示 4 GiB（32 位字段），不能作为显存依据；以 `torch.xpu.get_device_properties()` 或 ComfyUI `/system_stats` 为准。

## 3. 核心栈

| 组件 | 职责 | 版本 | 许可证 | 状态 |
|---|---|---|---|---|
| Python（调度） | 编排 | 3.12.10 | PSF-2.0 | `PASS_VERIFIED` |
| uv | 环境/依赖锁定 | 0.10.8 | Apache-2.0 / MIT | `PASS_VERIFIED` |
| ComfyUI | 生成引擎 | 0.43.0（`bb878b9`） | **GPL-3.0** | `PASS_VERIFIED` |
| ComfyUI-GGUF | GGUF 加载 | `6ea2651` / gguf 0.19.0 | Apache-2.0 | `PASS_VERIFIED` |
| PyTorch | XPU 推理 | 2.15.0+xpu | BSD-3-Clause | `PASS_VERIFIED` |
| FLUX.3 Klein distilled | 静帧 | GGUF Q4_K_M，3.67 GB；16 步 / CFG 1.0 | FLUX Kommunity License | `PASS_LIMITED` |
| FLUX 文本编码器 | 提示词编码 | `qwen3vl_4b_int8_convrot.safetensors`，4.86 GB | 随 BFL 仓库；Qwen3-VL-4B 本体 Apache-2.0 | `PASS_LIMITED` |
| FLUX.2 VAE | 解码 | `flux2-vae.safetensors`，336 MB | Apache-2.0 | `PASS_VERIFIED` |
| Wan2.2 TI2V 5B | 图生/文生视频 | GGUF Q4_K_M，3.43 GB；20 步 / CFG 5 / shift 8 | Apache-2.0（Comfy-Org 模型卡） | `PASS_VERIFIED` |
| UMT5-XXL 编码器 | Wan 提示词 | `umt5_xxl_fp8_e4m3fn_scaled`，6.73 GB | 随 Comfy-Org 重打包；底层 UMT5 待复核 | `PASS_VERIFIED` |
| Wan2.2 VAE | 解码 | `wan2.2_vae.safetensors`，1.41 GB | Apache-2.0 | `PASS_VERIFIED` |
| VoxCPM2 | 中文旁白（zero-shot 克隆） | 2B 运行时，48 kHz，CPU | Apache-2.0（代码与权重） | 技术 `PASS_VERIFIED`；商用授权 `UNVERIFIED` |
| FFmpeg / ffprobe | 剪辑/混音/字幕/放大 | 8.1 full build | **GPLv3 构建** | `PASS_VERIFIED` |
| llama.cpp（本地 AI 服务） | 剧本/分镜 | SYCL b12024 | MIT（llama.cpp）；模型按模型卡 | `PASS_VERIFIED` |

调度依赖：`pydantic`、`typer`、`rich`、`pyyaml`、`httpx`、`websockets`、`pysubs2`、`pypinyin`、`pillow`、`fastapi`、`uvicorn`。工作台实测 FastAPI 0.162.0 / Uvicorn 0.54.0；不引入 node、torch 或数据库服务。

字体：思源宋体 CN 2.003R / 思源黑体 CN 2.005R（SIL OFL 1.1），只保留 Regular/Medium/Bold；OTF 不进 Git，由 `scripts/fetch_fonts.py` 重建并校验。字幕已接入思源黑体；标题/诗词角色仍为 `preview_only`。

## 4. AI 运行时就绪状态

### 4.1 llama.cpp（8080）

- 入口：`本地 AI 服务\start_server.bat`（交互式）；后端 SYCL（`bin-sycl`）/ Vulkan（`bin`）。
- OpenAI 兼容：`http://127.0.0.1:8080/v1`；**只允许一个实例**（ADR-013）。
- 项目默认：`Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf`，CPU-only（`-ngl 0`），`-c 65536`（64K，已验证），别名 `Qwen3-30B-A3B-Instruct-2507`；不占显存，约 19 GB 内存。
- 生命周期：`scripts\llm_server.ps1 -Action start|stop|status`；调用结束必须停止，空闲时端口为空。`literary_intelligence/run_li15.py` 只停止自己启动的实例。
- 定时任务 `OpportunityRadarDaily` 检测到 8080 占用时延后，不另开端口、不 kill 别人的进程。

### 4.2 VoxCPM2（50000）

- 目录：`VoxCPM-Runtime`（独立 Python 3.12 venv，CPU）。
- 唯一模式：参考音克隆（`zero_shot`）；SFT 预置音色已退休。
- 启动：`scripts\cosyvoice_server.ps1 -Action start`（脚本名保留历史叫法）；加载约 25–30 秒；单句 RTF ≈ 9–12。
- ASR QA：同一 venv 的 `openai-whisper`，供 `scripts/tts_qa.py` 调用。

### 4.3 ComfyUI（8188）

- 生成环境：`runtime/ComfyUI/.venv`；`scripts\start.ps1` 等待 `/system_stats`，`scripts\stop.ps1` 只杀本项目进程树。
- 模型经 `runtime/ComfyUI/extra_model_paths.yaml` 映射到 `D:/AI/models`：`diffusion_models` 同时暴露顶层与 `diffusion_models/` 子目录，`text_encoders`、`vae` 各自映射。
- 模型切换不需要重启；`/free` 通常是 no-op（自动卸载）。

## 5. 模型目录

权重统一在 `models`（本机 `D:/AI/models`），不进入 Git。两个扩散 GGUF 必须在**顶层**，因为 `本地 AI 服务\start_server.bat` 只扫描顶层 `*.gguf`。

| 文件/目录 | 用途 |
|---|---|
| `diffusion_models/flux3/flux-3-image-klein-Q4_K_M.gguf` | 图像 |
| `text_encoders/qwen3vl_4b_int8_convrot.safetensors` | 图像编码器 |
| `vae/flux2-vae.safetensors` | 图像 VAE |
| `Wan2.2-TI2V-5B-Q4_K_M.gguf` | 视频（顶层） |
| `text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | Wan 编码器 |
| `vae/wan2.2_vae.safetensors` | Wan VAE |
| `Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf` | 本地 LLM（顶层） |

`config/models.yaml` 记录精确字节数；`doctor` 拒绝缺失或大小不符的文件。

## 6. 环境变量

本机路径不写进仓库，由 `.env`（已 gitignore）提供；模板见 `.env.example`。

| 变量 | 用途 |
|---|---|
| `DRAMA_MODELS_ROOT` | 模型仓库（默认 `D:/AI/models`） |
| `DRAMA_AI_HOME` | 本地 AI 服务目录（`D:/AI`） |
| `DRAMA_OUTPUT_ROOT` | 产出根（默认 `D:/DramaStudio`） |
| `VOXCPM_RUNTIME` | `D:/AI/VoxCPM-Runtime` |
| `DRAMA_ROOT` | 可选，显式项目根 |

## 7. 端口

| 服务 | 端口 | 规则 |
|---|---|---|
| ComfyUI | 8188 | 单实例；启动前探测 |
| 本地 LLM | 8080 | 单端口；谁启动谁停止；定时任务让路 |
| VoxCPM2 | 50000 | 单实例 |
| 工作台 | 8765 | 不是 LLM 端口 |

本地探测绕过系统代理：Python `httpx(..., trust_env=False)`；PowerShell 用 `curl.exe`。

## 8. 显存与实测

| 场景 | 峰值 VRAM | 时间 |
|---|---|---|
| FLUX 512×512 / 4 步 | 2.61 GiB | 99.5 s |
| FLUX 576×1024 | ~2.8–3.0 GiB | 22–53 s/张 |
| Wan 1024×576 / 73 帧 | ≤6.12 GiB | 40–43 min |
| Wan 576×1024 / 73 帧 | 5.48 GiB | 36.4 min |
| Wan safe8g 448×768 / 49 帧 | ~5 GiB | 8–14 min/段 |
| 38 s 成片全链路 | — | 43.8 min |

GPU 是独占资源：LLM / FLUX / Wan 一次只跑一个生成任务；8080 的 CPU 实例不占 VRAM 但占约 19 GB 内存。文本编码器在 CPU 上跑（Qwen3-VL-4B 约 7.67 GB；UMT5 6.4 GB 自动 offload）。Wan **必须 20 步**；10 步出现彩虹伪影。

## 9. 明确不要动的东西

- `本地 AI 服务\start_server.bat`、`bin-*`、`VoxCPM-Runtime`。
- 根 `.venv` 里不得安装 torch；不要把生成环境与调度环境合并。
- 不要移动 `models` 顶层的扩散 GGUF。
- 不要在 ComfyUI 生成时启动 GPU 模式的 LLM；不要同时跑 FLUX 与 Wan。
- 不要提交模型权重、OTF、参考图、渲染产物（见 [REPO_LAYOUT.md](REPO_LAYOUT.md)）。

## 10. 已知风险

- A750 8 GB 是天花板：全 Wan 多镜头不可行；建筑/人物运动不稳定。
- FLUX.3 Klein 许可要求内容过滤与 AI 标注，且年营收 < 500 万美元免费商用。
- ComfyUI（GPL-3.0）与 FFmpeg（GPLv3 构建）若打包分发需做合规评估。
- Windows 编码：非 TTY stdout 需 UTF-8（CLI 已处理）；PowerShell 脚本必须 UTF-8 with BOM。

## 11. 复现命令

```powershell
uv sync --python 3.12
scripts\setup.ps1 -WithComfyUI
.venv\Scripts\python.exe scripts\fetch_fonts.py --check
scripts\doctor.ps1
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\check_repo_hygiene.py
```
