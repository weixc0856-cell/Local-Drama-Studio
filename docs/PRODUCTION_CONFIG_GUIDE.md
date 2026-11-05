# 生产配置手册

> 文档状态：Phase B 配置文档（2026-11-04）
> 原则：**实际配置、推荐默认值、实验参数、尚未验证的参数分开写**。推荐值不是已生效值；不要把推荐值直接写进生产配置。
> 相关：[PRODUCTION_PIPELINE_GUIDE.md](PRODUCTION_PIPELINE_GUIDE.md)、[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)、[TECH_STACK.md](TECH_STACK.md)

---

## 1. 配置分层

| 文件 | 作用 | 谁读 |
|---|---|---|
| `config/settings.yaml` | 路径、ComfyUI、LLM、TTS base_url/sample_rate、FFmpeg | `config.py`、doctor、TTS、workspace |
| `config/models.yaml` | 模型文件路径 + 精确字节数 | doctor |
| `config/generation.yaml` | R0 profile、并发/重试/超时 | doctor 加载；**生产 jobs 不读 profile** |
| `config/audio.yaml` | TTS 模式/音色/zero-shot、诵读模式、字幕、响度、声景 | `voice/tts.py`、`voice/recitation.py`、`voice/soundscape.py`、`r3_build.py` |
| `config/voices.yaml` | Voice Profile 库（SFT speaker / zero-shot 参考音、状态、许可） | `voice/profiles.py`、`voice/tts.py`、workspace |
| `config/styles.yaml` | 两种风格的视觉/运动/合成/美学 profile | `style_presets.py`、`motion`、`aesthetics` |
| `config/fonts.yaml` | 字体角色、字号、字幕边距 | `fonts.py`、`r3_build.py` |
| `config/pronunciation.yaml` | 词组读音与同音别名 | `voice/pronunciation.py` |
| `config/comfyui_extra_model_paths.yaml` | ComfyUI 模型映射 | `setup.ps1` 复制 |

---

## 2. 模型选择（实际）

