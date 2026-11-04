# 04 · PRODUCTION_WORKFLOW — 从选题到成片

> 文档状态：v1.0 流程 `DECISION`；当前实现是“单篇可跑通”，不是“全自动批处理”。
> 每个步骤标注实际状态，避免把规划写成已实现。

## 1. 目标流程（14 步）

| # | 步骤 | 目标 | 当前实现 | 状态 |
|---|---|---|---|---|
| 1 | 主题/文本整理 | 选篇、核对原文、出处 | 人工 | `PARTIAL` |
| 2 | 内容策划 | 角度、结构、时长、情绪 | 人工 | `PARTIAL` |
| 2b | 内容包 | 已登记语料 + 有效 claim | `package.build` → ContentPackage(draft) | `PASS_VERIFIED`（P1 短文本 4 场景） |
| 3 | 分镜设计 | 镜头表、主体/相机/背景/结束状态 | `script.generate` + `ProductionScript`；真实 30B | `PASS_VERIFIED`（4 镜头） |
| 4 | 视觉风格 | 色板、参考图、提示词后缀 | R1 视觉规范 + 参考图 | `PASS_VERIFIED` |
| 5 | 镜头美学设计 | 六维规格 + A/B 候选 + Prompt 编译 + 冻结 | `aesthetic.plan` → snapshot + jobs | `PARTIAL`（4 组实图；人工 PENDING） |
| 5b | 静帧生成 | 4-6 张竖屏关键帧 | FLUX + `comfy.batch`（按 snapshot jobs） | `PARTIAL`（A/B 8 张实图） |
| 6 | 动态镜头 | 镜头运动 + 局部微动 + 转场；Wan 只作局部补充 | `motion.plan` → `motion.render`（FFmpeg 确定性合成）；Wan I2V 可选 | `PARTIAL`（两风格技术链走通；人工看片 PENDING） |
| 7 | 旁白/朗诵 | 逐句 TTS；标准朗诵/古典吟诵；发音核验 | CosyVoice + `tts.synthesize`（模式/分句/停顿）；`pronunciation_report.json` + `scripts/tts_qa.py` | `PARTIAL`（波形/ASR 通过；发音人工复核 PENDING） |
| 8 | 音乐/音效 | BGM、环境声 | 未实现 | `NOT_RUN` / 待选型（R3-D） |
| 9 | 字幕 | SRT/ASS、时间轴、本地字体 | `r3_build.py` + `config/fonts.yaml` | `PASS_VERIFIED`（P1 4 行） |
| 10 | 合成 | 1080×1920、混音、字幕 | FFmpeg | `PASS_VERIFIED`（P1 14 s + R3 38 s） |
| 11 | 质量检查 | 技术 + 音频 + 美学风险 + 内容 + 成本 | `quality.check` / `static_quality --aesthetic` / `quality --aesthetic-motion` / `tts_qa.py` + 人工 | 技术 `PASS_VERIFIED`；美学/音频 `PARTIAL`；人工 H3 `NOT_RUN` |
| 12 | 平台适配 | 封面、标题、正文、话题 | 未实现 | `NOT_RUN` |
| 13 | 人工审核/发布 | 人看片、手动发布 | 人工 | `PARTIAL` |
| 14 | 数据记录 | 播放/完播/互动/涨粉 | 未实现 | `NOT_RUN` |

> **R3-D 前置**：字体候选已完成来源、许可、覆盖和预览验证，字幕已接入正式构建，排版仍待人工审查；女声已本地合成/试听并固化韵律方案，但未进入正式成片；BGM、音效与商用授权未完成。必须在下一篇完整样片之前完成。R3 的「中文男」只验证了技术链路，不是最终声音方案。
>
> **S3-B.2 字体**：`scripts/r3_build.py` 已通过 `config/fonts.yaml` + `src/drama_studio/fonts.py` 使用 `Source Han Sans CN` 字幕，正式构建会校验 OTF SHA-256 并用 `fontselect` 日志拒绝静默 fallback。标题/诗词/现代解说角色仍为 `preview_only`；R3-B 历史成片仍使用 Microsoft YaHei，未覆盖。

## 2. 人工控制点

| 控制点 | 时机 | 必须确认 |
|---|---|---|
| H1 人物/首帧锁定 | 人物资产或首帧生成后 | 角色可辨认、服装/场景正确 |
| H2 关键帧审批 | 批量 Wan 之前 | 构图、月亮、空间关系、无现代物件 |
| H3 成片验收 | 合成后 | 节奏、音量、字幕、可看性 |
| H4 平台包装 | 发布前 | 封面、标题、正文、话题、AI 标识 |
| H5 发布与记录 | 发布后 | 链接、时间、初始数据 |

