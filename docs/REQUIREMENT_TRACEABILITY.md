# 需求追踪矩阵

> 文档状态：PRD 配套治理文档（2026-11-04）
> 唯一需求来源：[PRD.md](PRD.md)。本文件不创造需求，只把 PRD 需求编号映射到验收标准、Phase A 审计证据、当前状态与下一步。
> 状态口径：`PASS_VERIFIED` / `IMPLEMENTED_NOT_VERIFIED` / `PARTIAL` / `NOT_IMPLEMENTED` / `BLOCKED` / `OPEN_QUESTION`（见 PRD §0.2）。
> 规则：代码存在不等于需求通过；单测/Mock/缓存复用/历史产物不能冒充真实端到端。

---

## 1. 需求矩阵

| 编号 | PRD 章节 | 需求 | 验收标准 | 状态 | 当前证据 | 差距 / 下一步 |
|---|---|---|---|---|---|---|
| `PRD-GOV-001` | §0.1 | PRD 是唯一 SSOT；冲突按优先级处理 | 其他文档不得创造/覆盖需求；冲突有记录与修正 | `IMPLEMENTED_NOT_VERIFIED` | PRD §0.1；本文件；PRD_CHANGELOG | 待项目所有者评审确认；确认后再改代码 |
| `PRD-GOV-002` | §0.2 | 需求状态必须由真实证据决定 | 无证据不得 `PASS_VERIFIED`；Mock/单测不等于端到端 | `PARTIAL` | 审计发现文档/状态多处过期；本文件已按证据标注 | 继续清理旧文档中的过期状态 |
| `PRD-GOV-003` | §0.2/§21 | 历史证据路径缺失必须如实标注 | 不伪造路径；报告保留；替代证据可查 | `PARTIAL` | `docs/audit/REPOSITORY_STRUCTURE.md` §8 已标注 R1–R3/S2 目录缺失 | 旧报告中的失效路径需逐条加注或索引 |
| `PRD-TTS-001` | §11.1 | **默认调用 CosyVoice2-0.5B zero-shot** | 默认配置/默认任务实际加载 0.5B；manifest 记录 `zero_shot/CosyVoice2` | `PASS_VERIFIED` | 2026-11-04 默认配置真实 2 行；`voice_profile` 真实 2 行；manifest `zero_shot/CosyVoice2/0.5B/prompt/voice_cast`；354 tests | 保持；SFT 继续显式 |
| `PRD-TTS-002` | §11.1 | 300M SFT 仅显式可选，不能作为默认 | 必须显式 `tts_mode=sft` + `-Model sft`；任务/manifest 可追溯 | `PASS_VERIFIED` | 2026-11-04 真实 SFT 1 行；P1/81.373 历史 SFT 成片 | 保留为可选模式；UI/任务需明确默认不是它 |
| `PRD-TTS-003` | §11.1 | 模型/服务/参数不满足时明确报错，禁止静默回退 | 0.5B 缺失/加载失败/参考音缺失 → 失败；不得回退 300M | `PASS_VERIFIED` | SFT↔zero-shot 双向错配均真实报错；`_validate_runtime` 校验 `/health` | 保持；新增模式必须同样校验 |
| `PRD-TTS-004` | §11.1 | UI/任务/配置/日志/manifest/报告记录实际模型与模式 | `tts_mode/model_class/model_dir/speaker_id/prompt` 可查 | `PARTIAL` | CLI 输出与 `audio_manifest.json` 真实 2 行；任务参数/UI 已加 `tts_mode`、`voice_profile`、`voices`；任务结果回传 `voice_cast` | UI/任务/生产报告仍未做真实端到端；报告模板需引用这些字段 |
| `PRD-TTS-005` | §11.1 | zero-shot 必须有参考音频与逐字参考文本 | 缺失即失败；参考音哈希写入 manifest | `IMPLEMENTED_NOT_VERIFIED` | 真实 zero-shot manifest 有 `prompt.sha256/text`；voice profile 解析对缺失参考音直接失败；单测覆盖 `prompt_text` 缺失 | 真实服务上的“参考音缺失即失败”路径仍待一次复验 |
| `PRD-TTS-006` | §15 | 参考音/模型权重的商用授权范围 | 有书面许可或明确替代方案 | `OPEN_QUESTION` | `ASSET_AND_LICENSE_REGISTRY.md`：CosyVoice 权重/音色/生成音频商用 `UNVERIFIED`；自录参考音为 self-owned | 法务/授权核验；不得把技术试听当商用许可 |
| `PRD-STYLE-001` | §9.2 | 每篇作品只能选择一个主视觉风格 | 作品级 `style_id` 唯一；全片不混用 | `PARTIAL` | 期数 `style_id/style_snapshot`；`ProductionScript.style_id` | 镜头/资产无独立 `style_id`；无强制门 |
| `PRD-STYLE-002` | §9.2 | 风格贯穿剧本、镜头、资产、任务、质量检查 | 每层可追溯到同一 `style_id/style_sha256` | `PARTIAL` | 期数快照 → `ProductionScript` 提示词；P1 可追溯 | 任务可覆盖；`comfy.batch` 不校验；质量门不校验 style_id |
| `PRD-STYLE-003` | §9.2 | 生成任务不得自行覆盖/切换作品风格 | 任务参数不能改风格；改风格走新版本 | `NOT_IMPLEMENTED` | `motion.plan`/`aesthetic.plan` 有 `--style`；`comfy.batch` 不校验 | 移除/限制覆盖；加 style_id 校验与测试 |
| `PRD-STYLE-004` | §9.2 | 改风格必须创建新生产/风格版本，不覆盖历史 | 旧构建/旧 manifest 不变 | `NOT_IMPLEMENTED` | UI“应用为快照”直接替换期数 snapshot；无版本表/链 | 新版本入口 + 记录旧/新 style sha |
| `PRD-STYLE-005` | §9.2 | 两种风格有独立规范、提示词、参数、质量评价 | `config/styles.yaml` 两套 profile；不按 style 写代码分支 | `IMPLEMENTED_NOT_VERIFIED` | `style_presets.py` 严格校验 + 8 项测试；两套 `aesthetic_profile/motion/compositing` | 尚未用完整作品验证；`validation_status` 仍 `NOT_RUN` |
| `PRD-STYLE-006` | §9.2 | 两种风格分别完成技术生产验证 | 每种风格有真实样片 + 质量证据 | `PASS_VERIFIED`（技术） | M7 水墨 10.087 s、工笔 9.583 s；quality/audio QA PASS；81.373 s 工笔 quality+verification PASS | 人工审美 PENDING 的项继续标 PENDING；不得升级为完整作品一致性 |
| `PRD-STYLE-007` | §9.2 | 同一作品跨镜头风格一致性单独验证 | 有跨镜头一致性检查/人工结论；不能用两张图代替 | `NOT_IMPLEMENTED` | 只有相邻镜头 LAB/亮度连续性（`check_color_continuity`）；无风格分类/一致性门 | 设计并实现风格一致性指标/门 |
| `PRD-QUAL-001` | §17 | 静态质量门必须可执行、不可静默绕过 | 动图前有 `static_quality.json`；缺失时失败或显式跳过 | `IMPLEMENTED_NOT_VERIFIED` | `build_motion_plan` 默认要求每镜头报告，缺失即失败；`--skip-static-gate` / 任务 `skip_static_gate` 显式跳过；`test_production` 覆盖 | `static.check` 任务已注册；真实 `motion.plan` + 报告端到端待跑 |
| `PRD-QUAL-002` | §17 | 质量门要区分技术/美学/人工 | 技术 PASS 不等于内容通过 | `PARTIAL` | 技术门 PASS；美学/人工 PENDING；工作台 `quality.check` 不暴露 motion manifest | 质量视图/参数/报告分层 |
| `PRD-UX-001` | §13 | 工作台不得展示过期能力或暗示未实现功能 | 节点/按钮与真实任务注册表/产物一致 | `PARTIAL` | 工作流页仍写“写入路径未实现/分镜生成器未实现/r3_tts 尚未参数化”；无 package/script/motion/aesthetic 节点 | 重写 `discovery._workflow` 与节点 |
| `PRD-CASE-001` | §21.3 | 81.373 s 工笔为已验证生产案例，路径为 scroll_shot | 1080×1920 / 13 段 / 18 句 / quality+verification PASS；不得写成 motion.plan | `PASS_VERIFIED` | `projects/proj_chunjiang_gongbi/.../build-20261103-161945/`；`84628a06…`；`PRODUCTION_REPORT.md` | 保持路径区分；不要把它当 motion.plan 证据 |
| `PRD-DATA-001` | §4/§7 | 生产数据契约必须明确、单一 | 文档与代码对当前生产契约一致；历史契约不冒充现状 | `PARTIAL` | 生产用 `ProductionScript`；`models.Storyboard` 仅测试；PRD/ARCHITECTURE 已注明 | 统一文档措辞；或明确 Storyboard 为 legacy |
| `PRD-CONFIG-001` | §16 | 配置字段必须有效或明确标注为未接线 | 改配置有可观察效果；死字段有清单 | `PARTIAL` | TTS 模式已接线；`subtitles.*`、`narration_modes.leading_ms`、`generation.profiles` 仍无消费者 | 接线或删除；更新配置手册 |
| `PRD-OPS-001` | §17/§18 | 成本、失败率、重试与批次结果可汇总 | 是否进入 v1.0 验收尚未决定 | `OPEN_QUESTION` | 任务表有状态/日志；无成本/批次聚合 | 先确认是否 v1.0；确认后再排 P2 任务 |

