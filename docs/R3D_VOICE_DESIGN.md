# R3-D 女声朗读设计与韵律规范

> 版本：v0.4 时间轴模块正式化（S3-A.5）
> 日期：2026-11-03
> 当前模型：CosyVoice-300M-SFT（本地 CPU）
> 默认音色：`中文女`；`中文男`仅作回退
> 状态：S3-A.3 规范已接入 `scripts/r3_build.py`；S3-A.5 时间轴已迁入正式包；合成夹具验证通过；真实 CosyVoice/R3-B 重建 `NOT_RUN`
> 合成实验见 [R3D_VOICE_PROSODY_REPORT.md](R3D_VOICE_PROSODY_REPORT.md)
> S3-A.5 未运行 CosyVoice/FLUX/Wan/ComfyUI，未提交 Git。

## 1. 核心原则

1. **原文、解说、TTS 稿、字幕分开保存。** 不把现代解说混入原文，不擅自改写古诗。
2. **诗词与口播是两种朗读任务。** 诗词重韵律、留白、意境；口播重自然、清晰、信息传达。
3. **字幕先设计，时间轴后生成。** 字幕内容与断句在合成前确定，时间轴用实际音频时长计算。
4. **分段合成 + 精确静音**优先于依赖模型对长文本的自动停顿。
5. **情绪标签只是设计元数据。** 当前 SFT 模型没有可用的情绪指令接口，不能把 `emotion` 拼进 TTS 文本。
6. **不预设女声更好。** 以人工盲听与质量表为准；S3-A.3 的人工结论是女声首选、男声回退，但仍不代表所有文本都适用。
7. **默认方案与实验方案分开。** 诗词 B、口播 B 是默认；诗词 C、混合 C 是实验方案，不得未经试听直接进入生产。
8. **开头静音只加一次。** 开头静音属于全片时间轴，不属于每一段；不得在每段重复添加。
9. **生产时间轴统一使用整数毫秒。** 不以浮点秒作为生产字段，避免累计误差和字幕边界漂移。

## 2. 三类内容

| 类型 | 输入 | 朗读策略 | 字幕策略 |
|---|---|---|---|
| poetry | 原文，逐句/逐联 | 慢、留白、韵律优先 | 保留诗句结构，一屏一到两句 |
| narration | 现代口语稿 | 自然、清晰、长短句交替 | 按语义断句，不按固定字数 |
| mixed | 原文 + 现代解说交替 | 原文用 poetic，解说用 natural | 用“原文/解说”标签区分 |

## 3. 朗读设计数据结构

设计文件顶层与每个段落至少包含：

```json
{
  "design_id": "chunjiang_poetry_v1",
  "content_type": "poetry",
  "leading_silence_ms": 400,
  "segments": [
    {
      "segment_id": "P01",
      "source_text": "原文或解说来源",
      "narration_text": "实际提交 TTS 的文本",
      "subtitle_text": "屏幕显示文本，可含换行",
      "content_type": "poetry | narration | mixed",
      "emotion": "calm | gentle | wistful | solemn | joyful | dramatic | reflective",
      "delivery": "natural | poetic | intimate | emphatic | concluding",
      "speed": 0.95,
      "pause_after_ms": 300,
      "pronunciation_notes": "多音字/生僻字提示",
      "priority": "high | medium | low"
    }
  ]
}
```

约束：

- `source_text` 保留来源；现代解说必须注明“非原文”。
- `narration_text` 不包含情绪标签、舞台说明或字幕换行。
- `subtitle_text` 与 `narration_text` 可以不同：字幕按阅读体验断句。
- `pause_after_ms` 由后期静音实现，不依赖模型原生停顿。
- `speed` 只在方案 C 中使用；方案 B 固定 1.0，避免混入变量。
- `leading_silence_ms` 是项目级字段，按内容类型取默认值；项目级覆盖必须写入时间轴/清单。
- 时间轴字段全部使用整数毫秒，不得用浮点秒替代。

样例：

- `experiments/r3d/voice/designs/chunjiang_poetry_design.json`
- `experiments/r3d/voice/designs/chunjiang_narration_design.json`
- `experiments/r3d/voice/designs/chunjiang_mixed_design.json`
- 默认配置样例：`experiments/r3d/voice/designs/defaults/poetry_default.json`、`narration_default.json`；混合实验配置 `mixed_experimental.json`

## 3.1 人工试听决策（S3-A.3）

