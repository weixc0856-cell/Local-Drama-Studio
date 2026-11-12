# 仓库结构与分层（2026-11-12）

本仓库只承载**开发管线**：源码、声明式配置、文档、测试、ComfyUI 工作流和小的文本清单（manifest）。
所有**产出物**（图片、视频、音频、日志、参考板、工作区数据库）都写在仓库之外的产出根目录。

## 1. 双根目录

| 根 | 默认位置 | 内容 | 进 Git |
|---|---|---|---|
| `repo_root()` | 本仓库检出目录 | `src/` `config/` `docs/` `tests/` `workflows/` `scripts/`、`assets/` 中的输入登记表与许可证 | 是 |
| `output_root()` | `D:/DramaStudio`（`DRAMA_OUTPUT_ROOT` 可改） | projects、experiments、style_boards、logs、literary runs、工作区 DB | 否 |

`drama_studio.paths` 是唯一的解析入口：

```python
from drama_studio.paths import (
    repo_root, output_root, output_path, projects_root, experiments_root,
    style_boards_root, logs_root, literary_runs_root, project_dir,
    workspace_db_path, config_root,
)
```

规则：

1. 领域/应用代码只接收显式路径参数；**不**自己拼 `ROOT / "projects"`。
2. `config_root(root)` 用于 style pack 等配置：传入工作区根也总能找到仓库里的 `config/`。
3. 产出根不允许位于仓库内（`scripts/check_repo_hygiene.py` 会失败）。

产出根布局：

```
D:/DramaStudio/
  projects/<project_id>/            # 项目工作区：契约 JSON、分镜、关键帧、Wan、渲染
  experiments/<name>/               # 实验
  style_boards/<group>/<pack>/candidates/   # 生成的风格参考板
  logs/                             # 运行日志、工作区任务日志、缩略图
  literary_intelligence/runs/       # LI 运行产物
  backups/                          # 本地备份（如历史重写前的 bundle）
```

## 2. 什么进 Git

进：`src/`、`config/`（yaml、style pack 声明、manifest）、`docs/`、`tests/`、`workflows/`、`scripts/`、`assets/` 下的音频/字体**登记表与许可证**、字体 manifest。

不进：任何图片/视频/音频/字体二进制、模型权重、`projects/`、`experiments/`、`logs/`、参考板候选图、`workspace.db`。

守门：

```powershell
.venv\Scripts\python.exe scripts\check_repo_hygiene.py
```

CI 在测试前执行；规则为「无被跟踪的媒体文件」「无被跟踪文件大于 512 KiB」「产出根不在仓库内」。

## 3. 分层

```
src/drama_studio/
  domain/           纯规则与契约：不发起网络/进程调用
    contracts.py      Storyboard / ProductionScript 等严格 schema
    style/            style pack schema、注册表、prompt 编译、一致性度量、style lock
    voice/            voice profile、读音词典、吟诵规则
    motion/           镜头语言策略、缓动与区域规则
    film/             剧本/分镜/时间轴契约与连续性规则
    aesthetics.py     六维镜头设计与 A/B 约束
    bible.py          角色/镜头圣经检查
  application/      用例：编排领域规则与基础设施端口
    film/             规划、关键帧作业、Wan、配音、时间轴、装配、状态
    voice/            TTS 管线、混音、音频资产与时间轴
    motion/           确定性运动渲染
    production.py     生产脚本 → ComfyUI 作业
    script_engine.py  本地 LLM → ProductionScript
    quality.py        质量门（ffprobe 等外部调用）
    operations/tasks.py 工作区任务注册表
  infrastructure/   适配器：文件系统、SQLite、HTTP 引擎、FFmpeg、字体
    storage/          store / discovery（状态推导）
    media.py          媒体安全访问与缩略图
    fonts.py  locks.py  envprobe.py
  interfaces/       CLI 与 HTTP API、静态 UI
  paths.py          双根解析（共享内核）
  config.py         设置加载（共享内核）
```

依赖方向：`interfaces → application → domain`；`application → infrastructure` 通过显式端口/函数调用。`domain` 不导入 `application`/`infrastructure`/`interfaces`。

## 4. 兼容 shim

迁移期间旧路径（如 `drama_studio.models`、`drama_studio.style_engine`、`drama_studio.film.assemble`）保留为一行 shim：

```python
from drama_studio.domain.contracts import *
```

用途仅为不打断既有脚本与外部引用。新代码必须使用分层路径；后续清理时删除 shim 并修正剩余引用。

## 5. 迁移工具

- `scripts/restructure_ddd.py --stage <domain|application|infrastructure|interfaces> [--apply]`：移动模块、重写绝对/相对导入、留下 shim。
- `scripts/migrate_outputs.py [--apply]`：把历史产出物从仓库搬到产出根（幂等，跳过被占用文件）。
