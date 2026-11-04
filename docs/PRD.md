# 01 · PRD — Local-Drama-Studio 产品需求

> 文档状态：`DECISION` / 2026-11-04 SSOT 修订。
> 本文件是**产品需求的唯一权威来源（Single Source of Truth）**；实现状态以本文件 §21、§23 与真实产物为准。
> 本文件取代 2026-11-03 早先的 v1.0 PRD。历史技术证据（`docs/R0_*` ~ `docs/R3_*`、R3-D 报告）保留，不合并、不删除。
>
> **2026-11-04 最新决策**：TTS 默认调用 **CosyVoice2-0.5B zero-shot**；CosyVoice-300M-SFT 仅作为**显式可选**模式。此前“默认 SFT 中文女”的决定由本版取代。当前代码默认已为 `zero_shot`，并完成真实 2 行验证（`PRD-TTS-001 = PASS_VERIFIED`）。

## 0. 文档规则与状态词典

### 0.1 权威边界与冲突处理

| 内容 | 唯一权威 |
|---|---|
| 产品定位、范围、流程、验收、需求编号 | 本文件 |
| 技术选型与版本 | `docs/TECH_STACK.md` |
| 实际系统架构与数据流 | `docs/ARCHITECTURE.md` |
| 环境、端口、硬件事实 | `docs/ENVIRONMENT.md` |
| 设计决策历史 | `docs/DECISIONS.md` |
| 技术证据 | `docs/R0_*` ~ `docs/R3_*`、`docs/R3D_*` |

**唯一 PRD**：仓库当前只有 `docs/PRD.md` 一个 PRD。若未来出现第二个 PRD 文件，以本文件为准，另一个必须标记为历史或被删除；不得并行维护两套需求。

**提案边界**：`docs/proposals/PRD_AMENDMENT_2026-11-04.md` 汇总了 AUDIO / `PRD-TTS-007` / VOICE-ASSET / MOTION / STORY / QA 的待批准变更。它**不是**本文件的一部分；批准前不构成需求，不得据此把实现标为 `PASS_VERIFIED`。

**冲突处理顺序**：

1. 最新确认的 PRD 决策优先；
2. PRD 优先于其他项目文档；
3. 项目文档优先于代码中的旧实现与注释；
4. 代码现状只能作为审计证据，不能反向定义产品需求；
5. 历史实验结果只能作为证据，不能自动升级为产品能力；
6. 不得自行恢复已被最新决策否定的旧方案；
7. 不确定的需求必须标记为 `OPEN_QUESTION`，不得擅自补充假设。

发现冲突时，必须记录：冲突位置、PRD 正确要求、当前实现差距、修改方案、验证方式。不得为了迁就旧代码修改 PRD 中已经确认的产品决策。

本文件不复制端口、版本号、模型路径等易漂移细节；这些只在上表对应文档维护一次，但**产品决策与验收标准必须以本文件为准**。

### 0.2 需求状态与证据规则

**需求状态（本文件 §23 与需求追踪矩阵唯一使用）**：

| 状态 | 判定标准 |
|---|---|
| `PASS_VERIFIED` | 在本机真实执行，有产物、哈希/ffprobe/日志/任务记录等可核验证据 |
| `IMPLEMENTED_NOT_VERIFIED` | 代码/配置/自动化测试已实现，但没有真实生产运行证据 |
| `PARTIAL` | 已实现一部分，或已有真实运行但存在明确限制/未闭环环节 |
| `NOT_IMPLEMENTED` | 没有实现，或只有规划/文档 |
| `BLOCKED` | 存在明确阻断条件，当前不可执行 |
| `OPEN_QUESTION` | 需求尚未明确，禁止用假设代替 |

**历史证据标签**（只用于旧报告/阶段表，不得用于需求矩阵）：

| 旧标签 | 映射 |
|---|---|
| `PASS_STATIC` | `IMPLEMENTED_NOT_VERIFIED` |
| `NOT_RUN` | `NOT_IMPLEMENTED`（若已有入口但未执行，在证据列注明） |
| `DEPRECATED` | 历史能力，不再作为需求状态 |
| `PASS_LIMITED` | 仅 `doctor` 诊断标签，不进入需求矩阵 |

规则：

1. 下载、安装、Mock、单测通过都不等于生产能力。
2. 任何没有文件或任务证据的值，只能是 `NOT_IMPLEMENTED` / `OPEN_QUESTION`；不得写成 `PASS_VERIFIED`。
3. 能力状态变化必须同时更新本文件 §21/§23 与对应证据路径。
4. 同一需求若只有部分证据，必须写 `PARTIAL`，并在“差距”列说明缺哪一段。
5. 需求编号一经分配不得复用；需求被删除时保留编号并标 `DEPRECATED`（历史），不得让编号指向新需求。

### 0.3 内容与产品的区分

Local-Drama-Studio 是**生产系统**；具体作品（诗词、人物、神话、历史题材）是系统中创建的**内容项目/期数**。

- 通用代码、配置、提示词模板、测试和产品文档不得把某一部作品写成产品默认内容或固定业务流程。
- 作品名可以出现在：项目实例数据、示例配置、测试夹具、集成测试、生产报告。
- 开发与集成测试统一使用短文本夹具 **「白日依山尽」**。它只用于验证“任意短文本可进入链路”，不代表产品内容方向。
- 现有代码中仍存在写死作品名的地方（见 §21、§22），属于必须修复的基线缺陷，不是产品设计。

### 0.4 需求编号与验收入口

需求编号格式：`PRD-<域>-<三位序号>`。域包括 `GOV`（治理）、`TTS`（语音）、`STYLE`（视觉风格）、`QUAL`（质量）、`UX`（工作台）、`CASE`（案例）。

完整需求、验收标准、Phase A 审计映射与当前状态见：

- [REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md) — 需求追踪矩阵
- [PRD_CHANGELOG.md](PRD_CHANGELOG.md) — 2026-11-04 变更记录与冲突修正

核心需求摘要（完整矩阵以追踪文件为准）：

| 编号 | 需求 | 验收要点 |
|---|---|---|
| `PRD-GOV-001` | PRD 是唯一 SSOT；冲突按 §0.1 处理 | 其他文档不得创造/覆盖需求；冲突有记录与修正 |
| `PRD-GOV-002` | 需求状态必须由证据决定 | 无真实证据不得 `PASS_VERIFIED`；Mock/单测不等于端到端 |
| `PRD-TTS-001` | **默认调用 CosyVoice2-0.5B zero-shot** | 默认配置/默认任务实际加载 0.5B；manifest 记录 `zero_shot/CosyVoice2` |
| `PRD-TTS-002` | 300M SFT 仅显式可选，不能作为默认 | 必须显式 `tts_mode=sft` + `-Model sft`；任务/manifest 可追溯 |
| `PRD-TTS-003` | 模型/服务/参数不满足时明确报错，禁止静默回退 | 0.5B 缺失/加载失败/参考音缺失 → 失败；不得回退 300M |
| `PRD-TTS-004` | UI/任务/配置/日志/manifest/报告记录实际模型与模式 | `tts_mode/model_class/model_dir/speaker_id/prompt` 可查 |
| `PRD-TTS-005` | zero-shot 必须有参考音频与逐字参考文本 | 缺失即失败；参考音哈希写入 manifest |
| `PRD-STYLE-001` | 每篇作品只能选择一个主视觉风格 | 作品级 `style_id` 唯一；全片不混用 |
| `PRD-STYLE-002` | 风格贯穿剧本、镜头、资产、任务、质量检查 | 每层可追溯到同一 `style_id/style_sha256` |
| `PRD-STYLE-003` | 生成任务不得自行覆盖/切换作品风格 | 任务参数不能改风格；改风格走新版本 |
| `PRD-STYLE-004` | 改风格必须创建新生产/风格版本，不覆盖历史 | 旧构建/旧 manifest 不变 |
| `PRD-STYLE-005` | 两种风格有独立规范、提示词、参数、质量评价 | `config/styles.yaml` 两套 profile；不按 style 写代码分支 |
| `PRD-STYLE-006` | 两种风格分别完成技术生产验证 | 每种风格有真实样片 + 质量证据 |
| `PRD-STYLE-007` | 同一作品跨镜头风格一致性单独验证 | 有跨镜头一致性检查/人工结论；不能用两张图代替 |
| `PRD-QUAL-001` | 静态质量门必须可执行、不可静默绕过 | 动图前有 `static_quality.json`；缺失时失败或显式跳过 |
| `PRD-QUAL-002` | 质量门要区分技术/美学/人工 | 技术 PASS 不等于内容通过 |
| `PRD-UX-001` | 工作台不得展示过期能力或暗示未实现功能 | 节点/按钮与真实任务注册表/产物一致 |
| `PRD-CASE-001` | 81.373 s 工笔为已验证生产案例，路径为 scroll_shot | 1080×1920 / 13 段 / 18 句 / quality+verification PASS；不得写成 motion.plan |
| `PRD-GOV-003` | 历史证据路径缺失必须如实标注 | 不伪造路径；报告保留；替代证据可查 |

