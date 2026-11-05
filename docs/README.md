# Local-Drama-Studio 文档索引

> **唯一需求入口：[PRD.md](PRD.md)（Single Source of Truth）。** 产品定位、范围、TTS/视觉决策、需求编号与验收标准以 PRD 为准；其他文档只能解释、执行、验证或记录现状，不得创造或覆盖需求。
> 配套治理：[PRD_CHANGELOG.md](PRD_CHANGELOG.md)（变更/冲突修正）、[REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md)（需求矩阵 + Phase A 映射）。
> 产品基线：v1.0（2026-11-03 冻结）；2026-11-04 PRD SSOT 修订。
> 规则：产品文档是“方向与规范”；R0-R3 报告是“技术证据”。两者不互相替代。

## Phase A/B 生产文档（2026-11-04）

| 文档 | 内容 |
|---|---|
| [REFERENCE_STYLE_STUDY.md](REFERENCE_STYLE_STUDY.md) | 参考片风格研究：东方仙宫 / 水墨梦境 previs、可抄规则与边界 |
| [REFERENCE_FILMS.md](REFERENCE_FILMS.md) | 2026-11-05 三条两分钟对标片的实测拆解、镜头语法与验收标准 |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | 产品是什么、能做什么、两种风格、TTS 策略、边界 |
| [PRODUCTION_PIPELINE_GUIDE.md](PRODUCTION_PIPELINE_GUIDE.md) | 四类生产路径、每阶段输入/输出/命令/失败恢复/续跑 |
| [USER_GUIDE.md](USER_GUIDE.md) | 从环境准备到一篇成片、工作台操作、复用与排障 |
| [PRODUCTION_CONFIG_GUIDE.md](PRODUCTION_CONFIG_GUIDE.md) | FLUX/Wan/TTS/字幕/FFmpeg/质量阈值；实际 vs 推荐 vs 未验证 |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 架构、契约、任务注册表、API、扩展方式、已知陷阱 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 服务/显存/生成/配音/字幕/合成/任务故障树 |
| [PROJECT_NEXT_STEPS.md](PROJECT_NEXT_STEPS.md) | P0–P4 路线与工作量评估 |
| [audit/REPOSITORY_STRUCTURE.md](audit/REPOSITORY_STRUCTURE.md) | Phase A 仓库结构审计 |
| [audit/IMPLEMENTATION_STATUS.md](audit/IMPLEMENTATION_STATUS.md) | 22 项能力矩阵 + 历史验证索引 |
| [audit/ARCHITECTURE_AUDIT.md](audit/ARCHITECTURE_AUDIT.md) | 架构边界、配置传递、风险清单 |
| [audit/PHASE_A_SUMMARY.md](audit/PHASE_A_SUMMARY.md) | Phase A 结论与产品决策修正 |
| [PRD_CHANGELOG.md](PRD_CHANGELOG.md) | PRD 2026-11-04 变更记录与旧文档冲突修正 |
| [REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md) | 需求编号、验收、Phase A 审计映射、当前状态 |

## 待审提案（未写入 PRD）

| 文档 | 内容 |
|---|---|
| [proposals/AUDIOVISUAL_GAP_AUDIT.md](proposals/AUDIOVISUAL_GAP_AUDIT.md) | 音频/运动/TTS/叙事/QA 仓库差距审计 |
| [proposals/PRD_AUDIOVISUAL_UPGRADE_PROPOSAL.md](proposals/PRD_AUDIOVISUAL_UPGRADE_PROPOSAL.md) | 视听能力升级需求、schema、FFmpeg 方案、批次与验收提案 |
| [proposals/VOICE_ASSET_SOURCE_REVIEW.md](proposals/VOICE_ASSET_SOURCE_REVIEW.md) | 声音来源核验、已拉取候选、授权阻断项与首批种子库状态 |
| [proposals/PRD_AMENDMENT_2026-11-04.md](proposals/PRD_AMENDMENT_2026-11-04.md) | 2026-11-04 已批准的变更提案：AUDIO / TTS-007 / VOICE-ASSET / MOTION / STORY / QA，已并入 PRD §24 |

> 提案不是已批准需求；批准前不写入 `docs/PRD.md`，不据此开工。

> Phase A/B 文档描述的是 **当前工作区**（HEAD `06f91e4` + M8/声景/zero-shot 未提交工作），不是更早的 v1.0 冻结快照。历史报告不删除、不重写结论。

## 产品基线（v1.0）

