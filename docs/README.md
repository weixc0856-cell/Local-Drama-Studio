# Local-Drama-Studio 文档索引

> **唯一需求入口：[PRD.md](PRD.md)（Single Source of Truth）。** 产品定位、范围、需求编号与验收标准以 PRD 为准；其他文档只能解释、执行、验证或记录现状。
> 文档状态口径：`DECISION`（已决策）、`PASS_VERIFIED`（有执行证据）、`PARTIAL`（部分验证）、`NOT_RUN`（未执行）、`PENDING_REVIEW`（等人工）。

## 1. 当前文档（14 份）

| 文档 | 内容 | 状态 |
|---|---|---|
| [PRD.md](PRD.md) | 产品定位、范围、需求编号、验收标准（SSOT） | `DECISION` |
| [ENVIRONMENT.md](ENVIRONMENT.md) | 硬件/软件、双 venv、模型目录、端口、显存、技术栈 | `DECISION` |
| [REPO_LAYOUT.md](REPO_LAYOUT.md) | 仓库 vs 产出根、DDD 分层、依赖规则、卫生守门 | `DECISION` |
| [CONTENT_SPEC.md](CONTENT_SPEC.md) | 视觉/人物/声音/视频/字幕规范；内容包边界 | `DECISION` |
| [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) | 14 步流程、Script-to-Film 链路、配置与参数、失败降级 | `DECISION` |
| [FILM_PRODUCTION_GUIDE.md](FILM_PRODUCTION_GUIDE.md) | Script-to-Film 方法（分镜规划、连续性、剪辑时间轴） | `DECISION` |
| [VISUAL_STYLE.md](VISUAL_STYLE.md) | 风格引擎、23 套 Style Pack、两条核心管线、参考板 | `DECISION` |
| [AUDIO_AND_LICENSING.md](AUDIO_AND_LICENSING.md) | 音频策略、资产与授权台账、许可门禁 | `DECISION` |
| [QUALITY_AND_METRICS.md](QUALITY_AND_METRICS.md) | 质量门、成本、平台指标、失败模式 | `DECISION` |
| [PLATFORM_PUBLISHING.md](PLATFORM_PUBLISHING.md) | 抖音/小红书母版、舒适区、合规、发布清单 | `DECISION` |
| [ROADMAP.md](ROADMAP.md) | 冻结范围、已完成、待验证、能力边界、v1.1 候选 | `DECISION` |
| [DECISIONS.md](DECISIONS.md) | ADR-001…025（含产出分离、DDD、历史清理、文档收敛） | 记录 |
| [GUIDE.md](GUIDE.md) | 启动/关闭、工作台、开发、测试、排障 | `DECISION` |
| [ARCHIVE.md](ARCHIVE.md) | 归档索引（31 份历史文档，本地归档，不进 Git） | 记录 |

Literary Intelligence 规格仍在 [literary_intelligence/](literary_intelligence/)（L1_SPEC、RISKS、TOOL_MATRIX）。

## 2. 阅读顺序

1. 新人/接手：PRD → ENVIRONMENT → REPO_LAYOUT → GUIDE
2. 做片：PRODUCTION_GUIDE → FILM_PRODUCTION_GUIDE → VISUAL_STYLE
3. 决策/验收：QUALITY_AND_METRICS → ROADMAP → DECISIONS
4. 发布：PLATFORM_PUBLISHING → AUDIO_AND_LICENSING（授权）
5. 找旧资料：ARCHIVE

## 3. 文档规则

- 一份事实只在一处维护；其他文档链接过去，不复制。
- 状态必须跟证据走：没有执行日志/产物路径的结论不得写 `PASS_VERIFIED`。
- 平台/服务不可用写 `NOT_RUN`，不猜。
- 历史材料归档到 `D:\DramaStudio\archive\docs\<date>\`，仓库只留 [ARCHIVE.md](ARCHIVE.md) 索引。
- 文档中的命令以当前分层路径（`application/`、`infrastructure/`、`interfaces/`）和产出根（`D:\DramaStudio`）为准。
