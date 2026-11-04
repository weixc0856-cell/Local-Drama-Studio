# PRD 变更记录与文档冲突修正

> 文档状态：PRD 配套变更记录（2026-11-04）
> 唯一需求来源：[PRD.md](PRD.md)
> 适用：所有产品/架构/开发/测试/用户/审计文档
> 规则：本文件记录“PRD 改了什么、为什么改、哪些旧文档被修正”；不创造新需求。

---

## 1. 版本

| 项 | 值 |
|---|---|
| 当前 PRD 版本 | 2026-11-04 SSOT 修订 |
| 上一版 | 2026-11-03 基线重建 |
| 唯一 PRD 文件 | `docs/PRD.md` |
| 需求追踪 | [REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md) |
| 状态口径 | PRD §0.2（六态需求状态 + 历史标签映射） |

仓库检查结果：**只有一个 PRD 文件 `docs/PRD.md`**；未发现第二个并行 PRD。`docs/PROJECT_AUDIT.md` 是历史审计，不是 PRD；`docs/ROADMAP.md` 是历史路线，不是 PRD。

---

## 2. 本次变更（2026-11-04）

### 2.1 治理

| 变更 | 位置 | 说明 |
|---|---|---|
| PRD 明确为唯一 SSOT | PRD §0.1 | 最新 PRD > 其他文档 > 代码现状 > 历史实验；代码不能反向定义需求 |
| 冲突处理顺序 | PRD §0.1 | 冲突必须记录位置、PRD 要求、差距、修改方案、验证 |
| 需求编号体系 | PRD §0.4 | `PRD-<域>-<序号>`；矩阵见 `REQUIREMENT_TRACEABILITY.md` |
| 需求状态六态 | PRD §0.2 | `PASS_VERIFIED` / `IMPLEMENTED_NOT_VERIFIED` / `PARTIAL` / `NOT_IMPLEMENTED` / `BLOCKED` / `OPEN_QUESTION` |
| 历史标签映射 | PRD §0.2 | `PASS_STATIC`→`IMPLEMENTED_NOT_VERIFIED`；`NOT_RUN`→`NOT_IMPLEMENTED`；`DEPRECATED` 仅历史 |
| 需求追踪 | PRD §23 | 矩阵与状态汇总入口 |
| 本次治理不改代码 | 本文件 §5 | 只改 PRD/文档；已有工作区代码改动按差距记录 |

### 2.2 TTS 默认决策（覆盖此前决定）

| 项 | 2026-11-04 早先决定（已被取代） | 本版 PRD（最新） |
|---|---|---|
| 默认模式 | SFT | **CosyVoice2-0.5B zero-shot** |
| 默认音色 | 中文女（300M-SFT） | zero-shot 参考音（默认配置的 prompt） |
| 300M SFT | 默认 | **仅显式可选**，不得默认 |
| 静默回退 | 不允许 | **明确禁止**；0.5B 不可用即失败 |
| 记录 | mode/model/voice | `tts_mode/model_class/model_dir/speaker_id/prompt` 全链路 |

PRD 位置：§11.1（需求）、§11.3（状态）、§0.4（编号 `PRD-TTS-001..005`）。

**当前实现差距（必须记录，不得写成已通过）**：

- `config/audio.yaml` 仍 `tts.mode: sft`；默认任务仍加载 300M SFT。
- 显式 zero-shot（`--tts-mode zero_shot` + `-Model cosyvoice2`）已真实跑通 1 行；显式 SFT 也跑通 1 行；双向错配均报错。
- 因此 `PRD-TTS-001` = `PARTIAL`，不是 `PASS_VERIFIED`。默认切换是下一项代码任务。
- 本次 PRD 治理**没有**把默认配置改成 zero-shot，以遵守“先文档治理、后代码开发”的指令。

### 2.3 双视觉风格

| 变更 | PRD 位置 | 说明 |
|---|---|---|
| 每篇作品只能一个主风格 | §9.2 `PRD-STYLE-001` | 全片不混用 |
| 风格贯穿剧本/镜头/资产/任务/质量 | §9.2 `PRD-STYLE-002` | 作品级 `style_id` |
| 生成任务不得覆盖 | §9.2 `PRD-STYLE-003` | 改风格走新版本 |
| 改风格必须版本化 | §9.2 `PRD-STYLE-004` | 不覆盖历史 |
| 两种风格独立规范 | §9.2 `PRD-STYLE-005` | 不按 style 写代码分支 |
| 分别验证两种风格 | §9.2 `PRD-STYLE-006` | 技术样片不等于完整作品 |
| 跨镜头一致性单独验证 | §9.2 `PRD-STYLE-007` | 不能用两张图代替 |
| S3 拆分状态 | §9.3 | 不再用单一 PARTIAL/NOT_RUN 概括 |

