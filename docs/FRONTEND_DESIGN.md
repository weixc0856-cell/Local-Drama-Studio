# 前端方案与数据模型（Phase B）

> 日期：2026-11-03
> 前置：`docs/PROJECT_AUDIT.md`（Phase A）
> 状态：设计已定稿并按下述契约实现。实现完成后回填实测结果（原 `WORKSPACE_REPORT.md` 已删除，见 Git 历史）
> 约束：本地单用户、只读优先、真实数据、不新建第二套环境

---

## 1. 技术栈选择与依据

### 1.1 现状检查

- 仓库**没有任何前端框架、构建工具或 `package.json`**。
- 根 `.venv` 只有 typer / rich / pydantic / pyyaml / httpx / websockets / pysubs2 / pillow。
- 环境已有 Node 24，但项目从未使用；引入 Vite/React 会新增 `node_modules`、构建产物和第二套依赖体系，与项目“双 venv、模型外置、不新增大型依赖”的纪律直接冲突。

### 1.2 选定方案

| 层 | 选择 | 理由 |
|---|---|---|
| 后端 | **FastAPI 0.162 + Uvicorn 0.54**（MIT / BSD-3-Clause） | 需要路由、请求校验（复用已有 Pydantic）、异步子进程、静态文件与 Range。新增 5 个小包（fastapi/starlette/uvicorn/click/opentelemetry-api），总计约 1 MB，不引入 torch 或数据库服务。 |
| 前端 | **无构建步骤的 ES Modules + 原生 JS/CSS** | 零 npm 依赖、零打包、改完即生效；页面以模块拆分，保持可维护。避免为 UI 新建第二套工具链。 |
| 状态库 | **SQLite（标准库 `sqlite3`）** | 与项目既定 ADR-005 一致；单文件、无服务、可备份。 |
| 媒体 | **Starlette 静态 + 自实现 Range** | 视频拖动进度需要 206；缩略图用 Pillow（已在依赖）与 FFmpeg（已在 PATH）。 |

**被否决的方案**

| 方案 | 否决理由 |
|---|---|
| React + Vite | 需要 node_modules 与构建步骤；与“不新建第二套环境”冲突；收益主要是组件复用，而本项目页面数量有限 |
| Flask / Django | Flask 无内建异步与校验；Django 是完整全栈框架，明显过重 |
| 纯 `http.server` | 需手写路由、校验、Range、并发，代码量更大、缺陷面更宽 |
| Electron / 桌面壳 | 与“本地 Web 页面”目标不符 |

### 1.3 目录

```text
src/drama_studio/workspace/     # 后端（新包）
  __init__.py
  store.py          # SQLite schema、CRUD（不自动导入内容）
  discovery.py      # 从真实文件派生 projects/episodes/workflow/assets
  media.py          # 安全路径解析、Range、缩略图缓存
  tasks.py          # 任务注册表、单飞锁、执行器、日志
  envprobe.py       # 端口/服务/磁盘/ffmpeg 探测
  api.py            # FastAPI 应用与请求模型

src/drama_studio/web/           # 前端（新目录，随包分发）
  index.html
  app.css
  js/app.js
  js/api.js
  js/ui.js
  js/pages/*.js

src/drama_studio/cli.py         # 仅追加 serve 命令（不改 doctor）
tests/test_workspace_*.py       # 新增测试
```

---

## 2. 信息架构与导航

左侧主导航（按真实模块裁剪，不机械照搬）：

| 序 | 页面 | 路由 | 作用 |
|---|---|---|---|
| 1 | 工作台 | `#/dashboard` | 全局概况、最近制作、流程总览、最近任务、环境 |
| 2 | 内容项目 | `#/projects` | 系列管理、创建期数 |
| 3 | 期数管理 | `#/episodes` | 全部期数、状态筛选、完成度 |
| 4 | 期数工作区 | `#/episodes/{id}` | 单期核心操作页（7 个 Tab） |
| 5 | 生产工作流 | `#/workflow` | 真实依赖图、节点输入输出、可执行入口 |
| 6 | 素材库 | `#/assets` | 按类型/期数检索、预览、来源 |
| 7 | 风格管理 | `#/styles` | 风格预设与项目/期数引用 |
| 8 | 任务中心 | `#/tasks` | 六态任务、日志、错误、重跑 |
| 9 | 系统设置 | `#/settings` | 环境、路径、服务、doctor |

顶部工具栏：面包屑、刷新、环境状态胶囊（LLM 8080 / ComfyUI 8188 / CosyVoice 50000 / FFmpeg），不可探测显示 `UNKNOWN`。

