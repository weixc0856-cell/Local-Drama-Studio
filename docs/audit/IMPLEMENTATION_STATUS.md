# 功能实现状态审计（Phase A）

> 审计日期：2026-11-04
> 审计基线：`main` / HEAD `06f91e4` + 未提交工作区（M8、声景、zero-shot）
> 状态口径：`PASS_VERIFIED` / `PASS_STATIC` / `PASS_LIMITED` / `PARTIAL` / `NOT_RUN` / `NOT_IMPLEMENTED` / `BLOCKED` / `UNKNOWN`
> 判定原则：
> 1. 有真实入口、真实产物、可复核证据 → `PASS_VERIFIED`；
> 2. 只过静态/单元/技术检查，未做人工审美或完整成片 → `PASS_STATIC` 或 `PARTIAL`；
> 3. 代码存在但本轮没执行 → `NOT_RUN`，不写成 PASS；
> 4. 只有文档/规划 → `NOT_IMPLEMENTED`；
> 5. 证据路径已缺失、无法判断 → `UNKNOWN`。

---

## 1. 总表（22 项）

| # | 模块 | 功能 | 实际入口 | 实现文件 | 测试证据 | 状态 | 限制 / 说明 |
|---|---|---|---|---|---|---|---|
| 1 | 环境管理 | 双 venv、uv、ComfyUI XPU、FFmpeg、模型尺寸校验 | `scripts\setup.ps1`、`drama doctor` | `config.py`、`doctor.py`、`setup.ps1` | `tests/test_config.py`、`tests/test_doctor.py`；本轮 `doctor` 15 PASS / 0 FAIL | **PASS_VERIFIED** | 三个服务当前未启动；`doctor` 只校验 4 份 YAML，不校验 styles/pronunciation/fonts |
| 2 | 配置管理 | `config/*.yaml` 加载、路径解析、严格风格校验 | `load_settings/load_models/load_generation/load_audio`、`load_style_presets` | `config.py`、`style_presets.py`、`fonts.py` | `test_config`、`test_style_presets`、`test_font_manifest` | **PASS_VERIFIED** | TTS 模式已接线（P0-1）；仍存在死字段：`subtitles.*`、`narration_modes.*.leading_ms`、`generation.profiles` |
| 3 | 数据契约 | 严格 Pydantic、ID/引用完整性、JSON Schema | 测试；`ProductionScript` 生产入口 | `models.py`、`script_engine.py`、`literary_intelligence/schemas/` | `test_models` 6、`test_script_engine` 4、LI schemas/roles | **PASS_VERIFIED**（契约本身） / **PARTIAL**（单一契约目标） | `models.Storyboard` **只被测试使用**；实际生产用 `ProductionScript`。两套契约并存 |
| 4 | ContentPackage | 已登记语料 + 证据校验 claim → 严格 draft | `python -m drama_studio.content_package`、`package.build` | `content_package.py`、`literary_intelligence/harness/*` | `test_content_package_build` 2；P1 真实 4 场景 | **PASS_VERIFIED**（短文本） / **PASS_LIMITED**（长篇） | 只验证了 4 句夹具；完整诗篇/长篇未跑；claim 全部未人工 approved |
| 5 | 文案生成 | 本地 LLM → `ProductionScript`；2 次有界修复；原始输出保留 | `python -m drama_studio.script_engine`、`script.generate` | `script_engine.py` | `test_script_engine` 4；P1 `script_raw_attempt1/2` + 最终脚本 | **PASS_VERIFIED**（CLI 真实 LLM） / **PARTIAL**（工作台新生成） | P1 真实任务 `task_20261103113359` 因后置校验 `ModuleNotFoundError` 被标记 FAILED；随后成功任务是 `--reuse`，未再次真实调用 LLM。当前代码已修，但“工作台新生成”未重新实证 |
| 6 | 分镜处理 | 3–5 镜头、覆盖全部台词、镜头 ID 连续、风格拼接 | 同上；`aesthetic.plan` 读取 | `script_engine.py`、`aesthetics.py` | `test_script_engine`、`test_aesthetics` 13 | **PASS_VERIFIED**（4 镜头） | `build_jobs` 为 image/video 镜头都生成 FLUX 关键帧；`build_video_jobs` 为 video 镜头生成 Wan I2V；镜头上限 24，脚本要求 3–5 |
| 7 | FLUX 图片生成 | ComfyUI 提交→轮询→下载→哈希；576×1024；4 步；CFG 1.0 | `scripts\r1_batch.py`、`comfy.batch` | `r0_comfy_probe.py`、`r1_batch.py`、`workflows/r0_flux_t2i_api.json` | P1 4/4、gongbi 13 张、R1/R3 报告；`logs/r0/R0-C-flux*` | **PASS_VERIFIED**（历史） / **NOT_RUN**（当前服务） | 8188 当前未监听；P1 生成 76.6/59.0/44.7/16.1 s；R3 竖屏 22–53 s/张 |
| 8 | Wan 视频生成 | Wan2.2 TI2V 5B，20 步，I2V/T2V，73 帧 | `r1_batch.py`（jobs JSON） | `workflows/r0_wan_*.json`、`r0_comfy_probe.py` | `docs/R2*`、`docs/R3*`、`assets/vertical/06_flower_pushin_wan.mp4`、`logs/r0/R0-D-wan-i2v` | **PASS_VERIFIED**（推近类） / **PASS_LIMITED**（精确主体位移） | 原 `experiments/r2*`、`r3a`、`r3b` 目录已缺失；报告仍在。H3 船体 24.6 px 但方向错误；121 帧有颜色漂移 |
| 9 | 参考图/关键帧 | FLUX ReferenceLatent 编辑；J2 参考；4 张 16:9 关键帧 | `r1_batch.py` + `workflows/r1_flux_edit_api.json` | 同左 + `assets/*.meta.json` | `assets/keyframes/*.meta.json`、`assets/visual_style/reference/*.meta.json`、R1 报告 | **PASS_VERIFIED** | 一致性是“空间锚点稳定”，不是人物/跨镜头同一张脸；KF4 光源有歧义 |
| 10 | CosyVoice 配音 | 逐句 TTS、48 kHz、四层文本、发音词典、manifest 哈希；SFT/zero-shot 显式模式 | `scripts/r3_tts.py`、`tts.synthesize` | `voice/tts.py`、`pronunciation.py`、`recitation.py`、`zeroshot.py` | `test_voice_tts` 9、`test_voice_profiles` 9、`test_pronunciation*` 20、`test_recitation` 4、`test_voice_prompt` 6；P1 4 行、gongbi 18 行、M7 4 行、voice profile 2 行 | **PASS_VERIFIED**（PRD-TTS-001：默认 0.5B zero-shot 真实 2 行；显式 SFT 1 行） | 默认 `tts.mode: zero_shot`；`/health` 校验 0.5B；manifest 记录 `tts_mode/model_class/model_dir/speaker/speaker_id/runtime/prompt`；`config/voices.yaml` + 逐行 `voice_cast`；错配双向拒绝 |
| 11 | 字幕生成 | SRT + ASS、整数毫秒时间轴、本地字体、fontselect 校验 | `scripts\r3_build.py`、`build.rebuild` | `voice/timeline.py`、`fonts.py`、`r3_build.py` | P1/M7/gongbi `drama.srt`/`drama.ass`/`timeline.json`/`fontselect.log`；`test_fonts` | **PASS_VERIFIED** | `config/audio.yaml` 的 `subtitles.max_chars_per_line/max_lines/format/burn_in` **未被消费**；每行一条字幕，不自动换行；`burn_in` 总是尝试生成烧录版 |
| 12 | FFmpeg 合成 | 1080×1920 / 24 fps / H.264 + AAC + mov_text；Ken Burns；混音；淡入淡出 | `scripts\r3_build.py`、`build.rebuild` | `r3_build.py`、`voice/soundscape.py` | P1 14.0 s、R3 38.042 s、gongbi 81.373 s、M7 两片；`quality_report` PASS | **PASS_VERIFIED** | 1080×1920 是 Lanczos 放大，不是原生；每次构建写新目录，拒绝覆盖；当前 `soundscape.enabled=true` 会让新构建与历史构建音频不同 |
| 13 | 质量检查 | 图片空/黑、视频解码/分辨率、音频峰值/静音、成片哈希；运动/美学风险 | `python -m drama_studio.quality`、`quality.check`、`motion.render` 后置 | `quality.py` | `test_quality` 3、`test_motion_quality_gates` 11、`test_quality_plates` 9 | **PASS_VERIFIED**（技术） / **PARTIAL**（运动/美学） | 技术门是独立的；运动门 `motion.render` 会跑，但 `quality.check` UI 只暴露 `manifest`，无法从 UI 选 `motion_manifest`；发音正确性只到 `PARTIAL` |
| 14 | 任务注册表 | 23 种任务；参数 Pydantic；单飞锁；前置/后置；日志；取消 | `drama serve` → `/api/tasks` | `workspace/tasks.py` | `test_workspace_*` 37、`test_workspace_motion_tasks` 1；DB 39 个任务 | **PASS_VERIFIED** | 注册表不是唯一执行路径：`scripts/*.py` 可直接跑；CLI 只对 GPU 有跨进程锁，TTS/LLM 无 |
| 15 | GPU 单飞锁 | `logs/locks/gpu-comfy.lock` + SQLite `lock_key` 唯一索引 | `r1_batch.py`、`comfy.batch` | `locks.py`、`store.py` SCHEMA | `test_locks` 3、`test_workspace_store` 6 | **PASS_VERIFIED** | 只覆盖 ComfyUI/GPU；TTS、LLM、FFmpeg 不共享此锁；`service.comfy.start` 的前置 lambda 实际总是空 |
| 16 | 任务恢复 | 服务重启把遗留 `RUNNING` 标成 `FAILED`；取消条件迁移 | `drama serve` lifespan | `store.recover_stale_tasks`、`tasks.TaskRunner._execute` | `test_workspace_store`、`test_workspace_review` | **PASS_VERIFIED**（代码/测试） | 没有真实崩溃恢复演练；中断后不会自动重跑，只标记失败 |
| 17 | SQLite 工作台 | projects/episodes/styles/tasks/meta；只存用户事实 | `drama serve` | `workspace/store.py` | `test_workspace_store` 6；真实 DB 4/4/4/39 | **PASS_VERIFIED** | 生产状态不落库；`styles` 与 `config/styles.yaml` 不自动同步 |
| 18 | Web 页面 | 9 个导航页 + 期数 7 Tab；真实派生数据；媒体 Range/缩略图 | `drama serve --port 8765` | `workspace/api.py`、`web/**` | `test_workspace_api` 8、`test_workspace_media` 11；历史 Puppeteer 34/34 | **PASS_VERIFIED**（API/页面） / **PARTIAL**（浏览器 E2E 可复跑） | 浏览器 E2E 脚本与截图未入库，当前不能复跑；工作流页文案有过期内容（见 §3.3） |
| 19 | 日志与监控 | 任务日志、doctor JSON、服务日志、锁日志 | `logs/workspace/tasks/*.log`、`logs/doctor-*.json` | `tasks.read_log`、`doctor.write_report` | 39 个任务日志；多份 doctor JSON | **PARTIAL** | 没有统一指标/告警；没有历史成本聚合；日志按任务分散 |
| 20 | 素材管理 | 扫描、归属、引用/临时分类、缩略图、Range | `/api/assets`、`/api/thumb` | `workspace/discovery.scan_assets`、`media.py` | `test_workspace_media`、`test_workspace_discovery` | **PARTIAL** | 只有目录扫描与构建目录；没有正式资产台账/版本号/生命周期 |
| 21 | 授权管理 | 模型/字体/音频素材登记；BGM/SFX 候选 | 文档 + `assets/audio/manifest.json` + `assets/fonts/font_manifest.json` | 文档、manifest | 字体 `fetch_fonts --check`：2 个字族 / 6 个字重均 ok；音频 manifest 3 项 | **PARTIAL** | 字体/合成 IR/自录声音已登记；BGM、环境音、商用授权仍 `NOT_RUN` |
| 22 | 平台发布准备 | 封面/标题/正文/话题/合规 | 仅文档 | `docs/PLATFORM_PUBLISHING_SPEC.md` | 无代码/无测试 | **NOT_IMPLEMENTED** | 没有发布 API、没有平台数据记录、没有自动发布；v1.0 明确不做 |