v1.0 的 R3 样片使用了 H2/H3；H1 未使用（无人物），H4/H5 未执行。

## 2.5 动态与声音接入（2026-11-04）

```text
production --motion-plan  (align_audio + style policy + motion_regions.json)
  → work/motion_shots.json
scripts/motion_build.py
  → work/motion/build-<time>/shot_XXX.mp4 + sequence/sequence.mp4
production --sequence → work/segments.json (single video segment)
scripts/r3_build.py → final_9x16.mp4 + 字幕/混音
drama_studio.quality --audio-manifest（工作台 `audio.qa`）→ audio_qa_report.json
scripts/tts_qa.py (CosyVoice venv) → tts_qa.json
```

关键约束：

- 转场只消耗上一镜头尾部 handle，序列总时长 = 镜头时长之和；音频时间轴不变。
- `segments.json` 的 sequence 模式会在序列短于旁白时直接失败，不靠拉长冻结画面。
- 局部微动只能使用 `motion_regions.json` 中人工给出的区域；没有分割模型。
- 发音词典只核验、不改字；`chant` 明确拒绝。

## 2.6 镜头美学设计接入（2026-11-04）

```text
ProductionScript
  → aesthetic.plan
      + config/styles.yaml aesthetic_profile
      + designs.json（人工场景设计）
      → aesthetic_plan.json + snapshot-<time>/{A,B}/jobs_<A|B>.json
  → comfy.batch（A、B 各一次 FLUX）
  → aesthetic.compare
      → comparison.json / comparison.md / contact_sheet.png
      → human_review: PENDING
  → aesthetic.review（人工结论，新增文件）
  → static_quality --aesthetic（设计 vs 成图风险）
  → motion.plan / motion.render
  → quality --aesthetic-motion（稳定性 + 色彩/亮度连续性）
```

规则：

- 美学设计发生在图像生成之前；没有设计规格就不进入 A/B 生成。
- 一份 `snapshot` 只对应一次生成；人工改设计生成新快照，不覆盖旧版。
- A/B 除一个维度外逐字段相同；不是“两套完全不同的提示词”。
- 自动指标只给风险提示；人工看片前保持 `PENDING_HUMAN_REVIEW`。
- FLUX 负向条件被清零且 CFG=1.0，负向提示词不作为控制；以正向约束为主。

## 3. 当前单篇流程（R3 实测）

```text
1. 人工选篇：春江花月夜 7 句
2. 人工定结构：5 静帧 + 1 Wan + 7 句朗诵
3. FLUX 生成 5 张 576×1024 静帧
4. Wan 生成 1 段 576×1024 / 73 帧推近
5. CosyVoice 逐句合成 7 段音频，重采样 48 kHz
6. 计算句首时间，生成 SRT + ASS
7. FFmpeg：Ken Burns + Wan + 混音 + 字幕 + 1080×1920 放大
8. 人工抽帧/看片/音量检查
```

产物：

```text
experiments/r3b/
├─ narration.json
├─ audio/line_01..07.wav
├─ audio_manifest.json
├─ segments.json
└─ renders/
   ├─ drama.srt / drama.ass
   ├─ final_9x16.mp4
   ├─ final_9x16_burned.mp4
   └─ build_manifest.json
```

## 4. 脚本职责