### 2.1 视觉规范

- 深色工作区：背景 `#0d0f12`，面板 `#14171c`，描边 `#232830`，主文本 `#e7eaf0`，次要 `#8b93a1`。
- 强调色：琥珀橙 `#e0813a`（仅用于主操作与当前状态，不作装饰）。
- 状态色：已验证绿 `#4c9a6a`、部分黄 `#c9a227`、失败红 `#c4553f`、未运行灰 `#6b7280`、未知虚线灰。
- 不使用渐变、发光、霓虹、装饰性图表。
- 表格密度对齐 Linear；卡片圆角 8px，1px 描边，无阴影堆叠。
- 中文为主；`PASS_VERIFIED` / `RUNNING` 等技术状态保留英文。
- 断点：≥1440 三栏；1024-1440 两栏；<1024 单栏、导航折叠；最小可用宽度 360。

---

## 3. 数据模型

### 3.1 原则

1. **状态不落库推导，落库只存用户创建的事实**：项目、期数、风格、任务记录在 SQLite；产物状态每次从文件实时派生。
2. **期数必须绑定真实产物目录**（`artifact_root`），否则进度一律 `NOT_RUN`。
3. **进度只按必需步骤中 `PASS_VERIFIED` 的数量计算**，`PARTIAL` 不计入完成。

### 3.2 SQLite schema（`projects/workspace.db`）

```sql
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  positioning TEXT NOT NULL DEFAULT '',
  default_style_id TEXT,
  default_voice TEXT NOT NULL DEFAULT '',
  aspect_ratio TEXT NOT NULL DEFAULT '9:16',
  target_platforms TEXT NOT NULL DEFAULT '[]',   -- JSON array
  origin TEXT NOT NULL DEFAULT 'user',           -- user | imported
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE episodes (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  number INTEGER NOT NULL,
  title TEXT NOT NULL,
  track TEXT NOT NULL DEFAULT 'video',           -- video | literary
  artifact_root TEXT,                            -- 相对仓库根的真实目录
  style_id TEXT,
  style_snapshot TEXT NOT NULL DEFAULT '{}',     -- 创建/绑定时冻结的风格副本
  notes TEXT NOT NULL DEFAULT '',
  origin TEXT NOT NULL DEFAULT 'user',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(project_id, number)
);

CREATE TABLE styles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  visual_language TEXT NOT NULL DEFAULT '',
  color_palette TEXT NOT NULL DEFAULT '{}',      -- JSON object
  lighting TEXT NOT NULL DEFAULT '',
  camera_language TEXT NOT NULL DEFAULT '',
  composition TEXT NOT NULL DEFAULT '',
  character_design TEXT NOT NULL DEFAULT '',
  environment_design TEXT NOT NULL DEFAULT '',
  positive_prompt TEXT NOT NULL DEFAULT '',
  negative_prompt TEXT NOT NULL DEFAULT '',
  reference_assets TEXT NOT NULL DEFAULT '[]',   -- JSON array（仓库相对路径）
  aspect_ratio TEXT NOT NULL DEFAULT '9:16',
  applicable_content_types TEXT NOT NULL DEFAULT '[]',
  source_files TEXT NOT NULL DEFAULT '[]',       -- 该风格的证据文件
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  lock_key TEXT NOT NULL,
  status TEXT NOT NULL,                          -- PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED/BLOCKED
  project_id TEXT,
  episode_id TEXT,
  params TEXT NOT NULL DEFAULT '{}',
  result TEXT NOT NULL DEFAULT '{}',
  error TEXT,
  exit_code INTEGER,
  log_path TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_episode ON tasks(episode_id);
CREATE UNIQUE INDEX idx_tasks_running_lock
  ON tasks(lock_key) WHERE status = 'RUNNING';
```

**版本规则**：任务只追加，不更新历史；期数的 `style_snapshot` 在绑定时冻结，修改全局风格不会改变历史期数。构建产物写入新的时间戳目录，永不覆盖。

### 3.3 初始数据

工作台**不再自动导入任何具体作品**。`projects/workspace.db` 只保存用户在本地创建的项目、期数、风格与任务；新克隆首次打开为空状态。

本机已有记录属于本地导入数据，不是产品默认内容，也不会在其他机器上重建。开发与集成测试使用 `literary_intelligence/tests/fixtures/corpus_short/` 的短文本夹具「白日依山尽」，测试不依赖真实实验资产。

### 3.4 状态词典