---

## 1. 产品定位

Local-Drama-Studio 是一个**本地化、自动化、可管理的东方视觉短视频内容生产系统**。

它面向抖音、小红书等竖屏短视频平台，把“选题/原文 → 结构化内容 → 分镜 → 视觉素材 → 配音/字幕 → 成片 → 人工审核 → 发布记录”组织成可追踪、可恢复、可复用的生产流程。

产品本体由四部分组成：

1. **生产状态与数据契约**：项目、期数、内容包、分镜、资产、任务、成片的事实来源。
2. **调度与质量门**：任务注册、单飞锁、日志、失败记录、技术校验。
3. **本地生成能力编排**：ComfyUI（FLUX/Wan）、CosyVoice、本地 LLM、FFmpeg。
4. **本地生产工作台**：只读派生真实状态，并提供受限的真实任务入口。

产品不是：某个模型的封装、某个 ComfyUI 工作流的集合、某一首诗词的专用工程、自动发布/涨粉工具。

---

## 2. 产品目标

| 编号 | 目标 | 可验证结果 |
|---|---|---|
| G1 | 一条内容从原文走到可发布 MP4 | 存在成片、构建 manifest、ffprobe/解码通过 |
| G2 | 状态可信 | 每个进度值都能追到文件或任务记录；无证据即 `NOT_RUN` |
| G3 | 内容实例相互隔离 | 新项目/期数不改代码、不覆盖历史产物 |
| G4 | 失败可定位、可恢复 | 任务日志、退出码、失败原因、重跑不改写旧成片 |
| G5 | 成本和时间可预期 | 每期记录生成耗时、模型、参数、成本 |
| G6 | 质量门可执行 | 技术检查与人工审核分开记录，技术通过不等于内容通过 |

目标不是账号增长、市场验证、自动发布或商业转化。

---

## 3. 用户与使用场景

| 项 | 约定 |
|---|---|
| 用户 | 单人创作者或 2-3 人小团队 |
| 环境 | Windows 11 + Intel Arc A750 8 GB + 64 GB RAM 的本地工作站 |
| 使用节奏 | 夜间批量生成，白天人工审核与发布 |
| 操作方式 | 浏览器工作台为主，CLI/脚本为正式补充入口 |
| 并发 | 单用户；同一时间只允许一个 GPU 生成任务 |
| 网络 | 本地回环为主；不做公网部署、多用户权限、远程访问 |

典型场景：

1. 新建一个内容项目，创建第 N 期，绑定原文与产物目录。
2. 运行文学分析（可选），得到候选 claim 与内容包草稿。
3. 人工确认内容后，生成旁白、分镜、静帧、少量英雄镜头。
4. 合成竖屏成片，做技术检查与人工看片。
5. 记录发布包装与发布结果；本期产物永久保留。

---

## 4. 系统边界

### 4.1 系统负责

- 项目/期数/风格/任务等业务事实的持久化。
- 内容结构与生产状态的派生、校验、追溯。
- 本地生成服务的调用编排、生命周期约束、失败记录。
- 音频、字幕、时间轴与视频合成。
- 本地工作台与受限任务入口。

### 4.2 系统不负责

- 训练/微调模型；实现 ComfyUI、CosyVoice、llama.cpp 内部逻辑。
- 公网服务、账号体系、多租户、权限系统。
- 平台自动发布、自动抓取平台数据、自动涨粉。
- 电影级人物一致性、口型同步、数字人。

### 4.3 外部依赖与端口

| 依赖 | 职责 | 端口 | 约束 |
|---|---|---|---|
| ComfyUI | 图像/视频生成 | 8188 | 仅生成引擎，不存业务状态 |
| 本地 LLM（llama.cpp） | 文学分析/文本任务 | 8080 | 单端口、单实例；谁启动谁停止 |
| CosyVoice | 语音合成 | 50000 | CPU 推理；不复用其他项目环境 |
| FFmpeg | 合成/转码/探测 | — | 唯一合成工具 |
| 本地工作台 | 状态与任务 | 8765 | 仅 127.0.0.1，不占用模型端口 |

硬约束：根 `.venv` 不安装 torch；生成环境在 `runtime/ComfyUI/.venv`；模型权重在 `D:\AI\models`，不复制进仓库。

### 4.4 单一事实来源

| 对象 | 权威来源 | 说明 |
|---|---|---|
| 项目、期数、风格、任务 | `projects/workspace.db` | 用户创建的事实；任务只追加 |
| 生产步骤状态 | 真实文件 + manifest + 哈希/ffprobe | 每次请求实时派生，不落库 |
| 一次构建 | `build_manifest.json` | 输入、字体、输出、哈希、解码结果 |
| 文学证据 | `literary_intelligence/corpus/<corpus>/` | 原文、来源、claims、reviews |
| 风格在某期的取值 | `episodes.style_snapshot` | 绑定时冻结，不随全局风格变化 |

`[PRD-DATA-001]` 生产数据契约必须明确、单一：当前生产使用 `ProductionScript` 与 `segments.json`/`audio_manifest.json`/`build_manifest.json`；`models.Storyboard` 仅测试使用，不得被当成生产契约。

本文件明确：**当前不采用** `projects/<project>/state.db` 方案，也不使用未被写入的 `ProjectManifest` 作为状态来源。二者属于早期设计，未实现且与工作台数据模型冲突；在出现明确需求前不再建设第二套状态库。

---

## 5. 核心功能

| 能力域 | 产品要求 | 当前状态（详见 §21） |
|---|---|---|
| 项目管理 | 创建/读取/更新项目；项目不绑定单一作品 | `PASS_STATIC`（CRUD 测试通过；自动种子已移除，测试使用短文本夹具） |
| 期数管理 | 每期有稳定 ID、编号、轨道、产物目录；状态派生 | `PASS_VERIFIED`（读取与派生）；创建为 `PASS_STATIC` |
| 原文管理 | 原文、来源、版本、定位、哈希可追溯 | `PARTIAL`（仅文学语料有登记；视频期数无独立来源文件） |
| 文学分析 | 五轮分析、证据校验、候选 claim、人工审核 | `PARTIAL`（真实 LLM 跑通；0 approved；无人工审核） |
| 内容包 | 结构化 `ContentPackage`，可转为生产输入 | `PASS_VERIFIED`（真实构建 + Adapter） |
| 文案 | 生成并保存现代文案/解说 | `PASS_VERIFIED`（LLM 生成、严格 Schema、可编辑 JSON） |
| 分镜 | 生成并保存镜头表/分段 | `PASS_VERIFIED`（4 镜头，绑定台词与风格 prompt） |
| 风格管理 | 风格实体、快照、引用、漂移提示 | `PASS_VERIFIED`（快照进入生成 prompt） |
| 图片生成 | FLUX 文生图/参考图编辑，记录参数与哈希 | `PASS_VERIFIED`（脚本链路） |
| 视频生成 | Wan I2V/T2V，记录参数与哈希 | `PASS_VERIFIED`（推近类）；精确位移 `PARTIAL` |
| 配音 | 逐句 TTS、48 kHz、清单哈希；默认 0.5B zero-shot，SFT 显式可选 | `PASS_VERIFIED`（默认 zero-shot 2 行 + 显式 SFT 1 行 PASS；多音色档案为提案阶段） |
| 字幕 | SRT/ASS、整数毫秒时间轴、本地字体校验 | `PASS_VERIFIED`（字幕角色） |
| 视频合成 | 1080×1920 母版、混音、软/烧录字幕 | `PASS_VERIFIED` |
| 工作台 | 真实状态、受限任务、日志、媒体预览 | `PASS_VERIFIED`（API/服务器）；浏览器 E2E 仅报告级证据 |
| 素材管理 | 发现、预览、归属、引用状态 | `PASS_VERIFIED`（扫描/预览）；资产台账 `NOT_RUN` |
| 发布与数据 | 平台包装、发布记录、数据回收 | `NOT_RUN` |

---

## 6. 项目与期数管理

### 6.1 数据关系

