# 双管线动态表现与古诗词声音能力升级报告

> 执行日期：2026-11-04
> 环境：Intel i7-13700K / 64 GB DDR5 / Intel Arc A750 8 GB / FFmpeg 8.1 / Python 3.12
> 服务：ComfyUI 未启动、Qwen3 LLM 未启动、CosyVoice-300M-SFT 仅在配音阶段启动（CPU，50000）
> 状态口径：`docs/PRD.md` §0.2。**技术检查通过不等于人工审美通过；两者分开记录。**

## 0. 结论

| 能力 | 状态 | 证据 |
|---|---|---|
| 确定性镜头运动（缓入缓出推近/拉远/横移/推近带横移） | `PARTIAL` | 技术执行 + 首/中/末帧 + 参数 manifest；人工看片 PENDING |
| 局部微动（水面、植物、云雾、墨迹） | `PARTIAL` | 真实执行；静态机位结构带差 0.0014–0.0633/255；人工看片 PENDING |
| 水墨转场（crossfade / ink_dissolve / ink_reveal / ink_spread） | `PARTIAL` | 两段独立测试视频全部通过；无黑帧、时长准确；人工看片 PENDING |
| 标准朗诵（`recitation`） | `PARTIAL` | 波形/时长/ ASR 通过；发音人工复核 PENDING |
| 古典吟诵（`classical_recitation`） | `PARTIAL` | 速度/停顿/分句真实执行；无音高控制；人工试听 PENDING |
| 真正吟唱（`chant`） | `NOT_RUN`（不支持） | 接口无音高/旋律/时长参数；CLI 明确拒绝 |
| 发音词典与逐句标注 | `PASS_STATIC`（数据结构） | 14 词组；显示/ TTS / 原文分层；ASR 辅助复核 |
| 双风格接入同一生产链路 | `PARTIAL` | 两种风格各 2 镜头成片；技术 PASS；人工审美 PENDING |
| 春江花月夜正式双版本 | `NOT_RUN` | 本轮不进入正式作品；人工审查后再做 |

## 1. 实际调用链（改动后）

```text
storyboard (shot.motion 文本)
  → production --motion-plan
      + config/styles.yaml (motion.camera / local_policy / transition)
      + audio_manifest (align_audio)
      + motion_regions.json (人工区域)
      → work/motion_shots.json + motion_plan.meta.json
  → scripts/motion_build.py
      → work/motion/build-<time>/<shot_id>.mp4
      → work/motion/build-<time>/sequence/sequence.mp4（转场已合成，时长不变）
  → production --sequence → work/segments.json（单条 video segment）
  → scripts/r3_build.py → 配音 + 字幕 + 1080×1920 母版
  → drama_studio.quality → build_quality + audio_qa
```

工作台新增三个受限任务：`motion.plan`、`motion.render`、`audio.qa`；`segments.build` 新增 `sequence` 参数；`tts.synthesize` 新增 `mode` 参数。

## 2. 修改与新增文件

新增：

- `src/drama_studio/motion/`：`spec.py`、`camera.py`、`local.py`、`transition.py`、`render.py`、`texture.py`、`noise.py`、`__init__.py`
- `src/drama_studio/voice/pronunciation.py`、`src/drama_studio/voice/recitation.py`
- `config/pronunciation.yaml`
- `scripts/motion_build.py`、`scripts/transition_probe.py`、`scripts/tts_qa.py`
- `tests/test_motion.py`、`tests/test_pronunciation.py`、`tests/test_recitation.py`

修改：

