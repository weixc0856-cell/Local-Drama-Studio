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

## 技术证据（保留，不合并）

| 阶段 | 文档 |
|---|---|
| R0 环境 | [R0_TEST_PLAN.md](R0_TEST_PLAN.md) / [R0_TEST_REPORT.md](R0_TEST_REPORT.md) |
| R1 视觉资产 | [R1_AUDIT.md](R1_AUDIT.md) / [R1_VISUAL_DESIGN.md](R1_VISUAL_DESIGN.md) / [R1_TEST_PLAN.md](R1_TEST_PLAN.md) / [R1_TEST_REPORT.md](R1_TEST_REPORT.md) |
| R2-A 性能边界 | [R2_TEST_PLAN.md](R2_TEST_PLAN.md) / [R2_TEST_REPORT.md](R2_TEST_REPORT.md) |
| R2-B 英雄镜头 | [R2B_TEST_PLAN.md](R2B_TEST_PLAN.md) / [R2B_TEST_REPORT.md](R2B_TEST_REPORT.md) |
| R3 竖屏成片 | [R3_TEST_PLAN.md](R3_TEST_PLAN.md) / [R3_TEST_REPORT.md](R3_TEST_REPORT.md) |

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

- R3-D：女声、字体、BGM、音效选型与授权核验（`DECISION` / `NOT_RUN`），见 [ROADMAP.md](ROADMAP.md)。

## 状态规则

统一使用：`PASS_VERIFIED` / `PASS_LIMITED` / `PASS_STATIC` / `PARTIAL` / `NOT_RUN` / `DECISION`。

- 产品规划不是已实现功能。
- 单篇样片不是市场验证。
- 技术成功不等于内容合格。