```text
Project
  └── Episode（video | literary）
        ├── Source（原文/来源/定位）
        ├── ContentPackage（可选，文学轨道）
        ├── Narration（旁白行）
        ├── Storyboard / segments（分段与镜头）
        ├── StyleSnapshot（绑定时冻结）
        ├── Assets（图片/视频/音频/字幕/字体）
        ├── Tasks（真实执行记录）
        └── Renders（每次构建一个独立目录）
```

### 6.2 要求

1. `Project.id`、`Episode.id` 一旦创建不可变；期数编号在同一项目内唯一。
2. 期数必须声明 `track`（`video` 或 `literary`）。轨道决定派生规则，不允许前端临时猜测。
3. 进入生产的期数必须绑定 `artifact_root`（仓库相对真实目录）；未绑定时所有生产步骤为 `NOT_RUN`。
4. 期数绑定风格时写入 `style_snapshot`；全局风格后续修改不得改变历史期数。
5. 期数状态只能由真实文件派生：`draft / ready / producing / completed / failed` 及对应中文标签。
6. 删除、归档、重命名产物目录不属于当前能力；不提供破坏性入口。

### 6.3 当前实现

- `projects/workspace.db` 的 `projects` / `episodes` / `styles` / `tasks` 四表已实现，WAL、外键、唯一约束、单飞索引均生效。
- 系统启动时**不会**自动导入任何内容；新克隆首次打开为空状态。本机 `workspace.db` 中已有的记录属于历史导入数据，不是产品默认内容，也不会在其他机器上重建。
- 早期文档中的 `projects/<id>/state.db` 与 `ProjectManifest` 未实现，且没有写入方；在 PRD 中不作为权威模型。

---

## 7. 内容生产流程

### 7.1 标准流程（14 步）

| # | 步骤 | 输入 | 输出 | 人工门 | 当前状态 |
|---|---|---|---|---|---|
| 1 | 选题/原文 | 用户输入 | 原文文件、来源登记 | — | `PARTIAL` |
| 2 | 文本规范化 | 原文 | 规范化文本、字符映射 | — | `PARTIAL`（仅文学语料） |
| 3 | 文学分析（可选） | 语料、claims | 五轮运行记录、候选 claim | 人工审核 | `PARTIAL` |
| 4 | 内容包 | 分析结果、定位 | `ContentPackage` | — | `PASS_VERIFIED`（4 场景） |
| 5 | 文案/解说 | 内容包/原文 | 旁白行文本 | 人工确认 | `PASS_VERIFIED`（4 行） |
| 6 | 分镜/分段 | 文案、风格 | `segments.json` | H2 关键帧前 | `PASS_VERIFIED`（4 镜头） |
| 7 | 风格快照 | 风格实体 | 期数内冻结风格 | — | `PASS_VERIFIED`（进入 4 个 prompt） |
| 8 | 静帧生成 | 提示词、参考图 | PNG + 参数/hash | H2 | `PASS_VERIFIED`（4/4 FLUX） |
| 9 | 英雄镜头 | 静帧 | Wan MP4 | — | `PASS_VERIFIED`（推近类） |
| 10 | 配音 | 旁白行 | WAV + `audio_manifest.json` | — | `PASS_VERIFIED`（女声 4 行） |
| 11 | 字幕/时间轴 | 配音与文本 | SRT/ASS/`timeline.json` | — | `PASS_VERIFIED` |
| 12 | 合成 | 分段 + 音频 + 字幕 | MP4 + `build_manifest.json` | — | `PASS_VERIFIED` |
| 13 | 技术/内容检查 | 成片 | 检查记录 | H3 | `PASS_VERIFIED`（技术）；人工 H3 `NOT_RUN` |
| 14 | 发布记录 | 成片、平台包装 | 发布记录 | H4/H5 | `NOT_RUN` |

### 7.2 顺序约束

1. 先出全部静帧并人工确认，再批量生成视频；不允许先烧掉最贵的视频算力。
2. 配音在视频之后、合成之前；时间轴由实际音频时长决定。
3. 每个镜头/分段独立成任务；失败只重跑该单元。
4. 生成并发固定为 1；LLM、FLUX、Wan 不同时占用 8 GB 显存。
5. Wan 分辨率必须能被 32 整除；默认 73 帧；20 步；不使用 Wan 承担精确主体位移。

### 7.3 内容实例化要求

新增一期内容必须只通过数据与配置完成：

- 不修改 `src/drama_studio/` 通用代码；
- 不复制工作流 JSON；
- 不把作品名、作者名、诗词句子写进通用提示词或代码分支；
- 只提供原文、来源、风格、分段、旁白、音色等实例数据。

现有代码尚未完全满足（见 §21），这是基线修复项，不是流程设计。

---

## 8. Literary Intelligence 的定位与边界

### 8.1 定位

Literary Intelligence（LI）是可选的**文学证据链与内容包前置能力**，用于古典文本的原文核验、候选解释生成、证据校验和内容包草稿。它服务于内容生产，但不是生产链路的必经步骤。

### 8.2 五轮角色

| 轮次 | 职责 | 程序级约束 |
|---|---|---|
| text_analyst | 目标句的文本观察 | 必须覆盖 target；目标 claim 的 locator/scope 必须匹配；目标不可分析时 `coverage=not_analyzable` |
| literary_analyst | 修辞、意象、情感候选 | 不得把解释写成唯一结论；非目标句必须 `scope=contextual` |
| researcher | 可验证来源/典故 | 不得输出原文 claim、不得回显已有 claim、不得伪造 source_id；无新增来源时 `claims=[]` + `no_source_found` |
| skeptic | 审查当前候选风险 | 只能引用本轮 `current_claim_ids`；必须给结构化 finding 或 `no_material_risk` |
| editor | 基于 approved claim 组织文案 | 无 approved claim 时 `draft_text` 必须为空 |

### 8.3 边界

1. LLM 输出永远只能是 `unreviewed`；LLM 不能自我批准。
2. 只有人工审核 + 有效证据才可 `approved`。
3. 引文必须存在于规范化原文；`source_quote` 必须存在于原始文本；locator 必须是已登记段落。
4. LI 不直接写视频生产输入；必须先产出 `ContentPackage`，再由 Adapter 转为 `segments.json` / `audio_manifest.json`。
5. LI 不进行默认外网检索；只使用已登记来源。外部检索属于独立、可审计的后续能力。
6. 作品名/作者名必须来自语料登记，不得写死在通用提示词合同里。

### 8.4 当前状态

- 真实本地 LLM 五轮已在 5 个运行目录中执行；其中三次 5/5 通过证据校验，两次保留失败记录。
- 人工审核 `NOT_RUN`；`claims.json` 中 approved 数量为 0；editor 输出为空（设计如此）。
- `ContentPackage` 只有 Schema 与测试；未真实生成，未进入 R3。
- 通用提示词 `OUTPUT_CONTRACT` 仍写死了一部作品的名称与作者，属于基线缺陷。

---

## 9. 视觉风格管理

### 9.0 双核心视觉风格（2026-11-03 确立）

产品视觉方向收敛为两种核心美学，不再以增加风格数量为发展方向：

| id | 风格 | 定位 |
|---|---|---|
| `court_green_fine_line` | 宋代院体青绿工笔 | 绢本设色、结构清晰；以长卷横移与缓慢推近让静态画卷产生生命感 |
| `ink_wash` | 东方写意水墨 | 生宣纸本、墨分五色；以墨迹渗染、留白与局部微动表现气韵 |

1. 两种风格共享同一套生产系统；差异只体现在 `config/styles.yaml` 的配置项，不建设两套架构。
2. 风格 id 稳定；作品通过配置选择风格，不改业务代码，不在代码中按风格分支。
3. 规范、配置边界与动画/合成路线见 `docs/VISUAL_STYLE_SPEC.md`。
4. 规范与配置为 `IMPLEMENTED_NOT_VERIFIED`；每种风格已有 2 镜头技术样片（M7，`PASS_VERIFIED` 技术）；作品级风格锁定为 `IMPLEMENTED_NOT_VERIFIED`（revision/hash/任务拒绝覆盖）；跨镜头一致性为 `NOT_IMPLEMENTED`。M7 不等于完整作品一致性。
5. 风格配置层独有的 `motion` / `compositing` 字段不写入 `workspace.db`；工作台 `styles` 实体只保存共有字段。

### 9.1 风格实体