---

## 2. 逐项证据与限制

### 2.1 环境管理（1）

- 双 venv 边界成立：根 `.venv` 无 torch；`runtime/ComfyUI/.venv` 有 torch 2.15.0+xpu。
- `doctor` 的模型检查用精确字节数，能拒绝未下载完的文件（`config.py` `ModelSpec.sizes` + `doctor._model_checks`）。
- 缺口：`doctor._config_checks` 只加载 settings/models/generation/audio，不加载 `styles.yaml`、`pronunciation.yaml`、`fonts.yaml`。这三份配置坏了，doctor 仍可能报 `cfg.load PASS_VERIFIED`。

### 2.2 配置管理（2）

- 已确认的“死配置”：
  - `config/settings.yaml` `tts.mode`：`voice/tts.py` 只读 `settings.tts.base_url/sample_rate`，不读 `mode`。
  - `config/audio.yaml` `tts.mode`：Phase C P0-1 后是唯一默认来源；CLI/任务 `tts_mode` 显式覆盖。
  - `config/audio.yaml` `subtitles.format/max_chars_per_line/max_lines/burn_in`：`r3_build.py` 未读取。
  - `config/audio.yaml` `narration_modes.*.leading_ms`：`ModeSpec.leading_ms` 只被序列化，`r3_build` 用 `content_type` 默认或显式 `--leading-ms`。
