# R3-D 女声韵律优化实验报告

> 执行日期：2026-11-03
> 模型：CosyVoice-300M-SFT（本地 CPU）
> 音色：`中文女`（主）；`中文男`仅 S3-A.1 对照
> 状态：技术实验 + 人工试听决策完成；S3-A.3 已固化默认；S3-A.4 正式链路已用合成夹具验证；S3-A.5 时间轴已迁入正式包；授权 `UNVERIFIED`
> 设计规范：[R3D_VOICE_DESIGN.md](R3D_VOICE_DESIGN.md)

## 0. S3-A.3 人工决策与固化

S3-A.3 是规范固化，不是新一轮合成。用户人工试听结论如下（`DECISION`；未记录数值化评分）：

| 项 | 决策 | 备注 |
|---|---|---|
| 诗词默认 | **Poetry B** | 语义分段 + 固定语速 1.0 + 精确静音 |
| 口播默认 | **Narration B** | 语义分段 + 固定语速 1.0 + 精确静音 |
| 混合内容 | Mixed C 仅作实验 | 不作为生产默认 |
| 诗词方案 C | 仅作实验 | 不作为生产默认 |
| 音色 | 中文女首选；中文男回退/对照 | 仍不代表所有文本都适用 |
| S3-A.3 重跑 A/B/C | 不重跑 | `NOT_RUN`；复用已有试听结果与音频 |

固化参数：

- `leading_silence_ms`：poetry 400 / narration 300 / mixed 350。
- 时间轴统一整数毫秒；开头静音只加一次；第一句字幕从实际发声开始。
- 后续 True Peak 目标 `≤ -2.0 dBTP`；S3-A.2 历史副本使用 `-1.5 dBTP`，不重渲染。
- 默认配置样例：`experiments/r3d/voice/designs/defaults/poetry_default.json`、`narration_default.json`；混合实验配置 `mixed_experimental.json`。

**重要：** §1 的时长是 S3-A.2 历史实测，**不包含**开头静音。S3-A.3 不重新生成音频；不能把“未来默认总时长”误写成这些历史文件的实测值。

时间轴实现与验证：

- `src/drama_studio/voice/timeline.py`：正式模块，纯函数，负责整数毫秒时间轴、开头静音、字幕边界。
- `experiments/r3d/voice/test_timeline.py`：300/350/400 ms 参数化测试；14 项通过（含 S3-A.4 追加的 2 项 padding 测试），pytest 退出码 0。
- `experiments/r3d/voice/run_prosody.py`：已接入 `build_timeline` 和开头静音，供后续运行使用；本阶段未运行。
- 现有 `experiments/r3d/voice/prosody/` 音频、SRT、timeline 文件保持原状，未覆盖。

## 1. 本阶段验证结论

| 方案 | 内容 | 时长 | 语音时长（不含静音） | 设计停顿 | LUFS | True Peak | 生成墙钟 |
|---|---|---|---|---|---|---|---|
| A | 整段一次合成（S3-A.1 女声） | 20.155 s | 20.155 s | 1 处 / 0.495 s | -17.29 | -1.50 | 139.58 s |
| B | 6 段语义分段 + 静音 | 24.048 s | 20.248 s | 6 处 / 3.800 s | -16.85 | -1.47 | 84.57 s |
| C | 6 段 + 局部语速 | 26.718 s | 22.918 s | 6 处 / 3.800 s | -16.15 | -1.50 | 91.34 s |
| 口播 B | 5 段现代解说 | 24.714 s | 21.664 s | 5 处 / 3.050 s | -16.67 | -1.50 | 97.26 s |
| 混合 C | 5 段原文+解说 | 22.682 s | 19.482 s | 5 处 / 3.200 s | -16.53 | -1.50 | 80.58 s |

**关键结果：B/C 把女声从 1 处停顿提升到 6 处可控停顿；C 的总时长增加主要来自语速放慢，不是新增文本。**

## 2. 方案对比

### A：整段合成

- 复用 S3-A.1 女声整段音频，20.155 s。
- 只有 1 处 ≥0.3 s 停顿（0.495 s）。
- 优点：生成一次，流程简单；缺点：句间节奏不可控。
- 无逐句时间轴，因此没有 A 的 SRT。

### B：按语义分段 + 精确静音