| 角色 | 模型 | 文件 | 大小（字节） | 节点 |
|---|---|---|---|---|
| 图像 | FLUX.2 klein 4B Q4_K_M | `D:\AI\models\flux-2-klein-4b-Q4_K_M.gguf` | 2,604,311,104 | `UnetLoaderGGUF` |
| 图像文本编码器 | Qwen3-4B | `D:\AI\models\text_encoders\qwen_3_4b.safetensors` | 8,044,982,048 | `CLIPLoader(type=flux2, device=cpu)` |
| 图像 VAE | FLUX.2 VAE | `D:\AI\models\vae\flux2-vae.safetensors` | 336,211,292 | `VAELoader` |
| 视频 | Wan2.2 TI2V 5B Q4_K_M | `D:\AI\models\Wan2.2-TI2V-5B-Q4_K_M.gguf` | 3,433,116,000 | `UnetLoaderGGUF` |
| 视频文本编码器 | UMT5-XXL fp8 | `D:\AI\models\text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6,735,906,897 | `CLIPLoader(type=wan, device=cpu)` |
| 视频 VAE | Wan2.2 VAE | `D:\AI\models\vae\wan2.2_vae.safetensors` | 1,409,400,960 | `VAELoader` |
| 文本 | Qwen3-30B-A3B-Instruct-2507 Q4_K_M | `D:\AI\models\Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf` | ~18.56 GB | llama.cpp 8080 |
| TTS SFT | CosyVoice-300M-SFT | `D:\AI\CosyVoice-Runtime\pretrained_models\CosyVoice-300M-SFT` | 目录 | `inference_sft` |
| TTS zero-shot | CosyVoice2-0.5B | `D:\AI\CosyVoice-Runtime\pretrained_models\CosyVoice2-0.5B` | 目录 | `inference_zero_shot` |

**硬约束**：

- FLUX 必须用 Qwen3-**4B** 编码器 + FLUX.2 VAE；不能用 Qwen3-8B 或 FLUX.1 VAE。
- Wan TI2V-5B 用它自己的 VAE/latent 工作流；不是 14B 的缩小版。
- 两个扩散 GGUF 必须在 `D:\AI\models` 顶层。
- `doctor` 会拒绝缺失或大小不符的文件。

---

## 3. FLUX 图像参数

### 3.1 当前生产默认（`production.build_jobs`）

| 参数 | 值 | 说明 |
|---|---|---|
| workflow | `workflows/r0_flux_t2i_api.json` | API 格式 |
| width × height | 576 × 1024 | 9:16 竖屏 |
| steps | 4 | FLUX.2 klein 的验证值 |
| cfg | 1.0 | `CFGGuider(1.0)` |
| sampler | euler | `KSamplerSelect` |
| scheduler | Flux2Scheduler | 不是 `simple` |
| seed | `seed_base + shot.index`，默认 7100 | 每镜头可追溯 |
| batch_size | 1 | 一次一张 |
| negative | 记录但不控制 | `ConditioningZeroOut` + CFG 1.0 |
| filename_prefix | `p1/<shot_id>` | 生成器输出前缀 |

### 3.2 分辨率

| 用途 | 分辨率 | 状态 |
|---|---|---|
| R0 最小验证 | 512×512 | `PASS_VERIFIED`（历史） |
| R1 16:9 关键帧 | 768×432 | `PASS_VERIFIED`（历史） |
| R2 Wan 输入 | 1024×576 | `PASS_VERIFIED`（历史） |
| R3/P1 竖屏 | 576×1024 | `PASS_VERIFIED` |
| Wan 竖屏 | 576×1024 | `PASS_VERIFIED`（历史） |
| 最终成片 | 1080×1920 | FFmpeg Lanczos 放大，不是原生 |

### 3.3 性能（实测）

| 场景 | 时间 | 峰值 VRAM |
|---|---|---|
| 512×512 / 4 步 | 99.5 s | 2.61 GiB |
| 768×432 | 70–102 s/张 | 2.84 GiB |
| 576×1024 | 22–53 s/张 | ~2.8–3.0 GiB |
| P1 4 张 | 76.6 / 59.0 / 44.7 / 16.1 s | — |

> 这些是历史测量；当前 8188 未启动，不构成本轮复测。

---

## 4. Wan 视频参数

| 参数 | 当前/推荐 | 状态 | 说明 |
|---|---|---|---|
| workflow | `r0_wan_i2v_api.json` / `r0_wan_t2v_api.json` | `PASS_VERIFIED` | API 格式 |
| 分辨率 | 1024×576 或 576×1024 | `PASS_VERIFIED` | **必须能被 32 整除** |
| frames | **73** | `PASS_VERIFIED` | 约 3 s；121 帧 `PASS_LIMITED`（颜色漂移） |
| fps | 24 | `PASS_VERIFIED` | Wan 输出按 24 fps 解释 |
| steps | **20** | 强制 | 10 步会产生彩虹伪影 |
| cfg | 5.0 | `PASS_VERIFIED` | — |
| shift | 8.0 | `PASS_VERIFIED` | `ModelSamplingSD3` |
| sampler | `uni_pc` | `PASS_VERIFIED` | — |
| scheduler | `simple` | `PASS_VERIFIED` | — |
| denoise | 1.0 | `PASS_VERIFIED` | — |
| 用途 | 缓慢推近/局部动态 | `PASS_VERIFIED` | **不用于精确主体位移** |

性能：

| 场景 | 时间 | 峰值 VRAM |
|---|---|---|
| 1024×576 / 73 帧 | 40–43 min / 3 s | ≤6.12 GiB |
| 1024×576 / 121 帧 | 66–69 min / 5 s | ≤6.12 GiB |
| 576×1024 / 73 帧 | 36.4 min | 5.48 GiB |
| R2-B 4 英雄镜头 | 32.6–46.4 min/个 | 5.50–5.66 GiB |

**不要**：用 Wan 做精确船体位移（R2-B H3 方向错误）；用 10 步；在 8 GB 卡上同时跑 LLM/FLUX/Wan。

---

## 5. 视觉风格配置（`config/styles.yaml`）

### 5.1 两种正式风格

| 项 | `court_green_fine_line` | `ink_wash` |
|---|---|---|
| 名称 | 宋代院体青绿工笔 | 东方写意水墨 |
| 材质 | 绢本设色、矿物颜料层 | 生宣纸本、墨分五色 |
| 线条 | 游丝描/铁线描 | 笔触概括、虚实相生 |
| 主色 | 石青/石绿；赭石/泥金点缀 | 焦墨/浓墨/中墨/淡墨；赭石/淡花青 |
| 默认相机 | `scroll_pan` | `slow_push_in` |
| 相机缓动 | linear | ease_in_out |
| 横移速度 | 30 px/s | 18 px/s |
| 转场 | crossfade 0.8 s | ink_dissolve 1.2 s |
| 本地微动 | 水波/倒影/云/叶/芦苇/墨扩散（部分） | 水波/倒影/云/叶/芦苇/墨扩散 |
| 2.5D parallax | 允许，depth_alpha 0.50–0.75，max 3 plates | 允许，0.45–0.85，max 3 plates |
| 适用内容 | 山水/长卷/建筑/花鸟/空镜 | 山水/云雾/水面/花鸟/空镜 |
| `validation_status`（配置字段） | `PARTIAL` | `PARTIAL`（技术样片 + A/B 选型已做，完整作品未做） |

### 5.1.1 场景风格 `shinkai_scenery` / `ghibli_scenery`

`config/styles.yaml` 新增两套 `category: scene` 风格：`shinkai_scenery`（高饱和天空、体积积雨云、金时刻逆光、雨后倒影）与 `ghibli_scenery`（手绘水粉、温润草木绿、田园/森林/老式建筑）。两者都不是 core 风格，`validation_status=NOT_RUN`，且 negative prompt 显式排斥另一套风格；完整场景样片见 `experiments/shinkai_scene/renders/`。

### 5.2 风格配置的边界

- `visual_language` + `positive_prompt` 是自包含的材质/线条/细节描述，进入 `script_engine.compose_visual_prompt`。
- `material/line/detail` 是审计字段，不单独拼接。
- `motion/compositing` 由 `drama_studio.motion` 消费；`camera/local_policy/transition` 是机械策略，不是提示词。
- `aesthetic_profile` 是六维设计的上游；不是提示词模板目录。
- 通用代码不得按 `style_id` 写分支。
- `workspace.styles` 只存 `STYLE_ENTITY_FIELDS`，**不含** motion/compositing/aesthetic_profile；不要以为 UI 改风格会影响运动策略。

### 5.2.1 已选 A/B 生产基线（2026-11-04）

`config/styles.yaml` 新增 `production_baselines`，记录项目所有者选定的 A/B 组合：

- `court_green_fine_line`：`shot_001=A`、`shot_002=A`
- `ink_wash`：`shot_001=B`、`shot_002=A`

每项包含 `variant`、完整 `prompt`、`prompt_sha256`、`sections` 与人工 `rationale`；
`source_snapshot` 指向原始 A/B 快照。下一部正式样片以此为 prompt 模板，但不得在代码里
按 style id 写分支。配置由 `style_presets.ProductionBaseline` 严格校验。

### 5.3 作品级风格约束（产品目标）

| 规则 | 目标 | 当前 |
|---|---|---|
| 每作品一个主风格 | `style_id` 作品级 | 期数 `style_snapshot._style_lock`；项目默认风格仍非强制 |
| 全片一致 | 不混用 | 期数锁 hash；`comfy.batch` 绑定 `episode_id` 时校验 production_script |
| 生成任务不覆盖 | 任务继承 | `motion.plan` / `aesthetic.plan` / `static.check` 拒绝不同 style；其他任务待补 |
| 改风格留版本 | 新版本/新生产 | `_style_lock.revision` + `history` 保留旧 sha；旧 build 目录不覆盖 |
| 跨镜头一致性 | 质量门 | 只有相邻 LAB/亮度连续性（`PRD-STYLE-007` 仍 `NOT_IMPLEMENTED`） |

> 详见 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) §4 与 [audit/IMPLEMENTATION_STATUS.md](audit/IMPLEMENTATION_STATUS.md) §2.23。

工作台 `styles` 新增可选 `preset_id`，用于把 DB 风格映射到 `config/styles.yaml` 的
`ink_wash` / `court_green_fine_line`。期数创建/改风格时把它写入
`style_snapshot._style_lock.preset_id`；`motion.plan` / `aesthetic.plan` 使用该
preset id，而不是 DB 风格 id。旧库在 `WorkspaceStore.init_schema()` 中做一次
只增迁移，仅对名称含“水墨/写意”或“工笔/青绿”的风格自动映射，其他保持未映射。

---

## 6. TTS 配置

### 6.1 PRD 目标 vs 当前实现

| 项 | PRD 要求 | 当前实现 | 状态 |
|---|---|---|---|
| 默认模式 | **CosyVoice2-0.5B zero-shot** | `config/audio.yaml` `tts.mode: zero_shot`，真实任务加载 0.5B | `PASS_VERIFIED` |
| 默认音色 | zero-shot 参考音 | `zero_shot.prompt_audio` 已配置并真实使用；`config/voices.yaml` 的 `narrator_self` 提供显式档案 | `PASS_VERIFIED` |
| SFT | 仅显式可选，不得默认 | 显式 `--tts-mode sft` + `-Model sft` 可用并已验证 | 已实现 |
| zero-shot 模型 | 只允许 CosyVoice2-0.5B | `/health` 校验 `model_class=CosyVoice2` + `model_dir` 含 `CosyVoice2-0.5B` | 已实现 |
| 模式选择 | UI/CLI/任务显式 | CLI `--tts-mode`；任务 `tts_mode`；narration 可选；无 `enabled` 静默开关 | 已实现 |
| 产物记录 | mode/model/voice | manifest 记录 `tts_mode/model_class/model_dir/speaker/speaker_id/runtime/prompt`；多音色另有 `voice_cast` 与逐行字段 | 已实现 |
| 禁止回退 | 0.5B 失败不得回退 300M | SFT↔zero-shot 双向错配均报错 | 已实现 |
| 真实验证 | 两种模式分别跑通 | 默认 zero-shot 2 行真实 PASS；显式 SFT 1 行历史 PASS | 已验证 |

### 6.2 当前 `config/audio.yaml` 关键值

| 项 | 值 | 消费者 | 备注 |
|---|---|---|---|
| `tts.mode` | `zero_shot`（当前默认） | `tts.py` | PRD 默认；CLI/任务可显式覆盖为 `sft` |
| `tts.default_speaker` | `中文女` | `_default_speaker` | 仅 SFT 显式模式使用；zero-shot 默认应为参考音 |
| `tts.zero_shot.prompt_audio` | `assets/audio/prompts/my_voice_clean_v1.wav` | `tts.py` | 仅显式 zero-shot |
| `tts.zero_shot.prompt_text` | `希望你以后能够做的比我还好呦。` | `tts.py` | 必须逐字一致 |
| `tts.zero_shot.speed` | `0.90` | `tts.py` | zero-shot 默认 |
| `tts.zero_shot.runtime` | `cosyvoice2` | 文档/校验说明 | 实际模型由 `/health` 校验 |
| `tts.sample_rate` | `48000` | `tts.py` | 最终统一采样率 |
| `tts.speakers.narrator` | `中文男` | `_default_speaker` 的兜底 | 不再优先于 `default_speaker` |
| `tts.speakers.female_01` | `中文女` | 记录 | SFT |
| `narration_modes.narration` | speed 1.0 / line_pause 800 / leading 300 | `recitation.py` | `leading_ms` 未被 `r3_build` 消费 |
| `narration_modes.recitation` | speed 0.92 / line_pause 950 / leading 450 | `recitation.py` | 同上 |
| `narration_modes.classical_recitation` | speed 0.82 / line_pause 1000 / leading 550 | `recitation.py` | 同上 |
| `narration_modes.chant` | `supported: false` | `recitation.py` | 明确拒绝 |

> `settings.tts.mode` 已从 `config/settings.yaml` 与 `TTSSettings` 删除；不要恢复第二份开关。

### 6.3 SFT vs zero-shot 的真实模型映射（已实现校验）

```text
SFT（显式可选）
  scripts\cosyvoice_server.ps1 -Action start -Model sft
  -> start_cosyvoice_sft.bat
  -> COSY_MODEL_CLASS=CosyVoice
  -> pretrained_models\CosyVoice-300M-SFT
  -> api_server._synthesize_sft() -> inference_sft()
  -> speakers: 中文男 / 中文女 / ...