每个风格至少包含：名称、视觉语言、色板、光线、镜头语言、构图、人物设计、环境设计、正向/负向提示词、参考资产、画幅、适用内容类型、来源文件。双核心风格还可在配置层声明动画与合成要求（见 `docs/VISUAL_STYLE_SPEC.md` §4）。

### 9.2 要求

1. `[PRD-STYLE-001]` 每篇作品只能选择一个主视觉风格（青绿工笔 / 写意水墨）；全片不得混用。
2. `[PRD-STYLE-005]` 两种风格共享 FLUX/Wan/FFmpeg 基础设施，但拥有独立视觉规范、提示词策略、生成参数与质量评价标准；代码不得按 `style_id` 写分支。
3. `[PRD-STYLE-002]` 风格是作品级配置；期数、`ProductionScript`、镜头、视觉资产、生成任务与质量检查必须继承同一 `style_id`。
4. `[PRD-STYLE-003]` 生成任务不得自行覆盖或切换作品风格；如允许例外，必须有显式“新风格版本”入口并记录。
5. `[PRD-STYLE-004]` 修改作品风格必须创建新的风格版本或新的生产版本；不得覆盖旧构建、旧 manifest 或旧成片。
6. 期数绑定风格时冻结快照；修改全局风格不得改变历史期数。
7. 前端必须显示“当前全局风格”与“本期快照”的漂移状态。
8. 风格中的参考资产与来源文件必须真实存在；不得引用不存在的证据。
9. 生成链路必须从期数快照派生提示词，而不是从代码常量或某次实验目录读取。
10. `[PRD-STYLE-007]` 同一作品跨镜头风格一致性必须单独验证；2 张不同风格的测试图不能证明完整作品一致性。

### 9.3 当前状态（2026-11-04）

- 风格 CRUD、期数快照、漂移字段已实现并有测试：`IMPLEMENTED_NOT_VERIFIED`（需求 `PRD-STYLE-001/002` 的基础设施）。
- 工作台不自动导入作品或种子风格；双核心风格预设由 `config/styles.yaml` 显式导出，不自动写入数据库。
- 生成链路已消费风格：`script.generate` 把期数 `style_snapshot` 写成 `style_snapshot.json`，`script_engine` 将其拼入每个镜头的 `visual_prompt`；P1 的 4 张 FLUX 图片参数可追溯。
- `PRD-STYLE-001/002`：`PARTIAL`。期数和 `ProductionScript` 有 `style_id/style_sha256`，但镜头/资产没有独立 `style_id` 字段；`style_lock` 已锁定期数快照，`comfy.batch` 仍未按 episode 校验。
- `PRD-STYLE-003/004`：`IMPLEMENTED_NOT_VERIFIED`。`style_locked` 拒绝任务级不同 style 覆盖；改风格 revision+1 并保留旧 sha/history；旧 build 目录不覆盖。真实改版任务与 UI 入口待补。
- `PRD-STYLE-005`：`IMPLEMENTED_NOT_VERIFIED`。`config/styles.yaml` 两套 profile + 严格校验/测试；尚未完成完整作品验证。
- `PRD-STYLE-006`：`PASS_VERIFIED`（技术样片）。M7 水墨 10.087 s、工笔 9.583 s；quality/audio QA PASS；人工审片记录在 M7 报告。
- `PRD-STYLE-007`：`NOT_IMPLEMENTED`。只有相邻镜头 LAB/亮度连续性指标，没有跨镜头风格一致性门或完整作品验证。
- 81.373 s 工笔是较长生产案例，但实现为 `scroll_shot.py` + 预渲染 clips，不是 `motion.plan` 自动运动；不能替代 `PRD-STYLE-006/007` 的完整验证。

---

## 10. 媒体生成

### 10.1 图片

- 引擎：ComfyUI + FLUX.2 klein 4B（GGUF Q4_K_M）。
- 工作流：API 格式；占位符按 JSON 树遍历替换，保持数值类型。
- 参数：提示词、负向提示词、seed、宽高、步数、CFG、参考图。
- 溯源：每次生成记录 prompt、seed、模型/工作流哈希、耗时、显存、输出哈希。

### 10.2 视频

- 引擎：ComfyUI + Wan2.2 TI2V 5B（GGUF Q4_K_M）。
- 工作流：T2V / I2V；`Wan22ImageToVideoLatent`、`ModelSamplingSD3(shift=8)`、`uni_pc/simple`、CFG 5、20 步。
- 分辨率必须除以 32；默认 73 帧；121 帧有颜色漂移风险。
- Wan 只承担缓慢推近/轻微运动；精确主体位移不可依赖。

### 10.3 生成纪律

1. 同一时间只允许一个 GPU 生成任务。
2. 模型/节点/工作流升级后必须重跑对应验收，旧工作流重新登记。
3. 缓存键至少包含：工作流哈希、模型哈希、规范化参数、输入图哈希。
4. 生成失败保留日志；不得把 CPU 执行写成 GPU 执行，不得把下载写成推理成功。

### 10.4 当前状态

- FLUX 文生图与参考图编辑：`PASS_VERIFIED`（R1/R3-A）。
- Wan T2V/I2V：`PASS_VERIFIED`（R0/R2/R2-B/R3-A）；精确主体位移 `PARTIAL`（一次方向错误）。
- 工作台 `comfy.batch`：`PASS_VERIFIED`（4/4 FLUX 任务成功）。
- 人物跨镜头一致性：`NOT_RUN`。

---

## 11. 音频与字幕

### 11.1 配音

- `[PRD-TTS-001]` **默认模式：CosyVoice2-0.5B zero-shot**。默认任务/默认配置必须加载 0.5B；不得默认 300M SFT。
- `[PRD-TTS-002]` 300M SFT 保留为**显式可选**模式；必须由用户显式选择（CLI/任务/narration/config），并记录。
- `[PRD-TTS-003]` 模型权重、模型类型、推理接口、运行环境必须区分；服务/参数不满足时明确报错，**禁止静默回退**到 300M SFT。
- `[PRD-TTS-004]` UI、任务记录、配置、日志、`audio_manifest.json` 和最终生产报告必须记录实际 `tts_mode/model_class/model_dir/speaker_id/prompt`。
- `[PRD-TTS-005]` zero-shot 必须提供参考音频与逐字参考文本；参考音哈希写入 manifest；缺失即失败。
- 逐句合成，不整段合成；一行失败只重跑一行。
- CosyVoice 输出统一重采样为 48 kHz 单声道。
- 每行记录文本、文件、时长、SHA-256、合成耗时。
- 音色必须来自已登记配置；不得在代码中写死某一期路径。

### 11.2 时间轴与字幕

- 所有内部时间使用**整数毫秒**。
- 开头静音只加一次；字幕不得早于对应语音，也不得包含开头静音。
- 时间轴、SRT、ASS 和混音必须来自同一份事件数据。
- 中文每行 ≤ 18 字，最多 2 行。
- 默认软字幕（SRT 封装）；烧录使用 ASS + libass。
- 字体必须来自本地字体清单，校验 SHA-256；构建时使用本地 `fontsdir` 并以 `fontselect` 日志拒绝静默回退。

### 11.3 当前状态（2026-11-04）

- 男声/女声 SFT 历史成片：`PASS_VERIFIED`（R3-B 中文男；P1/81.373 中文女）。
- 显式 zero-shot（CosyVoice2-0.5B）：`PASS_VERIFIED`（2026-11-04 真实 2 行；manifest 记录 `zero_shot/CosyVoice2/0.5B/prompt/voice_cast`）。
- **默认 0.5B zero-shot（PRD-TTS-001）：`PASS_VERIFIED`**。2026-11-04 生产配置默认 `tts.mode: zero_shot`，未加 `--tts-mode` 的真实任务加载 `CosyVoice2-0.5B`，manifest 记录 `zero_shot/CosyVoice2/0.5B/prompt`；SFT 仍需显式选择。
- 禁止静默回退（PRD-TTS-003）：`PASS_VERIFIED`；SFT↔zero-shot 双向错配均被拒绝，真实 1 行验证。
- 参考音/参考文本要求（PRD-TTS-005）：`IMPLEMENTED_NOT_VERIFIED`（单测覆盖缺失即失败；真实服务缺失路径待复验）。
- 字幕/时间轴/字体校验：`PASS_VERIFIED`（字幕角色）。
- 工作台 `tts.synthesize`：`PASS_VERIFIED`（参数化 narration/out/manifest/speaker/speed/tts_mode）。
- BGM、音效、混音对照：`NOT_IMPLEMENTED`。
- 字体资产可复现：`PASS_VERIFIED`（`fetch_fonts.py` 重建/校验）。