| 段 | 文本 | 时长 | 语速 | 段后停顿 |
|---|---|---|---|---|
| P01 | 春江潮水连海平，海上明月共潮生。 | 3.053 s | 1.00 | 300 ms |
| P02 | 滟滟随波千万里，何处春江无月明。 | 3.309 s | 1.00 | 450 ms |
| P03 | 江流宛转绕芳甸，月照花林皆似霰。 | 3.692 s | 1.00 | 450 ms |
| P04 | 空里流霜不觉飞，汀上白沙看不见。 | 3.239 s | 1.00 | 600 ms |
| P05 | 江天一色无纤尘，皎皎空中孤月轮。 | 3.135 s | 1.00 | 800 ms |
| P06 | 江畔何人初见月？江月何年初照人？ | 3.820 s | 1.00 | 1200 ms |

- 语音总长 20.248 s，与 A 的 20.155 s 接近；总时长增加主要来自 3.8 s 静音。
- 适合作为“只验证分段/停顿”的对照。
- S3-A.3 人工决策：Poetry B 为诗词默认方案；Poetry C 仅作实验。

### C：语义分段 + 局部语速

| 段 | 时长 | 语速 | 与 B 的差异 |
|---|---|---|---|
| P01 | 4.261 s | 0.95 | +1.208 s |
| P02 | 4.377 s | 0.93 | +1.068 s |
| P03 | 3.796 s | 0.92 | +0.104 s |
| P04 | 3.320 s | 0.90 | +0.081 s |
| P05 | 3.437 s | 0.92 | +0.302 s |
| P06 | 3.727 s | 0.90 | -0.093 s |

- 语音总长 22.918 s，总时长 26.718 s。
- 语速变化只在段落级，不是逐字拉伸；是否自然必须人工听。
- 不预设 C 优于 B；C 更慢、更抒情，也可能更拖沓。

## 3. 字幕与时间轴

| 方案 | SRT 事件 | 时间轴事件 | 时间单调 | 字幕在音频内 | 解码 |
|---|---|---|---|---|---|
| poetry_B | 6 | 6 | ✅ | ✅ | 0 |
| poetry_C | 6 | 6 | ✅ | ✅ | 0 |
| narration_B | 5 | 5 | ✅ | ✅ | 0 |
| mixed_C | 5 | 5 | ✅ | ✅ | 0 |

- SRT 时间来自实际 48 kHz 分段音频，不是固定字数或固定帧。
- 字幕结束 = min(语音结束 + 0.2 s, 下一段开始 − 0.05 s)；不包含长静音。
- 原文/解说混合稿用“原文：/解说：”前缀区分，但音频不朗读标签。
- 以上为 S3-A.2 历史 schema（浮点秒）；S3-A.3 新生产 schema 使用整数毫秒，全片字段为 `audio_start_ms`、`audio_end_ms`、`leading_silence_ms`；段级字段为 `audio_start_ms`、`audio_end_ms`、`speech_start_ms`、`speech_end_ms`、`subtitle_start_ms`、`subtitle_end_ms`、`leading_silence_ms`、`pause_after_ms`。段级 `audio_end_ms` 包含段后停顿。历史文件不改写。
- 文件：
  - `experiments/r3d/voice/prosody/poetry_B/poetry_B.srt`
  - `experiments/r3d/voice/prosody/poetry_C/poetry_C.srt`
  - `experiments/r3d/voice/prosody/narration_B/narration_B.srt`
  - `experiments/r3d/voice/prosody/mixed_C/mixed_C.srt`

## 4. 音频质量检查

| 项 | 结果 |
|---|---|
| 解码 | 四组 `ffmpeg -f null` 退出码 0 |
| 文件缺失 | 无 |
| 段边界 | 每段 5 ms 淡入/淡出，减少爆音 |
| LUFS | -16.15 ~ -16.85（目标 -16） |
| True Peak | 历史：B -1.47；其余 -1.50。S3-A.3 后续目标 ≤ -2.0 dBTP；历史文件不重渲染 |
| 削波 | 未发现（volumedetect max -1.5 dB） |
| BGM 相对响度 | `NOT_RUN`，本阶段无 BGM |
| 段间静音 | 300/450/450/600/800/1200 ms（诗）；口播 300/450/500/600/1200；混合 500/400/600/500/1200 |

词级漏字/重复与异常拼接：目前只完成分段/时间轴/解码/响度检查；**没有**用 ASR 作为词级正确性的 definitive 判据。ASR（Whisper base）对古典诗词错误较多，必须人工核对；转写文件仅作辅助：

- `experiments/r3d/voice/prosody/poetry_B/asr_poetry_B.txt`
- `experiments/r3d/voice/prosody/poetry_C/asr_poetry_C.txt`
- `experiments/r3d/voice/prosody/narration_B/asr_narration_B.txt`
- `experiments/r3d/voice/prosody/mixed_C/asr_mixed_C.txt`