用户已完成 S3-A.1/S3-A.2 的人工试听，形成以下 `DECISION`；本阶段没有新的自动评测，也没有重跑合成：

| 项 | 决策 | 状态 |
|---|---|---|
| 诗词默认方案 | 方案 B：语义分段 + 固定语速 + 精确静音 | `DECISION` |
| 口播默认方案 | 方案 B：语义分段 + 固定语速 + 精确静音 | `DECISION` |
| 混合内容 | 方案 C（混合 C）仅作实验方案，不作为默认 | `DECISION` |
| 诗词方案 C | 仅作实验方案，不作为默认 | `DECISION` |
| 音色 | 中文女首选；中文男回退/对照 | `DECISION` |
| S3-A.3 重跑 A/B/C | 不重跑；复用已有试听结果与音频 | `NOT_RUN` |
| 评分数据 | 本阶段未记录数值化评分；只记录方案取舍 | `NOT_RUN` |

注意：S3-A.2 的四组音频生成于本决策之前，**没有开头静音**；S3-A.3 不重新生成、不覆盖现有试听音频。新的 `leading_silence_ms` 只对后续生产运行生效。

## 4. 当前 CosyVoice 能力矩阵

依据：

- 本机代码：`D:\AI\CosyVoice-Runtime\app`，commit `074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc`（2026-05-26）。
- 官方仓库 README：https://github.com/FunAudioLLM/CosyVoice
- 本地 API：`api_server.py` 仅暴露 SFT/zero-shot；`inference_instruct` 方法存在，但未暴露，且本机没有 `CosyVoice-300M-Instruct` 权重。

| 能力 | 当前 SFT | 当前是否实测 | 备注 |
|---|---|---|---|
| 中文女声 | 支持 | 是 | S3-A.1 成功生成；默认首选 |
| 全局语速 `speed` | 支持（每请求） | `PASS_VERIFIED`（1.0） | A/B 使用 1.0 |
| 分段语速 | 可做（多次请求） | `PASS_VERIFIED` | 方案 C 6 段不同 speed 全部成功 |
| 情绪指令 | `inference_instruct` 代码存在，但当前 API/模型未启用 | 否 | 不能把 `emotion` 当参数；需 Instruct 权重，未下载 |
| 停顿控制 | 无原生精确参数 | `PASS_VERIFIED`（后期） | 方案 B/C 用 FFmpeg 精确静音 |
| 发音纠正 | 未验证拼音/SSML | 否 | 文本前端会做归一化，不等于发音纠正 |
| 音量控制 | 无原生参数 | 后期 FFmpeg | 不能当作模型能力 |
| 长文本切分 | 代码按强标点切分，token_max≈80、会合并短句 | 代码核验 | 6 句 84 字符可能被合并为一个片段；这是女声停顿不足的原因之一 |
| 输出格式 | 22,050 Hz / mono / PCM s16le | 是 | 后期转 48 kHz |
| 原文保护 | 无自动保护 | 设计层 | 必须分字段保存，人工核验多音字 |

### `text_frontend` 的真实作用

本机 `frontend.text_normalize`：

- `wetext` 归一化（数字、标点等）；
- 删除换行；
- 替换中文空白/角标；
- 将 `.` 转 `。`；
- 按 `。？！；：、` 等强标点切分；
- 短句会合并（`token_max_n=80`、`token_min_n=60`、`merge_len=20`）；
- 逗号默认不切分。

因此：**把长诗整段提交时，模型可能把多句合并成一个合成片段，句间停顿不受控。** 方案 B/C 改用逐段请求 + 后期静音，绕开这个限制。

## 5. 停顿与语速设计

### 开头静音（S3-A.3 固化）

| 内容类型 | `leading_silence_ms` | 状态 |
|---|---:|---|
| poetry | 400 | 默认 |
| narration | 300 | 默认 |
| mixed | 350 | 实验配置值；混合内容非生产默认 |

规则：

- **只加一次**：位于完整音频文件开头，不是每段都加。
- 首段 `speech_start_ms = leading_silence_ms`；后续段不使用该字段，仍按上一段 `speech_end_ms + pause_after_ms` 计算。
- 第一句字幕 `subtitle_start_ms = speech_start_ms`，不得从 0 开始，也不得覆盖开头静音。
- 项目可以覆盖，但覆盖值必须写入时间轴 JSON 和生成清单；不得只改音频不改时间轴。