- `config/generation.yaml` 的 `profiles` 没有被生产构建消费；`production.build_jobs` 自带默认 576×1024 / 4 步 / CFG 1.0。
- `config/styles.yaml` 的 `validation_status` 已于 2026-11-04 从 `NOT_RUN` 更新为 `PARTIAL`（技术样片 + A/B 选型；完整作品未做）。

### 2.3 数据契约（3）

- `models.Storyboard` 有 6 项测试，但 `grep` 显示生产代码不导入它。
- `ProductionScript` 是实际边界：`ScriptLine`、`ScriptShot`、引用完整性、`style_sha256`、`package_sha256`。
- `ContentPackage` 是另一条边界：`literary_intelligence/schemas/content_package.py`，被 `content_package.py` 和 `script_engine.py` 消费。
- 风险：文档/CLAUDE 仍把 `Storyboard` 写成“数据契约边界”，新开发者可能把 LLM 输出校验到错误模型。

### 2.4 ContentPackage（4）

- 真实产物：`projects/proj_p1_short/.../work/content_package.json`，4 场景，4 条 original_text claim，全部 `unreviewed`，warnings 5。
- 证据校验：claim 的 quote 必须出现在规范化原文；未知 source/locator 会拒绝。
- 限制：只跑了 4 句短夹具；完整 18 联诗篇的 ContentPackage 未生成；`verification_status=draft`。
- 代码注释说 schema 上限 120 subtitles / 60 scenes；长篇是否超限未实测。

### 2.5 文案生成（5）