| 值 | 含义 |
|---|---|
| `PASS_VERIFIED` | 有产物且有可核验证据（文件存在 + 哈希/ffprobe 通过） |
| `PASS_STATIC` | 仅测试/静态证据，无生产产物 |
| `PARTIAL` | 部分可用（例：LI 五轮跑通但无人工审核） |
| `NOT_RUN` | 未执行 |
| `BLOCKED` | 前置缺失 |
| `FAILED` | 执行失败 |
| `UNKNOWN` | 无法探测（禁止猜测为在线/正常） |

任务状态：`PENDING` / `RUNNING` / `SUCCEEDED` / `FAILED` / `CANCELLED` / `BLOCKED`。

---

## 4. 派生规则

### 4.1 视频期数的步骤

| 步骤 | 判定 | 证据 |
|---|---|---|
| `source` 原文 | `narration.json` 存在且 `lines` 非空 | 文件 + 行数 |
| `analysis` 文学分析 | `runs/*/real_pipeline.json` 存在；`editor.draft_text` 非空才算完成 | 运行目录 + 状态 |
| `script` 文案 | `narration.json` 的文本行（与 source 同源时标 `PARTIAL`） | 行文本 |
| `storyboard` 分镜 | `segments.json` 解析成功且 source 文件全部存在 | 分段数 |
| `images` 图片 | 分镜中的 image 段均有真实文件 | 数量 + 哈希 |
| `videos` 视频 | 分镜中的 video 段均有真实文件 | 数量 |
| `voice` 配音 | `audio_manifest.json` 每行文件存在且哈希一致 | N/N |
| `subtitles` 字幕 | 构建产物含 `.srt` 或 `.ass` | 文件 |
| `compose` 合成 | `build_manifest.json` 存在且 `final` 文件哈希一致 | 哈希 |
| `output` 成片 | `final_9x16.mp4` 可被 ffprobe 读取，分辨率/时长有效 | ffprobe 摘要 |

必需步骤：`source, storyboard, images, voice, compose, output`；`analysis/script/videos/subtitles` 视期数而定（`videos` 在无 Wan 段时视为可选）。

完成度 = 必需步骤 `PASS_VERIFIED` 数 / 必需步骤总数。

### 4.2 文学期数的步骤

`source`（原文/来源登记）→ `analysis`（五轮 + 人工审核）→ `package`（ContentPackage）→ `script/visual/voice/compose`（均 `NOT_RUN`）。

《洛神赋》当前：`source=PASS_VERIFIED`，`analysis=PARTIAL`（真实运行但 `human_review=NOT_RUN`，`approved claim=0`），其余 `NOT_RUN`。

### 4.3 期数状态

```
有 RUNNING 任务           → producing
无 RUNNING 且 final 有效  → completed
最近任务 FAILED 且无 final → failed
必需输入齐全但无 final     → ready
其余                      → draft
```

---

## 5. API 契约

统一前缀 `/api`。错误体：`{"error": {"code": "...", "message": "...", "detail": {...}}}`，HTTP 4xx/5xx 对应。

### 5.1 只读

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | `{ok, version, root}` |
| GET | `/api/overview` | 统计、最近期数、最近任务、环境摘要 |
| GET | `/api/projects` | 项目 + 期数计数 + 最近更新 |
| GET | `/api/projects/{id}` | 项目详情 + 期数列表 |
| GET | `/api/episodes?project_id=&status=` | 期数摘要（含完成度、最终成片状态） |
| GET | `/api/episodes/{id}` | 期数详情（步骤、绑定、风格快照） |
| GET | `/api/episodes/{id}/content` | 原文、分析、旁白、标题/Hook/结尾（有则返回，无则 `null` + 原因） |
| GET | `/api/episodes/{id}/storyboard` | 分镜段 + 素材状态 + 提示词 |
| GET | `/api/episodes/{id}/audio` | 音频行、时长、哈希校验、时间轴（若有） |
| GET | `/api/episodes/{id}/assets` | 本期引用素材（路径/类型/大小/时间/来源/哈希状态） |
| GET | `/api/episodes/{id}/output` | 全部构建记录 + 最新成片的 ffprobe 摘要 |
| GET | `/api/episodes/{id}/workflow` | 依赖图节点（状态、输入、输出、入口、错误） |
| GET | `/api/workflow?episode_id=` | 同上，供工作流页 |
| GET | `/api/styles` / `GET /api/styles/{id}` | 风格列表/详情 |
| GET | `/api/tasks?status=&episode_id=&kind=` | 任务列表 |
| GET | `/api/tasks/{id}` | 任务详情 |
| GET | `/api/tasks/{id}/log?offset=` | `{text, next_offset, eof}` |
| GET | `/api/tasks/kinds` | 任务注册表（参数 schema、成本、前置、是否可用） |
| GET | `/api/assets?type=&q=&project_id=&episode_id=` | 素材库 |
| GET | `/api/env` | 端口/服务/ffmpeg/磁盘（快速探测，5s 缓存） |
| GET | `/api/media/{path}` | 媒体字节流（Range 206），路径白名单 |
| GET | `/api/thumb/{path}` | 图片/视频缩略图（缓存于 `logs/workspace/thumbs/`） |

