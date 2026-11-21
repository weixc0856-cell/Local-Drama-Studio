# Local-Drama-Studio 文档索引

> **唯一需求入口：[PRD.md](PRD.md)（Single Source of Truth）。** 产品定位、范围、需求编号与验收标准以 PRD 为准；其他文档只能解释、执行、验证或记录现状。  
> 文档状态口径：`DECISION`（已决策）、`PASS_VERIFIED`（有执行证据）、`PARTIAL`（部分验证）、`NOT_RUN`（未执行）、`PENDING_REVIEW`（等人工）。

---

## 1. 核心生产与架构文档（18 份）

| 文档 | 内容与定位 | 状态 |
| :--- | :--- | :---: |
| [PRD.md](PRD.md) | 产品定位、范围、需求编号、验收标准（SSOT） | `DECISION` |
| [ENVIRONMENT.md](ENVIRONMENT.md) | 硬件/软件、双 venv、模型目录、端口、显存、双引擎与 Wan 14B 技术栈 | `DECISION` |
| [REPO_LAYOUT.md](REPO_LAYOUT.md) | 仓库 vs 产出根物理隔离、Junction 联接、DDD 分层、依赖规则 | `DECISION` |
| [WIDESCREEN_VIDEO_GENERATION_GUIDELINES.md](WIDESCREEN_VIDEO_GENERATION_GUIDELINES.md) | **16:9 横屏视频防糊工程规范**（潜空间 Token 载荷、景别控制、景深虚化） | `PASS_VERIFIED` |
| [PORTRAIT_PRODUCTION_SOP.md](PORTRAIT_PRODUCTION_SOP.md) | **人像全流程生产 SOP 标准**（Z-Image Turbo 裸跑原生肤质控制） | `PASS_VERIFIED` |
| [Z_IMAGE_TURBO_DEPLOYMENT.md](Z_IMAGE_TURBO_DEPLOYMENT.md) | **阿里 Z-Image Turbo 部署与运行手册**（Qwen3-4B CPU 卸载，8步蒸馏） | `PASS_VERIFIED` |
| [Z_IMAGE_TURBO_STYLE_ATLAS.md](Z_IMAGE_TURBO_STYLE_ATLAS.md) | **Z-Image 视觉风格图谱**（38 套配方 / 7 维度词典 / 零负面提示词 / 实测工作台，自动生成） | `DECISION` |
| [Z_IMAGE_STYLE_FINDINGS.md](Z_IMAGE_STYLE_FINDINGS.md) | **Z-Image 风格实测结论**（58 张实拍、五维评分、5 类失败模式与已验证修法、吞吐基线） | `PASS_VERIFIED` |
| [CONTENT_SPEC.md](CONTENT_SPEC.md) | 视觉/人物/声音/视频/字幕规范；内容包边界 | `DECISION` |
| [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) | 14 步流程、Script-to-Film 链路、配置与参数、失败降级 | `DECISION` |
| [FILM_PRODUCTION_GUIDE.md](FILM_PRODUCTION_GUIDE.md) | Script-to-Film 方法（分镜规划、连续性、剪辑时间轴） | `DECISION` |
| [VISUAL_STYLE.md](VISUAL_STYLE.md) | 风格引擎、23 套 Style Pack、双引擎路由策略 | `DECISION` |
| [AUDIO_AND_LICENSING.md](AUDIO_AND_LICENSING.md) | 音频策略、**商业版权穿透台账**（Stable Audio / ACE-Step 100% 商用合规） | `PASS_VERIFIED` |
| [PHOTOGRAPHY_PORTRAIT_COMPOSITION_GUIDE.md](PHOTOGRAPHY_PORTRAIT_COMPOSITION_GUIDE.md) | 电影级构图、光位设计（伦勃朗光/蝴蝶光/侧逆光）与景深指南 | `DECISION` |
| [LORA_STYLE_GUIDE.md](LORA_STYLE_GUIDE.md) | FLUX.3 胶片与写实 LoRA 挂载阈值及防过拟合蜡化指南 | `DECISION` |
| [QUALITY_AND_METRICS.md](QUALITY_AND_METRICS.md) | 质量门、成本、平台指标、失败模式 | `DECISION` |
| [PLATFORM_PUBLISHING.md](PLATFORM_PUBLISHING.md) | 抖音/小红书母版、双画幅适配、发布清单 | `DECISION` |
| [ROADMAP.md](ROADMAP.md) | 冻结范围、已完成、能力边界 | `DECISION` |
| [DECISIONS.md](DECISIONS.md) | ADR-001…032（含产出物理隔离、双引擎路由、Wan 14B 封板、Token Economy 跨工具移植） | 记录 |
| [TOKEN_ECONOMY_PORT.md](TOKEN_ECONOMY_PORT.md) | **Token Economy 跨工具交接规格**（Codex / Antigravity 配置面、守卫可移植性、分期方案、计费口径） | `DECISION` |
| [GUIDE.md](GUIDE.md) | 启动/关闭、统一 CLI (`src/produce.py`)、开发测试排障 | `DECISION` |

---

## 2. 生产阅读路径

1. **新人接手与架构认知**：PRD $\rightarrow$ ENVIRONMENT $\rightarrow$ REPO_LAYOUT $\rightarrow$ DECISIONS
2. **生图与视频实操**：
   - 电影级人像直出：PORTRAIT_PRODUCTION_SOP $\rightarrow$ Z_IMAGE_TURBO_DEPLOYMENT
   - 16:9 横屏电影级短片：WIDESCREEN_VIDEO_GENERATION_GUIDELINES
   - 工业/机械/海报双引擎比拼：`src/produce.py image --type industrial`
3. **商业化发布与版权安全**：AUDIO_AND_LICENSING $\rightarrow$ PLATFORM_PUBLISHING

---

## 3. 文档规则

- 一份事实只在一处维护；其他文档链接过去，不复制。
- 状态必须跟证据走：没有执行日志/产物路径的结论不得写 `PASS_VERIFIED`。
- 历史材料归档到 `<DRAMA_OUTPUT_ROOT>/archive/docs\<date>\`，仓库只留 [ARCHIVE.md](ARCHIVE.md) 索引。
- 文档中的命令以当前统一 CLI（`src/produce.py`）和产出根（`<DRAMA_OUTPUT_ROOT>/`）为准。
