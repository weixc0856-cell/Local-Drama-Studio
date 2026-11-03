# 02 · TECH_STACK — v1.0 冻结技术栈

> 文档状态：`DECISION` / v1.0 技术栈冻结（2026-11-03）。
> 依据：`docs/ENVIRONMENT.md`、R0-R3 报告、本机实际版本。
> **冻结不等于所有组件都通过生产验证；状态列与证据列必须一起读。**

## 1. 冻结原则

1. 不继续扩大技术栈；新增组件必须有明确业务需求、技术依据和实际验证。
2. 不升级 PyTorch / ComfyUI / 工作流节点，除非重新跑对应阶段验收。
3. 模型权重不进 Git，统一放在 `D:\AI\models`。
4. 根 `.venv` 不安装 torch；生成环境独立在 `runtime/ComfyUI/.venv`。
5. 所有新增依赖必须说明必要性；v1.0 不新增 Python 依赖。

## 2. 核心栈

| 组件 | 职责 | 实际版本 | 许可证 | 状态 |
|---|---|---|---|---|
| Python（调度） | 剧本/批处理/音频/字幕/剪辑编排 | 3.12.10 | PSF-2.0 | `PASS_VERIFIED` |
| uv | 环境与依赖锁定 | 0.10.8 | Apache-2.0 / MIT | `PASS_VERIFIED` |
| ComfyUI | 图像/视频生成引擎 | 0.43.0（commit `bb878b9`） | **GPL-3.0** | `PASS_VERIFIED` |
| ComfyUI-GGUF | GGUF 模型加载 | commit `6ea2651`，gguf 0.19.0 | Apache-2.0 | `PASS_VERIFIED` |
| PyTorch | XPU 推理 | 2.15.0+xpu | BSD-3-Clause | `PASS_VERIFIED` |
| torchvision / torchaudio | 配套 | 0.29.2+xpu / 2.11.1+xpu | BSD-3-Clause | `PASS_VERIFIED` |
| FLUX.2 Klein 4B | 静帧/参考图编辑 | GGUF Q4_K_M，2.60 GB | Apache-2.0（HF 模型卡） | `PASS_VERIFIED` |
| Qwen3-4B 文本编码器 | FLUX 提示词编码 | `qwen_3_4b.safetensors`，8.04 GB | Apache-2.0 | `PASS_VERIFIED` |
| FLUX.2 VAE | FLUX 解码 | `flux2-vae.safetensors`，336 MB | Apache-2.0（同仓库） | `PASS_VERIFIED` |
| Wan2.2 TI2V 5B | 图生视频/文生视频 | GGUF Q4_K_M，3.43 GB | Apache-2.0（Comfy-Org 模型卡） | `PASS_VERIFIED` |
| UMT5-XXL 文本编码器 | Wan 提示词编码 | `umt5_xxl_fp8_e4m3fn_scaled`，6.73 GB | 随 Comfy-Org 重打包；底层 UMT5 待复核 | `PASS_VERIFIED` |
| Wan2.2 VAE | Wan 解码 | `wan2.2_vae.safetensors`，1.41 GB | Apache-2.0（同仓库） | `PASS_VERIFIED` |
| CosyVoice | 中文旁白/朗诵 | CosyVoice-300M-SFT，CPU | Apache-2.0（本地 LICENSE）；模型/音色条款待复核 | `PASS_VERIFIED`（仅中文男）；中文女 `NOT_RUN` |
| FFmpeg / ffprobe | 剪辑、混音、字幕、放大 | 8.1-full_build（gyan） | **GPLv3 构建**（`--enable-gpl --enable-version3`） | `PASS_VERIFIED` |
| 本地 llama.cpp（D:\AI） | 剧本/分镜/提示词 | SYCL b12024 | MIT（llama.cpp）；模型许可按各模型卡 | `PARTIAL`（服务存在，未接入流水线） |

> CosyVoice 仅「中文男」在 R3-B 实测；「中文女」未测试。R3-D 负责音色试听、字体/BGM/音效选型与授权核验（`DECISION` / `NOT_RUN`）。

### 2.1 Python 调度依赖

`pydantic`、`typer`、`rich`、`pyyaml`、`httpx`、`websockets`、`pysubs2`、`pillow`。

许可证以各包元数据为准；当前未发现 copyleft 冲突。新增依赖前必须补充到本文档与授权台账。

## 3. 硬件与运行环境