| # | 文档 | 内容 |
|---|---|---|
| 01 | [PRD.md](PRD.md) | **唯一 SSOT**：定位、范围、TTS/风格决策、需求编号、验收标准 |
| 02 | [TECH_STACK.md](TECH_STACK.md) | 冻结技术栈、版本、许可证、性能基线 |
| 03 | [CONTENT_SPEC.md](CONTENT_SPEC.md) | 视觉、人物、场景、声音、字幕、视频规范 |
| 04 | [PRODUCTION_WORKFLOW.md](PRODUCTION_WORKFLOW.md) | 14 步生产流程、现状、失败降级、成本 |
| 05 | [PLATFORM_PUBLISHING_SPEC.md](PLATFORM_PUBLISHING_SPEC.md) | 抖音/小红书包装、合规、发布记录 |
| 06 | [ASSET_AND_LICENSE_REGISTRY.md](ASSET_AND_LICENSE_REGISTRY.md) | 模型/素材/字体/音乐授权台账 |
| 07 | [QUALITY_AND_METRICS.md](QUALITY_AND_METRICS.md) | 质量门、成本、平台数据、状态词典 |
| 08 | [ROADMAP.md](ROADMAP.md) | v1.0 冻结、M3-M6、v1.1 候选 |
| 09 | [VISUAL_STYLE_SPEC.md](VISUAL_STYLE_SPEC.md) | 双核心视觉风格（青绿工笔 / 写意水墨）、配置边界、动画与合成路线 |

## 技术证据（保留，不合并）

| 阶段 | 文档 |
|---|---|
| R0 环境 | [R0_TEST_PLAN.md](R0_TEST_PLAN.md) / [R0_TEST_REPORT.md](R0_TEST_REPORT.md) |
| R1 视觉资产 | [R1_AUDIT.md](R1_AUDIT.md) / [R1_VISUAL_DESIGN.md](R1_VISUAL_DESIGN.md) / [R1_TEST_PLAN.md](R1_TEST_PLAN.md) / [R1_TEST_REPORT.md](R1_TEST_REPORT.md) |
| R2-A 性能边界 | [R2_TEST_PLAN.md](R2_TEST_PLAN.md) / [R2_TEST_REPORT.md](R2_TEST_REPORT.md) |
| R2-B 英雄镜头 | [R2B_TEST_PLAN.md](R2B_TEST_PLAN.md) / [R2B_TEST_REPORT.md](R2B_TEST_REPORT.md) |
| R3 竖屏成片 | [R3_TEST_PLAN.md](R3_TEST_PLAN.md) / [R3_TEST_REPORT.md](R3_TEST_REPORT.md) |
| R3-D 字体候选与接入 | [R3D_FONT_SELECTION_REPORT.md](R3D_FONT_SELECTION_REPORT.md) |
| S2 双核心风格技术验证 | [S2_TEST_REPORT.md](S2_TEST_REPORT.md) |
| 双视觉管线首批验证 | [PIPELINE_AB_VALIDATION.md](PIPELINE_AB_VALIDATION.md) |
| 双管线专项修复（水墨 Motion Mask / 工笔风格） | [PIPELINE_FIX_REPORT.md](PIPELINE_FIX_REPORT.md) |
| 双管线动态与古诗词声音升级（2026-11-04） | [MOTION_VOICE_UPGRADE_REPORT.md](MOTION_VOICE_UPGRADE_REPORT.md) |
| 镜头美学设计系统集成（2026-11-04） | [AESTHETIC_DESIGN_REPORT.md](AESTHETIC_DESIGN_REPORT.md) |
| 视觉事故审计 M0（2026-11-04） | [M0_VISUAL_FAILURE_AUDIT.md](M0_VISUAL_FAILURE_AUDIT.md) |
| 主体保护机制 M1（2026-11-04） | [M1_REGION_PROTECTION_REPORT.md](M1_REGION_PROTECTION_REPORT.md) |
| 局部运动算法 M2（2026-11-04） | [M2_MOTION_ALGORITHMS_REPORT.md](M2_MOTION_ALGORITHMS_REPORT.md) |
| 时间连续性与质量门禁 M3（2026-11-04） | [M3_QUALITY_GATES_REPORT.md](M3_QUALITY_GATES_REPORT.md) |
| 转场与时序时间轴 M4（2026-11-04） | [M4_TRANSITIONS_REPORT.md](M4_TRANSITIONS_REPORT.md) |
| Wan 运动遮罩核验 M5（2026-11-04） | [M5_WAN_MOTION_MASK_REPORT.md](M5_WAN_MOTION_MASK_REPORT.md) |
| 发音校正与音频管线 M6（2026-11-04） | [M6_PRONUNCIATION_REPORT.md](M6_PRONUNCIATION_REPORT.md) |
| 双风格最终交付 M7（2026-11-04） | [M7_FINAL_DELIVERY_REPORT.md](M7_FINAL_DELIVERY_REPORT.md) |

## 生产工作台（2026-11-03）

