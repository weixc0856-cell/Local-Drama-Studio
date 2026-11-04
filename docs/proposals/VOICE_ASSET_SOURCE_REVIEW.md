# VOICE-ASSET 声音来源核验与首批选取

> 文档状态：**审计/候选评审**（2026-11-04），不是正式 PRD，也不是商用授权结论。
> 目的：核验声音来源、拉取允许拉取的候选、记录阻断项，并按 VOICE-ASSET 规则给出首批种子候选。
> 规则：自动发现 ≠ 自动授权；`APPROVED` 之前不得进入正式 TTS 生产。
> 相关：[PRD_AUDIOVISUAL_UPGRADE_PROPOSAL.md](PRD_AUDIOVISUAL_UPGRADE_PROPOSAL.md)、[AUDIOVISUAL_GAP_AUDIT.md](AUDIOVISUAL_GAP_AUDIT.md)

---

## 0. 结论

| 来源 | 能否自动拉取 | 当前状态 | 结论 |
|---|---|---|---|
| Mozilla Common Voice | 需要 Mozilla Data Collective 账号并接受 Data Consumer Terms | `BLOCKED` | 未下载；不得镜像/转存；商用取决于具体 Data Consumer License |
| AISHELL-3 (OpenSLR SLR93) | 官方 73 MiB Sample 可直接下载；全量 19 GB | `BLOCKED`（许可） | 已下载 Sample 并选 1 条候选；未下载全量；Apache-2.0 标签与第三方“仅学术”说法冲突，需书面澄清 |
| LibriVox | 可直接从 Internet Archive 下载 | `TECHNICALLY_VALIDATED` | **已拉取 1 条候选**；美国公有领域，其他司法辖区需复核；未批准生产 |
| Internet Archive 其他条目 | 逐条 | `DISCOVERED` | 不能把“可下载”当商用许可 |
| Piper / Sherpa-ONNX | 本地模型 | `DISCOVERED` | 只作测试源；逐 Voice Model Card 核验 |
| 自己录制 | 本地文件 | `LICENSE_VERIFIED` | 已有 3.37 s 自录 prompt；需人工试听后才能 `APPROVED` |

**首批种子库当前 = 0 个 `APPROVED`，4 个候选（自录 + LibriVox 美国公有领域 + AISHELL-3 Sample ×2）。** 这是真实状态，不是目标数量。

---

## 1. 来源核验

### 1.1 Mozilla Common Voice

- 数据集许可为 **CC0-1.0**，但下载已迁移到 **Mozilla Data Collective (MDC)**。
- MDC Data Consumer Terms 要求注册账号、接受具体 Data Consumer License；并禁止：
  - 在 MDC 之外的平台托管/存储/提供数据集；
  - 镜像、复制或再分发数据集的全部或实质部分；
  - 追踪、匹配或重新识别数据贡献者。
