# Local-Drama-Studio 产品总览

> 文档状态：Phase B 产品文档（2026-11-04）
> 适用版本：v1.0 基线 + 当前工作区（HEAD `06f91e4` + M8/声景/zero-shot 未提交工作）
> 读者：产品、内容制作、工程接手者
> 原则：**产品设计、已验证能力、代码现状三者分开写**。规划不是已实现；单次成功不是稳定产能。

---

## 1. 产品是什么

Local-Drama-Studio 是一套**本地运行的东方视觉短视频生产工具**，面向抖音和小红书：

```text
诗词/古典文本 → 内容包 → 文案/分镜 → 静态画面 → 镜头运动 → 配音 → 字幕 → MP4 → 质量检查
```

它不是“装一个 ComfyUI 然后生成几段视频”，而是：

- 用 Python 管理生产流程、数据契约、任务与质量门；
- 用 ComfyUI 做静态图/视频生成引擎；
- 用 CosyVoice 做本地 TTS；
- 用 llama.cpp + Qwen3 做文本结构化；
- 用 FFmpeg 做确定性合成；
- 用 SQLite 保存项目/期数/风格/任务；
- 用真实文件与哈希派生生产状态，不用 UI 猜。

---

## 2. 当前能做什么（有真实产物）

| 案例 | 规格 | 实现路径 | 证据 |
|---|---|---|---|
| P1 端到端 | 14.0 s / 1080×1920 / 4 静帧 / 4 句女声 | ContentPackage → LLM → TTS → FLUX → segments → build | `projects/proj_p1_short/episodes/ep_p1_short/renders/build-20261103-114226/` |
| R3 单篇 | 38.042 s / 1080×1920 / 5 静帧 + 1 Wan / 7 句 | `r3_build.py` 直接合成 | `projects/proj_chunjiang/episodes/ep_chunjiang_01/renders/build-20261103-074757/` |
| **完整工笔《春江花月夜》** | **81.373 s / 1080×1920 / 13 段 / 18 句** | **`scroll_shot.py` + 预渲染 clips** | `projects/proj_chunjiang_gongbi/episodes/ep_chunjiang_gongbi_01/renders/build-20261103-161945/`；`quality_report` + `verification_report` 双 PASS；SHA-256 `84628a06…` |
| M7 水墨 | 10.087 s / 1080×1920 / 2 镜头 | `motion.plan → motion.render` | `experiments/m7_final/ink/renders/` |
| M7 工笔 | 9.583 s / 1080×1920 / 2 镜头 | `motion.plan → motion.render` | `experiments/m7_final/court/renders/` |

**路径区别必须保留：**

- P1：自动内容包 + LLM 分镜 + 参数化 TTS + FLUX + segments。
- R3：人工编排的静帧/Wan + 逐句 TTS + `r3_build`。
- 81.373 s 工笔：**长卷预渲染 clips**（`scroll_shot.py`），不是 `motion.plan` 自动运动管线；也不是“全自动短剧”。
- M7：`motion.plan` 确定性相机/局部微动/转场，两风格各 2 镜头。

---

## 3. 能力地图

状态口径见 [QUALITY_AND_METRICS.md](QUALITY_AND_METRICS.md)。`PASS_VERIFIED` 只在有真实产物与证据时使用。