## 5. 当前模型能力与限制

| 能力 | 结论 | 证据 |
|---|---|---|
| 中文女声 | `PASS_VERIFIED` | S3-A.1 + 本实验 |
| 全局 `speed` | `PASS_VERIFIED`（1.0） | A/B |
| 分段 `speed` | `PASS_VERIFIED` | C 6 段不同 speed 全部成功 |
| 原生停顿控制 | 不支持/未验证 | 停顿由 FFmpeg 静音实现 |
| 情绪指令 | `NOT_RUN` / `UNVERIFIED` | `inference_instruct` 代码存在，但 API 未暴露，本机无 Instruct 权重 |
| 发音纠正 | `UNVERIFIED` | 无拼音/SSML 验证 |
| 音量控制 | 无原生参数 | 后期 FFmpeg |
| 长文本切分 | 代码核验 | `split_paragraph` 强标点切分、80 字上限、短句合并；整段 6 句可能合成一个片段 |
| 输出格式 | `PASS_VERIFIED` | 22,050 Hz mono PCM s16le |
| 生成音频商用 | `UNVERIFIED` | 见 §6 |

## 5.1 本地运行统计

| 项 | 值 |
|---|---|
| 请求数 / 失败 | 22 / 0 |
| 累计音频 | 84.31 s |
| 累计合成耗时 | 348.92 s |
| 进程工作集（结束后） | 3.67 GiB |
| 系统可用内存（结束后） | 32.9 GiB |

单段生成耗时、语速、时长与哈希见 `prosody/prosody_manifest.json`；此处不把 CPU 计数器当作峰值。

## 6. 授权状态

| 项 | 状态 |
|---|---|
| CosyVoice 代码 | Apache-2.0 |
| 模型权重 | `UNVERIFIED` |
| 预置「中文女」音色 | `UNVERIFIED` |
| 生成音频商用权 | `UNVERIFIED` |

技术试听可继续；发布前必须单独解决授权。不因 Apache-2.0 推断模型/音色/音频商用权。

## 7. 人工试听与决策（已完成）

用户已完成人工试听，并在 S3-A.3 给出决策：**Poetry B / Narration B 为默认；Mixed C、Poetry C 为实验；中文女首选、中文男回退。** 本阶段未记录数值化评分，也未重跑 A/B/C。

以下保留为试听方法记录，不是待办：

1. 先听 [poetry_ABC_compare.wav](experiments/r3d/voice/prosody/poetry_ABC_compare.wav)（A→B→C，1 s 间隔）。
2. 再分别听 B/C 干净人声与 norm 版本。
3. 按设计文档的 8 项评分：自然度、发音、断句、韵律、情绪、停顿、稳定性、听觉疲劳。
4. 重点判断：B 的固定语速 + 精确停顿是否自然；C 的局部语速是否过慢/拖沓。
5. 口播 B 与混合 C 分别评价，不把诗词和口播当成同一种任务。

**无法由自动指标判定“更像真人”**；本报告只证明停顿可控、时间轴可追溯、技术质检通过。

## 8. 交付文件

- 朗读设计：
  - `experiments/r3d/voice/designs/chunjiang_poetry_design.json`
  - `experiments/r3d/voice/designs/chunjiang_narration_design.json`
  - `experiments/r3d/voice/designs/chunjiang_mixed_design.json`
- 音频：
  - A：复用 `experiments/r3d/voice/female_raw.wav` / `female_norm.wav`（S3-A.1 整段，无新合成）
  - `prosody/poetry_B/poetry_B_clean.wav` / `_norm.wav`
  - `prosody/poetry_C/poetry_C_clean.wav` / `_norm.wav`
  - `prosody/narration_B/narration_B_clean.wav` / `_norm.wav`
  - `prosody/mixed_C/mixed_C_clean.wav` / `_norm.wav`
  - `prosody/poetry_ABC_compare.wav`
- 字幕与时间轴：各方案 `*.srt`、`timeline.json`
- 清单：`prosody/prosody_manifest.json`
- 质检：`prosody/quality_check.json`
- ASR 辅助：各方案 `asr_*.txt`
- S3-A.3 规范与验证：
  - `src/drama_studio/voice/timeline.py`
  - `experiments/r3d/voice/test_timeline.py`
  - `experiments/r3d/voice/timeline_validation.json`
  - `experiments/r3d/voice/designs/defaults/poetry_default.json`
  - `experiments/r3d/voice/designs/defaults/narration_default.json`
  - `experiments/r3d/voice/designs/defaults/mixed_experimental.json`