---

## 2. 需求状态汇总

| 状态 | 数量 | 需求 |
|---|---|---|
| `PASS_VERIFIED` | 5 | TTS-001/002/003；STYLE-006；CASE-001 |
| `IMPLEMENTED_NOT_VERIFIED` | 4 | GOV-001；STYLE-005；TTS-005；QUAL-001 |
| `PARTIAL` | 9 | GOV-002/003；TTS-004；STYLE-001/002；QUAL-002；UX-001；DATA-001；CONFIG-001 |
| `NOT_IMPLEMENTED` | 3 | STYLE-003/004/007 |
| `BLOCKED` | 0 | — |
| `OPEN_QUESTION` | 2 | TTS-006；OPS-001 |

> 数量以矩阵逐行统计为准；此表是摘要，不替代矩阵。

---

## 3. Phase A 审计映射

| 审计发现 | 审计位置 | 映射需求 | 当前结论 |
|---|---|---|---|
| A-01 TTS 模式静默切换 | `ARCHITECTURE_AUDIT.md` §10 A-01 | `PRD-TTS-001/003/004` | 默认 zero-shot、显式模式、运行时校验、逐行 `voice_cast` 已实现；TTS-001 `PASS_VERIFIED`，TTS-004 仍 `PARTIAL`（UI/报告未全验） |
| A-02 静态质量门可绕过 | 同上 A-02 | `PRD-QUAL-001` | `IMPLEMENTED_NOT_VERIFIED`；plan 默认强制，显式 skip 才绕过 |
| A-03 工作流页过期/缺节点 | 同上 A-03 | `PRD-UX-001` | `PARTIAL` |
| A-04 两套风格系统脱节 | 同上 A-04 | `PRD-STYLE-001/002/003/004` | `PARTIAL`/`NOT_IMPLEMENTED` |
| A-05 两套数据契约 | 同上 A-05 | `PRD-DATA-001` | `PARTIAL`；生产 `ProductionScript`，`Storyboard` 仅测试 |
| A-06 配置死字段 | 同上 A-06 | `PRD-CONFIG-001` | `PARTIAL`；TTS 已接线，其余仍在 |
| A-07 运动质量门无法从 UI 选 | 同上 A-07 | `PRD-QUAL-002` | `PARTIAL` |
| A-08 美学结果不进入派生状态 | 同上 A-08 | `PRD-UX-001` | `PARTIAL` |
| A-09 任务注册表非唯一执行路径 | 同上 A-09 | `PRD-GOV-002` | `PARTIAL`；CLI 可绕过工作台锁 |
| A-10 历史证据路径缺失 | 同上 A-10；`REPOSITORY_STRUCTURE.md` §8 | `PRD-GOV-003` | `PARTIAL`；已标注，未逐条修 |
| A-11 文档状态矛盾 | 同上 A-11 | `PRD-GOV-001` | `PARTIAL`；本轮修正 S3/TTS/81s，仍需持续维护 |
| A-12 doctor 不校验 styles/fonts/pronunciation | 同上 A-12 | `PRD-CONFIG-001` | `PARTIAL`；未实现 |
| A-13 81.373 s 未进主索引 | 同上 A-13 | `PRD-CASE-001` | `PASS_VERIFIED`；已纳入 PRD/文档索引 |
| A-14 ContentPackage/ProductionScript 不在工作台内容视图 | 同上 A-14 | `PRD-UX-001` | `PARTIAL` |
| A-15 quality_report 覆盖式写入 | 同上 A-15 | `PRD-QUAL-002` | `PARTIAL`；未版本化 |
| A-16 generation.profiles 与生产参数脱节 | 同上 A-16 | `PRD-CONFIG-001` | `PARTIAL`；死配置 |
| A-17 无成本/失败率监控 | 同上 A-17 | `PRD-OPS-001` | `OPEN_QUESTION`（是否进入 v1.0） |
| 81.373 s 实为 scroll_shot 路径 | `REPOSITORY_STRUCTURE.md` §9 | `PRD-CASE-001` | `PASS_VERIFIED`；路径已区分 |
| S3 被单一状态概括 | `PHASE_A_SUMMARY.md` §3 | `PRD-STYLE-001..007` | 已拆分为 7 项；见矩阵 |