### 停顿带（S3-A.2 实测后可继续微调）

| 类型 | 范围 | 用途 |
|---|---|---|
| 短停顿 | 200–350 ms | 句内/短句后 |
| 普通停顿 | 350–600 ms | 句间 |
| 意境停顿 | 600–1000 ms | 联间、情绪转折 |
| 段落收束 | 1000–1500 ms | 结尾/章节 |

不要求每句同值；按语义与情绪设计。

### 语速带（方案 C 初始值）

| 内容 | 范围 |
|---|---|
| 叙述 | 0.95–1.00 |
| 抒情 | 0.88–0.96 |
| 情绪收束 | 0.90–0.95 |

只在方案 C 使用；方案 B 固定 1.0。变化过多会损害自然感。

### 方案对比

| 方案 | 方法 | 变量 |
|---|---|---|
| A | 整段一次合成 | 基线 |
| B | 按语义分段 + 精确静音 | 只测分段/停顿 |
| C | 分段 + 每段 speed 变化 | 分段 + 语速 |

### 默认与实验方案（S3-A.3）

| 内容 | 方案 | 开头静音 | 语速 | 状态 |
|---|---|---:|---|---|
| 诗词 | Poetry B | 400 ms | 固定 1.0 | `DECISION`，默认 |
| 口播 | Narration B | 300 ms | 固定 1.0 | `DECISION`，默认 |
| 混合 | Mixed C | 350 ms | 每段不同 | 实验方案，非默认 |
| 诗词 | Poetry C | 400 ms | 每段不同 | 实验方案，非默认 |

配置样例见 `experiments/r3d/voice/designs/defaults/`。

## 6. 字幕设计

设计阶段：

- 诗词保留诗句结构，一屏 1–2 句；不按固定字数硬切。
- 口播按语义断句，避免一屏堆满。
- 原文与解说用前缀/样式区分，但音频里不朗读标签。
- 字幕行宽按 9:16 手机阅读设计；具体像素规则见 `docs/CONTENT_SPEC.md`。

合成阶段（S3-A.3 起）：

- 全片时间轴字段：`audio_start_ms`、`audio_end_ms`、`leading_silence_ms`。
- 每段字段：`audio_start_ms`（段落在完整音频中的起点，等于 `speech_start_ms`）、`audio_end_ms`（该段槽位终点，包含 `pause_after_ms`）、`speech_start_ms`、`speech_end_ms`、`pause_after_ms`、`subtitle_start_ms`、`subtitle_end_ms`。
- 所有字段使用整数毫秒；不得用浮点秒作为生产时间轴。
- `speech_start_ms`：首段 = `leading_silence_ms`；后续 = 上一段 `speech_end_ms + pause_after_ms`。
- `speech_start_ms` / `speech_end_ms` 是依据设计时间轴和音频片段时长计算的计划边界，不是 VAD 或真实语音波形检测结果。
- `subtitle_start_ms = speech_start_ms`；第一句不得从 0 开始，不得进入开头静音。
- `subtitle_end_ms = min(speech_end_ms + 200, next_speech_start_ms - 50)`；最后一段为 `speech_end_ms + 200`。
- 字幕结束不得进入下一段语音前 50 ms；长静音不计入字幕停留。
- SRT 从完整时间轴生成；事件必须单调、非空、最后一条结束 ≤ `audio_end_ms`。
- 输出 SRT + timeline JSON；时间轴与音频同源。

历史说明：S3-A.2 的四组 `timeline.json` 使用浮点秒字段（`audio_start`/`audio_end`/`subtitle_start`/`subtitle_end`），作为历史证据保留，不按新格式改写。

## 7. 音频后处理

1. 每段原始文件保留（22,050 Hz）。
2. 统一副本 48 kHz / mono / PCM s16le。
3. 段边界 5 ms 淡入/淡出，减少爆音。
4. 精确静音插入（按设计值）。
5. 干净人声版（无 BGM）保留。
6. 响度副本 `loudnorm I=-16 TP=-2.0 LRA=11`，仅作交付候选；原始/clean 不覆盖。
   - 新生产默认目标为 `≤ -2.0 dBTP`；S3-A.2 实测副本使用 `TP=-1.5`，属历史结果，不重渲染、不覆盖。
7. 测量 Integrated LUFS、True Peak、mean/max；BGM 相对响度在加入 BGM 后另行测量。
8. 不用响度归一化冒充音质优化；不过度压缩动态。

## 8. 授权状态