zero-shot（默认）
  scripts\cosyvoice_server.ps1 -Action start -Model cosyvoice2
  -> start_cosyvoice.bat
  -> COSY_MODEL_CLASS=CosyVoice2
  -> pretrained_models\CosyVoice2-0.5B
  -> api_server._synthesize() -> inference_zero_shot()
```

同一端口 50000，互斥。`/health` 返回 `model_class/model_dir/speakers/modes`，应记录到产物/日志。

### 6.2.1 Voice Profile（`config/voices.yaml`，显式启用）

`voice/profiles.py` 把“谁在说”从全局 `speaker` 提升为可追溯档案。仅当
`narration.json` 指定 `voice_profile`（顶层、逐行或 header）或 CLI
`--voice-profile` 时启用；未指定时仍走 `audio.yaml` 旧路径，不静默改变现有生产。

| 字段 | 必填 | 说明 |
|---|---|---|
| `profile_id` | 是 | `[a-z][a-z0-9_]{1,63}`；逐行引用 |
| `display_name` | 是 | UI/报告显示名 |
| `tts_mode` | 是 | `sft` 或 `zero_shot`；一次运行只能有一种 |
| `speaker` | SFT | CosyVoice 预置音色，必须出现在 `/health.speakers` |
| `prompt_audio` / `prompt_text` | zero-shot | 参考音必须存在、逐字对齐；SHA-256 写入 manifest |
| `speed` | 否 | 档案级语速；CLI/ narration 显式 speed 优先 |
| `status` | 是 | 只有 `APPROVED` 可进生产；`TECHNICALLY_VALIDATED` 只能试听 |
| `commercial_allowed` / `license_evidence` | 是（APPROVED） | 商用状态与证据路径 |
| `asset_id` | 否 | 关联 `assets/audio/manifest.json`，不复制资产 |

规则：

- 一个运行内可以混用多个 **同模式** profile；`sft` + `zero_shot` 混用会明确失败，
  因为 50000 一次只能加载一个模型。
- 逐行 `voice_profile` 覆盖运行默认；header 可单独指定。
- `audio_manifest.json` 增加 `voice_cast`（sha256 / profiles / 逐行记录）和每行
  `voice_profile / voice_label / tts_mode / speaker / speaker_id / speed / prompt`。
- 未 `APPROVED` 的档案默认被拒绝；`--allow-unapproved-voices` 只用于试听，
  仍会在 manifest 留下真实 `status`。

侧车（推荐，不污染 `ProductionScript`）：

```yaml
# voice_cast.yaml
schema_version: "1.0"
default_profile: narrator_self
header_profile: narrator_self       # 可选
lines:
  "1": sft_male_01                  # 1-based 行号
  "line_002": sft_female_01         # 或脚本 line_id
