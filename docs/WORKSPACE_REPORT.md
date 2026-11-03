> 状态：历史交付报告（Phase B-F，2026-11-03）。后续 P0 修复已改变种子数据、人工验收、任务取消与测试结构；现状以 `docs/PRD.md` §21 为准。

# 生产工作台交付报告（Phase B-F）

> 日期：2026-11-03
> 前置：`docs/PROJECT_AUDIT.md`（Phase A）、`docs/FRONTEND_DESIGN.md`（Phase B）
> 范围：Local Drama Studio — Production Workspace（本地单用户）
> 本报告只记录实际执行过的事情；未执行的接口和能力明确标注。

---

## 1. 完成内容

| 阶段 | 交付 | 状态 | 证据 |
|---|---|---|---|
| A 全项目审计 | `docs/PROJECT_AUDIT.md`：模块地图、真实调用链、能力矩阵、技术债 TD-01..TD-15、前端能力清单 | `PASS_VERIFIED` | 文档 + 本轮只读核验 |
| B 前端方案与数据模型 | `docs/FRONTEND_DESIGN.md`：技术栈、导航、SQLite schema、API 契约、任务状态模型 | `PASS_VERIFIED` | 文档 |
| C 可运行骨架 | 9 条路由、7 个期数 Tab、全部页面渲染真实数据 | `PASS_VERIFIED` | Puppeteer 34 项检查 |
| D 后端接入 | FastAPI 只读派生 API、媒体 Range、缩略图、任务注册表/执行器/日志 | `PASS_VERIFIED`（读取 + 2 类任务） / `PARTIAL`（ComfyUI、LI 任务已注册但本轮未触发） | 见 §5 |
| E 真实生产验证 | 《洛神赋》项目/期数/内容/claims 读取；《春江花月夜》素材/音频/成片读取；真实执行 `build.rebuild` 并回写 | `PASS_VERIFIED` | 真实任务 + 新构建目录 |
| F 完整性审计 | 路由/死链/错误处理/刷新恢复/路径穿越/控制台错误 | `PASS_VERIFIED`（34/34 通过） | Puppeteer + API 测试 |

### 1.1 页面清单

| 页面 | 路由 | 真实数据来源 |
|---|---|---|
| 工作台 | `#/dashboard` | `/api/overview`：workspace.db + 产物派生 + 端口探测 |
| 内容项目 | `#/projects` | `projects` 表 + 期数派生 |
| 期数管理 | `#/episodes` | `episodes` 表 + 每期步骤派生 |
| 期数工作区 | `#/episodes/{id}` | 概览/内容/分镜/视觉/音频/素材/成片 7 个 Tab |
| 生产工作流 | `#/workflow` | 依赖节点来自真实步骤与文件存在性 |
| 任务中心 | `#/tasks` | `tasks` 表 + 日志文件 |
| 素材库 | `#/assets` | 白名单目录扫描（正式 436 个；临时 1219 个默认隐藏） |
| 风格管理 | `#/styles` | `styles` 表（种子来自 R3-A 参数与视觉圣经） |
| 系统设置 | `#/settings` | `/api/env` + 任务注册表 + 运行环境 |

---

## 2. 修改文件

### 新增

```text
docs/PROJECT_AUDIT.md
docs/FRONTEND_DESIGN.md
docs/WORKSPACE_REPORT.md
src/drama_studio/workspace/__init__.py
src/drama_studio/workspace/store.py
src/drama_studio/workspace/discovery.py
src/drama_studio/workspace/media.py
src/drama_studio/workspace/tasks.py
src/drama_studio/workspace/envprobe.py
src/drama_studio/workspace/api.py
src/drama_studio/web/index.html
src/drama_studio/web/app.css
src/drama_studio/web/js/app.js
src/drama_studio/web/js/api.js
src/drama_studio/web/js/ui.js
src/drama_studio/web/js/forms.js
src/drama_studio/web/js/preview.js
src/drama_studio/web/js/pages/{dashboard,projects,episodes,episode,workflow,tasks,assets,styles,settings}.js
tests/test_workspace_store.py
tests/test_workspace_discovery.py
tests/test_workspace_media.py
tests/test_workspace_api.py
```

### 修改

| 文件 | 改动 | 说明 |
|---|---|---|
| `pyproject.toml` / `uv.lock` | 新增 `fastapi>=0.115,<1.0`、`uvicorn>=0.30,<1.0` | MIT / BSD-3-Clause；无 node 依赖 |
| `src/drama_studio/cli.py` | 追加 `serve` 命令 | 未改动 `doctor` |
| `.gitignore` | 忽略 `projects/workspace.db*`、`projects/*/episodes/*/renders/`、`projects/*/episodes/*/assets/` | 防止提交生成物 |
| `docs/DECISIONS.md` | 追加 ADR-014 | 取代 ADR-012 的“不做网页后台”，历史条目未改写 |
| `README.md` / `docs/README.md` / `docs/ROADMAP.md` / `docs/PRODUCTION_WORKFLOW.md` / `CLAUDE.md` | 工作台入口、索引、命令与边界说明 | 见对应文档 |

