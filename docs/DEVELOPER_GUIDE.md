# 开发者指南

> 文档状态：Phase B 开发者文档（2026-11-04）
> 读者：接手代码的工程师
> 基线：`main` / HEAD `06f91e4` + 未提交 M8/声景/zero-shot 工作区
> 原则：先读数据契约与任务注册表，再改代码；不要绕过质量门与单飞锁。

---

## 1. 仓库与运行环境

```text
Local-Drama-Studio/
├─ src/drama_studio/        # 生产 Python 包
├─ scripts/                 # CLI 适配器、实验工具、服务脚本
├─ config/                  # 8 份 YAML
├─ workflows/               # ComfyUI API 工作流
├─ tests/                   # 根测试
├─ literary_intelligence/   # 独立文学证据链包 + 测试
├─ projects/                # SQLite + 真实产物（本地）
├─ experiments/             # 实验产物（本地）
├─ assets/                  # 视觉/字体/音频（部分本地）
└─ runtime/ComfyUI/         # 独立生成环境（本地）
```

环境边界：

- 根 `.venv`：Python 3.12，只装调度依赖；**永不装 torch**。
- `runtime/ComfyUI/.venv`：PyTorch XPU + ComfyUI + GGUF；`src/` 不得导入。
- `D:\AI\CosyVoice-Runtime`：Python 3.10，TTS；不向其安装项目依赖。
- `D:\AI\models`：模型仓库，不在仓库内。

```powershell
uv sync --python 3.12
.venv\Scripts\python.exe -m pytest          # 379 passed（当前）
```

---

## 2. 包结构

| 路径 | 职责 |
|---|---|
| `config.py` | 根发现、YAML 加载、路径解析、模型尺寸 |
| `models.py` | 严格 `Storyboard` 契约（**仅测试使用**） |
| `content_package.py` | 语料 + claim → `ContentPackage` |
| `script_engine.py` | LLM → `ProductionScript` + `narration.json` |
| `production.py` | `ProductionScript` → jobs / segments / motion plan |
| `quality.py` | 技术/音频/运动/美学检查 |
| `doctor.py` | 环境/服务/模型诊断 |
| `cli.py` | `doctor` / `serve` |
| `fonts.py` | 字体 manifest/角色/路径 |
| `locks.py` | 跨进程 PID 锁 |
| `style_presets.py` | `config/styles.yaml` 严格模型与导出 |
| `bible.py` | Character/Shot Bible 契约与连续性检查（不承诺同脸） |
| `style_consistency.py` | 跨镜头调色板/LAB/亮度/饱和度/边缘密度技术门 |
| `aesthetics.py` | 六维设计、A/B、提示词编译 |
| `motion/` | 相机、spec、local、render、transition、plates、texture |
| `voice/` | tts、pronunciation、recitation、timeline、soundscape、zeroshot、profiles、audio_assets、audio_timeline、mix |
| `workspace/` | SQLite、discovery、media、tasks、envprobe、api |
| `web/` | 无构建 ES Modules UI |

### 2.1 数据契约（实际）

| 契约 | 文件 | 生产消费者 |
|---|---|---|
| `ContentPackage` | `literary_intelligence/schemas/content_package.py` | `content_package.py`、`script_engine.py` |
| `ProductionScript` | `script_engine.py` | `production.py`、`aesthetic_plan.py`、`motion` |
| `MotionPlan/ShotSpec` | `motion/spec.py` | `motion/render.py`、`quality.py` |
| `AestheticPlan` | `aesthetics.py` | `aesthetic_plan.py`、`aesthetic_compare.py` |
| `Storyboard` | `models.py` | **仅测试**（历史/目标契约） |

> 改契约前先确认它是生产契约还是目标契约。不要把 `models.Storyboard` 当成当前生产边界。

---

## 3. CLI 与入口