characters:                          # 预留；当前只校验，不自动按角色选角
  char_001: sft_male_01
```

```powershell
scripts\r3_tts.py ... --voice-cast work\voice_cast.yaml
```

逐行 `narration.json` 的 `voice_profile` 仍优先于 sidecar；sidecar 的
`default_profile` 只在未指定运行时默认时生效。`audio_manifest.json.voice_cast.source`
记录 sidecar 路径。

### 6.4 发音与诵读

- `config/pronunciation.yaml`：词组级，最长匹配；`verified` 5 条（扁舟/似霰/青枫浦/碣石/潇湘），其余 `candidate`。
- 同音别名只改 `acoustic_text`；`display_text/source_text` 不变。
- `chant` 不支持；不要用普通朗诵冒充。
- 行间停顿由 `line_pause_ms` 决定；`leading_ms` 当前不进入 `r3_build`（用 `content_type` 默认或显式 `--leading-ms`）。

### 6.5 字幕配置（当前部分未生效）

| 项 | 值 | 消费者 | 备注 |
|---|---|---|---|
| `subtitles.format` | `srt` | **无** | 脚本固定生成 SRT + ASS |
| `subtitles.max_chars_per_line` | 18 | **无** | 不自动换行 |
| `subtitles.max_lines` | 2 | **无** | 不自动换行 |
| `subtitles.burn_in` | `false` | **无** | 脚本总是尝试烧录版 |

### 6.6 声景/响度

| 项 | 值 | 消费者 | 备注 |
|---|---|---|---|
| `soundscape.enabled` | `true` | `r3_build.py` / `soundscape.py` | **当前开启**；新构建与历史不同 |
| `soundscape.reverb.method` | `early_reflections` | `soundscape.py` | `afir` 在本机 FFmpeg 8.1 输出数字静音，已实测阻断 |
| `soundscape.ir.path` | `assets/audio/ir/synthetic_hall_0.9s.wav` | `soundscape.py` | 合成 IR，非实测空间 |
| `soundscape.ir.dry/wet` | 0.85 / 0.18 | `soundscape.py` | — |
| `soundscape.voice_eq.highpass_hz` | 80 | `soundscape.py` | — |
| `soundscape.voice_eq.deess` | 6500 -2.0 / 8000 -3.0 | `soundscape.py` | — |
| `soundscape.voice_dynamics.enabled` | `false` | `soundscape.py` | 开启后可达 -16 LUFS |
| `soundscape.voice_style` | `broadcast_light` | `soundscape.py` | 06 |
| `soundscape.ambience.track` | `""` | `soundscape.py` | 无授权素材 |
| `soundscape.bgm.track` | `""` | `soundscape.py` | BGM 走 timeline 的 `asset_id`，不走该字段 |
| `soundscape.ducking.enabled` | `true` | `soundscape.py` | 有 BGM 时生效 |
| `loudness.dialogue_lufs` | -16.0 | `soundscape.py` | soundscape 关闭时 `r3_build` 硬编码 -16 |
| `loudness.true_peak_db` | -1.5 | `soundscape.py` | 同上 |
| `loudness.bgm_lufs` | -26.0 | `soundscape.py` | 参考值；timeline BGM 默认 gain -14 dB，最终两遍 loudnorm 到 -16 LUFS |

> 当前可用 BGM：`bgm_mozart_k330_piano`、`bgm_green_leaves_guitar`、`bgm_grieg_morning`、`bgm_mozart_k525_strings`、`bgm_schubert_d664_piano`、`bgm_serenity_guitar`（4 条 PD + 2 条 CC BY，见 `assets/audio/bgm/commons/`）以及 `bgm_court_strings_duo`、`bgm_ghibli_quartet`；Keynata 其余曲目与旧 drone 全部 `REJECTED`。CC BY 曲目必须署名。`soundscape.bgm.track` 留空，BGM 通过 `audio_timeline.json` 的 `asset_id` 或 `--bgm-id` 接入。

---

### 6.7 多轨音频与资产状态

| 项 | 当前实现 | 说明 |
|---|---|---|
| 时间轴 | `audio_timeline.json` sidecar | 不改 `segments.json` 数组；旧路径兼容 |
| 轨道 | narration / dialogue / bgm / sfx | narration/dialogue 用事件；bgm 用 asset_id；sfx 用事件 |
| BGM ducking | `sidechaincompress` | threshold/ratio/attack/release 可配；不是固定 -8 dB |
| SFX | 事件 start/duration/gain/fade | 每个事件独立定位 |
| 资产注册 | `assets/audio/manifest.json` | 兼容旧 `id`/`kind`；生产要求 `status=VERIFIED/APPROVED` 且 `commercial_allowed != false` |
| QA | `quality --audio-timeline --audio-assets` | 检查事件边界、资产哈希/状态、轨道结构 |
| 旧路径 | `r3_build` 不传 `--audio-timeline` | 仍逐行 `adelay/amix`，不改变历史行为 |

> BGM 现为 Wikimedia Commons 的公有领域/CC BY 真录音（`assets/audio/bgm/commons/`）：4 条 Public domain + 2 条 CC BY 3.0 US（需署名）；Keynata 5 条与旧正弦 drone 全部 `REJECTED`；SFX 为项目自生成、无第三方采样。BGM 人工听感与 ducking 听感 PENDING。

**登记新音频**：`scripts/audio_asset_entry.py <file> --license <license> --source-platform <platform> --artist <name> --status APPROVED` 会计算 SHA-256、ffprobe 时长并输出可直接粘贴的条目；`APPROVED` 条目必须给出已验证的 `--license`，需要署名的曲目必须同时给 `--attribution-required --attribution-text`。

**资产字段两种写法都接受**：旧版 `id`/`kind`/`license_type` 与模板版 `asset_id`/`type`/`license`/`attribution_text`/`tags` 由 `voice/audio_assets.py` 归一到同一模型；`style` 会转成 `style_tags`。新增字段 `artist`、`source_platform`、`attribution` 用于来源与署名追踪。

**人工指定 BGM（`--bgm-id`）**：不必改时间线 JSON，直接覆盖 BGM 轨的资产：

```powershell
.venv\Scripts\python.exe scripts/r3_build.py `
  --segments <segments.json> --audio <audio_manifest.json> `
  --audio-timeline <audio_timeline.json> --audio-assets assets/audio/manifest.json `
  --out <render_dir> --bgm-id bgm_mozart_k330_piano
```

