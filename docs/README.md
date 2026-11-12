# Local-Drama-Studio 文档索引

> **唯一需求入口：[PRD.md](PRD.md)（Single Source of Truth）。** 产品定位、范围、TTS/视觉决策、需求编号与验收标准以 PRD 为准；其他文档只能解释、执行、验证或记录现状，不得创造或覆盖需求。
> 配套治理：[PRD_CHANGELOG.md](PRD_CHANGELOG.md)（变更/冲突修正）、[REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md)（需求矩阵）。
> 状态词典以 `docs/PRD.md` §0.2 为唯一来源；本索引不再维护第二份。

> **2026-11-06 运行时变更：** 图像线为 FLUX.3 Klein（ADR-016；GGUF Q4_K_M、16 步、CFG 1.0）；TTS 为 VoxCPM2（端口 50000，48 kHz，CPU，无 SFT 预置音色）；视频线仍为 Wan2.2 TI2V 5B。
> **2026-11-06 本地清理：** `experiments/`、`projects/` 的媒体文件与旧实验目录已删除；`logs/r0/`、`logs/audit/` 原始日志已删除，旧报告中的 `PASS_VERIFIED` 不再能由日志复核。
> **2026-11-06 文档整合：** R0–R3、R3-D、M1–M8、管线 A/B 验证、冻结审计与项目阶段审计等历史报告已从工作区移除。需要原文时从 Git 历史取（`git log --diff-filter=D --name-only -- docs/`）。视觉风格与动画流程将整体重构，旧规格只作为设计输入保留。

## 核心规范

| 文档 | 内容 |
|---|---|
| [PRD.md](PRD.md) | **唯一 SSOT**：定位、范围、决策、需求编号、验收标准 |
| [PRD_CHANGELOG.md](PRD_CHANGELOG.md) | PRD 变更记录与冲突修正 |
| [REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md) | 需求编号、验收与实现映射 |
| [TECH_STACK.md](TECH_STACK.md) | 冻结技术栈、版本、许可证、性能基线 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 目标架构、状态机、ComfyUI 协议、FFmpeg 规范 |
| [ENVIRONMENT.md](ENVIRONMENT.md) | 硬件、双 venv、模型仓库、端口、实测显存 |
| [DECISIONS.md](DECISIONS.md) | ADR（含 ADR-016 图像线切换） |

## 生产与开发

| 文档 | 内容 |
|---|---|
| [PRODUCTION_WORKFLOW.md](PRODUCTION_WORKFLOW.md) | 14 步生产流程、现状、失败降级、成本 |
| [PRODUCTION_PIPELINE_GUIDE.md](PRODUCTION_PIPELINE_GUIDE.md) | 生产路径、每阶段输入/输出/命令/恢复 |
| [PRODUCTION_CONFIG_GUIDE.md](PRODUCTION_CONFIG_GUIDE.md) | FLUX/Wan/TTS/字幕/FFmpeg/质量阈值 |
| [USER_GUIDE.md](USER_GUIDE.md) | 环境准备到成片、工作台操作、排障 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 服务、显存、生成、配音、字幕、任务故障树 |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 架构、契约、任务注册表、API、扩展方式 |
| [FRONTEND_DESIGN.md](FRONTEND_DESIGN.md) | 工作台设计：技术栈、导航、SQLite schema、API 契约 |
| [STYLE_BOARD_STATUS.md](STYLE_BOARD_STATUS.md) | 12 套风格参考板的生产台账：定义、渲染、检查与评审状态 |
| [SURREALISM_STYLE_NOTES.md](SURREALISM_STYLE_NOTES.md) | 写实梦境派超现实：并置、软化、悬浮、尺度错位与冷静写实 |
| [SHINKAI_STYLE_NOTES.md](SHINKAI_STYLE_NOTES.md) | 新海诚式日系电影感的视觉要点：实景打底、镜头光晕、巨云与日常反射 |
| [NEO_CHINESE_DIRECTION.md](NEO_CHINESE_DIRECTION.md) | 新中式方向：几何抽象、哑光写实、40% 留白；苏州博物馆/聂隐娘/东方极简三条参考系 |
| [SONG_AESTHETIC_STUDY.md](SONG_AESTHETIC_STUDY.md) | 宋氏美学研究：平淡天真、三远/边角、留白、淡彩与宋瓷色，及对 `oriental.modern_chinese` 的映射 |
| [FRONTEND_PLAN.md](FRONTEND_PLAN.md) | 浅色影视工作站方案：视觉令牌、6 模块 IA、P0/P1 页面、API 与实施阶段；F0+F1 已实现 |

