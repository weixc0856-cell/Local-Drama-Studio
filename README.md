# Local-Drama-Studio · Product v1.0

面向抖音和小红书的**东方视觉内容生产工具**：用本地 AI 把诗词、古典人物与神话意象，制作成有画面、有声音、有字幕、有节奏的竖屏短视频。

> **唯一需求入口：[docs/PRD.md](docs/PRD.md)（SSOT）。** 最新决策：默认 TTS 为 CosyVoice2-0.5B zero-shot，300M SFT 仅显式可选。PRD 配套：[PRD_CHANGELOG](docs/PRD_CHANGELOG.md)、[REQUIREMENT_TRACEABILITY](docs/REQUIREMENT_TRACEABILITY.md)。

早期作为本地 AI 短剧实验室，目标链路：

```
剧本 → 分镜 → 人物/场景资产 → 首帧 → 视频片段 → 配音 → 字幕 → 剪辑 → MP4
```

目标不是"装一个 ComfyUI 然后生成几段视频"，而是一套**有数据契约、有状态、可断点续跑**的生产流水线。当前已实现单篇竖屏流程与本地生产工作台（项目/期数/风格/任务，SQLite `projects/workspace.db`）；镜头级状态机、自动文案/分镜、平台发布仍待开发（见 PRD §21 / ROADMAP）。

| 层（目标架构） | 职责 | 技术 |
|---|---|---|
| 调度层 | 剧本解析、任务状态、资产复用、质量门、断点续跑 | Python 3.12 + Pydantic + SQLite + Typer |
| 生成层 | 静态图、图生视频/文生视频 | ComfyUI + FLUX.2 klein 4B + Wan2.2 TI2V 5B |
| 语音层 | 角色对白、旁白 | 已有 CosyVoice CPU 服务（`D:\AI\CosyVoice-Runtime`） |
| 文本层 | 剧本结构化、分镜、提示词 | 已有 llama.cpp 服务（`D:\AI`，Qwen3） |
| 合成层 | 拼接、混音、字幕、转码 | FFmpeg 8.1 |

**ComfyUI 只是底层生成引擎，不是项目本体。**

---

## v1.0 产品基线（2026-11-03 冻结）

> 冻结产品方向、内容范围、技术栈、流程边界与文档体系；**不表示所有能力已验证，也不表示市场已验证**。

| 文档 | 内容 |
|---|---|
| [docs/PRD.md](docs/PRD.md) | **唯一 SSOT**：产品定位、范围、TTS/风格决策、需求编号、验收标准 |
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | 冻结技术栈、版本、许可证、性能基线 |
| [docs/CONTENT_SPEC.md](docs/CONTENT_SPEC.md) | 视觉/人物/声音/字幕/视频规范 |
| [docs/PRODUCTION_WORKFLOW.md](docs/PRODUCTION_WORKFLOW.md) | 14 步流程、现状、失败降级、成本 |
| [docs/PLATFORM_PUBLISHING_SPEC.md](docs/PLATFORM_PUBLISHING_SPEC.md) | 抖音/小红书包装与合规 |
| [docs/ASSET_AND_LICENSE_REGISTRY.md](docs/ASSET_AND_LICENSE_REGISTRY.md) | 模型/素材/字体/音乐授权 |
| [docs/QUALITY_AND_METRICS.md](docs/QUALITY_AND_METRICS.md) | 质量门、成本、平台数据 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | M3《洛神赋》、M4 平台测试、v1.1 |
| [docs/VISUAL_STYLE_SPEC.md](docs/VISUAL_STYLE_SPEC.md) | 双核心视觉风格（青绿工笔 / 写意水墨）、配置边界、动画合成路线 |
| [docs/README.md](docs/README.md) | 文档索引与状态规则 |
| [docs/PIPELINE_AB_VALIDATION.md](docs/PIPELINE_AB_VALIDATION.md) | 双视觉管线首批验证：水墨分层 / 工笔长卷 |
| [docs/PIPELINE_FIX_REPORT.md](docs/PIPELINE_FIX_REPORT.md) | 双管线专项修复：水墨 Motion Mask / C1-C2、工笔 G3 |

## 生产文档（2026-11-04）