构建会把实际使用的时间线写到 `<render_dir>/audio_timeline_effective.json`，便于反查。候选资产：`bgm_mozart_k330_piano`（明亮钢琴）、`bgm_green_leaves_guitar`（木吉他）、`bgm_grieg_morning`（晨曲）、`bgm_mozart_k525_strings`、`bgm_schubert_d664_piano`、`bgm_serenity_guitar`。不要用小调曲目再用 EQ 去"修情绪"。

---

## 7. 字幕与字体

| 角色 | 字体 | 字重 | 字号 | 集成状态 |
|---|---|---|---|---|
| `subtitle` | Source Han Sans CN | regular | 56 px | **formal_build** |
| `classical_title` | Source Han Serif CN | bold | 150 px | preview_only |
| `poetry_body` | Source Han Serif CN | medium | 64 px | preview_only |
| `modern_narration` | Source Han Sans CN | medium | 56 px | preview_only |

- `r3_build` 只把 `subtitle` 角色接入正式构建；其他角色预览用。
- 字幕 ASS `PlayRes 1080×1920`；底部边距 180 px；描边 3 px。
- 字体 OTF 不系统安装；构建时复制到 `renders/<build>/fonts/`，libass `fontsdir` 指向它。
- `fontselect.log` 必须命中配置的 PostScript 名，否则构建失败。