| 项 | 状态 |
|---|---|
| CosyVoice 代码 | Apache-2.0 |
| 模型权重 | `UNVERIFIED` |
| 预置「中文女」音色 | `UNVERIFIED` |
| 生成音频商用权 | `UNVERIFIED` |

技术试听可继续；发布前必须单独解决授权。不得从代码许可证推断音色/音频商用权。

## 9. S3-A.3 阶段不做

- 不下载 `CosyVoice-300M-Instruct` 或其他模型。
- 不升级 CosyVoice/PyTorch。
- 不调用云端 TTS。
- S3-A.3 不修改生产脚本；S3-A.4 已按新任务修改 `scripts/r3_build.py`。
- 不把情绪标签直接拼进 TTS 文本。
- 不承诺当前 SFT 具备情绪/发音纠正能力。
- 不在本阶段重跑 TTS 或 A/B/C，不覆盖现有试听音频。
- 不进入《洛神赋》完整生产。

## 10. 正式生产链路（S3-A.4）

### 实际入口与调用关系

正式语音组装与字幕入口是 `scripts/r3_build.py`；`scripts/r3_tts.py` 只负责生成 WAV 和 `audio_manifest.json`。实际调用关系：

```text
r3_tts.py
  -> experiments/r3b/audio/line_*.wav
  -> experiments/r3b/audio_manifest.json

r3_build.py
  -> build_timeline(..., leading_silence_ms)   [drama_studio.voice.timeline]
  -> timeline.json
  -> adelay + amix + loudnorm                  -> mixed.wav
  -> make_srt(timeline)                        -> drama.srt
  -> ASS from the same timeline                -> drama.ass / burned render
  -> final_9x16.mp4 + build_manifest.json
```

### 接入规则

- `--content-type` 支持 `poetry` / `narration` / `mixed`；也可在 `audio_manifest.json` 写入 `content_type`。未指定时按 narration 处理。
- 开头静音：poetry 400 ms、narration 300 ms、mixed 350 ms；`--leading-ms` 可显式覆盖并写入清单。
- `GAP_MS = 800` 保留既有段间停顿；单行可用 `pause_after_ms` 覆盖。
- `build_timeline()` 一次生成整数毫秒时间轴；音频 delay、SRT、ASS、manifest 全部使用同一份事件。
- 末尾按视频总时长补齐 `trailing_silence_ms`；`voice_end_ms` 与 `audio_end_ms` 分开记录。
- 已存在的 `final_9x16.mp4` 默认拒绝覆盖；需显式 `--allow-overwrite`。

### 已知限制

- `r3_build.py` 已改为 `from drama_studio.voice.timeline import ...`，不再依赖 `experiments/`。
- S3-A.4/S3-A.5 只用合成夹具验证；真实 CosyVoice 音频和 R3-B 重建未执行，状态为 `NOT_RUN`。
- `speech_start_ms` / `speech_end_ms` 以 `audio_manifest.json` 的分段时长为基准，是计划边界，不是 VAD 或真实语音边界识别结果。
- True Peak 处理策略未在本阶段调整；`r3_build.py` 仍使用既有 `loudnorm I=-16:TP=-1.5:LRA=11`。
- R3-B 的历史成片和 S3-A.2 实验音频均未覆盖；未来主动重建 R3-B 时会按 narration 300 ms 新规范生成不同的时间轴。

## 11. 时间轴模块正式化（S3-A.5）

- 正式模块：`src/drama_studio/voice/timeline.py`
- 包入口：`src/drama_studio/voice/__init__.py`
- 正式构建：`scripts/r3_build.py` 使用 `from drama_studio.voice.timeline import build_timeline, leading_silence_for, make_srt, pad_timeline_to`
- 实验测试：`experiments/r3d/voice/test_timeline.py` 直接导入正式模块，不再依赖实验目录内的旧模块。
- 实验 runner：`experiments/r3d/voice/run_prosody.py` 同样导入正式模块。
- 旧的 `experiments/r3d/voice/timeline.py` 已移入正式包，未保留副本。
- 行为未变：开头静音、段间停顿、字幕边界、尾部补齐规则保持 S3-A.3/S3-A.4 验收结果。
- 生产代码不再向 `experiments/` 注入 `sys.path`，也不存在 `experiments/` 反向导入依赖。
- R3-B 的默认数据输入仍在 `experiments/r3b/`；这是数据路径，不是模块依赖。