| 脚本 | 职责 | 状态 |
|---|---|---|
| `scripts/doctor.ps1` / `drama doctor` | 环境、服务、模型检查 | `PASS_VERIFIED` |
| `scripts/start.ps1` / `stop.ps1` | ComfyUI 启停 | `PASS_VERIFIED` |
| `scripts/r1_batch.py` | 通用任务批处理、续跑、重试 | `PASS_VERIFIED` |
| `scripts/r2_analyze_frames.py` | 帧序列编码、闪烁/黑帧指标 | `PASS_VERIFIED` |
| `scripts/r2b_track_boat.py` | 主体位移追踪（H3） | `PASS_VERIFIED`（启发式） |
| `scripts/r3_tts.py` | CosyVoice 逐句合成 | `PASS_VERIFIED`（中文男） |
| `scripts/r3_build.py` | 静帧/视频/配音/字幕合成 | `PASS_VERIFIED`（单篇） |
| `src/drama_studio/content_package.py` | 语料 → ContentPackage | `PASS_VERIFIED`（P1） |
| `src/drama_studio/script_engine.py` | LLM → 文案/分镜 | `PASS_VERIFIED`（P1，真实 LLM） |
| `src/drama_studio/production.py` | 分镜 → jobs / segments / motion plan | `PASS_VERIFIED`（P1）；motion plan `PARTIAL` |
| `src/drama_studio/motion/` | 镜头运动、局部微动、转场 | `PARTIAL`（技术执行，人工待审） |
| `scripts/motion_build.py` | 逐镜头动态片段 + 转场序列 | `PARTIAL`（两种风格 2 镜头 E2E） |
| `scripts/transition_probe.py` | 四种转场技术探针 | `PASS`（合成/时长/黑帧） |
| `src/drama_studio/voice/pronunciation.py` | 词组级发音标注与文本分层 | `PASS_STATIC` |
| `src/drama_studio/voice/recitation.py` | 诵读模式、分句与停顿 | `PARTIAL`（真实合成） |
| `scripts/tts_qa.py` | Whisper ASR 辅助复核（CosyVoice venv） | `PARTIAL`（代理，非听觉结论） |
| `src/drama_studio/quality.py` | 独立技术检查 | `PASS_VERIFIED`（P1） |
| `src/drama_studio/voice/tts.py` | 参数化 TTS | `PASS_VERIFIED`（P1） |
| `src/drama_studio/aesthetics.py` | 六维美学设计、A/B、Prompt 编译 | `PARTIAL`（4 组实图） |
| `scripts/aesthetic_plan.py` | 美学计划 + 冻结 snapshot + A/B jobs | `PARTIAL` |
| `scripts/aesthetic_compare.py` | A/B 联系表 + 风险指标 + 人工审核包 | `PARTIAL` |
| `scripts/p1_e2e.py` | P1 端到端验收 | `PASS_VERIFIED`（14 s / 4 段 / quality PASS） |
| `drama serve`（`src/drama_studio/workspace/`） | 本地工作台：状态派生 + 受限任务 | `PASS_VERIFIED`；`comfy.batch`/`tts.synthesize`/`quality.check` 已真实执行 |

## 5. 失败与降级

| 失败 | 处理 |
|---|---|
| ComfyUI 未就绪 | 等待就绪；批处理重试（最多 1+2 次） |
| FLUX 失败/OOM | 降分辨率或重跑；不伪装成功 |
| Wan 失败/OOM | 退回静帧 + Ken Burns；记录降级 |
| TTS 单句失败 | 只重跑该句，不重做全片 |
| 字幕/合成失败 | 保留日志，重建；不删中间产物 |
| 颜色漂移 | 人工首尾帧检查；校色或重摇 |
| 主体位移方向错误 | 不接受为“叙事成功”；改分镜或后期 |

**已知案例**：R2-B H3 船体移动 24.6 px，但方向向右下（靠近镜头），不是向远山；因此 R3 不用该镜头，改用静帧。

## 6. 成本

R3 单篇 38.04 秒：

| 环节 | 时间 |
|---|---|
| FLUX 5 张 | 2.4 min |
| Wan 1 段 | 36.4 min |
| TTS 7 句 | 2.7 min |
| FFmpeg 合成 | ≈2 min |
| 端到端 | **43.8 min** |

人工审核/返工时间未单独计时。多篇批处理未运行。

## 6.5 动态与声音实测（2026-11-04）

| 任务 | 实测 |
|---|---|
| 2 镜头 12 s（含 1 次水墨转场） | 18.8 s CPU |
| 4 镜头 10 s（3 次转场、8 个图层） | 28.5 s CPU |
| 两风格各 2 镜头 E2E | 17.0 s / 12.0 s |
| TTS 12 行 / 26.93 s（recitation, CPU） | 103 s |
| 8 张 576×1024 FLUX（4 步 / CFG 1.0） | 143.2 s；稳态 16.1 s/张；峰值 3.04 GiB |

全部 CPU + FFmpeg/Pillow；未占用 GPU。完整证据见 [`MOTION_VOICE_UPGRADE_REPORT.md`](MOTION_VOICE_UPGRADE_REPORT.md)。

## 7. 夜间批次（提案，`NOT_RUN`）

```text
晚上：读取待生产清单 → 逐篇生成素材 → 失败隔离 → 早上输出待审片单
早上：人工审核 → 平台适配 → 手动发布 → 记录数据
```

要求：

- 每篇独立目录与 manifest。
- 失败不阻塞整批；保留日志与降级版本。
- 不自动发布；不自动填平台数据。
- 批次结束输出：成功/降级/失败清单 + 成本摘要。

理论产能：43.8 min/篇 → 8 小时约 10 篇；计入审核/重试，保守 6-8 篇/夜（未验证）。

## 8. 工程规则

1. 不修改已验证工作流；需要改时保留旧版并重新验收。
2. 不安装新依赖；需要时先说明必要性与许可证。
3. 模型/字体/音乐先登记授权，再进入成片。
4. 所有生成记录 prompt、seed、模型/工作流哈希、耗时、显存。
5. 所有成片记录技术指标、人工结论、平台数据字段。
6. 不把实验脚本直接当正式服务；产品化需要状态机与内容包管理（未实现）。