> 未修改：`scripts/r3_build.py`、`scripts/r3_tts.py`、`literary_intelligence/run_li15.py`、`scripts/llm_server.ps1`、`scripts/start.ps1`、`scripts/stop.ps1`、任何历史实验产物。

---

## 3. 技术栈与架构选择理由

| 层 | 选择 | 理由 |
|---|---|---|
| 后端 | FastAPI 0.162 + Uvicorn 0.54 | 路由、Pydantic 校验、异步子进程、静态文件与 Range；新增 5 个小包，不引入数据库服务或 torch |
| 前端 | 无构建步骤 ES Modules + 原生 JS/CSS | 零 npm、零打包、无第二套环境；页面按模块拆分 |
| 状态 | SQLite（标准库）`projects/workspace.db` | 与 ADR-005 一致；单文件、可备份 |
| 媒体 | 自实现 Range 206 + Pillow/FFmpeg 缩略图 | 视频拖动进度、真实首帧缩略图 |

**被否决**：React/Vite（第二套工具链）、Flask/Django（过重或缺少异步）、纯 `http.server`（手写路由/校验缺陷面大）、Electron（与本地 Web 目标不符）。

### 3.1 数据原则

1. **落库只存用户事实**：项目、期数、风格、任务记录。
2. **状态实时派生**：每次请求读取 `segments.json`、`audio_manifest.json`、`build_manifest.json`、WAV/MP4 哈希与 ffprobe。
3. **进度只算必需步骤的 `PASS_VERIFIED`**；`PARTIAL` 不计入。
4. **写入只走注册表**：无任意 shell、无任意路径、无前端直连文件系统。
5. **单飞锁**：SQLite 唯一索引保证同一 `lock_key` 只能有一个 RUNNING 任务。

---

## 4. 测试结果

| 测试 | 命令 | 结果 |
|---|---|---|
| 根测试套件 | `.venv\Scripts\python.exe -B -m pytest tests` | **44 passed** |
| LI 测试套件 | `.venv\Scripts\python.exe -B -m pytest literary_intelligence/tests` | **61 passed** |
| 前端语法 | `node --check`（14 个模块） | 全部通过 |
| 浏览器端到端 | Puppeteer（系统 Chrome） | **34/34 通过，0 页面错误，0 非 abort 请求错误** |
| 响应式 | Puppeteer 1440×900 / 390×844 | **18/18 无横向溢出** |
| 媒体安全 | 6 类路径穿越/越权 | 403/404 全部拒绝 |
| Range | `bytes=0-9` | 206 + `Content-Range` 正确 |

**Puppeteer 覆盖**：9 条路由渲染、期数 7 个 Tab、重建确认弹窗、任务抽屉 + 实时日志、刷新后抽屉恢复、任务 URL 保持、风格编辑弹窗、项目创建/编辑弹窗、素材预览、工作流执行确认、设置页强制探测、8 个导航项。

> 说明：视频元数据在切换 Tab 时被浏览器主动 abort（`ERR_ABORTED`），不是服务端错误；服务端 Range 请求本身已单独验证为 206。

---

## 5. 真实运行结果

### 5.1 环境诊断任务

| 项 | 值 |
|---|---|
| 任务 ID | `task_20261103074645_c9ddce` |
| 入口 | `python -m drama_studio doctor --json --no-report` |
| 状态 | `SUCCEEDED` / exit 0 |
| 结果 | 15 `PASS_VERIFIED`、3 `NOT_RUN`、0 `FAIL`（必需项无失败） |
| 日志 | `logs/workspace/tasks/task_20261103074645_c9ddce.log` |

### 5.2 合成重建任务（Phase E 的真实生产任务）

| 项 | 值 |
|---|---|
| 任务 ID | `task_20261103074757_381576` |
| 入口 | `scripts/r3_build.py --segments experiments/r3b/segments.json --audio experiments/r3b/audio_manifest.json --out projects/proj_chunjiang/episodes/ep_chunjiang_01/renders/build-20261103-074757` |
| 状态 | `SUCCEEDED` / exit 0（约 19 秒） |
| 成片 | `.../build-20261103-074757/final_9x16.mp4` |
| 时长 / 分辨率 | 38.042 s / 1080×1920 |
| 字体（fontselect 校验） | `SourceHanSansCN-Regular` |
| 解码校验 | `decode_returncode = 0` |
| manifest 版本 | `current`（含 `content_type`、`timeline`、`font`） |
| 回写 | 期数「成片」页立即出现该构建；`/api/episodes/ep_chunjiang_01/output` 返回 `latest` |
| 历史资产 | `experiments/r3b/renders/final_9x16.mp4` 哈希仍为 `fbf2b943…`，未被覆盖 |

### 5.3 读取验证