- P1 真实 LLM：`production_script.json` 记录 `model=Qwen3-30B-A3B-Instruct-2507`、`generated_at=2026-11-03T11:35:55Z`、4 行 / 4 镜头。
- `script_raw_attempt1.json` / `attempt2.json` 保留两次尝试；第二次通过 Schema。
- 失败任务：`task_20261103113359_9bb953` 的子进程 exit 0，但后置校验抛 `ModuleNotFoundError: literary_intelligence`，任务被标 FAILED。
- 之后 `task_20261103113814_907979` / `...113859` 用 `--reuse` 成功；`--reuse` 只验证现有脚本，不调用 LLM。
- 结论：CLI 真实 LLM 能力已证明；工作台“新生成”路径在修复后没有重新实证。

### 2.6 分镜（6）

- `DraftScript` 强制 3–5 镜头；`ProductionScript` 强制镜头索引连续、每行至少被一个镜头覆盖。
- `build_jobs` 为所有镜头生成 FLUX 关键帧；`build_video_jobs` 只为 `type=video` 生成 Wan I2V jobs。
- P1 4 镜头/4 行；gongbi 13 镜头/18 行（由人工脚本生成，不是 LLM 3–5 限制路径）。

### 2.7 FLUX（7）

- 工作流：`UnetLoaderGGUF` → `CLIPLoader(type=flux2, device=cpu)` → `Flux2Scheduler` + `CFGGuider(1.0)` + `SamplerCustomAdvanced`；负向条件 `ConditioningZeroOut`，CFG 1.0。
- P1 4 张图：76.6 / 59.0 / 44.7 / 16.1 s（workspace 任务记录）；gongbi 13 张（含重绘）。
- R0-C 日志仍在；R1/R3 run 目录已缺失。

### 2.8 Wan（8）

- 工作流：`Wan22ImageToVideoLatent`（48-ch）、`ModelSamplingSD3(shift=8)`、`uni_pc/simple`、CFG 5、20 步。
- R0-D 日志仍在；R2/R2-B/R3 报告记录 73 帧 40–43 min、121 帧 66–69 min、峰值 ≤6.12 GiB。
- 精确主体位移不可靠（H3 方向错误）；Wan 只适合缓慢推近/局部动态。
- 原 R2/R3 输入目录缺失，无法按报告路径复跑。

### 2.9 参考图/关键帧（9）

- `assets/keyframes/kf01..kf04` 4 张 768×432 + meta；`relationships.json` 记录月亮路径、共享锚点、已知限制。
- `assets/visual_style/reference/style_ref_river_16x9.png` 是 J2 主参考；meta 记录 seed 1101、workflow sha、耗时 101.49 s、峰值 2.80 GB。
- 参考图编辑工作流 `r1_flux_edit_api.json` 已验证；不代表人物一致性。

### 2.10 CosyVoice（10）

- SFT 路径：P1 4 行「中文女」、gongbi 18 行「中文女」、M7 2 行/片；manifest 记录 speaker/speed/sample_rate/哈希。
- zero-shot 路径：`scripts/zeroshot.py` + `/tts/upload`；`experiments/audio_probe/zeroshot_e2e` 2 行，speaker `zero_shot:my_voice_clean_v1`，mode `classical_recitation`。
- **模式已显式化（P0-1）**：默认 `zero_shot` + 0.5B；显式 `--tts-mode`、`/health` 校验、manifest 记录均已落地；`PRD-TTS-001` = `PASS_VERIFIED`。
- `scripts/cosyvoice_server.ps1` 可切 `cosyvoice2` / `sft`，但工作台没有该任务入口；CLI 也没有 `--speaker-mode`。
- 发音：5 条 verified 同音别名；ASR 18/18 拼音通过、max pinyin CER 0.143；人工复核 PENDING。

### 2.11 字幕（11）

- `build_timeline` 生成整数毫秒 `speech_start/end`、`subtitle_start/end`；字幕不早于语音、不吞尾部停顿。
- `r3_build` 生成 SRT + ASS；ASS 显式 `PlayRes 1080×1920`；fontselect 必须命中配置的 PostScript 名，否则构建失败。
- 配置缺口：`subtitles.max_chars_per_line/max_lines` 未使用；长句不会自动换行。
- `burn_in` 配置未使用：脚本总是尝试生成 `final_9x16_burned.mp4`。

### 2.12 FFmpeg（12）

- `r3_build` 是唯一正式合成入口：逐段生成 1080×1920/24fps、concat、淡入淡出、逐行 adelay + amix + alimiter + apad、可选 soundscape 两遍响度、SRT/ASS、软/烧录成片、ffprobe/解码。
- 保护：已有 `final_9x16.mp4` 时拒绝覆盖，除非 `--allow-overwrite`；工作台 `build.rebuild` 总是写新时间戳目录。
- 当前 `soundscape.enabled=true`：新构建会走 `master()`（EQ + 早期反射 + 两遍响度），历史构建 manifest 的 `soundscape` 为 `null`，不能直接对比音频。

### 2.13 质量（13）

- 技术门：`check_image`（stddev/mean 空黑）、`check_video`（ffprobe + 全解码 + 尺寸）、`check_audio`（volumedetect、削波、静音比例）、`check_build`（final 1080×1920、哈希、分段素材、混音）。
- 运动门：`check_motion_quality`（刚体保护 + 时序连续性）；`motion.render` 默认执行，失败即任务失败。
- 美学风险：`check_aesthetic_risk`、`check_dynamic_aesthetics`、`check_rigid_protection`、`check_plate_reveal`。
- 限制：`quality.check` UI 只暴露 `manifest`，`motion_manifest` 只能走 API/CLI；发音只到 PARTIAL。