---

## 12. 视频合成

### 12.1 要求

1. 输入必须是显式的 `segments.json` 与 `audio_manifest.json`，不猜测参数。
2. 每期每次构建写入新目录：`projects/<project>/episodes/<episode>/renders/build-<time>/`。
3. 拒绝覆盖已有 `final_9x16.mp4`，除非显式允许重建。
4. manifest 必须记录：输入分段与哈希、字体来源与哈希、时间轴、输出路径与哈希、ffprobe 结果、全片解码退出码。
5. 母版 1080×1920 / 24 fps / H.264 + AAC 48 kHz；放大使用 Lanczos，不冒充原生 1080p。
6. 合成完成后必须做全片解码检查；失败即任务失败。

### 12.2 当前状态

- 历史 R3-B 成片：`PASS_VERIFIED`（38.042 s / 1080×1920 / 解码 0），但其 manifest 是旧版字段，缺少 `content_type/timeline/font`，系统标记为 `legacy`。
- 工作台重建：`PASS_VERIFIED`（`build-20261103-074757`，`content_type=narration`，字体 `SourceHanSansCN-Regular`，解码 0，哈希一致）。
- P1 端到端：`PASS_VERIFIED`（`build-20261103-114226`：14.0 s / 1080×1920 / 4 段 / 4 行女声 / 字幕 / quality PASS）。
- 构建脚本仍默认指向单一实验目录；作为通用入口时必须显式传参（工作台已这样做）。

---

## 13. 工作台与任务管理

### 13.1 产品要求

1. 本地单用户，监听 `127.0.0.1:8765`；不做公网、多用户、权限。
2. `[PRD-UX-001]` 页面只展示从真实文件/任务记录派生的状态；不得用固定进度、过期文案或假数据填充。
3. 写入只允许：项目/期数/风格的 CRUD，以及任务注册表中的固定任务。
4. 不提供任意 shell、任意路径、任意命令；所有任务参数必须经过 Pydantic 校验。
5. 同一 `lock_key` 同时只允许一个 RUNNING 任务。
6. 每个任务必须有：状态、参数、日志路径、开始/结束时间、退出码、失败原因。
7. 任务日志可增量读取；页面刷新后能恢复任务上下文。
8. 媒体读取必须限制在允许目录内；支持 HTTP Range 与缩略图。

### 13.2 任务注册表

| 任务 | 作用 | 要求 | 当前状态 |
|---|---|---|---|
| `doctor.run` | 环境诊断 | 只读 | `PASS_VERIFIED` |
| `build.rebuild` | 用真实分段/音频重新合成 | 新目录、不覆盖 | `PASS_VERIFIED` |
| `package.build` | 语料 → ContentPackage | 证据校验 | `PASS_VERIFIED` |
| `script.generate` | ContentPackage + 风格 → 文案/分镜 + jobs | 8080 单实例、严格 Schema | `PASS_VERIFIED` |
| `segments.build` | 分镜 + 图片 + 音频 → segments.json | 缺图/缺音频失败 | `PASS_VERIFIED` |
| `quality.check` | 独立技术检查 | 只读产物 | `PASS_VERIFIED` |
| `comfy.batch` | 执行 `experiments/` 或 `projects/` 下 jobs | 8188 在线、GPU 单飞 | `PASS_VERIFIED` |
| `li.run` | 运行 LI 五轮 | 8080 单实例、输出新目录 | `NOT_RUN`（已注册未触发） |
| `service.comfy.start` | 启动 ComfyUI | 复用既有脚本 | `NOT_RUN`（已注册） |
| `service.comfy.stop` | 停止 ComfyUI | 只停项目进程树 | `NOT_RUN`（已注册） |
| `tts.synthesize` | 逐句配音 | 参数化 narration/out/manifest/speaker/speed | `PASS_VERIFIED` |
| `review.accept` / `review.reject` | 记录人工验收 | 写 `human_review.json` | `PASS_VERIFIED` |

### 13.3 状态派生

- 期数进度只按“必需步骤中 `PASS_VERIFIED`”计算；`PARTIAL` 不计入完成。
- 合成完成但无人工验收时，状态可以是“已成片”，但“人工验收”必须为 `NOT_RUN`。
- 任何派生失败（文件损坏、哈希不一致、manifest 缺失）必须显示 `FAILED`/`PARTIAL`，不得降级为成功。

---

## 14. 素材与版本管理

### 14.1 素材

1. 素材必须有稳定路径、类型、大小、mtime、SHA-256（按需计算）。
2. 能绑定到期数时必须绑定；无法绑定的素材不得伪造归属。
3. 必须区分正式资产与临时中间产物（帧序列、concat、raw/faded 视频等）。
4. 素材库只读；不提供删除/移动入口，避免误删历史证据。
5. 缩略图与 Range 读取必须经过路径白名单。

### 14.2 版本

1. 每次构建写入独立目录，历史构建只增不改。
2. 风格快照在期数绑定时冻结。
3. 任务记录只追加，不更新历史状态（当前实现会更新状态字段，但必须保留最终记录与日志）。
4. 当前没有统一的“文案/分镜/素材版本号”；版本能力属于 `PARTIAL`，需要后续数据结构支持，不能只靠目录名。

### 14.3 当前状态

- 素材扫描、归属、引用标记、临时/正式分类、缩略图、Range：`PASS_VERIFIED`（实测 436 个正式资产、1219 个临时文件）。
- 资产台账（数据库级、可查询版本与来源）：`NOT_RUN`。
- 构建目录版本化：`PASS_VERIFIED`（不覆盖）。

---

## 15. 版权与来源追踪

### 15.1 要求

1. 原文必须有来源登记：作品、作者、版本、URL/出处、获取日期、许可证、商用状态、定位、哈希。
2. 字体必须有来源、许可证、SHA-256；构建使用本地文件，不依赖系统字体。
3. 模型必须记录来源、版本、许可证；许可证未确认不得商用发布。
4. 音乐/音效必须逐条登记：来源、作者、许可证、下载日期、哈希、署名要求。
5. 生成内容必须按平台规则标识 AI 参与。
6. 发布前把所有资产汇总到授权台账；缺一项即不得发布。
7. `[PRD-TTS-006]` CosyVoice 参考音、模型权重、预置音色与生成音频的商用授权必须单独核验；代码许可证不等于音色/输出可商用。

### 15.2 当前状态

- 文学作品来源登记：`PARTIAL`（已有真实来源、哈希、许可证字段；只有一部语料；古籍公有领域与转录 CC BY-SA 义务需分别处理）。
- 字体：来源/许可/哈希/预览已验证；6 个 OTF 与 LICENSE 存在于本地，但整个 `assets/fonts/` 被 `.gitignore` 排除。
- 模型：版本与许可证已登记在 `TECH_STACK` / 授权台账；Wan 文本编码器的底层许可仍标注“待复核”。
- CosyVoice 模型权重、预置音色、生成音频的商用条款：`UNVERIFIED`；不得因代码 Apache-2.0 推断可商用。
- BGM/音效：`NOT_RUN`，未选型、未登记。
- 平台 AI 标识字段：仅文档要求，未进入生产 manifest。

---

## 16. 环境与资源管理

1. 两套 Python 环境不得合并；根 `.venv` 不装 torch。
2. 模型仓库唯一为 `D:\AI\models`；顶层 GGUF 不得移动；新增编码器/VAE 放子目录。
3. 本地 LLM 只使用 8080，同一时间只允许一个实例；“谁启动，谁停止”。
4. ComfyUI 8188、CosyVoice 50000、工作台 8765；不得新增第二个模型端口。
5. GPU 租户互斥：LLM（GPU 模式）、FLUX、Wan 不得并行；CPU-only LLM 仍占用约 19 GB 内存，与生成任务错峰。
6. 生成前必须检查端口与显存状态；发现冲突拒绝执行，不抢占别人的进程。
7. 不升级 ComfyUI/torch/节点/模型而不重跑验收；不引入无明确用途的框架。
8. 本地探测必须绕过系统代理（Python `trust_env=False`，PowerShell `curl.exe`）。
9. `[PRD-CONFIG-001]` 配置字段必须有效或明确标注为未接线；不得保留“看起来能改但无效”的字段。

当前环境事实（2026-11-03 本轮结束）：8080 空闲。此前曾有一个带 `--api-key` 的外部 llama-server 占用 8080，项目的 `sk-local` 请求返回 401；本轮未操作该进程，它已自行停止。8188/50000 本轮结束时未监听；8765 未探测。若 8080 再次被外部实例占用，必须记录并让路，不得终止他人进程。

