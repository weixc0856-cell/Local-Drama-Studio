> 状态：历史审计（2026-11-03 Phase A）。本文件已被 `docs/PRD.md` §21 与 P0 修复取代，不再作为现状来源。
> 勘误：§1.5 与 TD-05 当时写“manifest 被跟踪”，实际整个 `assets/fonts/` 被忽略；P0 后 manifest/README/LICENSE 可跟踪，OTF 由 `scripts/fetch_fonts.py` 重建。

# 全项目审计（Phase A）

> 审计日期：2026-11-03
> 审计基线：`main` / HEAD `e21dc0d`（`feat(literary-intelligence): enforce LI-1.6 role contracts`）
> 范围：整个仓库（`src/`、`scripts/`、`literary_intelligence/`、`config/`、`experiments/`、`assets/`、`tests/`、`docs/`），不只是 literary_intelligence
> 方法：静态阅读全部源码与配置 + 实际执行测试 + 对真实产物做哈希/ffprobe 核验 + 比对文档声明与代码行为
> 本阶段：只读审计。未修改任何生产代码、未启动任何模型服务、未删除任何实验资产、未提交 Git

---

## 0. 执行前状态（保护记录）

| 项 | 实际值 |
|---|---|
| 分支 | `main` |
| HEAD | `e21dc0d3ea577b170056fff7c6a4afc230c159a5`（与预期一致） |
| 已修改未提交 | 25 个（LI-1.5/1.6、R3-D、v1.0 文档） |
| 未跟踪 | 12 项（`config/fonts.yaml`、5 份 R3-D 报告、`docs/literary_intelligence/`、`content_package.py`、`src/drama_studio/voice/`、`src/drama_studio/fonts.py`、`tests/test_fonts.py` 等） |
| 本次审计动作 | 只读；未执行 `reset/clean/checkout`；未改工作区 |

> 本次工作台工作新增的文件将全部为新文件；对既有文件的改动限于新增 CLI 命令与文档，不重写成熟模块。

---

## 1. 实际模块地图

### 1.1 源码（真实存在）

| 文件 | 职责 | 状态 | 被谁调用 |
|---|---|---|---|
| `src/drama_studio/config.py` | 发现根目录、加载 4 份 YAML、路径解析、模型尺寸校验 | 已实现、有测试 | `cli.py`、`doctor.py`、`fonts.py`、`run_li15.py` |
| `src/drama_studio/models.py` | `Storyboard/Shot/Character/Location/Prop/ProjectManifest` 严格契约 | 已实现、仅测试使用 | 仅 `tests/test_models.py` |
| `src/drama_studio/doctor.py` | 环境/服务/模型诊断，四态输出 | 已实现、有测试、已真实运行 | `cli.py` |
| `src/drama_studio/cli.py` | 仅 `doctor` 一个命令 | 已实现 | `drama` 入口 |
| `src/drama_studio/fonts.py` | 字体清单、SHA-256 校验、角色→字面映射 | 已实现（未跟踪）、有测试 | `scripts/r3_build.py` |
| `src/drama_studio/voice/timeline.py` | 整数毫秒时间轴、SRT、尾部静音 | 已实现（未跟踪）、有测试 | `scripts/r3_build.py` |
| `src/drama_studio/voice/__init__.py` | 包声明 | 空壳 | — |

### 1.2 脚本（真实存在，均为可执行入口，不是库）