| 文档 | 内容 |
|---|---|
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | 产品是什么、能做什么、两种风格、TTS 策略、边界 |
| [docs/PRODUCTION_PIPELINE_GUIDE.md](docs/PRODUCTION_PIPELINE_GUIDE.md) | 四类生产路径、阶段输入/输出/命令/失败恢复 |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | 从环境准备到一篇成片、工作台操作 |
| [docs/PRODUCTION_CONFIG_GUIDE.md](docs/PRODUCTION_CONFIG_GUIDE.md) | 实际配置 / 推荐值 / 未验证参数 |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | 架构、契约、任务、API、扩展 |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | 故障排查 |
| [docs/PROJECT_NEXT_STEPS.md](docs/PROJECT_NEXT_STEPS.md) | P0–P4 路线 |
| [docs/audit/](docs/audit/) | Phase A 仓库/能力/架构审计 |
| [docs/PRD_CHANGELOG.md](docs/PRD_CHANGELOG.md) | PRD 变更记录与旧文档冲突修正 |
| [docs/REQUIREMENT_TRACEABILITY.md](docs/REQUIREMENT_TRACEABILITY.md) | 需求编号、验收、Phase A 映射、当前状态 |

技术证据仍保留在 `docs/R0_*` ~ `docs/R3_*`、`docs/S2_TEST_REPORT.md`、`docs/PIPELINE_AB_VALIDATION.md` 与 `docs/PIPELINE_FIX_REPORT.md`，不合并、不删除。

## 当前状态（2026-11-04 更新）

| 项目 | 状态 |
|---|---|
| 根目录 `.venv`（调度环境） | ✅ 已创建（Python 3.12.10，uv 0.10.8） |
| 配置 / 数据契约 / doctor | ✅ 已实现；当前 **354 项测试通过** |
| R0-A 硬件与依赖诊断 | ✅ `PASS_VERIFIED`（见 [R0_TEST_REPORT](docs/R0_TEST_REPORT.md)） |
| R0-B ComfyUI + PyTorch XPU | ✅ `PASS_VERIFIED`：ComfyUI 0.43.0 / torch 2.15.0+xpu / xpu:0 Arc A750 7.75 GiB |
| R0-C FLUX 静态图 | ✅ `PASS_VERIFIED`：512×512 / 4 步 / 99.5s / 峰值 2.61 GiB |
| R0-D Wan 视频 | ✅ `PASS_VERIFIED`：T2V/I2V 512×512×33 帧，20 步；I2V 约 10 分钟 |
| R0-E 模型互斥 / 重载 | ✅ `PASS_VERIFIED`：3 轮 FLUX↔Wan 切换无 OOM |
| R1-A 项目审查 | ✅ `PASS_VERIFIED`（[R1_AUDIT](docs/R1_AUDIT.md)） |
| R1-B 视觉规范 | ✅ `PASS_VERIFIED`（[R1_VISUAL_DESIGN](docs/R1_VISUAL_DESIGN.md)） |
| R1-C FLUX 16:9 资产 | ✅ `PASS_VERIFIED`：11 次生成，768×432，70-102 s/张，峰值 2.84 GiB |
| R1-D 关键帧 | ✅ `PASS_VERIFIED`（保留 KF4 光源歧义） |
| R1-E 批处理/续跑/恢复 | ✅ `PASS_VERIFIED` |
| R2-A 1024×576 边界测试 | ✅ 73 帧 `PASS_VERIFIED`；121 帧 `PASS_LIMITED`（A4 漂色） |
| R2-B 英雄镜头 | ✅ 4/4 技术成功；H2 `PASS_VERIFIED`，H1/H3/H4 `PASS_LIMITED` |
| R3-A 竖屏能力 | ✅ `PASS_VERIFIED`：FLUX/Wan 576×1024，Wan 36.4 min / 5.48 GiB |
| R3-B 单篇成片 | ✅ `PASS_VERIFIED`：38.04 s / 1080×1920 / 5 静帧 + 1 Wan / 配音 / 字幕 |
| R3-C 单篇成本 | ✅ `PASS_VERIFIED`：端到端 43.8 min；多篇批处理 `NOT_RUN` |
| R3 基线提交 | ✅ `0204979`（父 `026509b`） |
| R3-D 声音/字体/BGM/音效选型 | ⚠️ `PARTIAL`：字体/字幕完成；SFT「中文女」已进入 P1 与 81.373 s 工笔；BGM/音效/商用授权未完成；默认已切换为 CosyVoice2-0.5B zero-shot，SFT 显式可选 |
| P1 生产闭环 | ✅ `PASS_VERIFIED`：ContentPackage → 文案/分镜 → 女声 TTS → FLUX → segments → 14.0 s 成片 → quality PASS；见 PRD §21 |
| 完整工笔案例 | ✅ `PASS_VERIFIED`（技术+验证）：81.373 s / 1080×1920 / 13 段 / 18 句；`scroll_shot.py` + 预渲染 clips，不是 `motion.plan` 自动运动；见本地 `projects/proj_chunjiang_gongbi/episodes/ep_chunjiang_gongbi_01/PRODUCTION_REPORT.md` |
| TTS 默认策略 | ✅ PRD：默认 **CosyVoice2-0.5B zero-shot**；300M SFT 仅显式可选。默认任务真实 0.5B 2 行 PASS（`PRD-TTS-001` = `PASS_VERIFIED`）；显式模式/运行时校验/manifest 记录已实现；`config/voices.yaml` 支持逐行多音色与 `voice_cast.yaml` sidecar |
| 双风格状态 | `PASS_STATIC`（规范/配置）；`PASS_VERIFIED`（各 2 镜头技术样片，M7）；`PARTIAL`（作品级锁定）；`NOT_RUN`（跨镜头一致性正式验证） |
| 生产工作台 | ✅ `PASS_VERIFIED`（doctor / build / TTS / ComfyUI 批处理 / quality 真实执行）；LI 任务 `NOT_RUN` |
| R4-R7（早期编号） | ⛔ 未执行；后续以 ROADMAP 的 M3/M4 为准 |