### 2.14 任务注册表（14）

23 种任务：

```text
doctor.run, build.rebuild, comfy.batch, li.run,
service.comfy.start, service.comfy.stop,
package.build, script.generate, segments.build,
motion.plan, motion.render, audio.qa,
aesthetic.plan, aesthetic.compare, aesthetic.review,
static.check, style.consistency, story.check, quality.check, tts.synthesize,
review.accept, review.reject
```

真实执行过的（DB 39 条）：`doctor.run`(1)、`build.rebuild`(5)、`comfy.batch`(8)、`package.build`(2)、`script.generate`(7)、`segments.build`(7)、`tts.synthesize`(4)、`quality.check`(5)。

**未通过工作台真实执行**：`li.run`、`service.comfy.*`、`motion.plan`、`motion.render`、`audio.qa`、`aesthetic.*`（这些走 CLI/实验）。注册不等于已验证。

### 2.15 GPU 单飞（15）

- `workspace` 用 SQLite partial unique index：同一 `lock_key` 只能有一个 `RUNNING`。
- `r1_batch.py` 用 `logs/locks/gpu-comfy.lock`，直接 CLI 跑也受保护。
- `locks.py` 是 PID 感知锁，进程死亡可回收。
- 缺口：TTS、LLM、FFmpeg 没有跨进程锁；`service.comfy.start` 的前置检查是空 lambda。

### 2.16 任务恢复（16）

- `recover_stale_tasks` 在 FastAPI lifespan 把遗留 `RUNNING` 全部标 `FAILED`，写“服务重启时任务仍在运行，已标记为中断”。
- `TaskRunner._execute` 在启动前后都检查 `CANCELLED`，取消会 `taskkill /T /F`。
- 没有自动续跑；没有“从断点继续”的任务语义。

### 2.17 SQLite（17）

- schema：`projects`、`episodes`、`styles`、`tasks`、`meta`；JSON 字段编码；外键与唯一索引。
- 真实 DB：4 项目 / 4 期数 / 4 风格 / 39 任务；2 个 FAILED。
- `styles` 是用户事实，不是 `config/styles.yaml` 的镜像；`style_snapshot` 在期数创建时冻结。

### 2.18 Web（18）

- 9 个导航页；期数 7 Tab；任务中心支持日志、取消、重跑；素材库支持图片/视频/音频/字幕/JSON/字体/日志筛选。
- 路由：`/api/overview`、`/api/projects`、`/api/episodes`、`/api/tasks`、`/api/styles`、`/api/assets`、`/api/env`、`/api/media`、`/api/thumb`。
- 浏览器 E2E 34/34 是历史报告；当前没有可复跑脚本/截图入库。

### 2.19 日志/监控（19）

- 任务日志在 `logs/workspace/tasks/task_*.log`；`/api/tasks/{id}/log` 支持 offset 分页。
- doctor 报告 JSON；服务日志 `comfyui.*`、`cosyvoice.*`、`llm-8080.*`；锁日志 `logs/locks/`。
- 没有统一监控面板、成本聚合、失败率趋势、告警。

### 2.20 素材管理（20）

- `scan_assets` 按类型/期数/引用/临时分类；`media.safe_path` 白名单只允许 assets/experiments/projects/literary_intelligence/workflows。
- 缺口：没有资产 ID/版本/生命周期/授权字段的统一台账；`assets/audio/manifest.json` 是一个独立局部清单。

### 2.21 授权（21）

- 字体：`font_manifest.json` + LICENSE；`fetch_fonts --check`：2 个字族 / 6 个字重均 ok。
- 音频：`assets/audio/manifest.json` 登记合成 IR、自录参考音、清理版参考音；`VOICE_RIGHTS.md`。
- 模型许可证：`docs/ASSET_AND_LICENSE_REGISTRY.md`。
- BGM、环境音、商用授权：`NOT_RUN`。

### 2.22 平台发布（22）

- 只有 `docs/PLATFORM_PUBLISHING_SPEC.md`（封面/标题/正文/话题/合规）。
- 没有代码、没有平台 API、没有数据记录。

---

### 2.23 作品级风格锁定与 TTS 模式（2026-11-04 产品决策）

> 本节原为 Phase B 的产品决策/现状对照；TTS 部分已在 Phase C P0-1（2026-11-04）实施。双视觉风格仍为现状对照。

#### TTS 目标决策（PASS_VERIFIED：默认 0.5B zero-shot）

| 项 | 产品目标 | 当前实现 |
|---|---|---|
| 默认模式 | **CosyVoice2-0.5B zero-shot** | `config/audio.yaml` `tts.mode: zero_shot`；默认任务真实 0.5B 2 行 PASS |
| 默认音色 | zero-shot 参考音 | `zero_shot.prompt_audio` 默认使用；`narrator_self` 档案真实 2 行 PASS |
| 可选模式 | **SFT，显式选择**，使用 CosyVoice-300M-SFT | `--tts-mode sft` / 任务 `tts_mode`；`/health` 校验 `CosyVoice` + `CosyVoice-300M-SFT` |
| 模式可识别 | UI、CLI、任务记录、`audio_manifest.json` 记录 mode/model/voice | CLI 输出与任务结果有 `tts_mode/model_class/speaker_id`；manifest 有 `tts_mode/model_class/model_dir/speaker/speaker_id/runtime/prompt` |
| 模型对应 | 300M-SFT = SFT；0.5B = zero-shot | 运行时由 `start_cosyvoice_sft.bat` / `start_cosyvoice.bat` 选择；调用前 `/health` 双向校验，错配直接失败 |
| 真实验证 | 两种模式分别跑通 | 2026-11-04 默认 zero-shot 2 行 + 显式 SFT 1 行；双向错配拒绝；2 行 `voice_profile` 真实 PASS |