| 脚本 | 职责 | 真实运行证据 |
|---|---|---|
| `scripts/doctor.ps1` | 调 `drama doctor` | `logs/doctor-*.json` 多份 |
| `scripts/setup.ps1` / `start.ps1` / `stop.ps1` | ComfyUI 安装与启停（8188） | `logs/comfyui*.log`、`comfyui-system-stats.json` |
| `scripts/llm_server.ps1` | 项目 llama-server 生命周期（8080，仅停自己启动的实例） | `logs/llm-8080.*.log`、`li15_llm.pid` |
| `scripts/r0_comfy_probe.py` | 提交 API 工作流 → 轮询 /history → 下载 | `logs/r0/*` |
| `scripts/r1_batch.py` | 批量、续跑、跳过、重试、来源记录 | `experiments/*/*_manifest.json`、30 个 `job.json` |
| `scripts/r1_compare.py` | 关键帧一致性对比 | `experiments/r1/runs` |
| `scripts/r2_analyze_frames.py` | 帧序列编码/闪烁/黑帧指标 | R2 报告引用 |
| `scripts/r2b_track_boat.py` | 主体位移启发式追踪 | R2-B 报告（H3 结论） |
| `scripts/r3_tts.py` | CosyVoice 逐句合成 + 48 kHz 重采样 | `experiments/r3b/audio/*.wav` + manifest |
| `scripts/r3_build.py` | FFmpeg 合成、时间轴、SRT/ASS、字体校验、成片 | `experiments/r3b/renders/final_9x16.mp4` |

### 1.3 literary_intelligence（独立包）

| 子目录 | 内容 | 状态 |
|---|---|---|
| `schemas/` | `Claim/Review/SourceRecord/LLMPassOutput/ContentPackage` | 已实现、有测试；`ContentPackage` 未被生产链路消费 |
| `harness/` | 规范化、来源注册、FTS5 检索、证据校验、五角色流水线、Mock LLM、真实 LLM 客户端 | 已实现、61 项测试；真实 LLM 运行 `PARTIAL` |
| `corpus/luoshen_fu/` | 原文、规范化文本、segments、source registry、claims（全部 `unreviewed`）、空 reviews | 真实数据 |
| `runs/li15`、`li15_pre_explicit`、`li16`、`li16d*` | 真实本地 LLM 五轮输出（含 1 次失败记录） | 真实证据，**被 `.gitignore` 忽略，仅本机存在** |
| `skills/` | 4 份分析/研究/审核/写作 Skill 文档 | 文档 |

### 1.4 文档中声明但代码不存在（关键）

`docs/ARCHITECTURE.md` §14 与 `CLAUDE.md` 列出的以下模块**均不存在**：

```text
state.py  comfy_client.py  generation/  quality/  script_engine/
character_manager/  storyboard/  audio/  subtitles/  editing/  storage/  orchestrator.py
```

CLI 规划中的 `create / script / assets / images / videos / audio / render / run / resume` **全部不存在**，`drama` 只有 `doctor`。

### 1.5 数据与资产

| 位置 | 内容 | 是否纳入 Git |
|---|---|---|
| `assets/visual_style/` | 风格圣经、J2 参考图、6 张场景、对比图 | 是（PNG） |
| `assets/keyframes/` | 4 张 16:9 关键帧 + meta + relationships | 是 |
| `assets/vertical/` | 5 张 576×1024 + 1 段 Wan + index.json | 是 |
| `assets/fonts/` | 6 个 OTF + LICENSE + manifest | 当时：否（整目录忽略）；P0 后：manifest/LICENSE 可跟踪，OTF 由 fetch 脚本重建 |
| `experiments/r1`、`r2`、`r2b`、`r3a`、`r3b` | 参数、manifest、部分视频 | 部分（帧序列被忽略） |
| `experiments/r3d/` | 字体预览、女声试听、时间轴验证 | **否（`.gitignore`）** |
| `projects/` | 仅 `.gitkeep` | 空 |
| `logs/` | doctor 报告、服务日志、R0 证据 | 否 |
| `literary_intelligence/runs/` | 真实 LLM 证据 | 否 |

---

## 2. 实际生产调用链

### 2.1 R3-B 单篇（唯一跑通的端到端链路）