---

## 17. 质量要求

### 17.1 技术质量（自动）

| 产物 | 最低检查 |
|---|---|
| 图片 | 可解码；尺寸符合预期；非全黑/全白；文件非空 |
| 视频 | ffprobe 时长/帧率/分辨率；全片解码无错误；轨道存在 |
| 音频 | 可解码；采样率/声道符合；不削波 |
| 成片 | 1080×1920；音画轨存在；字幕可解析；时长与目标偏差 ≤ 10% |
| 构建 | manifest 哈希与产物一致；字体 `fontselect` 命中；构建目录不覆盖 |

- `[PRD-QUAL-001]` 静态质量门必须可执行、不可静默绕过：动图前必须有 `static_quality.json`，缺失时失败或显式跳过。
- `[PRD-QUAL-002]` 技术检查、美学风险与人工结论必须分开记录；技术 PASS 不等于内容通过。

### 17.2 内容质量（人工）

| 门 | 时机 | 判定 |
|---|---|---|
| H1 | 人物/定妆资产后 | 角色可辨认、服装/气质连续（无人物题材可跳过） |
| H2 | 批量视频前 | 构图、主体、场景、动作方向符合分镜 |
| H3 | 成片后 | 节奏、字幕、音量、整体可看性 |
| H4 | 发布前 | 封面、标题、正文、话题、AI 标识 |
| H5 | 发布后 | 链接、时间、初始数据记录 |

技术通过不等于内容通过。人工结论必须与自动检查分开记录。

### 17.3 当前状态

- 合成脚本内已有 ffprobe、全片解码、哈希校验、字体校验：`PASS_VERIFIED`。
- 独立质量模块（空图/黑帧、音频峰值、视频解码/分辨率、成片哈希）：`PASS_VERIFIED`（P1 `quality.check`）。
- 人工验收写入：`PASS_VERIFIED`（`review.accept/reject` + `human_review.json`）。
- 素材库与工作台能显示“无人工验收记录”，不会伪造通过。

---

## 18. 异常与恢复

1. 自动重试上限 2 次，退避 30/90 秒；禁止无限循环。
2. 超时即失败；超时阈值来自配置；失败保留 stdout/stderr 与退出码。
3. 不静默覆盖有效产物；重建必须写新目录。
4. 任务中断后，服务重启时必须把遗留 `RUNNING` 标记为 `FAILED` 并说明原因（已实现）。
5. 取消必须真正终止子进程；当前 PENDING→RUNNING 的取消存在竞态，属于必须修复项。
6. 断点续跑以真实产物为准：已存在且哈希一致的单元可复用；不得靠“文件存在”猜测完成。
7. 模型 OOM/加载失败不得自动降级分辨率后冒充成功；必须记录并转人工决定。
8. 直接运行脚本绕过了工作台单飞锁；正式生产要求统一走任务入口，或在脚本侧增加同等锁。

---

## 19. 非目标

v1.x 明确不做：

- 自动发布、自动账号运营、自动涨粉、自动数据抓取。
- 公网部署、多用户、权限、计费、远程协作。
- 数字人、口型同步、复杂人物动画、跨镜头像素级同脸。
- 原生 1080p 视频生成、SeedVR2、新视频模型、多模型并行生产。
- Remotion、复杂 Agent 框架、向量数据库、无明确用途的新框架。
- 商品转化、商业投放系统。
- 把单条样片或单次数据当作市场结论。

---

## 20. 验收标准

### 20.1 产品级验收

| 编号 | 验收项 | 通过条件 |
|---|---|---|
| AC-01 | 任意短文本可建期 | 用「白日依山尽」创建项目/期数，不改代码、不依赖现有作品数据 |
| AC-02 | 完整链路 | 从原文到 1080×1920 MP4：3-5 个分段、≥1 段配音、字幕、构建 manifest |
| AC-03 | 状态可信 | 每个步骤状态都能追到文件/任务/哈希；无证据显示 `NOT_RUN` |
| AC-04 | 不覆盖历史 | 连续两次构建写入两个目录，旧成片哈希不变 |
| AC-05 | 失败可恢复 | 人为中断任务后，状态为 `FAILED`，日志保留；重跑不影响旧产物 |
| AC-06 | 任务安全 | 任意 shell/路径/未知任务被拒绝；同锁任务不能并发 |
| AC-07 | 内容与产品分离 | 通用代码、通用提示词、测试夹具中不出现具体作品名 |
| AC-08 | 可复现 | 干净克隆 + 文档步骤可安装依赖、获取字体/模型、运行测试与构建 |
| AC-09 | 质量门 | 技术检查与人工验收分别可记录；技术通过不自动等于内容通过 |
| AC-10 | 授权可查 | 成片涉及的原文/字体/模型/音色/音乐均有登记与许可状态 |

### 20.2 单项能力验收

每项能力必须同时具备：真实执行记录、产物路径、哈希或 ffprobe 证据、失败记录（如有）、对应测试。仅“页面可点”不算验收。

---

## 21. 当前真实完成状态（2026-11-04 更新）

> 证据基线：2026-11-04 工作区（HEAD `06f91e4` + 未提交 M8/声景/TTS 工作）。根测试与 LI 测试合并为一条命令，当前 **361 项通过**。历史 136/246 等数字是当时快照，不再作为当前基线。
> 本节保留历史证据标签（`PASS_STATIC`/`NOT_RUN` 等）；需求状态以 §0.4/§23 与追踪矩阵为准，映射见 §0.2。字体在隔离干净目录中由 `scripts/fetch_fonts.py` 重建并校验（6/6 OTF + 2 份 LICENSE），`load_font_config` 加载 6 个字面。

### 21.1 能力矩阵