```powershell
# 任何时候查看真实状态（不会猜测，未执行即 NOT_RUN）
scripts\doctor.ps1
```

### R1 结论摘要

- 16:9（768×432）可直接生成，无需改工作流；约 70-102 秒/张，峰值 2.84 GiB。
- `ReferenceLatent` 参考图编辑在本机 Q4 + XPU 上可用；它保留河湾/远山/色板，提示词控制时间与内容。
- 四张关键帧：江畔初月、花林月照、孤舟远行、落月晨曦；见 [assets/keyframes/](assets/keyframes/)。
- 一致性对比：参考图辅助在空间锚点上更稳，纯文字色板接近但地貌会漂移。
- （R1 时点）明确未做：1080p、视频、人物一致性。当时下一步是 R2 的 /32 分辨率约束（1024×576）。

### R2-A 结论摘要

- 1024×576 可行：73 帧 40-43 分钟 / 3 秒，121 帧 66-69 分钟 / 5 秒，峰值 ≤6.12 GiB，无 OOM。
- **默认 73 帧**；121 帧的 A4 花林出现肉眼可见的绿色漂移。
- 动作幅度普遍偏小；“孤舟漂移”几乎没有位移。
- 全 Wan 的 90 秒片约 20 小时；4-6 个 Wan 镜头 + 静帧推拉的混合方案约 4-5 小时。
- R2-B 随后执行（见下一节）；R2-B 后停在 R3 之前。

### R2-B 结论摘要

- 4 个英雄镜头全部生成，总耗时 2.62 小时，峰值 ≤5.66 GiB。
- H2 花林推近可直接使用。
- H3 孤舟有 24.6 px 主体位移，但方向向右下（靠近镜头），不是向远山；不能用于“远去”叙事。
- H1/H4 可作为近静态空镜，但推近/暖光变化未实现。
- 结论：Wan 适合“缓慢推近”类英雄镜头；精确主体位移需后期或改镜头设计。

### R3 结论摘要

- 竖屏 576×1024 可用：FLUX 22-53 秒/张，Wan 73 帧 36.4 分钟，峰值 5.48 GiB。
- 单篇 38.04 秒竖屏成片：5 张静帧 + 1 段 Wan + 7 句 CosyVoice + 字幕，1080×1920。
- 端到端 43.8 分钟/篇；8 小时理论约 10 篇，保守 6-8 篇/夜（多篇未实测）。
- 成片路径：`experiments/r3b/renders/final_9x16.mp4`（软字幕）与 `final_9x16_burned.mp4`。
- R3 已提交 `0204979`；下一步是 R3-D（女声/字体/BGM/音效选型），不是直接进入《洛神赋》。

### R0 结论摘要

- 两个模型都能在 A750 8 GB 上实际推理：FLUX 约 95-100 秒/张，Wan 约 9-10 分钟/1.375 秒片段。
- Wan **必须 20 步**；10 步会产生彩虹伪影。
- 文本编码器（Qwen3-4B / UMT5）放在 CPU，扩散模型与 VAE 在 XPU；峰值显存约 5 GiB。
- 45 秒成片按实测外推约 7-10 小时/集，属于挂机批处理，不是交互式创作。
- 完整证据与限制见 [docs/R0_TEST_REPORT.md](docs/R0_TEST_REPORT.md) §6。

---

## 环境边界（必须保持）

