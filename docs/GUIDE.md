# 操作与开发指南

> 状态：`DECISION` / 2026-11-12 由 `USER_GUIDE.md`、`DEVELOPER_GUIDE.md`、`TROUBLESHOOTING.md` 合并。
> 原始文档归档在 `D:\DramaStudio\archive\docs\2026-11-12\`（见 [ARCHIVE.md](ARCHIVE.md)）。
> 原则：先取证再修复；不删除历史产物；不把失败伪装成成功。

## 1. 环境与服务

两个 Python 环境，永不合并：根 `.venv`（Python 3.12）只做编排；`runtime/ComfyUI/.venv` 是 PyTorch-XPU + ComfyUI。根环境不得安装 torch。

```powershell
uv sync --python 3.12                          # 编排环境（幂等）
scripts\setup.ps1 -WithComfyUI                 # 生成环境（首次很重）
.venv\Scripts\python.exe scripts\fetch_fonts.py # OTF 不进 Git，按 manifest 重建并校验
scripts\doctor.ps1                             # 或 .venv\Scripts\drama.exe doctor --json
```

服务与端口：ComfyUI **8188**、本地 LLM **8080**（单端口，CPU-only 64K）、VoxCPM2 **50000**（48 kHz，CPU）、工作台 **8765**。8080 同一时间只跑一个实例；**谁启动，谁停止**。

```powershell
scripts\start.ps1
scripts\llm_server.ps1 -Action start
scripts\cosyvoice_server.ps1 -Action start     # VoxCPM2（脚本名保留历史叫法）
.venv\Scripts\drama.exe serve --port 8765
```

```powershell
scripts\stop.ps1
scripts\llm_server.ps1 -Action stop
scripts\cosyvoice_server.ps1 -Action stop
```

本地探测必须绕过系统代理：Python `httpx(..., trust_env=False)`，PowerShell 用 `curl.exe`（`Invoke-RestMethod` 对 localhost 返回 502）。

## 2. 生产工作台

浏览器打开 `http://127.0.0.1:8765`。

- 左侧导航：生产（工作台 / 期数管理 / 生产工作流 / 任务中心）、内容（内容项目 / 素材库 / 风格管理）、系统（系统设置）。
- 期数工作区 7 个 Tab：概览 / 内容 / 分镜 / 视觉 / 音频 / 素材 / 成片。
- 创建项目只是容器；创建期数时**必须选风格**，会把风格冻结为 `style_snapshot`。
- 期数“视觉”Tab 可换代风格快照；旧 `style_id`/`style_sha256` 写入 `_style_lock.history`，历史构建不覆盖。
- 任务中心只执行注册表里的任务；危险任务需勾选确认。执行模型：参数校验 → 单飞锁 → 前置条件 → 子进程/在进程 handler → 实时日志 → `after_success` 校验 → 成功/失败/取消。