## 内容、质量与资产

| 文档 | 内容 |
|---|---|
| [CONTENT_SPEC.md](CONTENT_SPEC.md) | 视觉、人物、场景、声音、字幕、视频规范 |
| [CONTENT_PACKS.md](CONTENT_PACKS.md) | 共享层与主题内容包边界 |
| [QUALITY_AND_METRICS.md](QUALITY_AND_METRICS.md) | 质量门、成本、平台指标、状态词典引用 |
| [PLATFORM_PUBLISHING_SPEC.md](PLATFORM_PUBLISHING_SPEC.md) | 抖音/小红书包装、合规、发布记录 |
| [ASSET_AND_LICENSE_REGISTRY.md](ASSET_AND_LICENSE_REGISTRY.md) | 模型/素材/字体/音乐授权台账 |
| [AUDIO_ASSET_STRATEGY.md](AUDIO_ASSET_STRATEGY.md) | 声音资产来源、音色与 BGM/SFX 策略 |

## 视觉与参考（重构输入）

| 文档 | 内容 |
|---|---|
| [VISUAL_STYLE_SPEC.md](VISUAL_STYLE_SPEC.md) | 现行双风格规范（青绿工笔 / 写意水墨）；**风格重构后将整体重写** |
| [REFERENCE_STUDY.md](REFERENCE_STUDY.md) | 两分钟对标片实测拆解 + 东方仙境/水墨梦境 previs 研究（2026-11-06 合并） |
| [M0_VISUAL_FAILURE_AUDIT.md](M0_VISUAL_FAILURE_AUDIT.md) | 视觉事故审计：旧风格失败模式，是新风格的设计输入 |

## 当前阶段

| 文档 | 内容 |
|---|---|
| [MODEL_UPGRADE_POC.md](MODEL_UPGRADE_POC.md) | 2026-11-06 三模型核验、FLUX.3 落地、VoxCPM2 盲听与 H3 评估 |
| [FILM_PRODUCTION_GUIDE.md](FILM_PRODUCTION_GUIDE.md) | Script-to-Film 制作指南：十阶段、数据契约、摄影语言、连续性、声音与剪辑、QC、分阶段实施 |
| [VISUAL_STYLE_ENGINE.md](VISUAL_STYLE_ENGINE.md) | 12 套 Style Pack、双模型约束、提示词编译、参考板、一致性检查与开发优先级 |
| [PRODUCTION_CAPABILITY.md](PRODUCTION_CAPABILITY.md) | 当前硬件与模型下能稳定做什么、不能做什么；三种生产模式与镜头决策规则 |
| [PLATFORM_COMFORT_ZONE.md](PLATFORM_COMFORT_ZONE.md) | 抖音/小红书舒适区：规格、内容、模板、合规与不接的活 |
| [VIDEO_ENHANCEMENT_PLAN.md](VIDEO_ENHANCEMENT_PLAN.md) | 低清时序生成 + 后置增强的分层架构、默认 Lanczos、学习型超分取舍 |
| [ENHANCEMENT_AB_REPORT.md](ENHANCEMENT_AB_REPORT.md) | S01 的 Lanczos / Real-ESRNet / Real-ESRGAN A/B 与兼容性结论 |
| [ROADMAP.md](ROADMAP.md) | 阶段路线与后续候选 |

## 子目录

| 目录 | 内容 |
|---|---|
| [literary_intelligence/](literary_intelligence/) | 文学智能模块：`L1_SPEC`（规格）、`TOOL_MATRIX`（工具矩阵）、`RISKS`（风险） |

## 文档维护规则

- 产品文档是“方向与规范”，历史报告是“技术证据”，两者不互相替代。
- 已删除的历史报告不在工作区恢复；需要时从 Git 历史取。
- 新增报告必须写明执行的日期、机器、命令与产物路径；没有证据的结论标 `NOT_RUN`。
- 风格与动画重构完成后，`VISUAL_STYLE_SPEC.md` 与 `M0_VISUAL_FAILURE_AUDIT.md` 需要同步重写，避免旧结论继续被引用。