---

## 8. FFmpeg / 视频编码

| 项 | 值 |
|---|---|
| 输出 | 1080×1920 / 24 fps |
| 视频 | H.264 libx264，CRF 18，preset medium |
| 音频 | AAC 192 kbps，48 kHz mono |
| 字幕 | mov_text 软字幕 + 可选烧录 |
| 图片段 | 先 scale 2160×3840 + crop，再 zoompan（max 1.06） |
| 视频段 | Lanczos 到 1080×1920 + fps 24 |
| 拼接 | concat demuxer，`-c copy` 到 video_raw |
| 淡入/淡出 | 0.6 s / 0.9 s |
| 混音 | 逐行 `adelay` + `amix normalize=0` + `alimiter 0.95` + `apad` |
| 响度 | soundscape 开启：两遍 EBU R128；关闭：单遍 `loudnorm I=-16:TP=-1.5:LRA=11` |
| 封装 | `-movflags +faststart` |
| 覆盖保护 | 已有 `final_9x16.mp4` 时拒绝，除非 `--allow-overwrite` |

---

## 9. 质量阈值（实际代码）

### 9.1 图片

| 检查 | 阈值 | 代码 |
|---|---|---|
| 空图 | stddev < 1.5 | `check_image` |
| 黑图 | mean < 4.0 且 stddev < 3.0 | `check_image` |
| 静态客观门 | 宽/高 ≥ 512；非空非黑 | `static_quality.py` |