| 命令 | 作用 |
|---|---|
| `drama doctor [--json] [--no-report]` | 环境诊断 |
| `drama serve [--host] [--port] [--reload]` | 工作台 |
| `python -m drama_studio.content_package` | 内容包 |
| `python -m drama_studio.script_engine` | 文案/分镜 |
| `python -m drama_studio.production` | jobs / segments / motion plan |
| `python -m drama_studio.quality` | 质量检查 |
| `python -m drama_studio.style_presets` | 列出/导出风格 |
| `python -m literary_intelligence.run_li15` | LI 五轮 |
| `scripts\r1_batch.py` | ComfyUI 批处理 |
| `scripts\r3_tts.py` | TTS |
| `scripts\r3_build.py` | 合成 |
| `scripts\motion_build.py` | 运动渲染 |
| `scripts\aesthetic_plan.py` / `aesthetic_compare.py` | 美学 A/B |
| `scripts\static_quality.py` | 静态门（CLI） |
| `scripts\make_bgm.py` | 重建两条自生成 BGM 铺底 |
| `scripts\make_sfx.py` | 重建风声/水声/钟磬/转场 SFX |
| `scripts ideo_jobs.py` | 为 `type=video` 镜头从 FLUX 关键帧生成 Wan I2V jobs |
| `scripts\tts_qa.py` | ASR 代理 |
| `scripts\fetch_fonts.py` | 字体重建 |

`python -m drama_studio.production` 的两种模式：

```text
默认：--script --images --audio --out [--clips | --sequence] [--align-audio ...]
--motion-plan：--script --images --audio --out --style ... [--regions ...]
```

---

## 4. 工作台 API

| 方法 | 路由 | 作用 |
|---|---|---|
| GET | `/api/health` | 版本/根目录 |
| GET | `/api/overview` | 统计、最近期数/任务、环境 |
| GET/POST/PATCH | `/api/projects`、`/api/projects/{id}` | 项目 CRUD |
| GET/POST/PATCH | `/api/episodes`、`/api/episodes/{id}` | 期数 CRUD/状态派生 |
| GET | `/api/episodes/{id}/content` | 内容视图 |
| GET | `/api/episodes/{id}/storyboard` | 分镜视图 |
| GET | `/api/episodes/{id}/audio` | 音频视图 |
| GET | `/api/episodes/{id}/assets` | 期数素材 |
| GET | `/api/episodes/{id}/output` | 成片/构建 |
| GET | `/api/episodes/{id}/workflow` | 工作流节点 |
| GET/POST/PATCH | `/api/styles`、`/api/styles/{id}` | 风格 CRUD |
| GET | `/api/tasks` | 任务列表 |
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks/{id}` | 任务详情 |
| GET | `/api/tasks/kinds` | 任务注册表 |
| GET | `/api/tasks/{id}/log` | 日志分页 |
| POST | `/api/tasks/{id}/cancel` | 取消 |
| GET | `/api/media/{path}` | Range 媒体 |
| GET | `/api/thumb/{path}` | 缩略图 |
| GET | `/api/env` | 服务/工具/磁盘/GPU |
| GET | `/api/assets` | 素材扫描 |

写入只走注册表；没有任意 shell、没有任意路径。

---

## 5. 任务注册表

定义在 `src/drama_studio/workspace/tasks.py` 的 `TASK_KINDS`（23 种）。每种任务包含：

```python
TaskKind(
  key, label, description, cost, safety,
  params_model, lock_key, build_argv,
  handler=None, prerequisites=..., after_success=..., danger=False,
)
```

执行模型：

1. `create()` 校验参数、单飞锁、前置条件；
2. 满足则 `insert_task` + `asyncio.create_task(_execute)`；
3. `_execute()` 条件迁移到 `RUNNING`，启动子进程或 in-process handler；
4. 实时把 stdout 写日志；
5. exit 0 后执行 `after_success`（哈希/文件校验），失败则任务 `FAILED`；
6. 取消会 `taskkill /T /F` 并写 `CANCELLED`。

### 5.1 新增任务

1. 在 `tasks.py` 定义 `*Params(BaseModel)`（`extra="forbid"`）。
2. 写 `_kind_paths/_prereqs/_argv/_after`。
3. 注册 `TaskKind`，选 `lock_key`（GPU/LLM/TTS/阶段）。
4. 危险任务设 `danger=True` + `confirm` 字段。
5. 更新 `tasks.js` 的 `launcherForm`（否则 UI 没有字段）。
6. 加 API/任务测试；不要允许任意路径。

### 5.2 当前未注册但应注册的能力

- `static_quality.py` → 已注册 `static.check`；`style_consistency.py` → 已注册 `style.consistency`；
- `tts_qa.py` → 建议 `audio.asr`（需 CosyVoice venv）；
- `scroll_shot.py` → 长卷路径仍靠 CLI。

---

## 6. ComfyUI 集成

### 6.1 协议

- 只使用 API 格式工作流。
- 占位符是整值字符串 `"{{seed}}"`，按 JSON 树替换，保留 number/string 类型。
- 调用链：`POST /prompt` → 轮询 `/history/{prompt_id}` → `/view` 下载。
- 本地 HTTP 必须 `trust_env=False`（Python）或 `curl.exe`（PowerShell）。
- 输出目录：`<job.out>/job.json`、`workflow.submitted.json`、`history.json`、`probe_attempt*.log`。

### 6.2 工作流

| 文件 | 节点要点 |
|---|---|
| `r0_flux_t2i_api.json` | `UnetLoaderGGUF` → `CLIPLoader(flux2, cpu)` → `Flux2Scheduler` + `CFGGuider(1.0)` + `SamplerCustomAdvanced` |
| `r1_flux_edit_api.json` | `LoadImage → VAEEncode → ReferenceLatent` + `EmptyFlux2LatentImage` |
| `r0_wan_i2v_api.json` | `Wan22ImageToVideoLatent` + `ModelSamplingSD3(shift=8)` + `KSampler(uni_pc, simple, 20)` |
| `r0_wan_t2v_api.json` | 同上，无 `start_image` |
| `m8_flux2_inpaint_api.json` | `LoadImageMask → SetLatentNoiseMask`（实验） |

### 6.3 新增/修改工作流

1. 从 ComfyUI 官方模板确认节点参数；
2. 只放 API 格式；
3. 占位符必须是整值字符串；
4. 先跑 R0 小尺寸验证，记录 `logs/r0/engine-versions.txt` 与 workflow sha；
5. 未验证工作流不得进入生产；
6. 记录模型 hash、seed、prompt、峰值 VRAM。

---

## 7. 运动与 FFmpeg

### 7.1 运动链路

```text
ProductionScript
  -> build_motion_plan（style policy + regions + audio timing）
  -> motion_shots.json
  -> motion_build.py
  -> motion/render.py: camera_pre -> local layers -> camera_post -> FFmpeg
  -> motion_manifest.json + sequence
  -> build_segments(sequence=...)
  -> r3_build.py
