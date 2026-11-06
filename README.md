# Local-Drama-Studio · Script-to-Film

面向抖音和小红书的**本地影视化内容生产系统**：把诗词、古典故事与意象，按导演分镜的方式制作成有画面、有声音、有剪辑节奏的竖屏短片。

> **唯一需求入口：[docs/PRD.md](docs/PRD.md)（SSOT）。** 治理文档：[PRD_CHANGELOG](docs/PRD_CHANGELOG.md)、[REQUIREMENT_TRACEABILITY](docs/REQUIREMENT_TRACEABILITY.md)、[DECISIONS](docs/DECISIONS.md)。
> 方法论：[FILM_PRODUCTION_GUIDE](docs/FILM_PRODUCTION_GUIDE.md)（Script-to-Film 十阶段）、[VISUAL_STYLE_ENGINE](docs/VISUAL_STYLE_ENGINE.md)（12 套风格包）。

## 当前技术栈（2026-11-06）

| 层 | 职责 | 技术 |
|---|---|---|
| 制作层 | 剧本、旁白、分镜、连续性、剪辑时间轴、提示词编译 | Python 3.12 + Pydantic（`film/`、`style_engine/`） |
| 图像 | 关键帧、场景与人物 | ComfyUI + **FLUX.3 Klein**（GGUF Q4_K_M，16 步，CFG 1.0） |
| 视频 | 镜头动画 | ComfyUI + **Wan2.2 TI2V 5B**（GGUF Q4_K_M） |
| 语音 | 逐句旁白 | **VoxCPM2**（`D:\AI\VoxCPM-Runtime`，端口 50000，48 kHz，CPU） |
| 文本 | 剧本结构化、分镜、提示词 | 本地 llama.cpp（`D:\AI`，端口 8080，Qwen3-30B-A3B） |
| 合成 | 剪辑、混音、字幕、转码 | FFmpeg 8.1 |

ComfyUI 只是生成引擎，不是项目本体；业务状态、调度、质量门与制作层都在 Python 侧。

## 生产链路

```
诗词/素材 → 编剧（旁白稿） → 导演分镜 → 视觉圣经 + 风格包
→ FLUX.3 关键帧 → Wan 镜头 → 连续性检查 → VoxCPM2 逐句配音
→ 剪辑时间轴 → FFmpeg 多轨合成 → 质量与人工审片
```

关键原则：剧本、分镜、声音、画面与时间轴共享同一份项目数据；`storyboard.json` 是镜头的唯一事实源。

## 目录

| 路径 | 内容 |
|---|---|
| `src/drama_studio/film/` | Script-to-Film：严格 Schema、分镜规划、连续性、时间轴、提示词、任务生成、配音、合成 |
| `src/drama_studio/style_engine/` | 视觉风格引擎：12 套 Style Pack 的注册表、提示词编译器、一致性检查 |
| `src/drama_studio/production.py` | FLUX/Wan 任务与参数（生成引擎适配） |
| `src/drama_studio/voice/` | VoxCPM2 调用、发音层、多轨音频 |
| `src/drama_studio/workspace/` | 本地工作台（SQLite + FastAPI，端口 8765） |
| `config/style_packs/` | 12 套风格包（retro 4 / oriental 3 / artistic 5） |
| `config/models.yaml` | 模型契约（含精确大小） |
| `workflows/` | API 格式工作流（`flux3_t2i_api.json`、Wan I2V） |
| `projects/deng_guan_que_lou/` | Script-to-Film 示例项目（8 镜 / 47 s） |
| `docs/` | PRD、架构、制作指南、风格引擎、质量与资产台账 |

## 快速开始

```powershell
uv sync --python 3.12

# 环境与模型体检
.venv\Scripts\drama.exe doctor --json

# 制作层（CPU，不触发生成）
.venv\Scripts\drama.exe film validate --project deng_guan_que_lou
.venv\Scripts\drama.exe film plan --project deng_guan_que_lou --beats projects\deng_guan_que_lou\beats.json
.venv\Scripts\drama.exe film prompts --project deng_guan_que_lou --style oriental.ink_wash
.venv\Scripts\drama.exe film keyframes --project deng_guan_que_lou --style oriental.ink_wash
.venv\Scripts\drama.exe film wan-jobs --project deng_guan_que_lou --style oriental.ink_wash
.venv\Scripts\drama.exe film contact-sheet --project deng_guan_que_lou

# 风格引擎
.venv\Scripts\drama.exe style list
.venv\Scripts\drama.exe style validate
.venv\Scripts\drama.exe style check-image --style oriental.ink_wash --image <png>

# 生成（需要 ComfyUI 8188；一次只跑一个 GPU 任务）
.venv\Scripts\python.exe scripts\r1_batch.py --jobs projects\deng_guan_que_lou\jobs\keyframes\jobs.json --timeout 7200

# 配音（需要 VoxCPM2 50000；谁启动谁停止）
scripts\cosyvoice_server.ps1 -Action start
.venv\Scripts\drama.exe film voice --project deng_guan_que_lou
scripts\cosyvoice_server.ps1 -Action stop

# 合成
.venv\Scripts\drama.exe film assemble --project deng_guan_que_lou --dry-run
```

## 当前状态（证据为准）

| 项 | 状态 |
|---|---|
| FLUX.3 在 A750 出图 | `PASS_LIMITED`（576×1024，约 2–2.5 分钟/张） |
| VoxCPM2 旁白 | `PASS_VERIFIED`（技术；盲听 7/7 优于旧模型） |
| Wan2.2 TI2V 5B | `PASS_VERIFIED`（历史实测；121 帧约 60–70 分钟/镜） |
| Script-to-Film 制作层 | `IMPLEMENTED_NOT_VERIFIED`（模块、CLI、示例项目、测试已落地，尚无完整成片） |
| 12 套风格包 | `SPEC_DRAFT`（引擎与校验已实现；参考板与样片待审） |
| MiniMax H3 | `NOT_RUN`（仅完成代码与硬件分析） |

## 环境边界

- 根 `.venv`（Python 3.12，uv）只做调度，**不装 torch**。
- `runtime/ComfyUI/.venv`（PyTorch XPU + ComfyUI + GGUF），生成专用。
- 模型仓库 `D:\AI\models`，单端口：ComfyUI 8188、LLM 8080、TTS 50000、工作台 8765。
- 8 GB A750 是独占资源：LLM / FLUX / Wan 不同时生成。
- 本地 HTTP 探测必须绕过系统代理（`httpx(trust_env=False)` / `curl.exe`）。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/PRD.md](docs/PRD.md) | 唯一 SSOT |
| [docs/FILM_PRODUCTION_GUIDE.md](docs/FILM_PRODUCTION_GUIDE.md) | Script-to-Film 制作指南 |
| [docs/VISUAL_STYLE_ENGINE.md](docs/VISUAL_STYLE_ENGINE.md) | 12 套风格包与一致性 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 目标架构与协议 |
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | 冻结技术栈 |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | 硬件、端口、环境 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | ADR（含 ADR-016…021） |
| [docs/README.md](docs/README.md) | 文档索引与状态规则 |