| 能力 | 状态 | 证据 / 限制 |
|---|---|---|
| 单一状态模型（`projects/workspace.db`） | `PASS_VERIFIED` | `ProjectManifest`/`state.db`/示例项目配置已移除或标注非现状；API/测试使用同一模型 |
| 环境诊断 `drama doctor` | `PASS_VERIFIED` | `logs/doctor-*.json`；工作台 `doctor.run` 任务 SUCCEEDED |
| 项目/期数读取与状态派生 | `PASS_VERIFIED` | `workspace.db` + `discovery.py`；真实期数 100% / 12% 进度 |
| 项目/期数/风格创建与编辑 | `PASS_STATIC` | 136 项测试覆盖；真实 P1 期数由验收脚本创建 |
| 素材扫描/归属/引用/临时分类 | `PASS_VERIFIED` | 实测 436 正式 / 1219 临时；缩略图与 Range 测试通过 |
| 媒体 Range / 缩略图 / 路径白名单 | `PASS_VERIFIED` | `tests/test_workspace_media.py` + API 测试 |
| 工作台 API / 页面渲染 | `PASS_VERIFIED` | `logs/workspace-server.log`；API 测试 |
| 浏览器端到端（34 项） | `PARTIAL` | 仅交付报告记录，无脚本/截图产物入库，不可复跑 |
| 任务注册/执行/日志/单飞 | `PASS_VERIFIED` | `doctor.run`、`build.rebuild` 真实 SUCCEEDED |
| 任务取消 / 崩溃恢复 | `PASS_VERIFIED` | `mark_running` 条件迁移 + 取消测试 + 崩溃恢复测试 |
| 脚本级 GPU 单飞锁 | `PASS_VERIFIED` | `src/drama_studio/locks.py` + `r1_batch.py` + 锁测试 |
| 通用代码无作品硬编码 | `PASS_VERIFIED` | `tests/test_no_hardcoded_works.py` 扫描 `src`/`harness`/`schemas` 无命中 |
| 通用短文本测试夹具 | `PASS_VERIFIED` | 「白日依山尽」LI 语料夹具 + 合成期数夹具；测试不依赖真实实验资产 |
| 一条命令执行全部测试 | `PASS_VERIFIED` | `pytest` 361 passed（根 + LI，2026-11-04） |
| FLUX 16:9 / 竖屏静帧 | `PASS_VERIFIED` | R1/R3-A 产物与报告 |
| FLUX 参考图编辑 | `PASS_VERIFIED` | R1 |
| Wan I2V/T2V（推近类） | `PASS_VERIFIED` | R0/R2/R2-B/R3-A |
| Wan 精确主体位移 | `PARTIAL` | R2-B H3 方向错误 |
| 人物跨镜头一致性 | `NOT_RUN` | 未做人物测试 |
| 文案/分镜生成（LLM→ProductionScript） | `PASS_VERIFIED` | 真实 30B 生成 4 镜头/4 行；2 次尝试保留 raw；Schema 校验通过 |
| 风格驱动生成 | `PASS_VERIFIED` | 期数 style_snapshot 拼入 4 个 FLUX prompt；图片与 params 可追溯 |
| 双核心风格规范与配置（S1） | `PASS_STATIC` | `docs/VISUAL_STYLE_SPEC.md` + `config/styles.yaml` + `style_presets.py` + 测试 |
| 青绿工笔技术验证（S2-工笔） | `PARTIAL` | `experiments/s2a/renders/build-20261103-210443/`：20 s / 1080×1920 / 24 fps；技术检查通过，人工审美 PENDING |
| 写意水墨技术验证（S2-水墨） | `PARTIAL` | `experiments/s2b/renders/build-20261103-210408/`：20 s / 1080×1920 / 24 fps；技术检查通过，人工审美 PENDING |
| 双管线静态质量门 | `PARTIAL` | `scripts/static_quality.py`；IA4/A1 均过客观检查，山石纹理重复记录为 `PARTIAL` |
| 管线 A 水墨分层样片 | `PARTIAL` | `experiments/pipeline_a/renders/build-20261103-212100/`：20 s；云气 ±24 px、水面 ±4 px、孤舟 8 px；技术通过，人工 PENDING |
| 管线 B 工笔长卷样片 | `PARTIAL` | `experiments/pipeline_b/renders/build-20261103-212022/`：28 s / 30 px/s；技术通过，人工 PENDING |
| 双核心风格（S3 分解） | `PASS_STATIC` / `PASS_VERIFIED`（技术样片）/ `PARTIAL` / `NOT_RUN` | ① 两风格独立规范/配置 `PASS_STATIC`；② 各风格 2 镜头技术样片 `PASS_VERIFIED`（M7）；③ 作品级风格锁定 `IMPLEMENTED_NOT_VERIFIED`；跨镜头一致性正式验证 `NOT_RUN`。M7 不等于完整作品一致性。 |
| 男声逐句 TTS（真实成片） | `PASS_VERIFIED` | 7 行 WAV + manifest 哈希；R3-B |
| 女声本地 TTS | `PASS_VERIFIED` | P1 成片使用「中文女」4 行 WAV + manifest 哈希；商用条款仍 `UNVERIFIED` |
| 0.5B zero-shot 默认（PRD-TTS-001） | `PASS_VERIFIED` | 2026-11-04 默认配置真实 2 行 PASS；`voice_profile` 真实 2 行 PASS；manifest 记录 `zero_shot/CosyVoice2/0.5B/prompt/voice_cast`；SFT 显式可选 |
| SFT 显式可选（PRD-TTS-002） | `PASS_VERIFIED` | 真实 SFT 1 行 + 历史 P1/81.373；需显式 `-Model sft` + `tts_mode=sft` |
| 禁止静默回退（PRD-TTS-003） | `PASS_VERIFIED` | SFT↔zero-shot 双向错配均报错；无自动切换 |
| 81.373 s 工笔案例（PRD-CASE-001） | `PASS_VERIFIED` | 1080×1920 / 13 段 / 18 句；quality + verification PASS；scroll_shot 路径 |
| 工作台 TTS 任务 | `PASS_VERIFIED` | `task_20261103113817` 真实 4 行合成；参数化路径/音色/语速 |
| 字幕 SRT/ASS + 时间轴 | `PASS_VERIFIED` | 时间轴整数毫秒；字幕角色正式接入 |
| 本地字体校验与接入 | `PASS_VERIFIED` | 6 个 OTF、SHA-256、`fontselect` 命中 |
| 字体资产可复现 | `PASS_VERIFIED` | 隔离干净目录中 `fetch_fonts.py` 下载/解压/校验 6/6；manifest/LICENSE 可跟踪 |
| 视频合成 1080×1920 | `PASS_VERIFIED` | 历史 38.042 s + 工作台重建；manifest 哈希一致 |
| 人工验收写入 / 读取 | `PASS_VERIFIED` | `review.accept/reject` 任务 + `human_review.json` + 工作台按钮 + 测试 |
| LI 五轮真实 LLM | `PARTIAL` | 5 个运行目录；3 次 5/5 通过；失败记录保留；人工审核 `NOT_RUN` |
| LI 通用语料支持（代码/合同层） | `PASS_STATIC` | 第二套短文本语料夹具通过 61 项 LI 测试；未对其跑真实 LLM |
| LI 人工审核 / approved claim | `NOT_RUN` | 0 approved；`reviews.json` 为空 |
| ContentPackage 构建 | `PASS_VERIFIED` | `package.build` 真实生成 4 场景；claim 均过证据校验 |
| ContentPackage → R3 Adapter | `PASS_VERIFIED` | `segments.build` 4 段；图片/音频/哈希齐全 |
| 工作台 `li.run` | `NOT_RUN` | 已注册未触发；本轮未运行 LI 五轮 |
| 工作台 `comfy.batch` | `PASS_VERIFIED` | 4/4 FLUX 任务成功；耗时 76.6/59.0/44.7/16.1 s |
| 工作台服务启停 | `NOT_RUN` | 已注册未触发（本轮服务由验收脚本外部启动） |
| `package.build` 任务 | `PASS_VERIFIED` | 真实任务 SUCCEEDED；4 场景 |
| `script.generate` 任务 | `PASS_VERIFIED` | 真实 LLM 产物经 reuse 校验后 SUCCEEDED；raw 保留 |
| `segments.build` 任务 | `PASS_VERIFIED` | 真实 4 段 segments.json + meta |
| `quality.check` 任务 | `PASS_VERIFIED` | 图片 4/4、音频、成片、哈希全部 PASS |
| P1 端到端（3-5 分段） | `PASS_VERIFIED` | 14.0 s / 1080×1920 / 4 段 / 4 行女声 / quality PASS |
| BGM / 音效 | `NOT_RUN` | 未选型、未登记 |
| 平台包装 / 发布 / 数据 | `NOT_RUN` | 无实现 |
| 多期夜间批处理 | `NOT_RUN` | 无调度器 |
| 统一资产台账/版本号 | `NOT_RUN` | 只有目录扫描与构建目录 |

### 21.2 P0 缺陷修复状态

| 编号 | 缺陷 | P0 结果 |
|---|---|---|
| D-01 | 通用代码写死具体作品（种子、提示词合同、discovery 耦合） | 已修复：种子删除；提示词从来源登记注入；storyboard 提示词按输出 SHA-256 通用反查；防回归测试 |
| D-02 | `assets/fonts/` 被整体忽略，构建不可复现 | 已修复：只忽略 OTF；manifest/README/LICENSE 可跟踪；`fetch_fonts.py` 隔离验证通过 |
| D-03 | 人工验收没有写入口 | 已修复：`review.accept/reject` + `human_review.json` + UI + 测试 |
| D-04 | 任务取消 PENDING→RUNNING 竞态 | 已修复：条件状态迁移 + 启动前/后取消检查 + 测试 |
| D-05 | 直接运行 `r1_batch.py` 绕过单飞锁 | 已修复：跨进程文件锁 + 锁测试 |
| D-06 | 测试依赖真实作品/实验产物 | 已修复：短文本语料 + 合成期数夹具；API/派生/媒体测试全部用 tmp 根 |
| D-07 | 默认 pytest 不含 LI | 已修复：`testpaths` 覆盖两套；120 项一条命令 |
| D-08 | `r3_tts.py` / `r3_build.py` 默认绑定单一实验目录 | 已修复：TTS 参数化（narration/out/manifest/speaker/speed）；build 使用显式参数 |
| D-09 | `run_li15.py` 复制五轮循环 | 未修复（P1，属于重复实现清理） |
| D-10 | 8080 被带 API Key 的外部实例占用 | 外部环境，按本轮约束不处理；`li.run` 保持 `NOT_RUN` |
| D-11 | `ProjectManifest` / `state.db` / 示例项目配置无写入方 | 已修复：模型与示例配置删除；ARCHITECTURE/CLAUDE 更新为 workspace.db |
| D-12 | 文档状态口径不一致 | 已修复：PRD/README/TECH_STACK/ARCHITECTURE/CLAUDE/ROADMAP/工作流/授权台账对齐 |

### 21.3 已验证生产案例：81.373 s 青绿工笔