| 项 | 值 |
|---|---|
| CPU | Intel i7-13700K，16C / 24T |
| RAM | 63.7 GiB |
| GPU | Intel Arc A750 8 GB（驱动 32.0.101.9150） |
| 系统 | Windows 11 Pro 10.0.26300 |
| 推理后端 | PyTorch XPU（无 CUDA） |
| 生成环境 | `runtime/ComfyUI/.venv` |
| 调度环境 | 根 `.venv` |
| 模型仓库 | `D:\AI\models`（顶层 GGUF 不能移动） |
| 端口 | ComfyUI 8188；项目 LLM 8081；CosyVoice 50000；8080 属于其他实例 |

## 4. 性能基线（实测，非估算）

| 场景 | 结果 | 证据 |
|---|---|---|
| FLUX 512×512 | 74.5 s/张，峰值 2.71 GiB | R0/R1 |
| FLUX 768×432 16:9 | 70-102 s/张，峰值 2.60-2.84 GiB | R1 |
| FLUX 576×1024 竖屏 | 22-53 s/张，峰值 2.63-3.53 GiB | R3-A |
| Wan 512×512×33 @20 步 | 约 9-10 min，峰值约 5 GiB | R0 |
| Wan 1024×576×73 @20 步（R2-A） | 40.2-43.0 min，峰值 5.42-6.12 GiB | R2-A |
| Wan 1024×576×73 @20 步（R2-B） | 32.6-46.4 min，峰值 5.50-5.66 GiB | R2-B |
| Wan 1024×576×121 @20 步 | 66-69 min，峰值 4.90-5.04 GiB | R2-A |
| Wan 576×1024×73 @20 步 | 36.4 min，峰值 5.48 GiB | R3-A |
| 38.04 s 成片（5 静帧 + 1 Wan + 7 句配音 + 字幕） | 43.8 min 端到端 | R3-B/C |

**注意**：冷热启动、缓存、提示词与输入图不同，以上数字不能直接横向比较“竖屏比横屏快”。

## 5. 按需使用（未集成）

| 组件 | 用途 | 状态 |
|---|---|---|
| Blender | 特殊 3D/合成镜头 | `DECISION`，未安装/未集成 |
| Motion Canvas | 文字与图形动画 | `DECISION`，未集成 |
| ControlNet 相关工具 | 构图/姿态控制 | `DECISION`，未验证 |

按需使用的前提：有明确镜头需求、通过兼容性测试、记录许可证。

## 6. 暂缓引入

- Remotion（Node 视频框架）
- 复杂 Agent 框架
- 新的视频生成模型
- 复杂人物动画/数字人系统
- 多模型并行生产系统
- 自动发布系统
- 没有明确用途的数据库或向量数据库
- SeedVR2 或其他未验证超分模型

## 7. 工程约束

1. 两套虚拟环境不能合并；根 `.venv` 不装 torch。
2. 模型文件、日志、生成帧不进入 Git；工作流与脚本进入 Git。
3. 工作流必须记录 sha256；模型/节点升级后旧工作流重新验收。
4. 所有外部调用记录 argv、退出码、耗时与日志。
5. 不把 CPU 推理写成 GPU 推理；不把“下载成功”写成“推理成功”。
6. 许可证未确认的模型/字体/音乐，不得用于商业发布。

## 8. 变更控制

| 变更 | 要求 |
|---|---|
| 升级 ComfyUI / torch / GGUF 节点 | 重跑 R0，更新版本记录与报告 |
| 新增模型/LoRA/插件 | 先写业务需求与许可证，再跑兼容性测试 |
| 新增 Python 依赖 | 说明必要性，更新 `pyproject.toml` 与本文档 |
| 修改已验证工作流 | 保留旧版，新增 `.meta.json`，重新验收 |
| 使用新字体/音乐/音色 | 先登记授权，再进入成片 |

## 9. 已知技术限制

- Wan 精确主体位移不可靠（R2-B H3：24.6 px，方向错误）。
- 121 帧长镜头有颜色漂移风险（R2-A A4）。
- 人物跨镜头一致性未验证。
- 1080×1920 是 FFmpeg Lanczos 放大，不是原生生成。
- 竖屏 576×1024 已实测，但只有少量样本。
- 多篇夜间批处理未运行。
- 中文女声、字体替换、BGM、音效未选型；R3-D 未执行。
- Windows 字体/路径/代理是常见坑：localhost 探测需绕过代理，烧录字幕需显式 PlayRes。