已核实的运行时映射（只读检查 `D:\AI\CosyVoice-Runtime`）：

```text
start_cosyvoice_sft.bat  COSY_MODEL_CLASS=CosyVoice
                         COSY_MODEL_DIR=pretrained_models\CosyVoice-300M-SFT
                         -> api_server._synthesize_sft() -> inference_sft()
start_cosyvoice.bat      COSY_MODEL_CLASS=CosyVoice2
                         COSY_MODEL_DIR=pretrained_models\CosyVoice2-0.5B
                         -> api_server._synthesize() -> inference_zero_shot()
```

`api_server.py` 的 `/health` 返回 `model_class`、`model_dir`、`speakers`、`modes`；`/tts` 在 `speaker` 非空时走 SFT，否则走 zero-shot。代码不再根据 `enabled` 开关静默切换。

#### 双视觉风格目标决策

| 规则 | 目标 | 当前实现 |
|---|---|---|
| 每个作品一个主风格 | 作品级 `style_id` | 期数 `style_snapshot._style_lock`（revision/hash）；项目 `default_style_id` 仍非强制 |
| 全片风格一致 | 第一帧到最后一帧不切换 | `style_lock` 锁定期数 snapshot；`motion.plan` / `aesthetic.plan` / `static.check` 拒绝不同 style；`comfy.batch` 仍未按 episode 校验 |
| 两种风格独立规范 | 视觉规范/提示词/参数/质量评价独立 | `config/styles.yaml` 有独立 `visual_language/positive_prompt/motion/aesthetic_profile`；`static_quality.py` 有独立 checklist |
| 生成任务不得覆盖 | 任务只继承作品风格 | `style_lock.assert_style_request` 已接入 `motion.plan` / `aesthetic.plan` / `static.check`；其他任务待补 |
| 改风格要新版本 | 新风格版本或新生产版本，并记录 | `attach_lock` revision+1，`history` 保留旧 sha/revision；旧 build 不覆盖；UI 新风格入口待做 |
| 质量检查风格一致性 | 能检查风格一致性 | `static_quality` 按风格检查单图；`style_consistency.py` 检查调色板/跨镜头 LAB/亮度/饱和度/边缘密度；人工审片仍 PENDING |
| 两种风格共享基础设施 | FLUX/Wan/FFmpeg 共用 | 是；代码只按 preset 配置分支，不按 style id 写死 |

#### 两套风格系统的实际断层

- `config/styles.yaml` 的 `StylePreset` 含 `motion`、`compositing`、`aesthetic_profile`；`motion.plan` / `aesthetic.plan` 只认这套 YAML preset id。
- `workspace.styles` 只存 `STYLE_ENTITY_FIELDS`（视觉描述、提示词、色板等），**不含 motion/compositing/aesthetic_profile**；`as_style_entity()` 明确只导出工作台字段。
- 因此 UI 里创建/编辑的风格，不能直接驱动 `motion.plan` / `aesthetic.plan`；P1 的 `style_p1_short` 不是 YAML preset，P1 motion 必须显式 `--style ink_wash`（`motion_plan.meta.json` 也记录 `style_id=ink_wash`）。
- 期数 `style_snapshot` 被 `script.generate` 写入 `style_snapshot.json`，`ProductionScript.style_id` 记录 snapshot id；这保证了“提示词层”的冻结，但不能保证“运动/美学层”的 preset 一致。

#### 结论（按三件事分别评价 S3）

| 评价项 | 状态 | 依据 |
|---|---|---|
| 两种视觉风格是否已建立独立规范和配置 | **PASS_STATIC** | `config/styles.yaml` + `style_presets.py` + `docs/VISUAL_STYLE_SPEC.md` + 8 项测试 |
| 两种风格是否分别完成技术生产验证 | **PASS_VERIFIED**（各 2 镜头技术样片 + M7 人工审片记录） | `experiments/m7_final/ink` 10.087 s、`court` 9.583 s；质量/音频 QA PASS；M7 报告记录人工审片通过 |
| 单篇作品是否具备作品级风格锁定 + 跨镜头一致性验证 | **IMPLEMENTED_NOT_VERIFIED**（锁定）/ **PASS_VERIFIED**（P1 跨镜头一致性） | 期数 `_style_lock` + `preset_id`；`style.consistency`；P1 修正后 ΔE 9.22 / luma 7.13 + 人工通过；最终 build 接入待做 |

> M7 的两支短片只能作为“对应风格的技术证据”，不能直接证明完整作品的跨镜头一致性已经验证。81.373 s 工笔是更长案例，但它使用预渲染 clips，同样不是 `motion.plan` 自动运动管线的证据。


## 3. 历史验证索引（区分“实验 PASS”与“生产集成”）