### 5.2 写入

| 方法 | 路径 | 校验 |
|---|---|---|
| POST | `/api/projects` | name 必填、唯一；slug 自动 |
| PATCH | `/api/projects/{id}` | 仅允许字段白名单 |
| POST | `/api/episodes` | project 存在；number 唯一；artifact_root 可选且必须在仓库内 |
| PATCH | `/api/episodes/{id}` | 同上 |
| POST | `/api/styles` / `PATCH /api/styles/{id}` | 字段白名单 |
| POST | `/api/tasks` | `{kind, params, confirm}`；按注册表校验；同 `lock_key` 已有 RUNNING → 409 |
| POST | `/api/tasks/{id}/cancel` | 仅 PENDING/RUNNING；终止自身子进程树 |

### 5.3 任务注册表

| kind | 参数 | 前置 | 成本 | 安全 |
|---|---|---|---|---|
| `doctor.run` | `{}` | 无 | 秒-分钟 | 只读 |
| `build.rebuild` | `{episode_id}` | 该期 `segments.json` + `audio_manifest.json` 且文件齐全 | ~2 分钟 | 强制新目录 `projects/<p>/episodes/<e>/renders/build-<UTC>/`；拒绝已存在目录 |
| `comfy.batch` | `{jobs}` | `jobs` 位于 `experiments/` 或期数 `projects/.../comfy/`；8188 健康 | 分钟到小时级 | `lock_key=gpu`；禁止并发 |
| `li.run` | `{corpus, out, max_tokens}` | corpus 位于 `literary_intelligence/corpus/` | 分钟级 | `lock_key=llm-8080`；由脚本自管服务 |
| `service.comfy.start` / `stop` | `{confirm:true}` | 无 | 秒-分钟 | 只调用既有 `start.ps1`/`stop.ps1` |
| `package.build` | `{episode_id}` | 语料含 source_registry/claims | 秒级 | 写本期 content_package.json |
| `script.generate` | `{episode_id, speaker?, speed?}` | 内容包存在、期数绑定风格、8080 可用 | 分钟级 | 严格 Schema；raw 保留 |
| `segments.build` | `{episode_id}` | 脚本、图片、audio_manifest 存在 | 秒级 | 缺图/缺音频失败 |
| `quality.check` | `{episode_id, manifest?}` | build_manifest 存在 | 秒到 1 分钟 | 只读；写 quality_report.json |
| `tts.synthesize` | `{episode_id, speaker?, speed?}` | narration.json 存在 | 分钟级 | 参数化；有效 manifest 复用 |

**永不注册**：任意命令、任意路径、shell 字符串、前端直连文件系统、第二个 LLM 端口。

---

## 6. 安全边界

1. 媒体路径：必须是仓库相对路径，拒绝 `..`、绝对路径、盘符；解析后必须位于 `assets/ experiments/ projects/ literary_intelligence/ workflows/` 之下。
2. 任务参数：Pydantic 严格校验（`extra="forbid"`），路径同样做根目录约束。
3. 子进程：`create_subprocess_exec` + argv 列表，`shell=False`；环境继承；工作目录固定仓库根。
4. 日志：只读追加文件，前端只读尾部；单次返回上限 64 KB。
5. 危险操作（服务启停、重建）必须 `confirm=true`，前端二次确认。
6. 单用户本地：默认只监听 `127.0.0.1`。

---

## 7. 页面实现细节

### 7.1 Dashboard

- 统计卡：项目数、期数、已完成、生产中、失败任务、待处理任务、成片数（全部由真实数据计算，点击可下钻）。
- 最近制作：按期数 `updated_at` + 产物 mtime 排序，显示缩略图（真实首帧）、状态、阶段、完成度。
- 全局流程：11 个节点横向条，节点状态来自当前选中/最近期数；不可执行节点显示原因。
- 最近任务：最近 8 条，状态、耗时、错误摘要。
- 环境：4 个服务胶囊 + GPU/磁盘；不可探测显示 `UNKNOWN`，附“最后探测时间”。

### 7.2 Episode Workspace

7 个 Tab：