| 能力域 | 当前状态 | 说明 |
|---|---|---|
| 双 venv 环境 / ComfyUI XPU / 模型校验 | `PASS_VERIFIED` | `doctor` 15 PASS / 0 FAIL（服务未启动时 3 NOT_RUN） |
| 配置加载 / 严格 Schema | `PASS_VERIFIED` | settings/models/generation/audio/styles/fonts/pronunciation |
| ContentPackage（语料 + 证据 claim） | `PASS_VERIFIED`（4 句短夹具） | 长篇未跑；claim 均未人工 approved |
| LLM 文案/分镜 | `PASS_VERIFIED`（CLI 真实 4 镜头） | 工作台“新生成”路径在修复后未重新实证 |
| FLUX 静态图 | `PASS_VERIFIED`（历史） | 576×1024，4 步，CFG 1.0；当前 8188 未启动 |
| Wan 视频 | `PASS_VERIFIED`（推近类） / `PASS_LIMITED`（精确位移） | 73 帧默认；20 步强制；主体位移不可靠 |
| 参考图 / 关键帧 | `PASS_VERIFIED` | J2 参考 + `ReferenceLatent`；不是人物一致性 |
| CosyVoice SFT 配音 | `PASS_VERIFIED`（历史） | 中文女 P1 4 行、gongbi 18 行、M7 4 行 |
| CosyVoice zero-shot | `PASS_STATIC`（2 行 E2E） | 必须显式选择，使用 CosyVoice2-0.5B；**不是默认** |
| 发音词典 / 诵读模式 | `PASS_STATIC` / `PARTIAL` | 5 条 verified 同音别名；chant 明确拒绝；人工复核 PENDING |
| 字幕 SRT/ASS + 本地字体 | `PASS_VERIFIED` | 1080×1920 PlayRes；fontselect 强校验 |
| FFmpeg 合成 | `PASS_VERIFIED` | 1080×1920 / 24 fps / H.264 + AAC + mov_text |
| 技术质量门 | `PASS_VERIFIED` | 图片空黑、视频解码/尺寸、音频峰值/静音、成片哈希 |
| 运动质量门 | `PARTIAL` | 刚体保护/时序连续性有代码与测试；人工审美 PENDING |
| 静态质量门 | `IMPLEMENTED_NOT_VERIFIED` | `static.check` 任务；`motion.plan` 默认要求报告，显式 `--skip-static-gate` 才跳过 |
| 双视觉风格规范/配置 | `PASS_STATIC` | 青绿工笔 / 写意水墨，两套独立配置 |
| 每种风格技术样片 | `PASS_VERIFIED`（各 2 镜头） | M7 两片；不代表完整作品一致性 |
| 作品级风格锁定 | `IMPLEMENTED_NOT_VERIFIED` | 期数 `_style_lock` revision/hash/history；任务拒绝不同 style；DB `preset_id` 映射 YAML；真实改版生产待跑 |
| 跨镜头风格一致性验证 | `PASS_VERIFIED` | P1 4 镜头修正后技术 OK（ΔE 9.22、luma 7.13）；人工通过；最终 build 接入待做 |
| 镜头美学 A/B | `PARTIAL` + `PENDING_HUMAN_REVIEW` | 8 张实图、联系表、风险指标 |
| 2.5D 分层 | `PASS_STATIC`（opt-in） | `PlateSpec` + 渲染路径 + 真实渲染 PASS；未成为默认 |
| 工作台（项目/期数/风格/任务/媒体） | `PASS_VERIFIED` | 39 个真实任务；API/媒体测试通过 |
| LI 五轮真实 LLM | `PARTIAL` | 3 次 5/5；人工审核 NOT_RUN |
| 两分钟全 Wan 场景片 | `PASS_VERIFIED`（技术） | 24/24 Wan、121.3 s / 1080×1920；`experiments/shinkai_scene/renders_24/final_9x16.mp4`；quality PASS |
| 两分钟水墨片（`ACCEPTANCE-2MIN-001`） | `IN_PROGRESS` | 24 镜全 Wan / 120 s；`scripts/run_ink_film.py` 已启动并排在 Shinkai 批次之后；对标与验收见 [REFERENCE_FILMS.md](REFERENCE_FILMS.md) |
| BGM / 音效 | `PASS_VERIFIED`（BGM 技术）/ `IMPLEMENTED_NOT_VERIFIED`（SFX） | 13 条 BGM 已登记；Keynata 5 条与旧 drone 已拒绝；Commons 公有领域/CC BY 古典与木吉他 6 条经用户试听「好很多」，重混 30 s/2 min quality PASS；SFX 无外部授权素材 |
| 商用授权 | `PARTIAL` | 字体/模型/自录声音有登记；预置音色/生成音频商用 UNVERIFIED |
| 批处理 / 断点续跑 | `NOT_RUN` / 部分 | `r1_batch` 有 job 级续跑；无阶段级 orchestrator |
| 平台发布 / 数据 | `NOT_IMPLEMENTED` | 只有规范文档 |

---

## 4. 两种正式视觉风格

产品有**两个正式创作方向**，不是同一篇作品里的两种混用风格：

| 风格 id | 名称 | 核心语言 | 适用内容 |
|---|---|---|---|
| `court_green_fine_line` | 宋代院体青绿工笔 | 绢本设色、石青石绿、游丝描/铁线描、长卷横移 | 山水、建筑、花鸟、空镜、长卷 |
| `ink_wash` | 东方写意水墨 | 生宣纸本、墨分五色、留白、渗染、局部微动 | 山水、云雾、水面、花鸟、空镜 |

### 4.1 产品规则

1. 每个作品必须选择一个**主视觉风格**。
2. 一个作品从第一帧到最后一帧保持该风格。
3. 不允许在同一作品中随意切换工笔和水墨。
4. 不同作品可以分别使用不同风格。
5. 同一风格内部允许景别、构图、色彩、光影、镜头运动变化，但不能破坏整体风格一致性。
6. 两种风格共享 FLUX、Wan、FFmpeg 等基础设施，但拥有独立的视觉规范、提示词策略、生成参数和质量评价标准。

### 4.2 作品级风格约束

- 视觉风格是**作品级配置**；期数、`ProductionScript`、镜头、视觉资产继承作品的 `style_id`。
- 生成任务不得自行覆盖或切换作品风格。
- 如需更改作品风格，应创建新的风格版本或新的生产版本，并明确记录。
- 质量检查需要能够检查风格一致性。

### 4.3 当前实现与目标的差距