## 9. S3-A.4 正式链路接入与测试

S3-A.4 已将 `timeline.py` 接入正式音频组装与字幕入口 `scripts/r3_build.py`，但只使用合成夹具验证，未运行真实 TTS。

### 调用关系

```text
r3_tts.py -> WAV + audio_manifest.json
r3_build.py
  -> build_timeline(...)                  # drama_studio.voice.timeline
  -> timeline.json
  -> adelay/amix/loudnorm                 -> mixed.wav
  -> make_srt(timeline)                   -> drama.srt
  -> ASS from the same events             -> drama.ass / burned
  -> final_9x16.mp4 + build_manifest.json
```

- 内容类型：`--content-type` 或 manifest 的 `content_type`；默认 narration。
- 开头静音：poetry 400 / narration 300 / mixed 350 ms；`--leading-ms` 可覆盖。
- 段间停顿：保留 `GAP_MS=800`，单行可用 `pause_after_ms` 覆盖。
- 末尾补齐：`trailing_silence_ms` 把音频补到视频总时长；`voice_end_ms` 与 `audio_end_ms` 分开。
- 历史保护：已有 `final_9x16.mp4` 默认拒绝覆盖，需 `--allow-overwrite`。

### 测试结果

命令：

```text
.venv/Scripts/python.exe -B -m pytest experiments/r3d/voice/test_timeline.py experiments/r3d/voice/test_production_build.py -q -p no:cacheprovider
```

结果：**19 项通过，退出码 0**。其中正式构建夹具 3 组全部返回 0；合成夹具为 3 个 2.0 s 画面、3 条 48 kHz 合成音频、段后停顿 800 ms。

| 内容 | 开头静音 | `voice_end_ms` | `audio_end_ms` | 首字幕 | 末字幕 | mixed / final |
|---|---:|---:|---:|---:|---:|---:|
| poetry | 400 ms | 4300 | 6000 | 400 ms | 3700 ms | 6.0 s / 6.0 s |
| narration | 300 ms | 4200 | 6000 | 300 ms | 3600 ms | 6.0 s / 6.0 s |
| mixed | 350 ms | 4250 | 6000 | 350 ms | 3650 ms | 6.0 s / 6.0 s |

- SRT 事件均为 3 条，单调；首条从实际发声开始，最后一条不超过 `audio_end_ms`。
- 每段 `audio_end_ms = speech_end_ms + pause_after_ms`，段后停顿未重复计入语音。
- `mixed.wav` 与 `final_9x16.mp4` 时长均与时间轴 `audio_end_ms` 一致。
- 证据文件：[production_validation.json](experiments/r3d/voice/production_validation.json)。

### 历史资产保护

[historical_hashes.json](experiments/r3d/voice/production_fixture/historical_hashes.json) 记录 110 个 S3-A.1/S3-A.2/R3-B 文件、106,392,377 字节；测试逐一校验 SHA-256，全部未变化。

### 状态表

| 项 | 状态 | 说明 |
|---|---|---|
| 正式构建接入时间轴 | `PASS_VERIFIED` | 合成夹具，3 种内容类型 |
| 正式构建完整运行 | `PASS_VERIFIED` | 3 次返回 0，软字幕/烧录成片生成，解码 0 |
| SRT/ASS 与音频同源 | `PASS_VERIFIED` | 同一 `timeline.json` |
| S3-A.1/S3-A.2/R3-B 历史资产未变 | `PASS_VERIFIED` | 110 个 SHA-256 |
| True Peak 策略未修改 | `PASS_STATIC` | 仍为 `loudnorm I=-16:TP=-1.5:LRA=11` |
| 真实 CosyVoice 音频接入 | `NOT_RUN` | 本阶段禁止运行 |
| R3-B 真实成片重建 | `NOT_RUN` | 现有成片未覆盖 |
| 商业授权 | `UNVERIFIED` | 模型/音色/音频条款仍未核验 |
| 《洛神赋》完整生产 | `NOT_RUN` | 未开始 |

已知限制：`speech_start_ms` / `speech_end_ms` 以 manifest 分段时长为基准，是计划边界，不是 VAD 或真实语音边界识别结果。

## 10. S3-A.5 时间轴模块正式化

S3-A.5 将时间轴实现从实验目录迁入正式包，生产代码不再向 `experiments/` 注入 `sys.path`。

