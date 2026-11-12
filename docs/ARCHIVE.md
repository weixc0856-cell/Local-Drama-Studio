# 文档归档索引（2026-11-12）

本仓库只保留**当前有效**的规格与指南。历史报告、一次性审计、旧设计稿和已合并的来源文档已移出检出目录。

- 归档位置：`D:\DramaStudio\archive\docs\2026-11-12\`（`DRAMA_OUTPUT_ROOT` 下）
- 清单与哈希：同目录 `MANIFEST.json`（文件名、字节数、sha256、归档原因）
- **归档文件不进 Git、不进远程仓库**
- 归档工具：`scripts/archive_docs.py`（可复现；`--apply` 才移动）

## 归档内容与替代文档

| 归档文件 | 原因 | 现在看哪份 |
|---|---|---|
| `ARCHITECTURE.md` | 目标架构设计稿，已被实际分层取代 | [REPO_LAYOUT.md](REPO_LAYOUT.md) |
| `TECH_STACK.md` | 与环境文档重复 | [ENVIRONMENT.md](ENVIRONMENT.md) |
| `PRODUCTION_WORKFLOW.md` | 流程/管线/配置三份互相重叠 | [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) |
| `PRODUCTION_PIPELINE_GUIDE.md` | 同上 | [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) |
| `PRODUCTION_CONFIG_GUIDE.md` | 同上，且含已失效的 FLUX.2 / 4 步参数 | [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) |
| `USER_GUIDE.md` | 操作/开发/排障三份合并 | [GUIDE.md](GUIDE.md) |
| `DEVELOPER_GUIDE.md` | 同上（包结构已变） | [GUIDE.md](GUIDE.md) |
| `TROUBLESHOOTING.md` | 同上 | [GUIDE.md](GUIDE.md) |
| `VISUAL_STYLE_SPEC.md` | 风格规范/引擎/笔记/参考板台账合并 | [VISUAL_STYLE.md](VISUAL_STYLE.md) |
| `VISUAL_STYLE_ENGINE.md` | 同上 | [VISUAL_STYLE.md](VISUAL_STYLE.md) |
| `STYLE_BOARD_STATUS.md` | 工作台账，状态已并入 | [VISUAL_STYLE.md](VISUAL_STYLE.md) |
| `SHINKAI_STYLE_NOTES.md` | 风格笔记 | [VISUAL_STYLE.md](VISUAL_STYLE.md) |
| `SONG_AESTHETIC_STUDY.md` | 美学依据 | [VISUAL_STYLE.md](VISUAL_STYLE.md) |
| `SURREALISM_STYLE_NOTES.md` | 风格笔记 | [VISUAL_STYLE.md](VISUAL_STYLE.md) |
| `XUANJI_STYLE_NOTES.md` | 风格笔记 | [VISUAL_STYLE.md](VISUAL_STYLE.md) |
| `NEO_CHINESE_DIRECTION.md` | 方向笔记 | [VISUAL_STYLE.md](VISUAL_STYLE.md) |
| `AUDIO_ASSET_STRATEGY.md` | 音频策略与授权台账合并 | [AUDIO_AND_LICENSING.md](AUDIO_AND_LICENSING.md) |
| `ASSET_AND_LICENSE_REGISTRY.md` | 同上 | [AUDIO_AND_LICENSING.md](AUDIO_AND_LICENSING.md) |
| `PLATFORM_PUBLISHING_SPEC.md` | 发布规范与舒适区合并 | [PLATFORM_PUBLISHING.md](PLATFORM_PUBLISHING.md) |
| `PLATFORM_COMFORT_ZONE.md` | 同上 | [PLATFORM_PUBLISHING.md](PLATFORM_PUBLISHING.md) |
| `PRODUCTION_CAPABILITY.md` | 能力边界并入路线图 | [ROADMAP.md](ROADMAP.md) §9 |
| `CONTENT_PACKS.md` | 内容包边界并入内容规范 | [CONTENT_SPEC.md](CONTENT_SPEC.md) §9 |
| `REQUIREMENT_TRACEABILITY.md` | 历史治理矩阵，已被 PRD 状态表取代 | [PRD.md](PRD.md) |
| `PRD_CHANGELOG.md` | 历史变更记录 | [PRD.md](PRD.md) / [DECISIONS.md](DECISIONS.md) |
| `M0_VISUAL_FAILURE_AUDIT.md` | 一次性审计 | [VISUAL_STYLE.md](VISUAL_STYLE.md) 限制条款 |
| `MODEL_UPGRADE_POC.md` | 历史 POC；结论在 ADR | [DECISIONS.md](DECISIONS.md) |
| `ENHANCEMENT_AB_REPORT.md` | 一次性 A/B 报告 | [ROADMAP.md](ROADMAP.md) |
| `VIDEO_ENHANCEMENT_PLAN.md` | 未执行的计划 | [DECISIONS.md](DECISIONS.md) / [ROADMAP.md](ROADMAP.md) |
| `FRONTEND_DESIGN.md` | 历史设计稿，UI 已实现 | [REPO_LAYOUT.md](REPO_LAYOUT.md) / `src/drama_studio/web/` |
| `FRONTEND_PLAN.md` | 历史计划 | 同上 |
| `REFERENCE_STUDY.md` | 参考片研究笔记（仅研究素材） | [VISUAL_STYLE.md](VISUAL_STYLE.md) |

## 需要旧内容时

1. 到 `D:\DramaStudio\archive\docs\2026-11-12\` 直接打开；
2. 用 `MANIFEST.json` 的 sha256 确认版本；
3. 不要把归档文件复制回 `docs/`；需要长期保留的结论请写进当前规格文档并补充测试或证据。