```
Local-Drama-Studio\
├─ .venv\                    # 调度环境：只装 httpx / pydantic / typer / FFmpeg 调用
├─ runtime\
│  └─ ComfyUI\
│     ├─ .venv\              # 生成环境：PyTorch XPU + ComfyUI + GGUF 节点，独立
│     ├─ custom_nodes\
│     └─ extra_model_paths.yaml
├─ config\                   # 全局配置（模型、生成参数、音频）
├─ workflows\                # ComfyUI API 格式工作流
├─ src\drama_studio\
├─ projects\                 # 工作台 SQLite 状态 + 每期产物目录
└─ scripts\                  # setup / doctor / start / stop
```

两条硬规则：

1. **根 `.venv` 永远不安装 torch。** Torch/XPU 只存在于 `runtime/ComfyUI/.venv`，ComfyUI 升级不会污染其他项目。
2. **模型权重不复制、不进 Git。** 统一存放在 `D:\AI\models`，ComfyUI 通过 `extra_model_paths.yaml` 引用。

`D:\AI\models` 的顶层文件**不能移动**：`D:\AI\start_server.bat` 只扫描顶层 `*.gguf`。新增的文本编码器/VAE 放到 `text_encoders\`、`vae\` 子目录，ComfyUI 同时映射顶层和子目录。

---

## 快速开始

```powershell
# 1. 创建调度环境（幂等）
uv sync --python 3.12

# 2. 重建并校验本地字体（OTF 不进 Git）
.venv\Scripts\python.exe scripts\fetch_fonts.py

# 3. 健康检查（写 logs\doctor-*.json）
scripts\doctor.ps1

# 4. 安装生成引擎（独立 venv，下载 PyTorch XPU）
scripts\setup.ps1 -WithComfyUI