### 模块迁移

| 项 | 迁移后 |
|---|---|
| 正式模块 | `src/drama_studio/voice/timeline.py` |
| 包入口 | `src/drama_studio/voice/__init__.py` |
| 正式构建导入 | `from drama_studio.voice.timeline import build_timeline, leading_silence_for, make_srt, pad_timeline_to` |
| 实验测试导入 | 同一正式模块；测试文件仍在 `experiments/r3d/voice/test_timeline.py` |
| 实验 runner | `experiments/r3d/voice/run_prosody.py` 改为导入正式模块 |
| 旧模块 | `experiments/r3d/voice/timeline.py` 已移入正式包，不保留副本 |

接口和行为保持不变：

- `build_timeline()`
- `pad_timeline_to()`
- `make_srt()`
- `leading_silence_for()`
- 开头静音 400/300/350 ms、段间停顿、200 ms 字幕尾部、50 ms 段间隔、尾部补齐

### 真实音频边界说明

`speech_start_ms` / `speech_end_ms` 是依据设计时间轴和 `audio_manifest.json` 中片段时长计算的计划边界；它们不是 VAD 输出，也不是对真实语音波形检测后的结果。S3-A.5 不引入 VAD，也不增加依赖。

### 验证结果

测试命令：

```text
.venv/Scripts/python.exe -B -m pytest experiments/r3d/voice/test_timeline.py experiments/r3d/voice/test_production_build.py -q -p no:cacheprovider
```

结果：**19 项通过，退出码 0**。

- 正式包导入：`from drama_studio.voice.timeline import ...` 成功
- 三种内容类型开头静音仍为 400/300/350 ms
- 时间轴 14 项测试通过
- 正式构建/合成夹具 5 项测试通过
- 110 个历史资产的 SHA-256 未变化
- `scripts/r3_build.py` 不再包含 `experiments/` 路径注入；R3-B 数据输入仍在 `experiments/r3b/`，属于数据路径而非模块依赖

### 状态表

| 项 | 状态 | 说明 |
|---|---|---|
| 正式模块迁移 | `PASS_VERIFIED` | `src/drama_studio/voice/timeline.py` 可导入 |
| 正式构建使用正式包导入 | `PASS_VERIFIED` | 合成夹具 3 组通过 |
| 无 `experiments/` 模块反向依赖 | `PASS_VERIFIED` | 导入检查和静态扫描；数据输入仍为 experiments/r3b |
| 原有时间轴行为保持 | `PASS_VERIFIED` | 19 项测试 |
| 历史资产 110 个未变 | `PASS_VERIFIED` | SHA-256 校验 |
| 无重复实现/循环导入 | `PASS_STATIC` | 仅正式模块一份；导入链单向 |
| 真实 CosyVoice 音频 | `NOT_RUN` | 本阶段禁止运行 |
| VAD / 真实语音边界 | `NOT_RUN` | 未实现，也未声称 |
| 商业授权 | `UNVERIFIED` | 模型/音色/音频条款未核验 |
| 《洛神赋》完整生产 | `NOT_RUN` | 未开始 |

## 11. 工作区状态（S3-A.5）

```text
HEAD: ad921ed
已修改、未暂存：
  scripts/r3_build.py
未提交新增：
  src/drama_studio/voice/
  docs/R3D_VOICE_SELECTION_PREP.md
  docs/R3D_VOICE_AUDITION_REPORT.md
  docs/R3D_VOICE_DESIGN.md
  docs/R3D_VOICE_PROSODY_REPORT.md
  experiments/r3d/
```

- S3-A.5 将 `timeline.py` 从 `experiments/r3d/voice/` 移入 `src/drama_studio/voice/`，新增 `src/drama_studio/voice/__init__.py`。
- `scripts/r3_build.py` 改为正式包导入，不再注入 `experiments/` 到 `sys.path`。
- 实验测试和实验 runner 改为导入正式模块；旧实验目录中的 `timeline.py` 不保留副本。
- 时间轴 + 正式构建测试合计 **19 项通过**，pytest 退出码 0。
- 110 个历史资产 SHA-256 未变化；未覆盖 S3-A.2 历史实验文件或 R3-B 现有成片。
- 未修改 `workflows/`、模型、模型权重或环境；未修改 CosyVoice 参数/声音风格/True Peak 策略。
- 未暂存、未提交、未推送。
- CosyVoice 50000、ComfyUI 8188 均未监听。
- 未调用云端 API，未下载新模型，未安装新依赖。
- 未进入《洛神赋》完整生产。