| Tab | 内容 |
|---|---|
| 概览 | 步骤清单、完成度、绑定路径、风格、最新构建、可执行任务 |
| 内容 | 原文/规范化文本、文学分析（解释/意象/情绪/历史注记及状态）、旁白、标题/Hook/结尾；有 `claim_refs` 时标注来源；无 approved 时明确显示空值原因 |
| 分镜 | 镜头卡（真实分段）：编号、来源素材缩略图、时长、运动、提示词（来自 R3-A params）、图片/视频状态 |
| 视觉 | 期数风格快照 + 全局预设；展示色板、镜头语言、正/负提示词、参考图；修改风格需显式“应用新快照” |
| 音频 | 每行文本、WAV 播放器、时长、哈希校验、时间轴（有则显示每个字幕区间） |
| 素材 | 本期全部引用文件：类型、路径、大小、时间、来源、哈希是否一致、是否被生产引用 |
| 成片 | 播放器（Range）、分辨率/帧率/时长/码率/音轨/字幕轨、构建日志、打开目录提示、构建历史 |

### 7.3 Workflow

真实依赖图（纵向分层）：

```text
原文 source
  └─ 文学分析 analysis
  └─ 文案 script
  └─ 分镜 storyboard
       ├─ 图片生成 images
       └─ 视频生成 videos
  └─ 配音 voice
  └─ 字幕 subtitles
  └─ 合成 compose → 成片 output
```

每个节点：状态、输入（路径+存在性）、输出（路径+存在性+哈希）、可执行入口（若有）、最近任务、错误原因。不可执行时给出“缺少什么”，不盲目启动。

### 7.4 Tasks

- 过滤：状态、类型、期数。
- 详情抽屉：参数、结果、错误、日志尾部（2 秒轮询直到终态）、取消/重跑（重跑=新任务，保留旧记录）。
- 刷新后从服务端恢复状态；重启时遗留 RUNNING 任务标记为 `FAILED`（原因：服务重启）。

### 7.5 Assets

分类：Source / Image / Video / Audio / Subtitle / Render / Reference / Temporary。来源目录白名单扫描；显示所属项目/期数（按期数 `artifact_root` 反查）；图片/视频缩略图；音频播放；字幕文本预览；成片播放器。实验临时文件单独标记 `Temporary`，不与正式资产混排。

### 7.6 Styles

列表 + 编辑表单（全部字段）。区分：全局预设（`styles` 表）、项目默认（`projects.default_style_id`）、期数快照（`episodes.style_snapshot`）。修改全局预设不影响历史期数；期数页提供“应用当前预设为新快照”。

---

## 8. 未实现 / 明确标注

| 能力 | 状态 | UI 表现 |
|---|---|---|
| 分镜编辑 | 未实现 | 只读，注明“编辑需 LI-2-C Adapter” |
| 内容编辑 | 只读（本期） | 注明写入路径未实现，避免静默覆盖 |
| TTS 任务 | `BLOCKED` | 注册表显示阻塞原因 |
| ContentPackage → R3 输入 | 未实现 | 内容页显示“尚未生成内容包” |
| 人物一致性 / H1 审核 | 未实现 | 不出现相关入口 |
| 自动发布 / 平台数据 | 未实现 | 不出现相关入口 |
| 多用户权限 | 不做 | — |

---

## 9. 测试与验收

| 层 | 测试 |
|---|---|
| store | 建库幂等、无自动内容导入、并发锁唯一索引 |
| discovery | R3-B 步骤判定与真实文件一致；删除文件后状态降级 |
| media | 路径穿越拒绝、Range 206、缩略图生成 |
| tasks | 注册表校验、单飞 409、取消、重启遗留任务清理 |
| api | 各只读端点在真实仓库返回 200；写接口 422/404 |
| 前端 | 构建后静态检查：无死链、无 `TODO` 占位、无假数字；Playwright 不可用则用 HTTP 冒烟 + 截图 |

**验收口径**

- 不允许任何页面出现硬编码统计数字。
- 不允许“404 的导航项”。
- 任务成功必须对应真实退出码 0 与真实产物。
- `PASS_STATIC` 不得写成 `PASS_VERIFIED`。

---

## 10. 实施顺序（对应 Phase C-F）

1. C：静态骨架 + 只读 API（mock 仅在单元测试，页面走真实 API）。
2. D：任务注册表/执行器/日志；媒体与缩略图；`serve` 命令。
3. E：《洛神赋》读取验证 + `build.rebuild` 真实执行（新目录）。
4. F：死链/错误处理/刷新恢复/数据一致性复核。