```text
[人工手写] experiments/r3b/narration.json
      │
      ▼  scripts/r3_tts.py  ──HTTP──▶ CosyVoice 127.0.0.1:50000
      │                                  (/health, /tts)
      ▼
experiments/r3b/audio/line_01..07.wav  +  audio_manifest.json
      │
[人工手写] experiments/r3b/segments.json ──┐
[既有资产] assets/vertical/*.png|mp4 ──────┤
[配置] config/fonts.yaml + assets/fonts ───┤
                                           ▼
                             scripts/r3_build.py
                               ├─ voice.timeline.build_timeline（整数毫秒）
                               ├─ FFmpeg: Ken Burns / 缩放 / concat / fade
                               ├─ 混音: adelay → amix → loudnorm → apad
                               ├─ SRT + ASS（字体角色 subtitle）
                               ├─ libass fontselect 校验（拒绝静默 fallback）
                               └─ ffprobe + 解码校验
                                           ▼
experiments/r3b/renders/final_9x16.mp4（软字幕）
                                final_9x16_burned.mp4（烧录）
                                build_manifest.json
```

**生成前置（另一条独立链路，非同一进程）**

```text
experiments/*/jobs*.json
      │
      ▼ scripts/r1_batch.py ──子进程──▶ scripts/r0_comfy_probe.py ──HTTP──▶ ComfyUI 127.0.0.1:8188
      │                                 (workflow JSON + params + 参考图)
      ▼
<out>/job.json（workflow_sha256、seed、prompt_id、峰值显存、输出 sha256）
<out>/*.png / *.mp4
```

### 2.2 Literary Intelligence（与 R3 完全未连接）

```text
corpus/luoshen_fu/{source_registry, original_text, normalized_text, segments, claims}
      │
      ▼ literary_intelligence/run_li15.py
         ├─ 8080 未启动时拉起项目 llama-server（atexit 停止“自己启动的”实例）
         ├─ 五轮：text_analyst → literary_analyst → researcher → skeptic → editor
         ├─ 证据校验 + 角色合同检查（程序级，不靠提示词）
         └─ 原始响应与失败记录全部落盘
      ▼
literary_intelligence/runs/<run>/{pass}.json + real_pipeline.json
```

`ContentPackage`（LI-2-A）目前只有 Schema 与测试；**没有 Adapter** 把它变成 `segments.json` / `audio_manifest.json`，因此 LI 的结果无法进入 `r3_build.py`。

### 2.3 结论

- 真实链路是**“人工准备 JSON + 单点脚本”**，不是文档描述的“状态机 + 调度器”。
- `run_li15.py` 是唯一一个自己管理外部服务生命周期的生产脚本（且严格遵循“谁启动谁停止”）。
- 三个外部服务（8188 / 8080 / 50000）没有任何统一的生命周期管理。

---

## 3. 能力状态矩阵（严格区分）

> 规则：`PASS_VERIFIED` 必须有执行产物 + 日志/哈希；`PASS_STATIC` 仅静态/测试证据；`PARTIAL` 部分可用；`NOT_RUN` 未执行；`BLOCKED` 依赖缺失。

### 3.1 已真实运行并有产物

| 能力 | 证据 | 状态 |
|---|---|---|
| 环境诊断 `drama doctor` | `logs/doctor-20261103-101221.json` 等 | `PASS_VERIFIED` |
| ComfyUI FLUX 静态图 | `logs/r0/R0-C-*`、`experiments/r3a` | `PASS_VERIFIED` |
| ComfyUI Wan I2V/T2V | `logs/r0/R0-D-*`、R2/R2-B/R3-A job.json | `PASS_VERIFIED` |
| 批处理续跑/失败隔离 | `experiments/r1/recovery_check.out`、`resume_check.out` | `PASS_VERIFIED` |
| CosyVoice「中文男」逐句 TTS | 7 个 WAV + manifest（本轮复核 7/7 哈希一致） | `PASS_VERIFIED` |
| FFmpeg 合成 1080×1920 成片 | `final_9x16.mp4`：38.042 s / h264 1080×1920 / aac 48 kHz 单声道 / mov_text 字幕 / 20.3 MB，manifest 哈希一致 | `PASS_VERIFIED` |
| 字体 SHA-256 + libass fontselect 校验 | `assets/fonts/font_manifest.json`、S3-B.2 fixture `fontselect_match=true` | `PASS_VERIFIED`（fixture 级） |
| LI 五角色真实 LLM 运行 | `runs/li15|li16|li16d`，5/5 JSON、含 1 次角色违规记录 | `PARTIAL`（无人工审核，质量未验收） |