- 商用不是平台默认权利，取决于具体 Dataset License。
- 结论：**`BLOCKED`（账号/条款）**；本轮未下载、未转存。
- 官方：[MDC Terms](https://mozilladatacollective.com/terms)、[Common Voice](https://commonvoice.mozilla.org/)

### 1.2 AISHELL-3 / OpenSLR SLR93

- OpenSLR 页面标注 **Apache License v2.0**，约 85 小时、218 名说话人、88,035 条普通话、字级/拼音级转写，下载 `data_aishell3.tgz` 约 **19 GB**。
- 第三方镜像（如 PaddleSpeech README）出现“仅学术研究、未经许可不得商用”的说法，与 OpenSLR 的 Apache-2.0 标签存在冲突。
- 官方 Sample 已下载：`AISHELL-3-Sample.rar`，73 MiB，SHA-256 `4879c25b…`；解压后包含 `train/` 与 `test/`，仅 2 个说话人（SSB0009、SSB1711），**不是全量 19 GB**。
- Sample 不包含完整 `spk-info`，因此 **未推断性别/年龄**；`speaker_id=SSB1711`，`gender_label=UNKNOWN_NOT_PRESENT_IN_SAMPLE`。
- 已选 2 条：`SSB17110133.wav`（3.83 s，“杭州之江金都极地海洋公园”）与 `SSB00090015.wav`（5.07 s，“不仅在赛事热身阶段安排型男教练带动热身”）；均转 16 kHz mono；CosyVoice2-0.5B zero-shot 实测均 PASS（2.26 s / 3.28 s）。
- `SSB0009` 的 female 标签来自第三方 HF voice package，sample 本身没有官方 gender/age；生产前必须用官方 `spk-info.txt` 复核。
- 结论：**来源仍 `BLOCKED`（许可冲突）**；候选仅 `TECHNICALLY_VALIDATED`，不批准商用生产。全量 19 GB 未下载。
- 官方：[OpenSLR SLR93](https://openslr.org/93/)、[Sample](http://aishell-3.oss-cn-beijing.aliyuncs.com/AISHELL-3-Sample.rar)

### 1.3 LibriVox

- LibriVox 只录制美国公有领域文本；声明**所有录音进入公有领域**，允许出售、广播、混音等任何用途，不要求署名（但欢迎 credit）。
- 明确警告：**美国公有领域不等于其他司法辖区公有领域**；非美国用户需自行核对本地版权。
- 本轮已从 Internet Archive 直接拉取一条中文录音：
  - 数据集/条目：`three_hundred_tang_poems_volume_5_1501_librivox`
  - 曲目：`01 - 224 Deer-park Hermitage`（《鹿柴》，王维）
  - 源文件：`300tangpoems5_01_various_128kb.mp3`
  - 源时长：40.4745 s；44.1 kHz mono MP3；651,688 B
  - 源 SHA-256：`3020b8355fccbc92b02bffa308364064e4f4143c8a9ae89aaa7113d8e5d095a3`
  - 许可：Public Domain Mark 1.0；LibriVox public-domain statement
  - 朗读人：条目列出多位读者，**未标明本曲目具体读者**
- 结论：**`TECHNICALLY_VALIDATED` / `LICENSE_VERIFIED_US_ONLY`**；不批准中国商用生产，直到完成辖区与读者身份复核。
- 官方：[LibriVox Public Domain](https://librivox.org/pages/public-domain/)、[Archive item](https://archive.org/details/three_hundred_tang_poems_volume_5_1501_librivox)

### 1.4 Internet Archive（非 LibriVox 条目）

- 每个条目的权利状态不同；平台可下载 ≠ 可商用。
- 结论：`DISCOVERED`；逐条检查 `licenseurl`/`rights`/来源作品。
- 官方：[Internet Archive](https://archive.org/)

### 1.5 Piper / Sherpa-ONNX

- 模型和每个音色的许可可能不同；必须逐个检查 Voice Model Card。
- 合成音频可用于**技术测试**，不应作为主力正式声音资产；生成音频的权利还取决于 TTS 模型/声音模型/训练数据条款。
- 结论：`DISCOVERED`；仅测试源。
- 官方：[Piper](https://github.com/rhasspy/piper)、[Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx)

### 1.6 自己录制

- `assets/audio/prompts/VOICE_RIGHTS.md`：项目所有者本人录制，授权本项目内 TTS 零样本参考、克隆推理与成片发布；不含向第三方再分发原始录音。
- 现有 `assets/audio/prompts/my_voice_clean_v1.wav`：3.37 s / 24 kHz mono / SHA-256 `745f569b…`。
- 结论：`LICENSE_VERIFIED`；人工试听/声纹 profile 验收前不标 `APPROVED`。

---

## 2. 已拉取的候选

### 2.1 LibriVox《鹿柴》后两句

| 项 | 值 |
|---|---|
| 候选文件 | `assets/audio/prompts/pending/librivox_tang5_01_20261104.wav` |
| 元数据 | `assets/audio/prompts/pending/librivox_tang5_01_20261104.meta.json` |
| 格式 | 16 kHz / mono / PCM WAV |
| 时长 | 5.250 s |
| SHA-256 | `c0e2f9e51bf93a0e2beee1decec2db0278d04221cd85743df5f000e0ef5b5a1b` |
| 文本 | `返景入深林，复照青苔上。` |
| ASR | Whisper base, zh, initial_prompt=full poem；转写与文本一致 |
| 电平 | mean -20.7 dB / max -0.8 dB；未达到削波阈值 |
| 静音 | 内部停顿 827 ms；头尾已修剪 |
| CosyVoice2 zero-shot | **PASS**（模型 `CosyVoice2-0.5B`；输出 `experiments/voice_asset_discovery/zeroshot_candidate.wav`，4.12 s，SHA-256 `d6060526…`） |
| 状态 | `TECHNICALLY_VALIDATED`，`approved_for_production=false` |
| 阻断 | 美国公有领域 vs 中国辖区未复核；本曲目读者未标明；人工试听未做。CosyVoice 技术可用不等于审美/商用通过。 |

> 裁剪方式：源 MP3 第 24.7–30.9 s → 16 kHz mono WAV（6.2 s）→ 去掉头 0.65 s、尾 0.35 s → 5.25 s。原始 MP3 与切片过程在 `experiments/voice_asset_discovery/`，不进入正式资产库。

### 2.2 AISHELL-3 Sample（SSB1711）

| 项 | 值 |
|---|---|
| 候选文件 | `assets/audio/prompts/pending/aishell3_ssb1711_20261104.wav` |
| 元数据 | `assets/audio/prompts/pending/aishell3_ssb1711_20261104.meta.json` |
| 格式 | 16 kHz / mono / PCM WAV |
| 时长 | 3.832 s |
| SHA-256 | `e20e10317ceb2ff59d28f3e48b929814575a2aed7ad13d06d5eb1a89be8e0c23` |
| 文本 | `杭州之江金都极地海洋公园` |
| 说话人 | `SSB1711`；sample 无性别/年龄标签，未推断 |
| 电平 | mean -31.4 dB / max -16.1 dB；未削波；偏轻 |
| CosyVoice2 zero-shot | **PASS**（输出 `experiments/voice_asset_discovery/zeroshot_aishell_candidate.wav`，2.26 s，SHA-256 `041ff8d0…`） |
| 状态 | `TECHNICALLY_VALIDATED`，`approved_for_production=false` |
| 阻断 | AISHELL 商用许可需书面澄清；无性别标签；人工试听/完整度未做 |

### 2.3 AISHELL-3 Sample（SSB0009，第三方标注 female）

| 项 | 值 |
|---|---|
| 候选文件 | `assets/audio/prompts/pending/aishell3_ssb0009_20261104.wav` |
| 元数据 | `assets/audio/prompts/pending/aishell3_ssb0009_20261104.meta.json` |
| 格式 | 16 kHz / mono / PCM WAV |
| 时长 | 5.072 s |
| SHA-256 | `73425857c927241d88296e9428e7fcf8fc111a84194a609c093eed686f060a01` |
| 文本 | `不仅在赛事热身阶段安排型男教练带动热身` |
| 说话人 | `SSB0009`；**female 仅来自第三方 HF voice metadata，不是 sample 官方标签** |
| 电平 | mean -26.6 dB / max -7.7 dB；未削波 |
| CosyVoice2 zero-shot | **PASS**（输出 `experiments/voice_asset_discovery/zeroshot_aishell_female_candidate.wav`，3.28 s，SHA-256 `836e498e…`） |
| 状态 | `TECHNICALLY_VALIDATED`，`approved_for_production=false` |
| 阻断 | AISHELL 商用许可待书面确认；官方 gender/age 标签缺失；人工试听未做 |

### 2.4 自录 prompt

| 项 | 值 |
|---|---|
| 文件 | `assets/audio/prompts/my_voice_clean_v1.wav` |
| 时长/格式 | 3.37 s / 24 kHz mono |
| SHA-256 | `745f569b4f6fa98bde6b18e0be08ad7c1303827e1f6aff128581cc2f1352d08c` |
| 文本 | `希望你以后能够做的比我还好呦。` |
| 权利 | 自录；`VOICE_RIGHTS.md` |
| 状态 | `LICENSE_VERIFIED`；`approved_for_production=false`（人工试听/voice profile 未记录） |

---

## 3. 技术筛选结论

- **3–8 s 是我们的筛选标准，不是 CosyVoice 的硬限制。** 本地 CosyVoice 代码对 prompt 的硬上限约 30 s（16 kHz token 提取），官方示例用 16 kHz prompt；社区经验建议 3–10 s（5–8 s 更稳）。系统应按 3–8 s 筛选，但错误信息/文档不要写成“模型只支持 8 s”。
- 输入统一转 16 kHz mono PCM WAV；最终输出采样率由服务决定（CosyVoice2 24 kHz / SFT 22.05 kHz），再由 `tts.py` 统一重采样到 48 kHz。
- ASR 只作辅助：候选必须保留原始标注文本；ASR 不一致 → `TRANSCRIPT_REVIEW_REQUIRED`，不得用 ASR 覆盖原文。
- 噪声/混响/音乐底噪、首尾字完整性、自然度目前 **未做自动判定**；`background_noise_check: NOT_RUN`、`human_review: PENDING`。

---

## 4. VOICE-ASSET 首批种子库状态

| 目标 | 目标数量 | 当前 |
|---|---|---|
| 旁白音色 | 3–5 | 0 `APPROVED` |
| 诗词朗诵音色 | 2–3 | 0 `APPROVED`；1 个 LibriVox 候选（美国公有领域） |
| 角色音色 | 2–3 | 0 `APPROVED` |
| 来源可追溯 | 100% | 4 个候选有 source/hash/transcript；2 个来源 `BLOCKED`（Common Voice / AISHELL 许可） |

**不要**把 5.25 s LibriVox 候选写成“已入库音色”；它只是 `TECHNICALLY_VALIDATED` 候选。

---

## 5. 建议的下一步（按顺序）

1. **Common Voice**：决定是否注册 MDC 账号并接受 Data Consumer Terms；若不能，保持 `BLOCKED`，不要下载/镜像。
2. **AISHELL-3**：Sample 已下载并完成 1 条技术验证；向 OpenSLR/数据提供方书面确认 Apache-2.0 是否覆盖商业使用。未确认前保持 `BLOCKED`，不要下载 19 GB 全量。
3. **LibriVox**：对中国商用辖区做法务复核；确认读者身份是否影响权利；人工试听候选；通过后才有资格 `LICENSE_VERIFIED` + `APPROVED`。
4. **自录**：做一次 voice-profile 试听/参数记录；它是最可控的正式音色来源。
5. **VOICE-ASSET 代码**：等 PRD 批准后，再实现 adapter/registry/slicing/QA；本轮只落候选与元数据。

---

## 6. 与 AUDIO/TTS 的合并原则

- **只建一套音频资产系统**：`PRD-AUDIO-005`（音频资产台账）与 `PRD-VOICE-ASSET-008`（Prompt 音频资产注册表）共用同一 `assets/audio/manifest.json` 扩展；不要再建第二套 BGM/SFX/voice 注册表。
- `VOICE-ASSET` 的资产类型只增加 `tts_prompt`；BGM/SFX 仍由 AUDIO 域管理。
- Voice Profile 引用 `asset_id`，不复制音频文件；一个 profile 可关联多个候选，一个候选可被多个 profile 引用。
- `APPROVED` 是生产门；`TECHNICALLY_VALIDATED`/`LICENSE_VERIFIED` 只是候选状态。

---

## 7. 来源链接

- Common Voice / MDC: https://commonvoice.mozilla.org/ , https://mozilladatacollective.com/terms
- AISHELL-3: https://openslr.org/93/
- LibriVox: https://librivox.org/pages/public-domain/ , https://archive.org/details/three_hundred_tang_poems_volume_5_1501_librivox
- CosyVoice: https://github.com/FunAudioLLM/CosyVoice
- Piper: https://github.com/rhasspy/piper
- Sherpa-ONNX: https://github.com/k2-fsa/sherpa-onnx
