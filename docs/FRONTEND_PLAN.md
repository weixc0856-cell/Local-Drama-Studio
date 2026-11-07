# 前端方案：浅色影视制作工作站（2026-11-06）

> 状态：`IN_PROGRESS` — F0（浅色外壳）与 F1（项目中心 + 剧本分镜）已实现，2026-11-06；F2–F5 未开始。
> 依据：本仓库实际代码与数据契约（`film/`、`style_engine/`、`workspace/`）、`docs/PRD.md`、`docs/FILM_PRODUCTION_GUIDE.md`、`docs/VISUAL_STYLE_ENGINE.md`。
> 视觉方向：**暖白专业创作工作站**（浅色），不做 DaVinci 式深色界面。

## 1. 现状审计

| 项 | 现状 |
|---|---|
| 技术 | FastAPI（8765）+ 免构建 ES Module；`src/drama_studio/web/` |
| 主题 | **深色**：`--bg #0d0f12`、`--panel #15181e`、强调 `#e0813a` |
| 页面 | dashboard / episodes / workflow / tasks / projects / assets / styles / settings |
| 数据源 | 全部读 `workspace.db`；刚清理为空（0 项目 / 0 期数 / 0 风格 / 0 任务） |
| 新能力 | `film/` 与 `style_engine/` 只有 CLI，**没有 API 与页面** |
| 示例项目 | `projects/deng_guan_que_lou`（8 镜 / 47 s）在磁盘上，DB 里没有记录 |

结论：前端需要一次**数据源改造**（DB + 文件双读）与**主题重做**，不是加几个菜单。

## 2. 对参考方案取舍

采纳：

- 以作品为中心，不做聊天式或节点画布式主界面。
- 分镜卡片 + 表格双视图，共用 `storyboard.json`。
- 镜头生命周期、版本历史、`stale` 标记（参数或风格版本变了就标脏）。
- 生成前排期：先估算耗时再执行；先关键帧、后视频。
- GPU 锁与队列可视化。
- 声音页把**实际 WAV 时长**写回时间轴。

不采纳（与项目实际不符）：

| 参考建议 | 为什么不做 |
|---|---|
| 每种风格都展示 FLUX + Wan 双样片 | 当前只有 3 套 Oriental 有 FLUX 参考板，12 套都没有 Wan 样片；缺失就显示 `NOT_RUN`，不能造 |
| 项目中心展示《洛神赋》《春江花月夜》 | DB 已清空，磁盘只有 `deng_guan_que_lou`；界面必须按真实项目渲染 |
| 完整多轨 NLE、实时预览、调色 | 我们的剪辑是**确定性 FFmpeg 组装**；v1 只做时间轴检视与排序/裁剪，写入 `timeline.json` |
| 全局搜索、多用户、权限、协作评论 | 单人本地工作台，v1 不做；先保证状态真实 |
| Animatic 实时播放 | 可用 FFmpeg 生成低码率预览片，但不是播放器；列为 P2 |
| 深色 DaVinci 风格 | 用户明确选择浅色 |

## 3. 视觉系统（浅色）

### 3.1 色彩令牌

| 令牌 | 值 | 用途 |
|---|---|---|
| `--bg` | `#F7F6F2` | 页面底色，暖白不刺眼 |
| `--panel` | `#FFFFFF` | 卡片、面板 |
| `--panel-2` | `#FBFAF7` | 次级面板、表头 |
| `--border` | `#E7E3DB` | 1px 分隔 |
| `--border-strong` | `#D8D2C7` | 选中/悬停边框 |
| `--text` | `#30343B` | 正文 |
| `--text-dim` | `#5C626C` | 次级文字 |
| `--muted` | `#8A9099` | 说明文字 |
| `--accent` | `#E47E42` | 主操作、当前选中 |
| `--accent-ink` | `#B85F2C` | 橙色文字（浅底可读） |
| `--ok / --warn / --bad / --info` | `#4F8A63 / #B8862F / #B5543F / #5B7FA6` | 状态 |
| `--monitor` | `#101216` | 仅视频预览窗口内部 |

规则：橙色只用于主按钮、选中态与进度；状态色不用于装饰；视频预览内部保持黑色，界面配色不影响画面判断。

### 3.2 排版与密度