### 3.2 只有测试 / Fixture / Mock

| 能力 | 证据 | 状态 |
|---|---|---|
| `Storyboard/Shot` 数据契约 | `tests/test_models.py`（6 项） | `PASS_STATIC` |
| `ContentPackage` Schema | `test_content_package.py`（来源/引用/重复校验） | `PASS_STATIC` |
| 时间轴规则（诗词/口播/混合、尾静音） | `test_timeline.py`（19 项，实验目录） | `PASS_STATIC`，已真实构建 fixture |
| 正式构建接入新字体 | `s3b2_validation.json` 的 6 秒合成 fixture | `PASS_VERIFIED`（fixture），真实剧集未重建 |
| LI 五轮 Mock | `mock_llm.json` | `PASS_STATIC` |

### 3.3 代码已实现但没有真实运行

| 能力 | 说明 |
|---|---|
| 字体接入真实剧集 | 当前 `final_9x16.mp4` 的 manifest **没有 `font` 字段**，成片是旧版脚本产物（见 §6） |
| `r3_tts.py` 用于第二篇 | 端口、输入、输出全部硬编码到 `experiments/r3b` |
| `r3_build.py` 的 `content_type` / `timeline.json` / `voice_end_ms` | 代码支持，历史成片 manifest 中不存在 |
| 女声 TTS | R3-D 试听产物在 `experiments/r3d/voice`，未进入任何成片；`中文女` 生产口径仍 `NOT_RUN` |

### 3.4 只有设计文档

SQLite 状态机、项目/期数管理、分镜规划器、人物资产、内容包 Adapter、质量门、批处理夜间调度、平台发布、数据回收。全部 `NOT_RUN`。

### 3.5 不应继续使用 / 已被取代

| 项 | 原因 |
|---|---|
| ADR-004「LLM 用 8081」 | 已被 ADR-013 取代，代码与配置均只用 8080 |
| `project.example.yaml` | 没有任何代码读取；字段（`aspect_ratio: 1:1`、`shot_count_target`）与当前竖屏流程不符 |
| `models.py::ProjectManifest` | 无写入方、无读取方；与真实产物脱节 |
| README「明确不做：网页管理后台」 | 与新需求冲突，需要新增 ADR 明示取代，而不是悄悄改历史 |

---

## 4. 文档与代码一致性核对

| 文档声明 | 实际 | 差异等级 |
|---|---|---|
| `PRD/README`：SQLite 状态机、断点续跑、质量门 | 不存在 | 高（已标注“目标架构”，但 README 同时写“有状态、可断点续跑”，易误读） |
| `ARCHITECTURE §14` 模块清单 | 12 个模块中 11 个不存在 | 高 |
| `CLAUDE.md`：`r1_batch` 每条 job 有 provenance | 属实 | — |
| `CLAUDE.md`：`logs/r0/engine-versions.txt` | 存在（logs 被 gitignore） | 低（证据不入库） |
| `ROADMAP`：字体“已接入正式构建” | 仅字幕角色；标题/诗词仍 `preview_only` | 中（措辞需限定为“字幕”） |
| `PRODUCTION_WORKFLOW`：BGM/音效 `NOT_RUN` | 属实 | — |
| `LI README`：61 项测试 | 实测 61 passed | — |
| `pytest` 默认 | `testpaths=["tests"]`，**不含** `literary_intelligence/tests` | 中（默认命令漏测 61 项） |
| `README`：38.04 s 成片 | ffprobe 38.042 s | — |
| `ADR-012`：不做网页后台 | 与新需求冲突 | 需新 ADR |

