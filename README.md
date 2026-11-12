# Local-Drama-Studio · Script-to-Film

面向抖音和小红书的**本地影视化内容生产系统**：把诗词、古典故事与意象，按导演分镜的方式制作成有画面、有声音、有剪辑节奏的竖屏短片。

> **唯一需求入口：[docs/PRD.md](docs/PRD.md)（SSOT）。** 文档索引：[docs/README.md](docs/README.md)；历史材料：[docs/ARCHIVE.md](docs/ARCHIVE.md)；决策记录：[docs/DECISIONS.md](docs/DECISIONS.md)。

## 当前技术栈

| 层 | 职责 | 技术 |
|---|---|---|
| 制作层 | 剧本、旁白、分镜、连续性、时间轴、提示词编译 | Python 3.12 + Pydantic（`domain/`、`application/film/`） |
| 图像 | 关键帧、场景与人物 | ComfyUI + **FLUX.3 Klein**（GGUF Q4_K_M，16 步，CFG 1.0） |
| 视频 | 镜头动画 | ComfyUI + **Wan2.2 TI2V 5B**（GGUF Q4_K_M，20 步） |
| 语音 | 逐句旁白 | **VoxCPM2**（`VoxCPM-Runtime`，50000，48 kHz，CPU，zero-shot） |
| 文本 | 剧本结构化、分镜、提示词 | 本地 llama.cpp（8080，Qwen3-30B-A3B，CPU-only，64K） |
| 合成 | 剪辑、混音、字幕、转码 | FFmpeg 8.1 + `r3_build` |

ComfyUI 只是生成引擎；业务状态、调度、质量门与制作层都在 Python 侧。

## 生产链路

```text
诗词/文本 → 旁白稿 → 导演分镜 → 视觉圣经 + 风格包
→ FLUX.3 关键帧 → Wan 镜头（PNG 帧）→ clips → 确定性运镜
→ VoxCPM2 逐句配音 → 音频优先时间轴 → r3_build 多轨合成
→ 技术质量门 → 人工 H2/H3 审片
```

关键原则：旁白是时间基准；`storyboard.json` 是镜头的唯一事实源；字幕、混音、画面共享同一毫秒边界。

## 目录

| 路径 | 内容 |
|---|---|
| `src/drama_studio/domain/` | 纯规则与严格契约（contracts / style / voice / motion / film / aesthetics / bible） |
| `src/drama_studio/application/` | 用例（film / voice / motion / operations / production / script_engine / quality） |
| `src/drama_studio/infrastructure/` | 适配器（storage / media / fonts / locks / envprobe） |
| `src/drama_studio/interfaces/` | CLI、FastAPI、静态 UI 服务 |
| `src/drama_studio/paths.py` | 仓库根 vs 产出根解析（`DRAMA_OUTPUT_ROOT`） |
| `config/style_packs/` | 23 套风格包（retro 4 / oriental 3 / artistic 5 / realism 2 / animation 3 / advertising 6） |
| `workflows/` | API 格式工作流（`flux3_t2i_api.json`、Wan I2V/T2V） |
| `docs/` | PRD、环境、流程、风格、音频、质量、路线图、架构与 ADR |
| `D:\DramaStudio\` | **产出根**：projects / experiments / style_boards / logs / workspace.db（不进 Git） |

## 快速开始

```powershell
Copy-Item .env.example .env      # 填 DRAMA_MODELS_ROOT / DRAMA_AI_HOME / DRAMA_OUTPUT_ROOT
uv sync --python 3.12
.venv\Scripts\drama.exe doctor --json

# Script-to-Film（制作层纯 CPU；生成前启动 ComfyUI 8188）
.venv\Scripts\drama.exe film init --project <id> --text <utf8.txt> --title "<title>" --duration 120
.venv\Scripts\drama.exe film script --project <id> --text <utf8.txt> --write-storyboard
.venv\Scripts\drama.exe film plan --project <id> --beats <beats.json>
.venv\Scripts\drama.exe film prompts --project <id>
.venv\Scripts\drama.exe film keyframes --project <id>
.venv\Scripts\drama.exe film wan-jobs --project <id> --profile safe8g
.venv\Scripts\python.exe scripts\wan_batch.py --project <id> --shots S02,S03
.venv\Scripts\drama.exe film clips --project <id>
.venv\Scripts\drama.exe film motion --project <id>
.venv\Scripts\drama.exe film voice --project <id>        # VoxCPM2 50000
.venv\Scripts\drama.exe film assemble --project <id>
.venv\Scripts\drama.exe film status --project <id> --write
.venv\Scripts\drama.exe film qc --project <id>