- 字体：Inter / Noto Sans SC；ID、路径、参数用等宽。
- 字号：正文 13px、面板标题 14px、页面标题 20px；行高 1.55。
- 圆角 8px，卡片细边框 + 极轻阴影；不堆叠卡片。
- 基准 1920×1080，兼容 1440×900；不做手机优先。

### 3.3 布局

```
┌ Topbar 56 ─ 项目名 · 画幅 · 时长 · 服务状态 · 保存状态 ┐
│ Sidebar 236 │ 主工作区（按页面）        │ Inspector 320 │
└ 底部状态栏 28：GPU 锁 · 队列 · 后台任务 ─────────────┘
```

Inspector 默认收起，选中镜头时展开。

## 4. 信息架构（6 个一级模块）

| 模块 | 页面 | 主要数据 |
|---|---|---|
| 项目中心 | `#/` | `projects/*/project.json`、进度、服务状态 |
| 剧本与分镜 | `#/storyboard` | `screenplay.json`、`narration.json`、`storyboard.json` |
| 视觉资产 | `#/visual` | `visual_bible.yaml`、`style_packs/`、关键帧、参考板 |
| 声音工作室 | `#/voice` | `narration.json`、`assets/audio/*`、`narration_manifest.json` |
| 剪辑工作台 | `#/edit` | `timeline.json`、镜头产物、`assemble` |
| 生产与质量 | `#/ops` | 任务注册表、GPU 锁、`qc/`、连续性报告 |

旧页面处置：`episodes`/`projects` 合并进项目中心；`styles` 并入视觉资产；`tasks` 并入生产与质量；`settings` 保留为顶栏抽屉。

## 5. 页面规格

### P0-1 项目中心

- 作品卡片：封面（最新关键帧）、标题、画幅、目标时长、风格 id、阶段进度条。
- 阶段：剧本 → 分镜 → 关键帧 → 镜头 → 配音 → 剪辑 → 成片，按真实文件计数。
- 右侧概览：服务状态（ComfyUI / LLM / VoxCPM2）、GPU 空闲/占用、待审核数量。
- 主按钮：新建作品（诗词 + 画幅 + 时长 + 风格包）。
- 空状态必须明确写“暂无作品”，不伪造示例。

### P0-2 剧本与分镜（核心页）

三栏：

| 区域 | 内容 |
|---|---|
| 左 20% | 场景列表、旁白段落（N001…）、镜头列表 |
| 中 55% | Storyboard 卡片 或 Table 视图（同一份数据） |
| 右 25% | 选中镜头的 Inspector |

镜头卡片：`S01`、对应旁白、关键帧缩略图、景别、运镜、时长、状态胶囊（planned / keyframe / approved / video / stale）、操作行（生成关键帧、生成镜头、审核、查看版本）。

Inspector 字段：scene_id、narration_ids、duration、shot_size、camera(move/angle/lens/dof)、layers、motion、continuity、keyframe_note、character_in_frame、generation.status。

交互：

- 拖拽排序后重排 shot_id 并重建 `previous/next` 链；保存前跑 `film validate`，失败不落盘。
- 修改提示词/风格版本 → 该镜头标记 `stale`，已有产物保留但需重新审核。
- 视图切换不产生第二份数据。

### P0-3 生成任务

- 队列：等待 / 运行 / 成功 / 失败 / 重试次数 / 耗时。
- GPU 锁：显示持锁任务与进程；明确“同一时间只跑一个 GPU 任务”。
- 生成前估算：按实测速率给出预计时间（FLUX.3 约 2–2.5 min/张；Wan 121 帧约 60–70 min/镜；VoxCPM2 约 9–12 倍实时）。
- 触发方式：只调用任务注册表（`film.keyframes` / `film.shots` / `voice.synthesize`），前端不拼模型参数。
- 失败详情：保留 stderr 末尾与重试策略。

### P0-4 剪辑工作台

- 上方：预览（视频/静帧），下方：时间轴。
- 轨道：V1 主镜头、V2 辅助层、V3 字幕；A1 旁白、A2 环境、A3 音乐、A4 音效。
- 操作：排序、裁剪起止、调整旁白起点、切换转场（cut / match_cut / dissolve / fade_black）。
- 所有操作写回 `timeline.json`，由 `film assemble` 生成成片；不做实时特效。
- 缺镜头时明确提示“该镜头无产物，将使用关键帧静帧”。