- `config/styles.yaml`：两种风格各自新增 `motion.camera`、`motion.local_policy`、`motion.transition`
- `src/drama_studio/style_presets.py`：严格校验上述字段
- `src/drama_studio/production.py`：`build_motion_plan`、`build_segments(sequence=...)`、CLI
- `src/drama_studio/quality.py`：逐行音频 QA（响度、削波、静音、时长、字幕时序）
- `src/drama_studio/voice/tts.py`：文本分层、诵读模式、分句/停顿、发音报告
- `src/drama_studio/workspace/tasks.py`：`motion.plan` / `motion.render` / `tts mode` / `segments sequence`
- `src/drama_studio/web/js/pages/tasks.js`：工作台表单
- `scripts/r3_tts.py`：`--mode`；`scripts/s2_build.py`：纹理实现改为共享模块
- `tests/test_workspace_api.py`、`tests/test_production.py`：新入口与序列模式测试

## 3. 镜头运动

| 能力 | 实现 | 验证 |
|---|---|---|
| 缓动 | linear / ease_in / ease_out / ease_in_out，FFmpeg 表达式 | 单测 + 真实渲染 |
| 推近/拉远 | `zoompan`，2× 画布，焦点可配，默认 3–6% | 5 s 推近实测 1.040（INK）/ 1.036（BOAT） |
| 横移 | `crop` 窗口，速度由风格配置（工笔 30 px/s） | 工笔 4.58 s 内 137 px，30.0 px/s |
| 推近带横移 | `zoompan` + 横向焦点漂移 | 手工计划真实执行 |
| 静止 | cover + crop | P1 shot_003 |
| 2.5D 视差 | 需要显式前后景图层；缺失时拒绝 | 未执行 |

约束写入配置而不是代码：`scroll_speed_px_s`、`push_rate_per_s`、`push_scale_min/max`、`easing`、`focus`、`push_pan_fraction`。所有解析结果（含 fallback 原因）写入 `motion_manifest.json`。

## 4. 局部微动

统一字段：`layer_id / motion_type / mask / amplitude / frequency / direction / duration / easing / feather / exclusion_masks`。区域由人工在 `motion_regions.json` 中给出；没有分割模型，也不从整图猜测。

已执行类型：`water_ripple`、`reflection_distortion`（复用同一实现）、`cloud_drift`、`leaf_sway`、`reed_sway`、`ink_diffusion`；`petal_drift` / `bird_motion` 只接受独立 RGBA 图层，缺失时直接拒绝。

静态机位隔离检查（P1 shot_003，1080×1920，首帧→中帧平均绝对差，0–255）：

| 区域 | 差值 |
|---|---|
| 水面（动态区） | 0.5242 |
| 左侧芦苇 | 1.3335 |
| 右侧芦苇 | 1.9912 |
| 天空结构带 0–15% | **0.0014** |
| 上部结构带 16–44% | **0.0633** |

结论：局部运动发生时，未覆盖的山体/天空几乎不变；动/静区域可独立检查。运镜镜头（push/pan）的结构带差值包含运镜位移，manifest 明确标注“不能单独归因于局部微动”。

## 5. 水墨转场

技术探针：`scripts/transition_probe.py`，两段 3 s、1080×1920、24 fps 纯色测试视频（左 `#B02C26`，右 `#1E4478`），1.2 s 转场。四种类型全部通过：

| 类型 | 时长 | 黑帧 | 起始=左 | 结束=右 | 中间混合 |
|---|---|---|---|---|---|
| crossfade | 1.2 s | 0 | 是 | 是 | 是 |
| ink_dissolve | 1.2 s | 0 | 是 | 是 | 是 |
| ink_reveal | 1.2 s | 0 | 是 | 是 | 是 |
| ink_spread | 1.2 s | 0 | 是 | 是 | 是 |

`ink_dissolve` / `ink_spread` 使用距离场 + 多尺度种子噪声 + 平滑 LUT，无二值阈值；合成使用 `alphamerge` + `overlay`（`maskedmerge` 会混合色度平面，已实测排除）。遮罩序列可复现（同一 seed 两次逐字节一致）。

时长保护：转场时长不得超过相邻较短镜头的 `max_fraction`（默认 0.35）。转场只消耗上一镜头的尾部 handle，序列总时长等于镜头时长之和，因此音频时间轴不变。