| 阶段 | 文档/证据 | 实验结论 | 生产代码已实现 | 生产入口可调用 | 真实端到端 |
|---|---|---|---|---|---|
| R0-A 硬件/依赖 | `docs/R0_TEST_REPORT.md`、`logs/r0/*` | `PASS_VERIFIED` | 是（doctor） | 是 | 是 |
| R0-B ComfyUI/XPU | 同上 | `PASS_VERIFIED` | 是 | 是 | 是 |
| R0-C FLUX 512 | `logs/r0/R0-C-flux*` | `PASS_VERIFIED` | 是 | 是 | 是 |
| R0-D Wan 512 | `logs/r0/R0-D-wan-i2v` | `PASS_VERIFIED` | 是 | 是 | 是 |
| R0-E 模型互斥 | `docs/R0_TEST_REPORT.md` | `PASS_VERIFIED` | 是（锁/批处理） | 是 | 历史 |
| R1-A~E | `docs/R1_*`、`assets/keyframes`、`assets/visual_style` | `PASS_VERIFIED` | 是（jobs/参考图） | 是 | 历史；run 目录缺失 |
| R2-A 1024×576 | `docs/R2_TEST_REPORT.md` | 73 帧 PASS；121 帧 PASS_LIMITED | 是（Wan jobs） | 是 | 历史；run 目录缺失 |
| R2-B 英雄镜头 | `docs/R2B_TEST_REPORT.md` | 4/4 技术；H2 PASS，H1/H3/H4 LIMITED | 部分（无专用脚本） | 手工 jobs | 历史；run 目录缺失 |
| R3-A 竖屏 | `docs/R3_TEST_REPORT.md`、`assets/vertical` | `PASS_VERIFIED` | 是（576×1024 默认） | 是 | 历史 |
| R3-B 38 s 成片 | `docs/R3_TEST_REPORT.md`、`projects/proj_chunjiang/.../build-20261103-074757` | `PASS_VERIFIED` | 是（r3_build） | 是 | 成片/manifest 在；输入缺失 |
| R3-C 成本 | `docs/R3_TEST_REPORT.md` | `PASS_VERIFIED`（43.8 min/篇） | 无调度器 | 否 | 单篇计时 |
| R3-D 声音/字体/BGM/SFX | `docs/R3D_*`、`fonts.yaml`、`audio.yaml` | `PARTIAL` | 字体/女声/TTS 是；BGM/SFX 否 | 部分 | 女声进 P1；BGM/SFX NOT_RUN |
| P1 生产闭环 | `projects/proj_p1_short/.../build-20261103-114226` | `PASS_VERIFIED`：14.0 s / 4 段 / 4 行女声 / quality PASS | 是 | 是（p1_e2e / 任务） | 是 |
| 工作台 | `docs/WORKSPACE_REPORT.md`、`workspace.db` | API/任务/媒体 PASS；浏览器 E2E 历史 | 是 | 是 | 39 任务真实执行 |
| S1 双风格配置 | `config/styles.yaml`、`docs/VISUAL_STYLE_SPEC.md` | `PASS_STATIC` | 是 | 是 | 否 |
| S2 工笔/水墨样片 | `docs/S2_TEST_REPORT.md` | `PARTIAL`（技术过，人工 PENDING） | 是 | CLI | 历史 |
| 管线 A 水墨分层 | `docs/PIPELINE_AB_VALIDATION.md`、`experiments/pipeline_a` | `PARTIAL` | 实验脚本 | CLI | 历史 |
| 管线 B 工笔长卷 | `docs/PIPELINE_AB_VALIDATION.md`、`experiments/pipeline_b` | `PARTIAL` | 实验脚本 | CLI | 历史 |
| S3 双风格链路 | 见 §2.23；不再用单一 PARTIAL/NOT_RUN 概括 | **PASS_STATIC**（规范/配置） / **PASS_VERIFIED**（各风格 2 镜头技术样片，M7） / **IMPLEMENTED_NOT_VERIFIED**（作品级锁定 + 跨镜头技术门） / **PENDING_HUMAN_REVIEW**（人工审片） | 是（motion/aesthetic 任务） | 是 | M7 两片；81.373 s 工笔为 scroll_shot 路径，不是 motion.plan |
| Aesthetic A/B | `docs/AESTHETIC_DESIGN_REPORT.md`、`experiments/aesthetic` | `PARTIAL` + `PENDING_HUMAN_REVIEW` | 是 | 是（任务注册） | 8 张实图 + 联系表 |
| M1–M4 运动 | `docs/M1..M4` | PASS/人工记录 | 是 | 是 | `experiments/m1..m4` |
| M5 Wan mask | `docs/M5_WAN_MOTION_MASK_REPORT.md` | `NOT_RUN (UNSUPPORTED_WORKFLOW)` | 否 | 否 | 否 |
| M6 发音 | `docs/M6_PRONUNCIATION_REPORT.md` | 5 verified + ASR 18/18 | 是 | 是 | 音频实验 |
| M7 双风格成片 | `docs/M7_FINAL_DELIVERY_REPORT.md`、`experiments/m7_final` | `PASS_VERIFIED`（技术+人工） | 是 | CLI | 两片 10.087/9.583 s |
| M8-A 视差 | `docs/M8_A_PARALLAX_REPORT.md`、`experiments/m8_parallax` | `PARTIAL`（人工 C 优于 A/B） | 实验 | CLI | 是 |
| M8-B 图层/PlateSpec | `docs/M8_B*`、`motion/plates.py` | `PASS_STATIC`/`PARTIAL` | 是（opt-in plates） | motion.render | 真实渲染 PASS |
| M8-C DA3 | `docs/M8_0_STATE_AUDIT.md` | `NOT_RUN` | 否 | 否 | 否 |
| 声景 S1 | `docs/AUDIO_SOUNDSCAPE_PLAN.md`、`soundscape.py` | `PASS_STATIC`（开启） | 是 | r3_build | zero-shot E2E 有 mixed_mastered |
| 声景 S2/S3 | 同上 | `NOT_RUN`（无授权素材） | 结构在 | 否 | 否 |
| Zero-shot S4 | `experiments/audio_probe/zeroshot_e2e` | `PASS_STATIC`（2 行 E2E） | 是 | 是（显式调用） | 参考音克隆，CosyVoice2-0.5B；PRD 默认模式；默认配置已切换并真实 2 行 PASS |
| Header/ledger S5 | `experiments/audio_probe/header_e2e` | `PASS_STATIC` | 是 | 是 | 2 行 + header |
| LI 五轮 | `literary_intelligence/runs/*` | `PARTIAL`（真实 LLM 5/5 但有角色违规） | 是 | 是（`li.run` 未在工作台跑） | 运行记录在 |
| LI 人工审核 | `corpus/luoshen_fu/reviews.json` | `NOT_RUN`（空） | 是（review 模型） | 否 | 否 |