- 《洛神赋》：项目、期数、来源登记、原文/规范化文本、6 个分段、4 条 claim（全部 `unreviewed`）、真实 LLM 五轮记录（`li16d`）均正确显示；文案为空并注明“无 approved claim”。
- 《春江花月夜》：6 个分镜段、5 张静帧、1 段 Wan、7 行音频（哈希 7/7 一致）、字幕、成片技术参数均正确显示。
- 环境：探测时 8080 上的 LLM 返回 `PASS_VERIFIED`（非本工作台启动，未停止）；ComfyUI/CosyVoice 显示 `NOT_RUN`；GPU 显示“无法读取，不推测”。

---

## 6. 未实现功能（明确标注）

| 能力 | 状态 | UI 表现 |
|---|---|---|
| 内容/分镜编辑 | `NOT_RUN` | 只读；注明写入路径未实现 |
| ContentPackage → R3 输入 Adapter | `NOT_RUN` | 内容包步骤显示未运行 |
| TTS 任务 | `BLOCKED` | 注册表显示阻塞原因（`r3_tts.py` 未参数化） |
| 人工验收写入 | `NOT_RUN` | 期数显示“无人工验收记录” |
| 素材删除/移动 | 不提供 | 避免误删历史资产 |
| 自动发布/平台数据 | 不提供 | 不在本阶段范围 |
| 多用户/权限/公网 | 不提供 | 本地单用户，监听 127.0.0.1 |
| ComfyUI / LI 任务真实触发 | 已注册、本轮未触发 | 需显式 `confirm=true`；单飞锁已就绪 |

---

## 7. 已发现的项目问题

沿用 Phase A 的 TD 清单，并在实现中确认：

1. **历史成片 manifest 与当前脚本不一致**（TD-06）：已通过 `manifest_version: legacy` 明确展示，新构建标记 `current`。
2. **字体与 R3-D 证据被 gitignore**（TD-05）：工作台可读取，但新克隆仍无法复现构建。
3. **`r3_tts.py` 硬编码**（TD-02）：TTS 任务被标为 `BLOCKED`，没有用假入口掩盖。
4. **内容包 Adapter 缺失**（TD-03）：文学内容无法自动进入分镜/成片。
5. **默认 pytest 不含 LI 测试**（TD-11）：仍需要单独运行；本报告分别记录两套结果。
6. **脚本直跑仍可绕过单飞锁**：工作台内部有锁，但直接运行 `r1_batch.py` 不受约束；未修改原脚本以避免改变已验证行为。
7. **构建中间产物较多**：素材库默认隐藏帧序列与 `video_raw/video_faded/concat.txt`，期数素材页仍完整展示。

---

## 8. 对原有 R3 / S3 生产链路的影响

| 项 | 结论 |
|---|---|
| `scripts/r3_build.py` | 未修改 |
| `scripts/r3_tts.py` | 未修改 |
| `literary_intelligence/run_li15.py` | 未修改 |
| ComfyUI / LLM / CosyVoice 生命周期脚本 | 未修改 |
| 历史产物 | `experiments/r3b` 全部文件未改动；历史成片哈希复核一致 |
| 新写入 | 仅 `projects/proj_chunjiang/episodes/ep_chunjiang_01/renders/build-20261103-074757/`（Git 忽略） |
| 依赖 | 根 `.venv` 增加 fastapi/uvicorn；未安装 torch，未创建 node 环境 |
| 端口 | 工作台使用 8765；未新增 LLM 端口，未占用 8080/8188/50000 |

---

## 9. Git 状态

- **未提交、未推送**。
- 本轮新增/修改文件见 §2。
- 既有未提交修改（LI-1.5/1.6、R3-D、v1.0 文档）保持原样，未回退、未覆盖。
- `projects/workspace.db`、任务日志、缩略图、构建产物均被忽略。

```text
HEAD: e21dc0d (main)
本轮新增代码/文档: docs/PROJECT_AUDIT.md, docs/FRONTEND_DESIGN.md, docs/WORKSPACE_REPORT.md,
  src/drama_studio/workspace/*, src/drama_studio/web/*, tests/test_workspace_*.py
本轮修改: pyproject.toml, uv.lock, .gitignore, src/drama_studio/cli.py, docs/DECISIONS.md,
  README.md, docs/README.md, docs/ROADMAP.md, docs/PRODUCTION_WORKFLOW.md, CLAUDE.md
```

---

## 10. 状态结论

| 结论 | 状态 |
|---|---|
| 工作台可打开、9 条路由可用、7 个 Tab 可用 | `PASS_VERIFIED` |
| 页面数字来自真实文件/任务记录 | `PASS_VERIFIED` |
| 真实任务执行并回写（doctor、build） | `PASS_VERIFIED` |
| ComfyUI / LI 任务触发 | `NOT_RUN`（已注册，未执行） |
| 内容包 Adapter、内容编辑、TTS 参数化 | `NOT_RUN` / `BLOCKED` |
| 原有 R3/S3 链路 | 未受影响 |

**一句话**：工作台现在是“真实状态的只读镜子 + 两条已验证的受限执行入口”；它不是全自动生产系统，也没有用假数据填补任何空白。