数据位置：项目与渲染在 `D:\DramaStudio\projects\...`，任务日志在 `D:\DramaStudio\logs\workspace\tasks\`；仓库里没有产出物（见 [REPO_LAYOUT.md](REPO_LAYOUT.md)）。

## 3. 代码结构与入口

```text
domain/          纯契约与规则（contracts / style / voice / motion / film / aesthetics / bible）
application/     用例（film / voice / motion / operations / production / script_engine / quality）
infrastructure/  适配器（storage / media / fonts / locks / envprobe）
interfaces/      CLI 与 FastAPI（cli / film_cli / http）
paths.py         双根解析（repo / output）
config.py        设置加载
```

| 命令 | 作用 |
|---|---|
| `drama doctor` | 环境诊断（`PASS_VERIFIED / PASS_LIMITED / FAIL / NOT_RUN`） |
| `drama serve` | 工作台（8765） |
| `drama film ...` | Script-to-Film 全链路（见 [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md)） |
| `drama style list/show/validate/check-image` | 风格包 |
| `python -m drama_studio.application.content_package` | 内容包 |
| `python -m drama_studio.application.script_engine` | 文案/分镜 |
| `python -m drama_studio.application.production` | jobs / segments / motion plan |
| `python -m drama_studio.application.quality` | 质量检查 |
| `scripts\r1_batch.py` | ComfyUI 批处理（resume / 重试 / 溯源） |
| `scripts\r3_build.py` | 唯一合成器（字幕 / 字体 / 响度 / ducking） |
| `scripts\motion_build.py` | 确定性运动渲染 |
| `scripts\static_quality.py` / `aesthetic_plan.py` / `aesthetic_compare.py` | 静态门与美学 A/B |
| `scripts\tts_qa.py` | ASR 代理（VoxCPM venv） |
| `scripts\check_repo_hygiene.py` | 仓库卫生守门（CI） |

工作台 API（节选）：`/api/health`、`/api/overview`、`/api/projects`、`/api/episodes/{id}/workflow`、`/api/styles`、`/api/tasks`、`/api/tasks/kinds`、`/api/tasks/{id}/log`、`/api/media/{path}`、`/api/thumb/{path}`、`/api/env`、`/api/assets`。写入只走任务注册表，没有任意 shell / 任意路径。

## 4. 任务注册表

定义在 `application/operations/tasks.py` 的 `TASK_KINDS`（23 种）。新增任务：

1. 定义 `*Params(BaseModel)`（`extra="forbid"`）。
2. 写 `_kind_paths / _prereqs / _argv / _after`。
3. 注册 `TaskKind`，选 `lock_key`（GPU / LLM / TTS / 阶段）。
4. 危险任务 `danger=True` + `confirm`。
5. 更新 `web/js/pages/tasks.js` 的 `launcherForm`。
6. 加 API/任务测试；不允许任意路径。

## 5. 测试与守门

```powershell
.venv\Scripts\python.exe -m pytest          # 全部（根 + LI + 分层守门）
.venv\Scripts\python.exe -m pytest tests\test_layering.py -q
.venv\Scripts\python.exe scripts\check_repo_hygiene.py
```

- `test_layering.py`：domain 不得依赖 application / infrastructure / interfaces；application 不得依赖 interfaces。
- `check_repo_hygiene.py`：不得有被跟踪的媒体文件、不得有 >512 KiB 的被跟踪文件、产出根不得在仓库内。
- 断言以真实文件 / 清单为依据；平台或服务不可用记为 `NOT_RUN`。

## 6. 排障

固定顺序：`doctor` → 端口 → 服务健康 → 最近任务日志 → 产物 → 配置。

```powershell
scripts\doctor.ps1
Get-NetTCPConnection -LocalPort 8188,8080,50000,8765 -State Listen -ErrorAction SilentlyContinue
curl.exe -s -m 3 http://127.0.0.1:8188/system_stats
curl.exe -s -m 3 http://127.0.0.1:50000/health
```

| 现象 | 处理 |
|---|---|
| ComfyUI 起不来 | 看 `logs\comfyui.err.log`；确认 `runtime\ComfyUI\.venv`；不要重复启动；`stop.ps1` 只杀本项目进程树 |
| XPU 不可用 | `runtime\ComfyUI\.venv\Scripts\python.exe -c "import torch; print(torch.xpu.is_available())"`；不要装 CUDA 版 |
| OOM | 一次只跑一个 GPU 任务；Wan 用 73 帧 / `safe8g`；不要 121 帧 |
| Wan 彩虹伪影 | 必须 20 步 |
| Wan 主体位移错 / 建筑变形 | Wan 不适合；改静帧运镜或 2.5D 分层 |
| FLUX 空图 / 黑图 | 重摇；不带入成片；检查 job 日志 |
| 负向提示词无效 | CFG 1.0 + `ConditioningZeroOut` 是设计；用正向约束 |
| 字体缺字 / 回退 | `font_manifest.json` 校验；`r3_build` 拒绝静默 fallback |
| 音频哈希不一致 | 重新登记 manifest，不覆盖旧证据 |
| 任务中断 | 任务日志在 `D:\DramaStudio\logs\workspace\tasks\`；取消会 taskkill 并写 `CANCELLED` |
| 风格不生效 | 期数风格是 DB 快照；`motion.plan` / `aesthetic.plan` 需要 `config/styles.yaml` 里有同名 preset |
| 历史路径缺失 | 产出物已迁到 `D:\DramaStudio`；用 `paths.output_root()` 解析，不要在仓库里找 |

## 7. 约定

- 不升级 ComfyUI / 节点或替换权重而不重跑 R0 检查；版本记录在 `logs/r0/engine-versions.txt`。
- 每次生成保留 seed、prompt、模型 / 工作流哈希。
- 重建写新的 `build-<time>/`；不覆盖历史。
- 新代码用分层路径；旧路径 shim 只作兼容，迁移后删除。