# 5. 启动/停止 ComfyUI
scripts\start.ps1
scripts\stop.ps1
```

模型配套文件（文本编码器、VAE）的下载清单与目标路径见 [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)。

---

## 生产工作台（2026-11-03）

本地单用户 Web 工作台，把项目、期数、素材、成片、任务与日志放到一个页面里管理。

```powershell
# 启动（默认 127.0.0.1:8765；不占用 8080/8188/50000）
.venv\Scripts\drama.exe serve --port 8765
# 浏览器打开 http://127.0.0.1:8765
```

原则：

- **只读派生**：期数进度、素材状态、成片参数每次从真实文件（`segments.json` / `audio_manifest.json` / `build_manifest.json` / 哈希 / ffprobe）计算；未执行的步骤显示 `NOT_RUN`。
- **受限执行**：只有任务注册表内的入口可被触发（环境诊断、合成重建、ComfyUI 批处理、LI 五轮、ComfyUI 启停）；无任意 shell、无第二个 LLM 端口、GPU 单飞锁。
- **不覆盖历史**：重建写入新的 `projects/<project>/episodes/<episode>/renders/build-<时间>/`；`experiments/r3b` 等历史产物保持原样。
- 项目/期数/风格/任务记录保存在 `projects/workspace.db`（Git 忽略）。

交付与限制见 [docs/WORKSPACE_REPORT.md](docs/WORKSPACE_REPORT.md)；审计见 [docs/PROJECT_AUDIT.md](docs/PROJECT_AUDIT.md)。

---

## CLI 规划

> 下面是早期 CLI 规划，v1.0 **尚未实现**；当前实际使用 `scripts/*.py` 与 `drama doctor`。

```text
drama doctor                 # 环境/服务/模型真实状态        [已实现]
drama create <project>       # 创建短剧项目                  [R4]
drama script <project>       # 剧本 → storyboard.json        [R4]
drama assets <project>       # 人物/场景/道具参考图           [R5]
drama images <project>       # 分镜首帧                      [R5]
drama videos <project>       # Wan 批量生成镜头片段          [R2/R3]
drama audio <project>        # 配音 + 字幕                   [R6]
drama render <project>       # 剪辑 + 输出 MP4               [R6]
drama run <project>          # 完整流水线                    [R7]
drama resume <project>       # 断点续跑                      [R7]
```

---

## 已执行阶段（历史证据）

| 阶段 | 实际内容 | 状态 |
|---|---|---|
| R0 环境 | XPU / ComfyUI / FLUX / Wan | `PASS_VERIFIED` |
| R1 视觉资产 | 16:9 关键帧、参考图编辑、批处理 | `PASS_VERIFIED` |
| R2-A 性能边界 | 1024×576 / 73 / 121 帧 | `PASS_VERIFIED` / `PASS_LIMITED` |
| R2-B 英雄镜头 | 4 镜头、主体位移审计 | `PASS_VERIFIED` / `PASS_LIMITED` |
| R3 竖屏成片 | 576×1024、38.04 秒 1080×1920 | `PASS_VERIFIED` |

后续产品路线见 [docs/ROADMAP.md](docs/ROADMAP.md)（M3《洛神赋》/ M4 平台测试）。早期 R4-R7 只是设计编号，未执行。

当前最长的已验证生产案例是 81.373 秒 / 1080×1920 / 13 段 / 18 句的工笔《春江花月夜》，使用 `scroll_shot.py` + 预渲染 clips；R3 的 38.04 秒单篇是 5 静帧 + 1 Wan 路径。两条路径不要混为一谈。后续路线：R3-D 剩余项（BGM/音效/商用授权）→ M3《洛神赋》完整样片 → M4 平台发布与数据验证；R3-D 完成前不进入《洛神赋》正式样片。

---

## 明确不做

- 不做公网部署、多用户权限或自动发布（本地单用户工作台已提供，见 ADR-014）
- 不引入 LangChain / 向量数据库 / 多 Agent 框架
- 不自己训练或微调生成模型
- 不承诺电影级人物一致性、口型同步、跨镜头同一张脸
- 不在 8GB 显存上同时加载 LLM、FLUX、Wan
- 不做自动发布、数字人、SeedVR2、新视频模型（v1.0）
- 不为未验证的市场假设扩大技术栈

---

## 仓库边界（2026-11-03）

远程仓库只包含**开发工作流**：

- 代码：`src/`、`scripts/`、`literary_intelligence/`
- 配置与工作流：`config/`、`workflows/`
- 文档与测试：`docs/`、`tests/`
- 字体清单/许可：`assets/fonts/font_manifest.json`、README、LICENSE
- 项目入口：`pyproject.toml`、`uv.lock`、`CLAUDE.md`、README

以下内容只保留在本地，不进入远程仓库：

- `experiments/`：技术验证产物、样片、帧、差分与运行日志
- `projects/`：真实项目/期数数据与产物（仅保留 `.gitkeep`）
- `assets/keyframes/`、`assets/vertical/`、`assets/visual_style/`：生成的视觉素材
- `logs/`、`runtime/ComfyUI/`、模型权重、字体 OTF 二进制

字体可由 `scripts/fetch_fonts.py` 按 manifest 哈希重建；样片与真实案例通过本地产物目录和授权台账管理。

---

## 文档

| 文档 | 内容 |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统设计、数据契约、状态机、失败恢复 |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | 已核实硬件、双 venv、模型仓库、端口与显存预算 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | 关键设计决策（ADR） |
| [docs/R0_TEST_PLAN.md](docs/R0_TEST_PLAN.md) | R0-A ~ R0-E 测试步骤与验收标准 |
| [docs/R0_TEST_REPORT.md](docs/R0_TEST_REPORT.md) | R0 实际执行结果与证据 |
| [docs/R1_AUDIT.md](docs/R1_AUDIT.md) | R1 现有工作流/编辑能力审查 |
| [docs/R1_VISUAL_DESIGN.md](docs/R1_VISUAL_DESIGN.md) | 《春江花月夜》视觉规范 |
| [docs/R1_TEST_PLAN.md](docs/R1_TEST_PLAN.md) | R1 实验与关键帧计划 |
| [docs/R1_TEST_REPORT.md](docs/R1_TEST_REPORT.md) | R1 实际结果、对比与限制 |
| [docs/R2_TEST_PLAN.md](docs/R2_TEST_PLAN.md) | R2-A/R2-B 计划 |
| [docs/R2_TEST_REPORT.md](docs/R2_TEST_REPORT.md) | R2-A 实测结果与生产预算 |
| [docs/R2B_TEST_PLAN.md](docs/R2B_TEST_PLAN.md) | 4 个英雄镜头设计与验收口径 |
| [docs/R2B_TEST_REPORT.md](docs/R2B_TEST_REPORT.md) | R2-B 逐镜头结果与 H3 位移分析 |
| [docs/R3_TEST_PLAN.md](docs/R3_TEST_PLAN.md) | 竖屏/单篇/成本计划 |
| [docs/R3_TEST_REPORT.md](docs/R3_TEST_REPORT.md) | R3 竖屏成片与成本实测 |
| [docs/CONTENT_PACKS.md](docs/CONTENT_PACKS.md) | 通用主题包与共享层边界 |