# 工作台
.venv\Scripts\drama.exe serve --port 8765
```

## 当前状态（证据为准）

| 项 | 状态 |
|---|---|
| Script-to-Film 全链路 | `PASS_VERIFIED`（47.0 s / 1080×1920 / 24 fps，quality + acceptance PASS） |
| FLUX.3 在 A750 出图 | `PASS_LIMITED`（576×1024，约 22–53 s/张） |
| Wan2.2 TI2V 5B | `PASS_VERIFIED`（纯风景条件可用；建筑/人物 `BLOCKED`） |
| VoxCPM2 旁白 | `PASS_VERIFIED`（技术；商用授权 `UNVERIFIED`） |
| 23 套风格包 | 参考板 23/23 生成、客观检查全过；人工审美 `PENDING_REVIEW` |
| BGM / SFX | BGM 已登记（Commons PD/CC BY）；SFX 自生成；商用授权 `NOT_RUN` |
| 全 Wan 多镜头 / 2–5 分钟全生成 | `BLOCKED`（A750 8 GB 限制） |

## 环境边界

- 根 `.venv` 只做调度，**不装 torch**；`runtime/ComfyUI/.venv` 是 PyTorch-XPU + ComfyUI。
- 模型仓库 `models`（默认 `D:/AI/models`）；两个扩散 GGUF 必须在顶层。
- 单端口：ComfyUI 8188、LLM 8080、TTS 50000、工作台 8765；8080 单实例、谁启动谁停止。
- 8 GB A750 是独占资源：LLM / FLUX / Wan 不同时生成。
- 本地 HTTP 探测绕过系统代理（`httpx(trust_env=False)` / `curl.exe`）。

## 仓库与产出分离

代码、配置、文档、测试与小型 manifest 在仓库；projects、渲染、参考板图片、日志与工作区 DB 在 `DRAMA_OUTPUT_ROOT`（默认 `D:\DramaStudio`）。规则与守门见 [docs/REPO_LAYOUT.md](docs/REPO_LAYOUT.md)。

```powershell
.venv\Scripts\python.exe scripts\check_repo_hygiene.py
.venv\Scripts\python.exe -m pytest
```

## 文档

| 文档 | 内容 |
|---|---|
| [docs/README.md](docs/README.md) | 文档索引（14 份当前文档 + 归档索引） |
| [docs/PRD.md](docs/PRD.md) | 唯一 SSOT |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | 硬件、技术栈、模型、端口、显存 |
| [docs/REPO_LAYOUT.md](docs/REPO_LAYOUT.md) | 仓库 vs 产出根、DDD 分层 |
| [docs/PRODUCTION_GUIDE.md](docs/PRODUCTION_GUIDE.md) | 14 步流程、film 链路、配置 |
| [docs/FILM_PRODUCTION_GUIDE.md](docs/FILM_PRODUCTION_GUIDE.md) | Script-to-Film 方法 |
| [docs/VISUAL_STYLE.md](docs/VISUAL_STYLE.md) | 风格引擎与 23 套风格 |
| [docs/AUDIO_AND_LICENSING.md](docs/AUDIO_AND_LICENSING.md) | 音频与授权台账 |
| [docs/QUALITY_AND_METRICS.md](docs/QUALITY_AND_METRICS.md) | 质量门与指标 |
| [docs/PLATFORM_PUBLISHING.md](docs/PLATFORM_PUBLISHING.md) | 平台发布与舒适区 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 路线与能力边界 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | ADR |
| [docs/GUIDE.md](docs/GUIDE.md) | 操作/开发/排障 |