---

## 4. 尚未分配为 PRD 需求的审计观察

以下属于工程债务/实现细节，未形成产品需求；不得自动升级为需求：

- 任务日志/缩略图缓存位置；
- `quality_report.json` 文件命名；
- `r1_batch` 重试间隔（立即重试 vs 30/90 s 退避）；
- `doctor` 的具体检查项数量；
- 历史报告中的失效 run 路径逐条修复。

这些可以作为 P2/P3 工程任务，但需先在 PRD 中建立对应需求（或明确为不影响产品验收的内部质量项）。

---

## 6. 提案阶段需求（**不在正式 PRD**）

以下编号来自 `docs/proposals/`，尚未批准写入 `docs/PRD.md`；不得当作正式 PRD 验收项。

| 编号 | 需求 | 状态 | 实现证据 | 待办 |
|---|---|---|---|---|
| `PRD-TTS-007` | 多音色角色映射 / Voice Profile | `IMPLEMENTED_NOT_VERIFIED` | `config/voices.yaml`、`src/drama_studio/voice/profiles.py`、逐行 `voice_profile`、`voice_cast.yaml` sidecar、`audio_manifest.json.voice_cast`；10 个单测 + 2 行真实 zero-shot + 真实 sidecar 2 行 | 正式 PRD 批准；多角色完整成片；UI 端到端 |
| `PRD-VOICE-ASSET-009` | Voice Profile 管理 | `PARTIAL` | 档案只读加载、状态门、许可证据、asset_id 引用；无写入 UI/DB | 资产库管理入口、审批流 |
| `PRD-AUDIO-001..006` | 多轨音频/ducking/SFX/资产台账 | `PARTIAL` | `audio_timeline.py`、`audio_assets.py`、`mix.py`、`quality.check_audio_timeline`；合成音频测试 PASS | 正式 PRD 批准；真实 BGM/SFX 授权与听感 |
| `PRD-MOTION-001..004` | 运动模板产品化 | `PARTIAL` | 现有 `motion/`、M8 报告；未按提案新增模板面 | 模板/参数文档与 UI |
| `PRD-STORY-001..002` | Character/Shot Bible | `PARTIAL` | `src/drama_studio/bible.py` 严格 CharacterBible/ShotBible；覆盖、引用、风格、声音档案检查；7 个单测 | 作者 UI/真实作品 Bible；跨镜头同脸仍为人工复核 |
| `PRD-QA-001..002` | 结构化视听 QA | `PARTIAL` | 技术质量门、音频时间线检查；无结构化人工听感表 | 人工听感/结构保护检查 |

> 正式 PRD 未包含上述编号；在批准前，代码实现只能标 `IMPLEMENTED_NOT_VERIFIED` / `PARTIAL`，不得标 `PASS_VERIFIED`。

---

## 5. OPEN_QUESTION

| 编号 | 问题 | 为什么不能假设 | 需要谁决定 |
|---|---|---|---|
| `PRD-TTS-006` | CosyVoice 权重、预置音色、自录参考音、生成音频的商用授权范围 | 代码 Apache-2.0 不等于权重/音色/输出可商用；授权台账仍是 `UNVERIFIED` | 项目所有者 + 法务/供应商条款 |
| `PRD-OPS-001` | 成本/批次指标是否进入 v1.0 验收，还是 P2 | PRD 目前只要求记录，未定义阈值 | 项目所有者 |

> 未决问题不得用“技术可行”代替产品决策；未决期间相关能力保持 `OPEN_QUESTION` 或 `PARTIAL`，不得写成 `PASS_VERIFIED`。