| 目标 | 当前实现 | 差距 |
|---|---|---|
| 期数绑定风格 | `episodes.style_id` + 冻结 `style_snapshot` | 成立 |
| `ProductionScript` 记录风格 | `style_id` + `style_sha256` | 成立（提示词层） |
| 镜头/资产继承 | 镜头只有 `visual_prompt`，没有 `style_id` 字段 | 不完整 |
| 生成任务不得覆盖 | `motion.plan` / `aesthetic.plan` 可 `--style` 覆盖；`comfy.batch` 不校验 | **未强制** |
| 改风格留版本 | UI 直接替换期数 snapshot；无版本表 | **未实现** |
| 跨镜头风格一致性门 | P1 修正后技术 OK + 人工通过 | **PASS_VERIFIED** |
| DB 风格与 YAML preset 一致 | `workspace.styles` 不含 motion/aesthetic profile | **脱节** |

> 这是 Phase C 的重点修复方向，不在 Phase B 修改代码。详细差异见 [audit/IMPLEMENTATION_STATUS.md](audit/IMPLEMENTATION_STATUS.md) §2.23。

---

## 5. TTS 产品策略

### 5.1 目标（2026-11-04 PRD）

| 项 | 决策 |
|---|---|
| 默认模式 | **CosyVoice2-0.5B zero-shot** |
| 默认音色 | zero-shot 参考音（`config/audio.yaml` 的 `prompt_audio`） |
| 300M SFT | **仅显式可选**，不得作为默认 |
| 禁止回退 | 0.5B 不可用/加载失败/参考音缺失 → 明确失败，不得静默回退 300M |
| 可识别性 | UI、CLI、任务记录、配置、日志、`audio_manifest.json`、报告记录实际 mode/model/voice |

### 5.2 当前实现（2026-11-04，PRD 治理时）

- **已实现**：`tts_mode` 显式选择（CLI `--tts-mode`、任务 `tts_mode`、narration 可选）；`/health` 校验 `CosyVoice2-0.5B` 与 `CosyVoice-300M-SFT`；SFT↔zero-shot 错配双向拒绝；manifest 记录 `tts_mode/model_class/model_dir/speaker/speaker_id/runtime/prompt`。
- **已真实验证**：显式 zero-shot（0.5B）1 行 PASS；显式 SFT（300M）1 行 PASS；历史 P1/81.373 为 SFT。
- **PRD-TTS-001 已满足**：`config/audio.yaml` 默认 `tts.mode: zero_shot`，默认任务真实加载 0.5B；状态 `PASS_VERIFIED`。SFT 仅显式可选。
- **多音色（提案 `PRD-TTS-007`）**：`config/voices.yaml` + 逐行 `voice_profile` 或 `voice_cast.yaml` sidecar；一次运行只允许一种后端；未 `APPROVED` 档案默认拒绝。
- **多轨音频（正式 `PRD-AUDIO-*`）**：`audio_timeline.json` + `assets/audio/manifest.json`；BGM ducking/SFX 由 FFmpeg 混音；旧旁白路径保持兼容。
- **故事圣经（提案 `PRD-STORY-*`）**：`character_bible.yaml` / `shot_bible.yaml` + `story.check`；只校验引用/覆盖/风格，不承诺同脸。
- `zero_shot` 参考音/参考文本缺一不可；`prompt_text` 必须与参考音逐字一致。
- 同一端口 50000，两个运行时互斥；启动 `-Model cosyvoice2` 或 `-Model sft`。

---

## 6. 产品不是什么

- 不是公网服务、多用户系统、自动发布工具。
- 不是电影级人物一致性/口型同步系统。
- 不是“一键全自动短剧”：镜头级状态机、断点续跑、批处理调度未实现。
- 不是“所有历史报告都能按路径复跑”：R1–R3/S2 的原始 run 目录已缺失，报告仍保留。
- 不是“所有配置字段都生效”：存在死配置（见配置手册）。

---

## 7. 文档怎么读

| 你想做什么 | 先读 |
|---|---|
| 了解产品边界与现状 | 本文件 |
| 从零产出一篇视频 | [USER_GUIDE.md](USER_GUIDE.md) |
| 理解每个阶段输入/输出/失败恢复 | [PRODUCTION_PIPELINE_GUIDE.md](PRODUCTION_PIPELINE_GUIDE.md) |
| 调 FLUX/Wan/TTS/FFmpeg 参数 | [PRODUCTION_CONFIG_GUIDE.md](PRODUCTION_CONFIG_GUIDE.md) |
| 扩展代码/新风格/新工作流 | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| 排障 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| 下一步优先级 | [PROJECT_NEXT_STEPS.md](PROJECT_NEXT_STEPS.md) |
| 审计证据与差距 | [audit/](audit/) |

---

## 8. 状态词典（摘要）

| 状态 | 含义 |
|---|---|
| `PASS_VERIFIED` | 有真实运行产物/日志/哈希，验证通过 |
| `PASS_STATIC` | 规范/配置/静态检查通过；未做完整动态或人工验收 |
| `PASS_LIMITED` | 已执行但有明确限制 |
| `PARTIAL` | 部分实现或部分验证 |
| `NOT_RUN` | 有入口/计划，但本次未执行 |
| `NOT_IMPLEMENTED` | 没有实现 |
| `BLOCKED` | 依赖/环境阻塞 |
| `UNKNOWN` | 证据不足，不能判断 |

**禁止**把 `NOT_RUN` 写成 `PASS_VERIFIED`；**禁止**把文档规划写成已实现功能。