| 项 | 值 |
|---|---|
| 路径 | `projects/proj_chunjiang_gongbi/episodes/ep_chunjiang_gongbi_01/renders/build-20261103-161945/` |
| 分辨率 | 1080×1920 |
| 时长 | 81.373 s |
| 片段 | 13 段 |
| 配音 | 18 句 |
| 质量 | `quality_report.json` PASS；`verification_report.json` PASS |
| 哈希 | SHA-256 以 `build_manifest.json` / 实际文件为准（当前 `84628a06…`） |
| 实现路径 | **`scroll_shot.py` + 预渲染 clips**，不是 `motion.plan` 自动运动管线 |

该案例属于 `PRD-CASE-001`，是已验证生产能力；但它**不能**证明 `motion.plan` 自动运动、跨镜头风格一致性或完整短剧能力已经通过。

## 22. 后续实施优先级

> 原则：先修基线与数据契约，再补完整闭环；不在缺陷未修复时叠加新功能。
>
> **注意**：§22 保留历史实施批次与旧状态标签（`PASS_STATIC`/`NOT_RUN` 等），只作背景；当前需求状态以 §0.4 与 [REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md) 为准。TTS 默认已在 2026-11-04 改为 0.5B zero-shot，旧 P1-1“TTS 参数化”不再代表当前默认策略。

### P0 · 基线与可复现（本轮已完成；P1 从 P1-1 开始）

| 序 | 工作 | 验收 |
|---|---|---|
| P0-1 | 统一数据模型：确认 `workspace.db` 为项目/期数权威；退役或明确冻结 `state.db`/`ProjectManifest` | 文档与代码一致；无第二套状态写入 |
| P0-2 | 字体可复现：将字体、LICENSE、manifest 纳入版本控制，或提供带哈希的确定性获取步骤 | 干净克隆可运行 `test_fonts.py` 并完成一次构建 |
| P0-3 | 移除通用代码中的作品硬编码，迁至导入数据/语料/夹具 | `grep` 通用代码无具体作品名；新增内容不改代码 |
| P0-4 | 修正提示词合同：作品/作者/版本从来源登记注入 | 同一提示词可服务任意语料 |
| P0-5 | 增加「白日依山尽」短夹具，并让工作台测试不依赖真实实验资产 | 测试在干净环境全绿 |
| P0-6 | 补齐人工验收任务（或明确的 reviews 写入口） | 能记录 H3 通过/拒绝，并在期数状态中显示 |
| P0-7 | 修复任务取消竞态与直接脚本绕过单飞锁 | 取消后无残留进程；并发任务被拒绝 |
| P0-8 | 默认 pytest 纳入 LI 测试 | 一条命令运行全部 105 项测试 |
| P0-9 | 文档收束：ARCHITECTURE/README/TECH_STACK/CLAUDE/ROADMAP 状态口径统一 | 不再出现“不做后台/中文女未跑/依赖缺失”等过期表述 |

### P1 · 完成视频生产闭环（本轮已完成；P2 从 P2-1 开始）

| 序 | 工作 | 验收 |
|---|---|---|
| P1-1 | TTS 参数化（`tts.synthesize` 解除 BLOCKED） | 任意期数可用配置合成逐句 WAV + manifest |
| P1-2 | 文案与分镜生成（LLM → 严格 Schema → 可编辑） | 输入短文本可生成通过校验的文案/分段；失败保留原始输出 |
| P1-3 | 风格快照进入生成提示词 | 同一分段用不同风格生成不同提示词，且可追溯快照 |
| P1-4 | `comfy.batch` 任务真实执行一次（单张图/单段视频） | 任务 SUCCEEDED，产物与 manifest 可核验 |
| P1-5 | ContentPackage → `segments.json`/`audio_manifest.json` Adapter | 文学内容包可生成一次真实构建 |
| P1-6 | 独立技术质量检查（空图/黑帧/时长/音频峰值） | 不合格产物被标 `FAILED`，不进入成片 |

### P2 · 资产、音频与发布准备

| 序 | 工作 | 验收 |
|---|---|---|
| P2-1 | 资产台账（哈希、来源、期数归属、版本） | 任一成片可反查全部输入 |
| P2-2 | BGM/音效选型与授权登记 | 至少 1 首 BGM + 2 个音效有许可证据 |
| P2-3 | 女声商用授权核验（P1 已进入正式成片） | 许可状态不再是 `UNVERIFIED` |
| P2-4 | 平台包装与发布记录 | 一条作品有封面/标题/正文/话题/发布记录 |
| P2-5 | 统一结果清单与成本摘要 | 每期输出成功/降级/失败 + 耗时 |

### S · 双核心视觉风格（2026-11-03 立项；与 P2 并行，不重排 P2）

| 序 | 工作 | 验收 | 状态 |
|---|---|---|---|
| S1 | 两种风格写入正式规范与配置边界 | `docs/VISUAL_STYLE_SPEC.md`；`config/styles.yaml` 严格校验；不自动写入数据库 | `PASS_STATIC` |
| S2-工笔 | 工笔 15-30 秒长卷动态验证 | 绢本质感、青绿设色、线条细节、横移平稳、无拉伸/结构破坏；产物与证据入库 | `PARTIAL`（技术通过，人工待审） |
| S2-水墨 | 水墨 15-30 秒动态验证 | 墨色层次、宣纸质感、留白、自然渗染、局部动态不变形；产物与证据入库 | `PARTIAL`（技术通过，人工待审） |
| S2.1 | 双管线静态质量门 | 两套独立缺陷检查表；`static_quality.json` 有客观指标与人工结论 | `PARTIAL`（山石纹理重复） |
| S2.2 | 管线 A 云气/水面/孤舟分层验证 | 山体冻结；云气/水面/孤舟独立图层运动；纸纹克制 | `PARTIAL`（技术通过，人工待审） |
| S2.3 | 管线 B 更慢长卷样片 | 28 秒 / 30 px/s；线条、设色、结构稳定 | `PARTIAL`（技术通过，人工待审） |
| S3 | 双风格链路（分解） | ① 独立规范/配置；② 各风格技术样片；③ 作品级锁定 + 跨镜头一致性 | `PASS_STATIC` / `PASS_VERIFIED`（技术样片）/ `PARTIAL` / `NOT_RUN`（分别对应三项） |

约束：不新增模型/LoRA/依赖；不另起动画框架；Wan 只做局部动态；S2 未通过前不扩展成新的生产子系统。

### P3 · 批处理与扩展（v1.x 之后）

多期夜间调度、平台数据回收、人物一致性。启动前提：P0/P1 全部验收通过，且已有至少 2 期真实作品。

---

## 23. 需求追踪与状态汇总

完整矩阵（需求、验收、Phase A 审计映射、证据、差距、下一步）见 [REQUIREMENT_TRACEABILITY.md](REQUIREMENT_TRACEABILITY.md)。变更记录见 [PRD_CHANGELOG.md](PRD_CHANGELOG.md)。

当前状态汇总（2026-11-04）：

| 状态 | 需求 |
|---|---|
| `PASS_VERIFIED` | `PRD-TTS-001/002/003`、`PRD-STYLE-006`、`PRD-CASE-001` |
| `PARTIAL` | `PRD-GOV-002/003`、`PRD-TTS-004`（UI/任务/报告未全验）、`PRD-STYLE-001/002`、`PRD-QUAL-002`、`PRD-UX-001`、`PRD-DATA-001`、`PRD-CONFIG-001` |
| `IMPLEMENTED_NOT_VERIFIED` | `PRD-GOV-001`、`PRD-STYLE-003/004/005`、`PRD-TTS-005`、`PRD-QUAL-001` |
| `NOT_IMPLEMENTED` | `PRD-STYLE-007`（跨镜头一致性门） |
| `BLOCKED` | 无（当前无硬阻塞；TTS 默认切换是待执行任务，不是阻塞） |
| `OPEN_QUESTION` | `PRD-TTS-006`（参考音/模型权重的商用授权）、`PRD-OPS-001`（成本/批次是否进入 v1.0） |

**当前状态**：`PRD-TTS-001` 默认 0.5B zero-shot 已真实落地；`PRD-STYLE-003/004` 的锁与 revision 已实现（`IMPLEMENTED_NOT_VERIFIED`）；`PRD-QUAL-001` 静态门默认强制；下一步是真实改版生产、跨镜头一致性门与 `comfy.batch` 风格校验。

## 附：本文件明确不回答的问题

- 某部作品是否值得制作、如何改编。
- 某种画风是否受欢迎、账号能否增长。
- 具体模型/字体/音乐/音色的商业条款结论（属于授权台账与外部核验）。

这些问题只能由内容决策、真实发布数据和授权核验回答，不能由技术文档替代。