| 文档 | 内容 |
|---|---|
| [PROJECT_AUDIT.md](PROJECT_AUDIT.md) | 历史审计（Phase A，已由 PRD §21 取代） |
| [FRONTEND_DESIGN.md](FRONTEND_DESIGN.md) | 工作台设计：技术栈、导航、SQLite schema、API 契约、任务状态模型 |
| [WORKSPACE_REPORT.md](WORKSPACE_REPORT.md) | 历史交付报告（Phase B-F） |

## 设计与参考

- [ARCHITECTURE.md](ARCHITECTURE.md) — 目标架构、状态机、ComfyUI 协议、FFmpeg 规范
- [ENVIRONMENT.md](ENVIRONMENT.md) — 硬件、双 venv、模型仓库、端口、实测显存
- [DECISIONS.md](DECISIONS.md) — ADR
- [CONTENT_PACKS.md](CONTENT_PACKS.md) — 共享层/主题包边界

## 冻结审计

- [V1_FREEZE_AUDIT.md](V1_FREEZE_AUDIT.md) — 冲突、解决记录、文件清单、Git 摘要
- [P0_R2B_FREEZE_CHECK.md](P0_R2B_FREEZE_CHECK.md) — R2-B 固化与仓库现状核对
- [R3_COMMIT_AUDIT.md](R3_COMMIT_AUDIT.md) — R3 提交前审查与边界
- [V1_COMMIT_AUDIT.md](V1_COMMIT_AUDIT.md) — v1.0 提交前审查与 R3-D 建议

## 当前下一步

- 视觉方向为两种正式产品风格（[VISUAL_STYLE_SPEC.md](VISUAL_STYLE_SPEC.md)）：S1 规范与配置已落地（`PASS_STATIC`）；S2-工笔/S2-水墨 各产出一段 20 秒片段；管线 A（水墨）/B（工笔）首批样片技术通过，静态门 `PARTIAL`，人工审美 PENDING。**S3 不再用单一状态概括**：① 两种风格独立规范/配置 = `PASS_STATIC`；② 每种风格各 2 镜头技术样片（M7）= `PASS_VERIFIED`（技术）；③ 作品级风格锁定 = `PARTIAL`、跨镜头一致性正式验证 = `NOT_RUN`。见 [MOTION_VOICE_UPGRADE_REPORT.md](MOTION_VOICE_UPGRADE_REPORT.md) 与 [audit/IMPLEMENTATION_STATUS.md](audit/IMPLEMENTATION_STATUS.md) §2.23。
- 镜头美学设计已接入：`aesthetic.plan → comfy.batch → aesthetic.compare → aesthetic.review`；4 组镜头共 8 张 A/B 实图，自动指标与联系表已生成，人工审美 `PENDING_HUMAN_REVIEW`。见 [AESTHETIC_DESIGN_REPORT.md](AESTHETIC_DESIGN_REPORT.md)。
- P1 生产闭环已完成：ContentPackage → 文案/分镜 → 女声 TTS → FLUX → segments → 成片 → quality。
- **完整工笔案例已纳入生产索引**：`projects/proj_chunjiang_gongbi/episodes/ep_chunjiang_gongbi_01/renders/build-20261103-161945/`，81.373 s / 1080×1920 / 13 段 / 18 句，`quality_report` + `verification_report` 双 PASS；实现是 `scroll_shot.py` + 预渲染 clips，不是 `motion.plan` 自动运动管线。
- **TTS 产品决策（2026-11-04 PRD）**：默认 **CosyVoice2-0.5B zero-shot**；300M SFT 仅显式可选。默认已真实跑通 0.5B（`PRD-TTS-001` = `PASS_VERIFIED`）；显式模式/运行时校验/manifest 记录已实现。
- **下一步优先级见 [PROJECT_NEXT_STEPS.md](PROJECT_NEXT_STEPS.md) 与 PRD §23**：P0-1（TTS 默认 0.5B zero-shot）✅ 已完成；剩余 P0 为作品级风格锁定、静态门不可绕过、工作流页对齐、证据索引。
- R3-D 剩余项是 BGM、音效与商用授权；内容路线仍以真实样片与平台数据为准。
- R3-D：字体/字幕接入已完成；SFT「中文女」已进入 P1 与 81.373 s 工笔成片；按最新 PRD，默认改为 0.5B zero-shot，SFT 仅显式可选；BGM、音效与商用授权仍未完成。见 [ROADMAP.md](ROADMAP.md)、[R3D_VOICE_PROSODY_REPORT.md](R3D_VOICE_PROSODY_REPORT.md) 与 [R3D_FONT_SELECTION_REPORT.md](R3D_FONT_SELECTION_REPORT.md)。

## 状态规则

状态词典以 `docs/PRD.md` §0.2 为唯一来源；本索引不再维护第二份。

- 产品规划不是已实现功能。
- 单篇样片不是市场验证。
- 技术成功不等于内容合格。