---

## 5. 重复实现与未调用代码

### 5.1 重复

| 重复项 | 位置 | 影响 |
|---|---|---|
| 服务地址 | `config/settings.yaml` vs `r0_comfy_probe.py:BASE` vs `r3_tts.py:BASE` | 改端口要改代码 |
| 端口默认值 | `config.py`、`settings.yaml`、`start.ps1`、`stop.ps1`、`llm_server.ps1` 各写一遍 | 易漂移 |
| 五轮流程 | `harness/pipeline.py` 与 `run_li15.py` 各实现一遍 | 行为漂移 |
| 音频清单 | `audio_manifest.json`（r3_tts 写）与 `narration.json`（人工） | 两套输入，语义重叠 |
| 状态定义 | `models.ShotStatus` 与文档状态机 | 前者无人使用 |

### 5.2 未被调用的代码

- `models.Storyboard / Shot / Character / Location / Prop`：仅测试引用。
- `models.ProjectManifest`：零引用。
- `ContentPackage`：仅测试与 Schema 导出。
- `harness/pipeline.run_pipeline / run_mock_pipeline`：仅测试；真实入口 `run_li15.py` **复制**了同样的五轮循环与合同检查，而非调用 `pipeline.py`。
- `harness/retrieval.py`：有测试，但生产入口未使用（`run_li15` 直接读 corpus 文件）。
- `config/audio.yaml` 的 `speakers` 映射：`r3_tts.py` 未使用（speaker 来自 `narration.json`）。

---

## 6. 数据一致性缺陷（实测）

本轮做了只读核验：

| 检查 | 结果 |
|---|---|
| `assets/vertical/index.json` 6 项哈希 | **全部一致** |
| `audio_manifest.json` 7 段 WAV 哈希 | **全部一致** |
| `segments.json` 6 个 source 文件 | **全部存在** |
| `build_manifest.json` 的 `final_sha256` | **一致** |
| `build_manifest.json` 字段 | **缺少** `content_type`、`timeline`、`voice_end_seconds`、`trailing_silence_seconds`、`font` |
| `build_manifest.json` 的 `outputs` | 缺少 `timeline.json`、`drama.ass`、`fontselect.log` |
| `drama.ass` 实际存在 | 是（但 manifest 未登记） |

**结论**：现有成片是**旧版 `r3_build.py`** 的产物，当前脚本会写出更完整的 manifest。因此：

- 无法从 manifest 证明“这版成片由当前代码构建”。
- 当前字体接入（Source Han Sans CN）**没有**体现在历史成片里。
- 历史成片实际使用 Microsoft YaHei（ROADMAP 已注明），属于已知事实而非校验结果。

其他一致性问题：

1. 没有稳定 ID：`experiments/r3b` 只是目录名，不是 episode ID；没有反查“该文件属于哪一期”的字段。
2. 没有输入→输出追溯：`r3_tts.py` 的 manifest 不记录 `narration.json` 哈希；`r3_build.py` 不记录 `audio_manifest.json` 哈希。
3. 文件存在 ≠ 记录存在：没有库存表，只能靠目录扫描。
4. `projects/` 为空，`state.db` 不存在，文档中的“权威状态”没有落地。

---

## 7. 任务恢复与并发

