# 04 · 生产流程与配置

> 状态：`DECISION` / 2026-11-12 由 `PRODUCTION_WORKFLOW.md`、`PRODUCTION_PIPELINE_GUIDE.md`、`PRODUCTION_CONFIG_GUIDE.md` 合并并校正到当前栈。
> 原始文档归档在 `D:\DramaStudio\archive\docs\2026-11-12\`（见 [ARCHIVE.md](ARCHIVE.md)）。
> 原则：**实际配置、推荐值、历史实测分开写**；推荐值不等于已生效值。

## 1. 四条生产路径

| 路径 | 入口 | 适用 |
|---|---|---|
| 工作台任务 | `drama serve`（8765）→ `application/operations/tasks.py` | 日常操作、可追溯任务记录 |
| Script-to-Film | `drama film init/plan/.../assemble` | 从任意文本到成片，推荐 |
| P1 生产链 | `scripts/p1_e2e.py` | 回归验证 ContentPackage → 成片 |
| 实验脚本 | `scripts/r1_batch.py`、`experiments/*` | 风格/模型实验，不承诺可复现 |

## 2. 目标流程（14 步）

| # | 步骤 | 当前实现 | 状态 |
|---|---|---|---|
| 1 | 主题/文本整理 | 人工 | `PARTIAL` |
| 2 | 内容策划 | 人工 | `PARTIAL` |
| 2b | 内容包 | `package.build` → ContentPackage(draft) | `PASS_VERIFIED` |
| 3 | 分镜设计 | `film script` + 本地 LLM → `ProductionScript` / `storyboard.json` | `PASS_VERIFIED` |
| 4 | 视觉风格 | style pack + `config/styles.yaml` | `PASS_VERIFIED` |
| 5 | 镜头美学设计 | 六维规格 + A/B + 快照 | `PARTIAL`（4 组实图，人工 PENDING） |
| 5b | 静帧生成 | FLUX.3 + `comfy.batch` | `PARTIAL` |
| 6 | 动态镜头 | 确定性运镜/局部微动；Wan 只作纯风景 hero | `PARTIAL`（技术链通，人工看片 PENDING） |
| 7 | 旁白/朗诵 | VoxCPM2 逐句 TTS + 读音层 + 音频 QA | `PASS_VERIFIED`（技术）；发音人工复核 PENDING |
| 8 | 音乐/音效 | `audio_timeline` + manifest + ducking | BGM 技术 `PASS_VERIFIED`；SFX/环境音 `IMPLEMENTED_NOT_VERIFIED` |
| 9 | 字幕 | `r3_build` + `config/fonts.yaml`（思源黑体） | `PASS_VERIFIED` |
| 10 | 合成 | `r3_build` 1080×1920 / 24 fps | `PASS_VERIFIED` |
| 11 | 质量检查 | `quality.check` / `static_quality` / `film qc` + 人工 H3 | 技术 PASS；美学/音频 PARTIAL；人工 H3 `NOT_RUN` |
| 12 | 平台适配 | 未实现 | `NOT_RUN` |
| 13 | 人工审核/发布 | 人工 | `PARTIAL` |
| 14 | 数据记录 | 未实现 | `NOT_RUN` |

## 3. 人工控制点

| 控制点 | 时机 | 必须确认 |
|---|---|---|
| H1 人物/首帧锁定 | 人物资产或首帧后 | 角色可辨认、服装/场景正确 |
| H2 关键帧审批 | 批量 Wan 之前 | 构图、空间关系、无现代物件 |
| H3 成片验收 | 合成后 | 节奏、音量、字幕、可看性 |
| H4 平台包装 | 发布前 | 封面、标题、正文、话题、AI 标识 |
| H5 发布与记录 | 发布后 | 链接、时间、初始数据 |

## 4. Script-to-Film 链路

```text
任意文本
  → film init / film script        分句、旁白、视觉圣经、导演节拍
  → film prompts / keyframes       FLUX 关键帧任务
  → film wan-jobs → comfy.batch    Wan I2V（PNG 帧，不是视频）
  → film clips                     PNG 帧 → 镜头 MP4（按时间轴补齐）
  → film motion                    静帧 → 确定性运镜/纹理
  → film timeline                  旁白真实时长决定镜头边界
  → film assemble                  segments + audio → r3_build
  → film qc / quality.check_build  技术 + 媒体 + 字幕流
  → film status / approve          H2/H3 人工结论
```

```powershell
.venv\Scripts\drama.exe film init --project <id> --text <utf8.txt> --title "<title>" --duration 120
.venv\Scripts\drama.exe film script --project <id> --text <utf8.txt> --write-storyboard
.venv\Scripts\drama.exe film timeline --project <id>
.venv\Scripts\drama.exe film prompts --project <id>
.venv\Scripts\drama.exe film keyframes --project <id>
.venv\Scripts\drama.exe film wan-jobs --project <id> --profile safe8g
.venv\Scripts\python.exe scripts\wan_batch.py --project <id> --shots S02,S03
.venv\Scripts\drama.exe film clips --project <id>
.venv\Scripts\drama.exe film motion --project <id>
.venv\Scripts\drama.exe film voice --project <id>        # VoxCPM2 on 50000
.venv\Scripts\drama.exe film assemble --project <id>
.venv\Scripts\drama.exe film qc --project <id>
.venv\Scripts\drama.exe film status --project <id> --write
```

项目数据在产出根：`D:\DramaStudio\projects\<id>\`（见 [REPO_LAYOUT.md](REPO_LAYOUT.md)）。

规则：

- 旁白是时间基准；镜头不足时延长镜头，不压缩语速。
- Wan 产物是帧序列，必须经 `film clips`；静帧必须带确定性运动。
- 字幕、混音、画面共享同一毫秒边界；`assemble` 校验起点一致。
- TTS 前清洗导演备注：括号/方括号/拉丁词不进朗读文本。
- 8 GB 显存用 `safe8g`（448×768、49/65 帧）；长镜头用 `film wan-chain` 末帧续接。
- 同景别/反推/换场切点用 0.5 s `xfade`；持续环境声贯穿全片。
- 成片只写新的 `renders/build-<time>/`，不覆盖历史；`quality.check_build` 是唯一技术门。

## 5. 配置分层

| 文件 | 作用 |
|---|---|
| `config/settings.yaml` | 路径、ComfyUI/LLM/TTS base_url、FFmpeg |
| `config/models.yaml` | 模型路径 + 精确字节数（doctor 校验） |
| `config/generation.yaml` | R0 profile、并发/重试/超时（生产 jobs 不读 profile） |
| `config/audio.yaml` | TTS 模式/音色/zero-shot、诵读、字幕、响度、声景 |
| `config/voices.yaml` | Voice Profile 库（状态与许可） |
| `config/styles.yaml` | 两种核心风格的视觉/运动/合成/美学 profile |
| `config/fonts.yaml` | 字体角色、字号、字幕边距 |
| `config/pronunciation.yaml` | 词组读音与同音别名 |

路径与密钥走 `.env`（已 gitignore）：`DRAMA_MODELS_ROOT`、`DRAMA_AI_HOME`、`DRAMA_OUTPUT_ROOT`、`VOXCPM_RUNTIME`。

## 6. 当前模型与参数

| 角色 | 模型 | 关键参数 |
|---|---|---|
| 图像 | FLUX.3 Klein GGUF Q4_K_M | `workflows/flux3_t2i_api.json`，576×1024，**16 步**，CFG 1.0，Flux2Scheduler，seed 可追溯 |
| 图像编码器 | `qwen3vl_4b_int8_convrot.safetensors` | `CLIPLoader(type=flux3, device=cpu)` |
| 图像 VAE | `flux2-vae.safetensors` | 必须用 FLUX.2 VAE |
| 视频 | Wan2.2 TI2V 5B Q4_K_M | **分辨率必须能被 32 整除**，**20 步**（10 步出彩虹伪影），CFG 5，shift 8，`uni_pc`/`simple` |
| Wan 帧数 | 73（≈3 s）默认；121 有颜色漂移风险 | 竖屏 576×1024 / 73 帧 ≈ 36.4 min |
| 文本 | Qwen3-30B-A3B-Instruct-2507 | 8080，CPU-only，64K 上下文 |
| 语音 | VoxCPM2 | 50000，CPU，48 kHz，RTF≈9.3，zero-shot |

已实测：FLUX 576×1024 约 22–53 s/张、峰值 ~3 GiB；Wan 1024×576/73 帧 40–43 min、峰值 ≤6.12 GiB；`safe8g` 448×768/49 帧 8–14 min。R3 成片 38 s 全链路 43.8 min；47 s 混合片约 1.2–1.5 h。

## 7. 已知未接线配置

| 字段 | 现状 |
|---|---|
| `audio.yaml subtitles.*` | 无消费者；接线或删除 |
| `audio.yaml narration_modes.*.leading_ms` | 未被 `r3_build` 消费 |
| `generation.yaml profiles.*` | 无生产消费者 |
| `styles.yaml validation_status` | 人工评审前保持 `PARTIAL` |

不要顺手改这些字段；它们属于独立任务。

## 8. 失败与降级

| 失败 | 处置 |
|---|---|
| Wan 产出墨团/白块/变形 | 该镜头改静帧运镜；不靠提示词硬调 |
| 显存不足 | 一次只跑一个 GPU 任务；Wan 用 `safe8g` |
| 字幕缺字/字体回退 | `r3_build` 拒绝静默 fallback；检查 `font_manifest.json` |
| 音频哈希不一致 | 重新登记 manifest，不覆盖旧证据 |
| 任务超时 | 有界重试（最多 2 次，30/90 s 退避），保留日志 |

## 9. 工程规则

- 状态只从真实文件/清单推导，UI 不发明进度；缺失即 `NOT_RUN`。
- 每次生成保留 seed、prompt、模型哈希、工作流哈希。
- 重建写入新的 `build-<time>/`，不覆盖历史产物。
- 不升级 ComfyUI/节点或替换权重而不重跑 R0 检查。
- 参考板候选图、渲染视频、日志都在产出根，不进 Git。