```

关键约束：

- `camera.py` 是确定性表达式；不要引入随机/非确定运动。
- `RegionSpec` 的 `locked/hard_excluded` 会自动从局部层 alpha 扣除；`reflection` 必须 `follows` 一个 `rigid_object`。
- `LocalMotionSpec` 只能使用风格 `local_policy` 启用的类型；区域合同优先。
- `layered_parallax` 在 `render.py` 显式拒绝无 plates 的镜头；plates 是 opt-in。
- 转场只消耗上一镜头尾部 handle；序列时长 = 镜头时长之和。
- 序列短于旁白时 `segments.build` 直接失败，不拉伸冻结画面。

### 7.2 FFmpeg

- `r3_build.py` 是正式合成；不要另写第二套。
- 1080×1920 / 24 fps；libx264 CRF 18；AAC 192k；mov_text；faststart。
- 字幕 ASS 显式 `PlayRes 1080×1920`；fontselect 强校验。
- 新构建写新目录；不要覆盖历史。
- 当前 `soundscape.enabled=true`；改音频链路前先看 `voice/soundscape.py` 的实测阻断（afir）。

---

## 8. 工作台状态派生

- `workspace/store.py`：只存用户事实（projects/episodes/styles/tasks）。
- `workspace/discovery.py`：从 `narration.json`、`segments.json`、`audio_manifest.json`、`build_manifest.json`、哈希、ffprobe 派生步骤。
- `PASS_VERIFIED` 必须有文件/哈希/任务证据；缺失即 `NOT_RUN`。
- `progress` 只统计必需步骤的 `PASS_VERIFIED`。
- `recover_stale_tasks` 在服务启动时把遗留 `RUNNING` 标 `FAILED`。

### 8.1 已知派生缺口

| 缺口 | 位置 |
|---|---|
| 不读 `content_package.json` / `production_script.json` | `_analyze_video` |
| 不读 `aesthetic_plan.json` / `comparison.json` | `discovery` |
| 工作流页文案过期 | `discovery.py:1061-1062,1082` |
| 不显示 motion plan / static gate | `discovery` |
| `drifted` 只比 `updated_at`，不比内容哈希 | `_style_view` |

> 修这些属于 Phase C；Phase B 只记录。

---

## 9. 两种风格系统与目标设计

### 9.1 现状

- `config/styles.yaml`：完整 `StylePreset`，含 motion/compositing/aesthetic_profile；`motion.plan`/`aesthetic.plan` 只认它。
- `workspace.styles`：只存 `STYLE_ENTITY_FIELDS`；不含运动/美学策略；不自动导入。
- 期数 `style_snapshot`：冻结 DB 风格；`script.generate` 用它拼提示词。
- `motion.plan`/`aesthetic.plan`：从期数 `_style_lock.preset_id` 取 YAML preset；显式 `--style` 相同才允许，不同直接拒绝。P1 的 `style_p1_short` 已在 DB 映射为 `ink_wash`；`comfy.batch` 绑定 `episode_id` 时校验 `production_script.style_id`。
- `comfy.batch`：不校验 style。
- 质量：`static_quality` 按单图风格；`check_color_continuity` 只查相邻 LAB/亮度。

### 9.2 目标（Phase C 设计约束）

1. 作品级 `style_id` 单一来源；
2. 期数/ProductionScript/Shot/资产都带 `style_id`；
3. 所有生成任务从作品继承，禁止 `--style` 覆盖（或只有显式“新建风格版本”才能改）；
4. 改风格创建新版本/新生产目录，记录旧/新 style sha；
5. 质量门增加风格一致性检查（至少：同一 `style_id`、跨镜头风格指标、色板/材质/线条约束）；
6. DB 风格新增可选 `preset_id` 列并显式映射 YAML preset；不自动 seed，旧库在 `WorkspaceStore.init_schema()` 中做一次性只增迁移。

### 9.3 TTS 模式（已实现，2026-11-04）

1. `tts_mode` 显式参数（`sft` / `zero_shot`）；**PRD 默认 `zero_shot`**，SFT 仅显式选择；
2. zero-shot 必须提供 `prompt_audio/prompt_text`；SFT 使用 `speaker=中文女` 仅作为可选模式；
3. 调用前校验 CosyVoice `/health`：SFT 只允许 `CosyVoice` + `CosyVoice-300M-SFT`，zero-shot 只允许 `CosyVoice2` + `CosyVoice2-0.5B`；
4. manifest 记录 `tts_mode/model_class/model_dir/speaker/speaker_id/runtime/prompt`；
5. CLI/任务/设置页显示实际模式；任务结果记录 `tts_mode/model_class/speaker_id`；
6. `settings.tts.mode` 已删除，`audio.yaml tts.mode` 是唯一默认来源；默认已是 `zero_shot`；
7. `PRD-TTS-001` = `PASS_VERIFIED`：2026-11-04 默认 zero-shot 2 行真实 PASS；
8. `voice/profiles.py` + `config/voices.yaml` 提供多音色档案；逐行 `voice_profile` 可追溯，一次运行只允许同一后端模式；未 `APPROVED` 的档案默认拒绝。

**不要**恢复 `zero_shot.enabled` 之类的静默开关；新增模式必须同时更新运行时校验、manifest 与测试。

---

## 10. 测试

```powershell
# 全部（根 + LI）
.venv\Scripts\python.exe -m pytest