### 2.4 81.373 s 工笔案例

| 变更 | PRD 位置 | 说明 |
|---|---|---|
| 纳入已验证案例 | §21.3 `PRD-CASE-001` | 1080×1920 / 81.373 s / 13 段 / 18 句 / quality+verification PASS |
| 明确实现路径 | §21.3 | `scroll_shot.py` + 预渲染 clips；**不是** `motion.plan` |
| 明确不可外推 | §21.3 | 不能证明 motion.plan 自动运动或跨镜头风格一致性 |

### 2.5 其他需求编号

| 编号 | 需求 | 状态 |
|---|---|---|
| `PRD-QUAL-001` | 静态质量门不可静默绕过 | `PARTIAL` |
| `PRD-QUAL-002` | 技术/美学/人工质量分层 | `PARTIAL` |
| `PRD-UX-001` | 工作台不展示过期能力 | `PARTIAL` |
| `PRD-DATA-001` | 生产数据契约明确、单一 | `PARTIAL` |
| `PRD-CONFIG-001` | 配置字段有效或明确标注未接线 | `PARTIAL` |
| `PRD-OPS-001` | 成本/失败/批次可汇总 | `OPEN_QUESTION`（是否进入 v1.0） |
| `PRD-TTS-006` | 参考音/模型权重商用授权 | `OPEN_QUESTION` |

---

## 3. 旧文档冲突修正

以下旧文档/旧状态与本版 PRD 冲突，已在本轮修正或明确标注：

| 位置 | 旧说法 | PRD 正确要求 | 本轮处理 |
|---|---|---|---|
| `README.md` TTS 行 | 默认 SFT 中文女，Phase C 修复 | 默认 0.5B zero-shot；SFT 显式可选 | 已改为“目标 0.5B；当前代码仍 SFT，PARTIAL” |
| `docs/README.md` TTS 决策 | 默认 SFT | 默认 0.5B zero-shot | 已改为最新决策；指向 PRD/追踪矩阵 |
| `docs/PROJECT_OVERVIEW.md` §5 | 默认 SFT；Phase C 前手动改配置 | 默认 0.5B zero-shot | 已改为目标 0.5B；当前代码 SFT 差距 |
| `docs/PRODUCTION_CONFIG_GUIDE.md` §6 | 默认 SFT；`tts.mode: sft` | 默认 0.5B zero-shot | 已改为目标/当前差距；配置表保留“当前 sft”并标注不符 PRD |
| `docs/USER_GUIDE.md` §0/§2/§4 | 默认 SFT，手动改配置 | 默认 0.5B zero-shot | 已改为目标 0.5B；SFT 显式可选 |
| `docs/TROUBLESHOOTING.md` §6 | 默认 SFT，改配置 | 默认 0.5B；SFT 显式 | 已改为按 manifest `tts_mode` 判断 |
| `docs/DEVELOPER_GUIDE.md` §9.3 | TTS 目标默认 SFT | 默认 0.5B zero-shot | 已改为目标 0.5B；当前代码 SFT 差距 |
| `docs/PROJECT_NEXT_STEPS.md` P0-1 | 已标记完成（SFT 默认） | 默认 0.5B zero-shot | 已重开为 `PARTIAL`，待默认切换 |
| `docs/audit/IMPLEMENTATION_STATUS.md` 行 10/§2.23 | 默认 SFT 已实现 | 默认 0.5B | 已改为 `PARTIAL`；显式模式 `PASS_VERIFIED` |
| `docs/audit/ARCHITECTURE_AUDIT.md` §12.1/A-01 | 默认 SFT 已满足 | 默认 0.5B | 已改为 `PARTIAL`；默认差距明确 |
| `docs/audit/PHASE_A_SUMMARY.md` §4 | 默认 SFT 已实施 | 默认 0.5B | 已改为最新决策 + 差距 |
| `docs/ROADMAP.md` R3-D/S3 | 默认/状态不一致 | PRD 最新状态 | 已修正 S3 拆分与 R3-D 默认表述（0.5B zero-shot；SFT 显式） |
| `docs/TECH_STACK.md` / `CONTENT_SPEC.md` / `ASSET_AND_LICENSE_REGISTRY.md` | 女声/SFT 历史状态 | 历史证据保留，默认以 PRD 为准 | 已保留历史证据，默认策略引用 PRD |
| `config/audio.yaml` | `tts.mode: sft` | 默认 zero_shot | **未改**；按“先文档治理”指令保留为代码差距 |
| `src/drama_studio/voice/tts.py` | 从配置默认读取；当前 sft | 默认 zero_shot | **未改默认**；显式模式/校验/记录已实现 |