证据：`experiments/mv/transition/build-20261104-004956/transition_manifest.json`。

## 6. 声音

### 6.1 文本分层与发音词典

- `source_text` / `display_text` / `tts_text` / `pronunciation_overrides` 分开保存；字幕显示原文，TTS 使用独立文本。
- `config/pronunciation.yaml` 收录首批 14 个词组，支持繁体变体（如 青楓浦、魚龍潛躍），按词组最长匹配，不做单字全局替换。
- 报告写入 `pronunciation_report.json`：每行命中、偏移、预期拼音、来源层（display/tts）、能力声明。
- **能力边界**：CosyVoice-300M-SFT 的 `/tts` 只接收 `text / speaker / speed / text_frontend`；没有音素、拼音、音高、时长接口。因此词典只用于核验，**不能声称已控制发音**，也不允许用改字来“修正”。

### 6.2 标准朗诵与古典吟诵

| 模式 | 语速 | 句间停顿 | 句内气口 | 分句 | 实测 |
|---|---|---|---|---|---|
| `narration` | 1.00 | 800 ms | — | 否 | P1 成片 |
| `recitation` | 0.92 | 950 ms | 150 ms | 逗号/顿号/分号/冒号 | 两风格 E2E、14 词组探针 |
| `classical_recitation` | 0.82 | 1200 ms | 260 ms | 同上 | 2 行样片，6.348 s |
| `chant` | — | — | — | — | 拒绝：`unsupported_chant` |

分句合成后按同一音色、同一语速拼接，停顿为数字静音；没有改变声线或音高。古典吟诵只是更慢的朗诵 + 气口，**不是**平长仄短或旋律吟唱。

### 6.3 14 词组发音探针

- 12 行繁体显示 + 简体 TTS，覆盖 14 个词组；12 行全部命中词典（display 与 tts 两层）。
- 波形/时长/响度：`PARTIAL`（无削波、无异常静音、无过低音量）。
- Whisper base ASR 辅助：11/12 行 CER 0.0；第 12 行「碣石瀟湘無限路」CER 0.571，ASR 两次均听成“接时销销/截时销销无线路”。
- 结论：**这是真实的能力缺口**，不是 ASR 偶发。当前接口无法指定 jié shí / xiāo xiāng，且禁止改字；因此记录为 `PARTIAL`，交人工抽听，不伪装修复。
- 证据：`experiments/mv/pronunciation/work/`（`audio_manifest.json`、`pronunciation_report.json`、`audio_qa_report.json`、`tts_qa.json`）。

### 6.4 两风格 E2E 的 ASR

两段成片的 2 行旁白均为 CER 0.0（`tts_qa.json`）。发音人工复核仍为 `PENDING`，因此音频总状态保持 `PARTIAL`。

## 7. 双风格端到端

两套夹具：`experiments/mv/e2e_ink_wash/`、`experiments/mv/e2e_court_green_fine_line/`。各 2 镜头，镜头时长由 `audio_manifest` 真实对齐，末镜头留 1 s 尾。

| 项 | 水墨 `ink_wash` | 工笔 `court_green_fine_line` |
|---|---|---|
| 源图 | IA4 水墨 + 孤舟 | G3 + A1 青绿 |
| 镜头 1 | 缓推近（含雾/水/树微动） | 长卷横移 30 px/s（水面/云微动） |
| 镜头 2 | 缓推近（水/云微动） | 反向长卷横移 |
| 转场 | `ink_dissolve` 1.2 s | `crossfade` 0.8 s |
| 音频 | `recitation`，中文女，0.92，2 行 | 同 |
| 成片 | 8.833 s / 1080×1920 / 24 fps | 9.083 s / 1080×1920 / 24 fps |
| 解码 | PASS | PASS |
| 黑帧 | 0 | 0 |
| 画质检查 | PASS | PASS |
| 音频 QA | PARTIAL（发音人工待审） | PARTIAL（同） |
| 人工审美 | PENDING | PENDING |

