# Local-Drama-Studio 文档索引

> 产品基线：v1.0（2026-11-03 冻结）。
> 规则：产品文档是“方向与规范”；R0-R3 报告是“技术证据”。两者不互相替代。

## 产品基线（v1.0）

| # | 文档 | 内容 |
|---|---|---|
| 01 | [PRD.md](PRD.md) | 定位、内容范围、范围边界、成功标准、风险 |
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

- 视觉方向已收敛为双核心风格（[VISUAL_STYLE_SPEC.md](VISUAL_STYLE_SPEC.md)）：S1 规范与配置已落地（`PASS_STATIC`）；S2-工笔/S2-水墨 各产出一段 20 秒片段；管线 A（水墨）完成云气/水面/孤舟/纸纹分层样片，管线 B（工笔）完成 28 秒长卷样片；技术检查通过，静态门 `PARTIAL`（山石纹理重复），人工审美 PENDING。见 [S2_TEST_REPORT.md](S2_TEST_REPORT.md) 与 [PIPELINE_AB_VALIDATION.md](PIPELINE_AB_VALIDATION.md)。S3 完整链路接入为 `NOT_RUN`。
- P1 生产闭环已完成：ContentPackage → 文案/分镜 → 女声 TTS → FLUX → segments → 成片 → quality。下一阶段为 P2（资产台账、BGM/音效、平台包装），S2/S3 不改变 P2 的既定项。
- R3-D 剩余项是 BGM、音效与商用授权；内容路线仍以真实样片与平台数据为准。
- R3-D：字体候选已完成来源/许可/覆盖/预览验证，字幕已接入正式构建，排版选型仍为 `DECISION`；女声已试听并固化方案但未进入正式成片；BGM、音效与商用授权待完成。见 [ROADMAP.md](ROADMAP.md) 与 [R3D_FONT_SELECTION_REPORT.md](R3D_FONT_SELECTION_REPORT.md)。

## 状态规则

状态词典以 `docs/QUALITY_AND_METRICS.md` 为唯一来源；本索引不再维护第二份。

- 产品规划不是已实现功能。
- 单篇样片不是市场验证。
- 技术成功不等于内容合格。