### 9.2 视频

| 检查 | 阈值 |
|---|---|
| 解码 | `ffmpeg -v error -i ... -f null -` 返回 0 |
| 时长 | > 0 |
| 分辨率 | 成片 1080×1920；视频分段也按 1080×1920 检查 |

### 9.3 音频

| 检查 | 阈值 |
|---|---|
| 削波 | max volume ≥ -0.1 dB |
| 过轻 | mean < -45 dB |
| 时长 | 与 manifest 差 ≤ max(0.35 s, 8%) |
| 静音 | `silencedetect noise=-45dB:d=0.35`；整行静音比 ≥0.85 判 broken |
| 发音 | 波形/时长通过也只到 `PARTIAL`，人工/ASR 才能 PASS |

### 9.4 成片

| 检查 | 阈值 |
|---|---|
| final | 1080×1920；解码 0 |
| 哈希 | 与 `outputs.final_sha256` 一致 |
| 分段素材 | 图片非空黑；视频解码/尺寸 |
| 混音 | 可解码、不削波 |

### 9.5 运动

| 检查 | 阈值 |
|---|---|
| 刚体帧差均值 | ≤6.0 |
| 刚体 p95 差 | ≤22.0 |
| 边缘漂移 | ≤6% |
| 时序跳变 | luma 6.0 / ratio 4.0 |
| 尾部下降 | 5.0 / 斜率 -0.8/s |
| 闪烁 | residual std 0.8 / oscillation 0.30 |