路径：

- 水墨：`experiments/mv/e2e_ink_wash/renders/build-20261104-005709/final_9x16.mp4`
- 工笔：`experiments/mv/e2e_court_green_fine_line/renders/build-20261104-005728/final_9x16.mp4`
- 镜头 manifest：各自 `work/motion/build-20261104-005651/` 与 `.../build-20261104-005715/`

真实工作台期数也走通了一遍：`projects/proj_p1_short/episodes/ep_p1_short/` 4 镜头 / 10.0 s，`motion.plan → motion.render → segments(sequence) → r3_build → quality`，成片 `renders/build-20261104-005408-motion-ink/final_9x16.mp4`，画质 PASS。

## 8. 配置是否真正生效

| 配置 | 消费点 | 证据 |
|---|---|---|
| `motion.camera.default/allowed/speed/push_scale/easing/focus/push_pan_fraction` | `motion.spec.resolve_camera` → `motion.camera.camera_chain` | 镜头 manifest 的 `camera` 字段与 FFmpeg argv |
| `motion.local_policy.*` | `motion.render._render_shot` → `motion.local.prepare_layers` | `layers[].info`、`layers_skipped` |
| `motion.transition.*` | `production.build_motion_plan` + `motion.transition` | `transition_in` 与转场 manifest |
| `narration_modes.*` | `voice.recitation` → `voice.tts` | manifest `mode_spec`、分句 `parts`、逐行 `pause_after_ms`（r3 时间轴实际使用） |
| `pronunciation.yaml` | `voice.pronunciation` → TTS 报告 | `pronunciation_report.json` |

未生效字段：无。`motion.width/height` 固定为 1080×1920，`fps` 由渲染器消费。

## 9. 性能与资源

| 任务 | 实测 |
|---|---|
| 单镜头 8 s，3 个局部层 | 10.6 s |
| 2 镜头 12 s，含 1 次水墨转场 | 18.8 s |
| 4 镜头 10 s，3 次转场，8 个局部层 | 28.5 s |
| 两种风格各 2 镜头（含转场 + 序列） | 17.0 s / 12.0 s |
| 四种转场技术探针 | 4.5 s |
| TTS 12 行 / 26.93 s 音频（recitation，CPU） | 103 s |

全部为 CPU + FFmpeg/Pillow；本轮未启动 ComfyUI、FLUX、Wan 或 LLM，GPU 显存占用 0。没有新增依赖（未使用 OpenCV/numpy；Pillow + FFmpeg 足够）。

## 10. 状态与未完成

已完成（技术）：

- 镜头缓动、推拉、横移、推近带横移；参数可复现。
- 水面/植物/云雾/墨迹局部微动；静态结构保护可量化。
- 四种转场；时长不改变；无黑帧。
- 文本分层、14 词组词典、标准朗诵、古典吟诵、逐行音频 QA、ASR 辅助。
- 两种风格独立配置、同一生产链路、独立成片。

未完成 / 需人工：

- 所有运动与转场的**人工看片**（`PENDING`）；未据此宣称 `PASS_VERIFIED`。
- 14 词组中「碣石 / 潇湘」的发音仍不正确；接口无法指定读音，禁止改字，记录为能力缺口。
- 真正吟唱（音高/旋律）未实现；需歌声模型，另行验证。
- 花瓣/飞鸟只有外部 RGBA 图层时才允许动画；本轮未提供素材。
- 2.5D 分层视差未执行（无可靠前后景图层）。
- 春江花月夜正式双版本（两个独立期数/快照/成片）未开始。
- BGM/音效/商用授权仍为 R3-D 缺口。

## 11. Git 状态

本报告生成时未提交、未推送、未 reset、未 clean。工作区包含本轮新增与修改；HEAD 仍为 `651c7dd`。详细文件列表见交付说明。