| 问题 | 现状 | 严重度 |
|---|---|---|
| 统一任务记录 | 无。只有各脚本自己的 `job.json` / `build_manifest.json` / `real_pipeline.json` | 高 |
| 进程崩溃恢复 | `r1_batch` 靠 `job.json` + 输出哈希续跑；`r3_build` 无中间状态，只能整体重跑 | 中 |
| 单任务重试 | `r1_batch` 最多 1+2 次；`r3_tts`/`r3_build` 无自动重试 | 中 |
| 并发保护 | **无进程级锁**。两个 `r1_batch` 可同时向 8188 提交，违反“GPU 单租户” | 高 |
| 重复启动保护 | `llm_server.ps1` 有端口检查；ComfyUI `start.ps1` 有端口检查；CosyVoice 无项目侧管理 | 中 |
| 失败状态记录 | `r1_batch` 写 `failed`；`run_li15` 写 `FAILED` 且保留 raw；`r3_build` 抛异常后无状态文件 | 中 |
| 覆盖保护 | `r3_build` 默认拒绝覆盖 `final_9x16.mp4`（好）；`r3_tts` 直接覆盖 WAV | 中 |

---

## 8. 版本管理

- 没有「文案/分镜/风格/素材/成片」版本号；同一路径重跑即覆盖。
- 没有 episode 级 `manifest.json`（`ProjectManifest` 模型存在但无人写）。
- 风格定义散落在 `assets/visual_style/style_bible.json`（16:9 项目专用）与提示词文本中，没有可复用的 Style 实体。
- `experiments/r3d/`、`literary_intelligence/runs/` 被 gitignore，导致“已完成的证据”无法随仓库复现。

---

## 9. 资源管理

| 项 | 现状 | 风险 |
|---|---|---|
| GPU 单租户 | 文档与配置声明并发 1，**代码未强制** | 两个批处理同时跑会 OOM |
| 显存读取 | 仅 ComfyUI `/system_stats`；项目无 GPU 监控 | 前端需实时状态时只能探服务 |
| 磁盘 | doctor 检查项目盘与模型盘 | 足够 |
| 临时文件 | `experiments/*/renders/segments/*.mp4` 保留 | 体积增长，无清理策略 |
| 服务生命周期 | 分散在 3 个脚本；`run_li15` 自带 atexit | 前端触发任务必须复用同一套规则，禁止另起端口 |
| 空闲端口 | 8080 必须归还（定时任务依赖） | 若前端常驻持有 LLM 实例，会阻塞定时任务 |

---

## 10. 生产质量可验证性

| 检查项 | 现有能力 | 状态 |
|---|---|---|
| 视频分辨率/比例 | ffprobe（r3_build 内） | 已有 |
| 可解码 | `ffmpeg -f null`（r3_build 内） | 已有 |
| 音频存在/时长 | ffprobe | 已有 |
| 字幕存在 | manifest / ffprobe | 已有 |
| 字幕与音频时间轴一致 | timeline.json 与 SRT 同源；无独立校验 | 部分 |
| 黑帧/空白 | `r2_analyze_frames.py` 可算，未接入构建 | 未接入 |
| 最终时长是否符合预期 | 只有人工 | 未接入 |
| 首尾帧/漂色 | 人工（R2 报告） | 未接入 |
| 内容质量 | 人工 | 不可自动 |

---

## 11. 内容与版权

| 项 | 证据 | 状态 |
|---|---|---|
| 《洛神赋》原文 | Wikisource oldid 7908816，原文/规范化 SHA-256 已登记；公有领域 | `PARTIAL`（转录 CC BY-SA 义务待复核） |
| 《春江花月夜》原文 | 无独立 source registry（只在 `narration.json` 中） | 缺失 |
| 字体 | 思源宋体/黑体，OFL 1.1，SHA-256 清单 | `PASS_VERIFIED`（许可文件在库） |
| 模型 | FLUX.2 klein / Wan2.2 / Qwen3 | 见 `ASSET_AND_LICENSE_REGISTRY.md` |
| 音色 | CosyVoice SFT 预设「中文男」已用于成片；「中文女」未验收 | `PARTIAL` |
| BGM/音效 | 未引入 | `NOT_RUN` |

**规则缺口**：没有机制阻止把 `UNVERIFIED` 内容展示成 `VERIFIED`；UI 必须原样传递状态字段。

---

## 12. 技术债清单