> 自动指标只做筛查；审美、发音、字幕可读性仍需人工。

---

## 10. 剩余死配置与未接线字段（重要）

TTS 模式字段已接线：`audio.yaml tts.mode` 是有效默认，`settings.tts.mode` 已删除；但默认值仍为 `sft`，需按 PRD 改为 `zero_shot`。以下仍未接线：

| 字段 | 现状 | 建议 |
|---|---|---|
| `audio.yaml subtitles.*` | 无消费者 | 接线或删除 |
| `audio.yaml narration_modes.*.leading_ms` | 未被 `r3_build` 消费 | 接线或删除 |
| `generation.yaml profiles.*` | 无生产消费者 | 让 jobs 读取，或标注“仅记录” |
| `styles.yaml validation_status` | 两风格 `PARTIAL`（2026-11-04 更新） | 完整作品后再升级 |
| `workflows/README.md` 的部分文件名 | 文件不存在 | 标注目标命名 |
| `docs/ENVIRONMENT.md` “待下载” | 文件已存在 | 更新 |

这些属于 Phase C 的其他独立任务，不要顺手改。

## 11. 推荐默认值（不是已生效值）

| 场景 | 推荐 | 依据 |
|---|---|---|
| 新短篇 | 576×1024 / 4 步 / CFG 1.0 / seed 7100+ | P1 实测 |
| 长卷工笔 | 576×1024 静帧 → 宽幅长卷 + scroll clips | 81.373 s 案例 |
| Wan | 73 帧 / 20 步 / CFG 5 / shift 8 | R2/R3 实测 |
| 成片 | 1080×1920 / 24 fps / CRF 18 / AAC 192k | R3/P1 |
| 字幕 | Source Han Sans CN Regular 56 px | 正式构建 |
| 配音 | SFT 中文女；recitation/classical_recitation | R3-D 决策 |
| 零样本 | 仅显式选择；CosyVoice2-0.5B | 产品决策 |
| 声景 | `broadcast_light`；BGM 通过 timeline 接入；SFX 留空 | 当前配置 |

> “推荐”不等于“已验证适用于所有题材”；每次风格/题材变化都要重新看片。