# 单文件
.venv\Scripts\python.exe -m pytest tests\test_production.py -q
.venv\Scripts\python.exe -m pytest literary_intelligence\tests -q

# 采集
.venv\Scripts\python.exe -m pytest --collect-only -q
```

当前 379 passed。测试覆盖：

| 区域 | 文件 |
|---|---|
| 配置/模型/doctor | `test_config`、`test_models`、`test_doctor` |
| ContentPackage/脚本 | `test_content_package_build`、`test_script_engine`、`test_short_text_fixture` |
| Production/quality | `test_production`、`test_quality`、`test_quality_plates` |
| Motion | `test_motion*`、`test_motion_regions`、`test_motion_plates*` |
| Voice | `test_voice_tts`、`test_pronunciation*`、`test_recitation`、`test_soundscape`、`test_voice_prompt` |
| Workspace | `test_workspace_*` |
| LI | `literary_intelligence/tests/*` |

测试原则：

- 不依赖真实实验资产；用 `tmp_path` 合成夹具。
- 不启动 GPU/LLM/TTS；用 mock transport 或纯函数。
- 失败保留原始输出；不要为了过测试放宽 Schema。
- 新增能力先有可执行验收，再有单测。

---

## 11. 扩展指南

### 11.1 新增内容主题

1. 在 `literary_intelligence/corpus/<id>/` 放原文/规范化/segments/registry/claims/reviews；
2. 确保 locator/quote/来源可校验；
3. `package.build` 生成 ContentPackage；
4. 不要硬编码作品名/诗句到 `src/`；`tests/test_no_hardcoded_works.py` 会扫描；
5. 主题相关的视觉方向放 `config/styles.yaml` 或 `designs.json`，不要写进通用代码。

### 11.2 新增视觉风格

1. 在 `config/styles.yaml` 增加 `StylePreset`：`visual_language/positive_prompt/motion/compositing/aesthetic_profile`；
2. 保证 `reference_assets/source_files/texture_asset` 存在；
3. 加 `tests/test_style_presets.py` 校验；
4. 跑 `static_quality.py --style <id>`；
5. 跑 `aesthetic.plan`/`motion.plan`/`m7` 类样片；
6. 不要自动 seed 到 `workspace.db`；工作台风格需要显式创建/导入；
7. 风格 id 不能按代码分支；只通过配置驱动。

### 11.3 新增 ComfyUI 工作流

见 §6.3。关键：API 格式、整值占位符、R0 验证、版本记录、模型 hash。

### 11.4 新增质量门

1. 在 `quality.py` 写纯函数，输入真实文件/manifest；
2. 返回 `{status, ...}`，不删除产物；
3. 加单测（合成视频/图片/音频）；
4. 接入 `TaskKind` 或 `motion.render` 后置；
5. UI 要能触发/显示（否则只是 CLI 门）。

### 11.5 新增工作台任务

见 §5.1。必须同时改：`tasks.py` + `tasks.js` + 测试 + 文档。

---

## 12. 代码规范与陷阱

### 12.1 规范

- 严格 Pydantic：`extra="forbid"`；ID/引用完整性。
- 路径必须相对仓库根或在白名单目录；拒绝 `..`/绝对路径/盘符。
- 本地 HTTP `trust_env=False`；PowerShell 用 `curl.exe`。
- 错误要保留原始输出/日志；重试有界。
- 不删除历史产物；新版本写新目录。
- 不把 CPU 说成 GPU；不把 `NOT_RUN` 说成 PASS。

### 12.2 陷阱

| 陷阱 | 说明 |
|---|---|
| `models.Storyboard` 不是生产契约 | 生产用 `ProductionScript` |
| `workspace.styles` ≠ `config/styles.yaml` | UI 风格不驱动 motion/aesthetic |
| TTS 模式不是“配置开关” | `audio.yaml tts.mode` 是默认；CLI/任务 `tts_mode` 显式覆盖；运行时模型必须匹配 |
| `subtitles.*`/`generation.profiles` 无效 | 不要以为改了会生效 |
| `static_quality` 不在任务注册表 | 动图前可能被绕过 |
| `quality.check` UI 不能选 motion manifest | 用 API/CLI |
| `comfy.batch` 不校验 style | 任务可跑任意 jobs |
| `r3_build --allow-overwrite` | 会覆盖历史，慎用 |
| `soundscape.enabled=true` | 新构建音频与历史不同 |
| 实验目录缺失 | 不要按 R1–R3 报告路径复跑 |

---

## 13. 当前测试/文档命令速查

```powershell
# 环境
scripts\doctor.ps1
.venv\Scripts\python.exe -m pytest

# 风格
.venv\Scripts\python.exe -m drama_studio.style_presets
.venv\Scripts\python.exe -m drama_studio.style_presets --id ink_wash --json
.venv\Scripts\python.exe -m drama_studio.style_consistency --style ink_wash --shot shot_001=path/a.png --shot shot_002=path/b.png --out report.json

# 字体
.venv\Scripts\python.exe scripts\fetch_fonts.py --check

# 质量
.venv\Scripts\python.exe -m drama_studio.quality --manifest <build_manifest.json> --root .
.venv\Scripts\python.exe -m drama_studio.quality --audio-manifest <audio_manifest.json> --timeline <timeline.json>
.venv\Scripts\python.exe -m drama_studio.quality --motion-manifest <motion_manifest.json> --root .
```