| ID | 问题 | 严重度 | 影响 |
|---|---|---|---|
| TD-01 | 无统一任务/状态层（无 `state.db`、无任务注册表） | 高 | 前端无法得到可信任务状态；无法断点续跑 |
| TD-02 | `r3_tts.py` 端口/输入/输出硬编码到 `experiments/r3b` | 高 | 无法为第二期生产配音 |
| TD-03 | 缺 `ContentPackage → segments.json / audio_manifest.json` Adapter | 高 | LI 输出无法进入成片 |
| TD-04 | 无项目/期数实体；`projects/` 为空 | 高 | 工作台没有可管理的对象 |
| TD-05 | 字体与 R3-D 证据被 gitignore（当时 manifest 也被忽略） | 高 | 已由 P0-2 `fetch_fonts.py` + manifest 跟踪修复 |
| TD-06 | 历史成片 manifest 与当前脚本版本不一致 | 中 | 无法证明产物来源 |
| TD-07 | 无并发/任务锁 | 高 | 违反 GPU 单租户 |
| TD-08 | `models.Storyboard` 等契约无生产消费方 | 中 | 文档承诺的边界是空的 |
| TD-09 | `pipeline.py` 与 `run_li15.py` 重复实现五轮流程 | 中 | 行为漂移 |
| TD-10 | 服务地址在三处重复 | 中 | 改端口需改代码 |
| TD-11 | 默认 `pytest` 不跑 LI 测试 | 低 | 漏测 |
| TD-12 | 质量检查未接入构建 | 中 | 黑帧/时长异常无法自动拦截 |
| TD-13 | 无版本化输出（覆盖式重跑） | 高 | 重新生成会静默覆盖 |
| TD-14 | doctor 不检查字体/CosyVoice/experiments 完整性 | 低 | 诊断不完整 |
| TD-15 | ADR-012 与“建工作台”冲突 | 低 | 决策记录需更新 |

---

## 13. 关键风险

1. **把“页面能打开”当成“生产可用”**：本项目最危险的不是缺功能，而是假状态。所有数字必须来自真实文件或任务记录。
2. **前端绕过生命周期规范**：若前端直接 spawn llama-server / ComfyUI，会破坏 8080 单端口与 GPU 单租户约束。
3. **覆盖历史资产**：工作台必须默认只读；任何写操作需显式确认，且不覆盖已验证产物。
4. **文件系统暴露**：静态文件服务必须做根目录约束，禁止 `..` 穿越。
5. **长任务阻塞页面**：必须异步执行 + 轮询 + 可恢复，而不是同步请求。
6. **证据不可复现**：gitignore 的字体/R3-D/LI runs 使“已验证”只存在于本机。

---

## 14. 前端需要调用的后端能力（能力清单）

> 设计原则：**读路径全部从真实文件派生**；**写路径只有受限任务注册表**；不复制业务规则到前端。

### 14.1 读取能力

| 能力 | 数据来源（真实） | 说明 |
|---|---|---|
| 项目列表 | `projects/workspace.db`（用户创建）+ 内置发现 | 首批项目由真实产物导入 |
| 期数列表 | `workspace.db` + 产物目录绑定 | 进度由必需步骤完成度计算 |
| 期数详情 | `segments.json` / `audio_manifest.json` / `build_manifest.json` / 目录扫描 | 缺失即 `NOT_RUN` |
| 内容（原文/分析/旁白） | `corpus/luoshen_fu/*`、`narration.json`、`runs/*` | 原样呈现状态字段 |
| 分镜 | `segments.json` + `assets/vertical/index.json` | 当前无 storyboard JSON，按真实分段展示 |
| 视觉风格 | `assets/visual_style/style_bible.json` + `workspace.db` styles | 可扩展，不写死 |
| 素材 | 目录扫描 + `index.json` 哈希 | 大小/时间/来源/引用状态 |
| 成片 | `build_manifest.json` + ffprobe（缓存） | 分辨率/时长/码率/字幕流 |
| 任务 | `workspace.db` tasks + 运行日志文件 | 六态，含 BLOCKED |
| 环境 | doctor 检查（按需）+ 端口探测 | 不可探测即 `UNKNOWN` |
| 日志 | `logs/` 白名单 + 任务日志 | 只读、限长 |