> 历史实验报告（`docs/R*_TEST_REPORT.md`、`docs/M*_REPORT.md`、`docs/S2_TEST_REPORT.md` 等）不删除、不重写实验结论；只在其状态被引用时按 PRD 重新解释。

---

## 4. 需要项目所有者确认

1. 本 PRD 版本与需求编号是否批准为唯一基线。
2. `PRD-TTS-001` 默认 0.5B：是否按下一项代码任务执行（切换默认、更新测试/UI/文档、真实端到端复验）。
3. `PRD-TTS-006` 商用授权是否作为发布前硬门（建议：是）。
4. `PRD-OPS-001` 成本/批次指标是否进入 v1.0，还是 P2。

在确认前，不进入大规模代码开发；不把 `PRD-TTS-001` 写成 `PASS_VERIFIED`。

---

## 5. 本轮实际写入

```text
docs/PRD.md                      # SSOT 修订、需求编号、TTS/风格/案例/状态
docs/PRD_CHANGELOG.md            # 本文件
docs/REQUIREMENT_TRACEABILITY.md # 需求矩阵 + Phase A 映射
docs/README.md                   # PRD 唯一入口 + 索引
README.md                        # 当前状态与 PRD 链接
docs/PROJECT_OVERVIEW.md         # TTS 目标/差距
docs/PRODUCTION_CONFIG_GUIDE.md  # TTS 目标/差距
docs/USER_GUIDE.md               # TTS 操作
docs/TROUBLESHOOTING.md          # TTS 排障
docs/DEVELOPER_GUIDE.md          # TTS 设计/差距
docs/PROJECT_NEXT_STEPS.md       # P0-1 重开
docs/audit/*.md                  # 状态修正
docs/ROADMAP.md                  # 状态对齐
docs/TECH_STACK.md / CONTENT_SPEC.md / ASSET_AND_LICENSE_REGISTRY.md / PRODUCTION_WORKFLOW.md / VISUAL_STYLE_SPEC.md
```

**未修改**：`src/`、`scripts/`、`config/`、`workflows/`、`tests/`、`projects/`、`experiments/`、`assets/`、`logs/`。工作区中已有的 P0-1 TTS 代码改动是上一轮留下的，不是本轮 PRD 治理新增；其默认 SFT 与新 PRD 冲突，已在追踪矩阵标 `PARTIAL`。

---

## 6. 下一步

1. 审阅并批准本 PRD/追踪矩阵。
2. 批准后执行 `PRD-TTS-001`：默认切换 0.5B zero-shot，更新配置/UI/测试/文档，做真实端到端复验。
3. 再做 `PRD-STYLE-003/004`（任务不得覆盖、改风格版本化）与 `PRD-QUAL-001`（静态门不可绕过）。
4. 不进入 M3《洛神赋》完整样片或批量生产，直到 P0 需求满足。

---

## 7. 后续执行更新（2026-11-04，实现批次）

> 本节记录 PRD 治理之后的真实执行结果；不改变正式 PRD 的需求正文。