---

## 4. 明确未实现（不要假设存在）

```text
src/drama_studio/state.py
src/drama_studio/comfy_client.py
src/drama_studio/generation/
src/drama_studio/storyboard/
src/drama_studio/character_manager/
src/drama_studio/audio/          （已有 voice/，但没有 audio/ 目录）
src/drama_studio/subtitles/
src/drama_studio/editing/
src/drama_studio/storage/
src/drama_studio/orchestrator.py
```

CLI 规划中的 `drama create/script/assets/images/videos/audio/render/run/resume` 均不存在；`drama` 只有 `doctor` 与 `serve`。

镜头级状态机 `PENDING → IMAGE_GENERATING → ...` 只有 `models.ShotStatus` 枚举，没有持久化/迁移代码；`workspace.db` 不存镜头状态。

---

## 5. 本轮无法确认（UNKNOWN）

| 项 | 原因 |
|---|---|
| R1/R2/R3/S2 原始 run 能否按报告路径复跑 | `experiments/r0..r3b`、`s2a/s2b` 目录缺失 |
| 工作台“新生成”路径在修复后是否稳定 | 成功记录用的是 `--reuse`，没有再次真实调用 LLM |
| 浏览器端 34 项 E2E 是否仍全过 | 历史报告有记录，但脚本/截图未入库，本轮未跑 |
| zero-shot 音色在完整成片中的听感 | 只有 2 行 E2E，未进入正式成片 |
| 完整 18 联 ContentPackage 是否超 schema 上限 | 未生成 |
| 2.5D plate 路径在长镜头/多镜头生产中的稳定性 | 有真实渲染 PASS，但仍是 opt-in，未成为默认 |
| 商用授权 | 字体/模型有登记；BGM/SFX/声音商用未完成 |

---

## 6. 已确认的生产案例（2026-11-04）

| 案例 | 路径 | 实现方式 | 规格 | 证据 |
|---|---|---|---|---|
| 完整工笔《春江花月夜》 | `projects/proj_chunjiang_gongbi/episodes/ep_chunjiang_gongbi_01/renders/build-20261103-161945/` | **`scroll_shot.py` + 预渲染 clips**；不是 `motion.plan` 自动运动管线 | 81.373 s / 1080×1920 / 13 段 / 18 句 | `quality_report.json` PASS、`verification_report.json` PASS、SHA-256 `84628a06…` 与 manifest 一致、18 句 ASR 记录 |
| R3 单篇 | `projects/proj_chunjiang/episodes/ep_chunjiang_01/renders/build-20261103-074757/` | `r3_build.py` 直接合成（5 静帧 + 1 Wan + 7 句） | 38.042 s / 1080×1920 | `quality_report` PASS；输入 `experiments/r3b` 已缺失 |
| P1 端到端 | `projects/proj_p1_short/episodes/ep_p1_short/renders/build-20261103-114226/` | ContentPackage → LLM → TTS → FLUX → segments → build | 14.0 s / 1080×1920 / 4 镜 / 4 句 | `quality_report` PASS |
| P1 motion | `projects/proj_p1_short/episodes/ep_p1_short/renders/build-20261104-005408-motion-ink/` | `motion.plan → motion.render → segments(sequence) → build` | 10.0 s / 1080×1920 | `quality_report` PASS |
| M7 双风格 | `experiments/m7_final/ink/renders/`、`experiments/m7_final/court/renders/` | `motion.plan → motion.render` | 10.087 s / 9.583 s | `quality_report` PASS + audio QA PASS |

**案例边界**：81.373 s 工笔与 R3/P1 不是同一条生产实现；不能把它当作 `motion.plan` 自动运动或跨镜头风格一致性的证据。