### 14.2 执行能力（受限注册表）

| 任务 | 入口 | 成本 | 前置 | 安全约束 |
|---|---|---|---|---|
| `doctor.run` | `drama doctor --json --no-report` | 秒级 | 无 | 只读 |
| `build.rebuild` | `scripts/r3_build.py --segments ... --audio ... --out <新目录>` | ~2 分钟 FFmpeg | 分段+音频存在 | **禁止**写入已有 renders 目录 |
| `tts.synthesize` | `scripts/r3_tts.py`（需先参数化，Phase D） | 分钟级 | CosyVoice 50000 | 需服务健康检查 |
| `li.run` | `literary_intelligence/run_li15.py` | 分钟级 | 8080 可用 | 复用其自管理服务逻辑 |
| `comfy.batch` | `scripts/r1_batch.py --jobs ...` | 小时级 | ComfyUI 8188 | 单飞锁；禁止并发 |
| `service.start/stop` | `scripts/start.ps1`、`stop.ps1`、`llm_server.ps1` | 秒-分钟 | — | 显式确认；LLM 用完即停 |

**不做**：任意 shell、任意路径、任意参数透传、前端直连文件系统。

---

## 15. 建议改造顺序

1. **Phase B**：数据模型与 API 契约（本文 §14 落地为具体 schema）。
2. **Phase C**：只读骨架（Dashboard/Projects/Episodes/Workspace/Workflow/Tasks/Assets/Styles），所有数字来自真实文件。
3. **Phase D**：
   - D1 任务注册表 + 单飞锁 + 日志落盘（`workspace.db`）。
   - D2 真实只读数据源接入（R3-B、洛神赋 corpus、LI runs）。
   - D3 受限执行（先 `doctor.run` 与 `build.rebuild`）。
   - D4 参数化 `r3_tts.py`（只加参数，不改行为），使第二期可用。
4. **Phase E**：以《洛神赋》真实数据验证读取；用 `build.rebuild` 做一次**新目录**真实构建，验证任务状态与输出回写。
5. **Phase F**：完整性审计（死链、假数据、错误处理、刷新恢复）。
6. 之后（不在本次范围）：ContentPackage Adapter、版本化、GPU 状态、BGM/SFX。

---

## 16. 审计结论

- 项目**不是**“有状态机、可断点续跑的流水线”；它是**五个可独立执行的脚本 + 一套严格的数据契约 + 一份真实的 38 秒成片**。
- 真实可用的能力集中在：环境诊断、FLUX/Wan 生成、中文男 TTS、FFmpeg 合成、字体校验、LI 证据链（未审核）。
- 最大的结构性缺口是：**没有项目/期数实体，没有任务层，没有内容包到成片的 Adapter**。
- 工作台第一阶段必须建立在“只读派生 + 受限执行”上；任何无法从文件得到的状态一律显示 `NOT_RUN` / `UNKNOWN`，不得估算。

---

## 17. 本轮审计执行记录

| 动作 | 结果 |
|---|---|
| `git rev-parse HEAD` | `e21dc0d3ea577b170056fff7c6a4afc230c159a5` |
| `pytest tests` | 14 passed |
| `pytest literary_intelligence/tests` | 61 passed |
| 资产哈希核验 | vertical 6/6、audio 7/7、segments 6/6、final 1/1 一致 |
| ffprobe 成片 | 38.042 s / 1080×1920 / 24 fps / aac 48 kHz mono / mov_text |
| 代码修改 | 无 |
| 服务启动 | 无 |
| Git 提交/推送 | 无 |