### P1-5 视觉资产

- 顶部 12 个风格包（retro 4 / oriental 3 / artistic 5），显示版本、状态（SPEC_DRAFT / REVIEWED / ACCEPTED）与参考板数量。
- 主体：参考板（有图显示图，无图显示“待生成”）、人物设定、场景设定、关键帧、版本历史。
- 每套风格提供“测试关键帧”入口：用当前风格包编译一张样片，便于比较。

### P1-6 声音工作室

- 左：逐句旁白（N001…）与朗诵指令（emotion / delivery / speed / pause）。
- 中：试听与重新生成；显示实际时长、合成耗时。
- 下：A1–A4 波形轨；旁白起点由实际 WAV 时长反推，不写预设时长。

### P1-7 生产与质量

- 任务历史、GPU 占用曲线（可选）、失败原因聚合。
- 连续性报告（`film validate`）、风格校验（`style check-image`）、QC 报告、人工审片记录。

## 6. 需要新增的 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/film/projects` | 扫描 `projects/*/project.json`，合并阶段进度 |
| GET | `/api/film/projects/{id}` | 项目 + 分镜 + 旁白 + 时间轴 + 计数 |
| PATCH | `/api/film/projects/{id}/storyboard/{shot}` | 编辑镜头；校验后写回并 bump revision |
| POST | `/api/film/projects/{id}/plan` | 节拍 → 分镜（复用 `film plan`） |
| POST | `/api/film/projects/{id}/jobs/{kind}` | 生成关键帧/镜头任务文件并提交任务 |
| GET | `/api/film/projects/{id}/assets` | 关键帧/镜头/音频最新产物与版本 |
| GET | `/api/style/packs` | 12 套风格包摘要 |
| GET | `/api/style/packs/{id}` | 完整配置 + 参考板状态 |
| GET | `/api/ops/gpu` | 锁持有者、队列、最近耗时 |

所有写操作必须经过 `film` 的 Schema 校验；前端不得直接写 JSON 文件。

## 7. 状态与版本

- 镜头状态：`planned → keyframe_generated → keyframe_approved → video_generated → video_approved → assembled → finalized`。
- `stale`：镜头参数哈希或风格版本与产物 `job.json` 不一致时置位；重新生成不覆盖已审核版本。
- 版本：每个产物保留 `v1..vN` 与审核人/时间；UI 默认显示最新已审核版本。

## 8. 实施阶段

| 阶段 | 内容 | 文件 | 状态 |
|---|---|---|---|
| F0 主题与外壳 | 浅色令牌、Topbar/Sidebar/Inspector/状态栏、路由 | `web/app.css`、`web/index.html`、`web/js/app.js` | 已实现 |
| F1 项目中心 + 分镜 | 文件扫描 API、卡片/表格双视图、Inspector、校验 | `workspace/film_api.py`、`web/js/pages/film_projects.js`、`web/js/pages/storyboard.js` | 已实现 |
| F2 生成任务 | 队列、GPU 锁、耗时估算、失败详情 | `workspace/tasks.py`、`web/js/pages/tasks.js` | 未开始 |
| F3 剪辑时间轴 | 时间轴检视、排序/裁剪、写回 timeline | `web/js/pages/edit.js`、`film/timeline.py` | 未开始 |
| F4 资产/风格/声音 | 风格包页、参考板、波形与逐句试听 | `web/js/pages/styles.js`、`voice.js` | 未开始 |
| F5 生产与质量 | QC、连续性、审片记录 | `web/js/pages/ops.js` | 未开始 |

F1 实际接口：`GET /api/film/projects`、`GET /api/film/projects/{id}`、`PATCH /api/film/projects/{id}/storyboard/{shot}`（写前用 `ShotSpec`/`Storyboard` 校验，失败返回 422 且不落盘）、`GET /api/film/styles/packs`、`GET /api/film/styles/packs/{id}`。测试见 `tests/test_workspace_film_api.py`。

技术选择：继续使用免构建 ES Module，不引入 React/Vue；页面变复杂时只增加本地工具模块，避免构建链。

## 9. 非目标

- 不做实时 NLE、调色、关键帧动画编辑器。
- 不做多用户、权限、云端同步。
- 不做手机端优先布局。
- 不在前端出现“未生成却显示完成”的状态。