| 项 | 结果 | 证据 |
|---|---|---|
| `PRD-TTS-001` 默认 0.5B zero-shot | **`PASS_VERIFIED`** | `config/audio.yaml tts.mode: zero_shot`；`experiments/tts_mode_check/default_zero_shot/audio_manifest.json`；`experiments/voice_profile_check/audio_manifest.json` |
| `PRD-TTS-002` SFT 显式可选 | `PASS_VERIFIED` | 显式 `tts_mode=sft` + `-Model sft` 历史真实运行 |
| `PRD-TTS-003` 禁止静默回退 | `PASS_VERIFIED` | `_validate_runtime` 双向错配报错；单测 + 真实错配 |
| Voice Profile 多音色（提案 `PRD-TTS-007`） | `IMPLEMENTED_NOT_VERIFIED` | `config/voices.yaml`、`voice/profiles.py`、逐行 `voice_profile`、`voice_cast`；10 个单测 + 2 行真实 zero-shot |
| 多轨音频（提案 `PRD-AUDIO-001..006`） | `PARTIAL` | `voice/audio_timeline.py`、`audio_assets.py`、`mix.py`、`quality.check_audio_timeline`；合成音频测试 PASS |
| 风格锁定（`PRD-STYLE-003/004`） | `IMPLEMENTED_NOT_VERIFIED` | `style_lock.py`；episode snapshot `_style_lock{revision,sha256,history}`；`preset_id` 映射 YAML；任务拒绝不同 style；期数详情可创建新 revision；8 个单测 + API 测试 |
| 工作流页节点（`PRD-UX-001`） | `IMPLEMENTED_NOT_VERIFIED` | `discovery._workflow` 增加 package/static/aesthetic/motion；script/voice 指向真实任务；删除过期文案；API 测试 |
| 跨镜头风格一致性（`PRD-STYLE-007`） | `PASS_VERIFIED` | `style_consistency.py` + `style.consistency`；P1 4 镜头修正后技术 OK（ΔE 9.22 / luma 7.13）；项目所有者 2026-11-04 明确通过；最终 build 接入待做 |
| BGM 资产与多轨混音（`PRD-AUDIO-004/005`） | `PASS_VERIFIED` | 2 条自生成 BGM 登记 `assets/audio/manifest.json`；P1 14.0 s 真实 build + BGM timeline；quality PASS；`experiments/bgm_mix_check/renders3/build_manifest.json` |
| Common Voice 27.0 筛选 | `TECHNICALLY_VALIDATED`（2 primary）/ `PENDING_REVIEW`（2 alternate） | 本机档案筛选 4 条；原始 16 kHz mono；2 条 zero-shot 技术 PASS；未镜像、未反推身份、未批准生产 |
| 视频镜头契约（`PRD-MOTION-004`） | `IMPLEMENTED_NOT_VERIFIED` | `ScriptShot.type=video` + `video_prompt`；`build_video_jobs` 生成 Wan I2V jobs；`build_segments --clips --allow-partial-clips` 混合片段/静帧；2 项生产测试 + 1 项脚本测试 |
| 自生成 SFX 资产 | `IMPLEMENTED_NOT_VERIFIED` | `sfx_wind/water/chime/whoosh` 已登记 manifest；参考研究 timelines 已接入；人工听感 PENDING |
| 全量测试 | 376 passed | 2026-11-04 `pytest` |

**修正历史记录**：本文件 §3 中“`config/audio.yaml` 未改默认”“`tts.py` 未改默认”的表述是治理轮的历史状态；后续实现批次已改为 `zero_shot`，并完成真实 2 行验证。正式 PRD 仍未写入 AUDIO/VOICE-ASSET/MOTION/STORY/QA 提案需求，相关实现只能标 `IMPLEMENTED_NOT_VERIFIED` / `PARTIAL`。


---

## 8. PRD 变更提案（待批准）

`docs/proposals/PRD_AMENDMENT_2026-11-04.md` 把 AUDIO、`PRD-TTS-007`、VOICE-ASSET、MOTION、STORY、QA 合并为一个待批准变更包，并规定唯一资产台账、唯一多轨时间线、唯一音色档案、唯一故事圣经 sidecar，避免重复建设。该文件**不是**正式 PRD；批准前不得把其中需求标为 `PASS_VERIFIED`。

---

## 9. 2026-11-04 变更提案批准并合并

项目所有者于 2026-11-04 批准 `docs/proposals/PRD_AMENDMENT_2026-11-04.md` 全部检查项：

- `PRD-TTS-007`、`PRD-AUDIO-001..006`、`PRD-VOICE-ASSET-001..012`、`PRD-MOTION-001..004`、`PRD-STORY-001..002`、`PRD-QA-001..002` 已并入 `docs/PRD.md` §24。
- 单一音频资产台账、单次运行后端互斥、仅 `APPROVED` 声音进生产、同脸仅人工复核、技术 PASS 不等于审美 PASS 均已成正式约束。
- 2026-11-04 声音决策：AISHELL-3 两条候选 `REJECTED`；LibriVox 一条 `PENDING_REVIEW`；外部 `APPROVED` = 0；`narrator_self` 为唯一 `APPROVED` 生产音色。
- A/B 选型基线写入 `config/styles.yaml.production_baselines`：工笔 `shot_001=A/shot_002=A`；水墨 `shot_001=B/shot_002=A`。
- P1 `shot_002` 以确定性 LAB 色彩迁移修正；style consistency 复跑 `PASS_VERIFIED`（ΔE 9.22、luma 7.13），最终 build 接入待做。
- `PRD-OPS-001`：不作为 v1.0 硬门，成本/失败率仅日志级观测。
- 状态仍按真实证据：AUDIO/MOTION/STORY/QA 等不得因“已批准”自动写成 `PASS_VERIFIED`。
