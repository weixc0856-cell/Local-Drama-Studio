# 音频素材与授权 · 落地方案

> 起草日期：2026-11-04
> 状态：`ACTIVE`（2026-11-04 部分实施；以代码与资产清单为准）
> 前置：[AUDIO_SOUNDSCAPE_PLAN.md](AUDIO_SOUNDSCAPE_PLAN.md)（S1 已落地）、[ASSET_AND_LICENSE_REGISTRY.md](ASSET_AND_LICENSE_REGISTRY.md) §5
> 本机实测数据均在文中标注来源；凡是与建议不一致的地方，以实测与条款原文为准。

> **2026-11-04 决策**：`narrator_self` 是唯一 `APPROVED` 生产音色；`sft_male_01`/`sft_female_01` 正式生产停用；AISHELL-3 两条候选 `REJECTED`；LibriVox 一条 `PENDING_REVIEW`；外部 `APPROVED` = 0。正式发布前必须在 `assets/audio/manifest.json` 登记至少 1 首 CC0/公有领域 BGM（含完整 SHA-256 与来源），未登记音频不得混入成片。

## 0. 结论与排序

四个阻塞项里，**只有一个是真法律问题（S4 声音人格权），另外三个都是工程问题**。先做能把"等素材"变成"不等"的部分：

| 项 | 真正的阻塞 | 今天能做什么（零成本、零风险） |
|---|---|---|
| S2 环境音 | 没有素材文件 | **程序化拟音**：`anoisesrc` + 滤波 + 调制，本机已可用，零素材依赖 |
| S3 垫乐 | 授权 | CC0 曲库（FreePD / Musopen）+ 许可登记；**不碰平台条款受限的曲库** |
| S4 参考音频 | 声音人格权 | **先不克隆**；先用已进过成片的 SFT 音色；真要克隆先做录音诊断 |
| 全部 | 素材与代码强耦合 | 资产清单 + 许可门禁 + mock/生成资产垫底 |

一句话：**S2 今天就能通；S3 是选源问题；S4 不该用"技术手段绕法律"，而该先判断"要不要克隆"。**

## 1. 本机现状（实测）

| 项 | 结果 | 来源 |
|---|---|---|
| FFmpeg 噪声/拟音滤镜 | `anoisesrc`、`highpass`、`lowpass`、`tremolo`、`vibrato` 均可用 | `ffmpeg -filters` |
| 程序化风声可用性 | 粉噪 10 s → 120 Hz HP + 1.6 kHz LP + 0.12 Hz 颤动 → `-49.71 LUFS / TP -35.28`，非静音 | `experiments/audio_probe/wind_probe.wav` |
| 外网可达性 | `freepd.com` 200、`freesound.org` 200、`sonniss.com` **403** | `curl.exe` 实测 |
| 现有音频资产 | 合成 IR + 13 条 BGM（Keynata 7 条中 5 条 REJECTED；Commons 6 条 PD/CC BY）+ 4 条自生成 SFX（wind/water/chime/whoosh） | `ls assets/audio`；`manifest.json` |
| 已在册的候选源 | `BGM-PIXABAY`、`BGM-MIXKIT`、`SFX-FREESOUND`（均 `NOT_RUN`） | `ASSET_AND_LICENSE_REGISTRY.md` §5 |
| 已进成片的音色 | CosyVoice-300M-SFT「中文男」（R3-B，`PASS_VERIFIED`）；正式生产当前只用 `narrator_self` | 同上 §4 |

注意：`sonniss.com` 返回 403，说明**就算决定用 Sonniss，也要先解决获取路径**（官网/镜像/离线包），不能假设"下就能下"。

## 2. S2 环境音：程序化优先

### 2.1 为什么程序化是对的

环境音的诉求是"有空气、有距离、不抢字"，不是"这是一段真实录音"。程序化生成满足三个硬条件：

- **零素材依赖**：管线今天就能跑通，不等下载、不等授权；
- **零版权**：不存在第三方权利；
- **可复现**：种子固定，哈希稳定，和项目其它资产一个待遇。

### 2.2 实现形态（建议）

`scripts/make_ambience.py`，输出到 `assets/audio/ambience/`，每种一条 30–60 s 无缝循环：

| 预设 | 合成方式 | 用途 |
|---|---|---|
| `river_calm` | 粉噪 → 180–900 Hz 带通 → 0.08 Hz 缓慢起伏 | 江面静水 |
| `wind_soft` | 粉噪 → 120–1600 Hz → 0.12 Hz 颤动 + 轻微立体声失相干 | 夜风 |
| `room_tone` | 棕噪 → 80–400 Hz → 极低电平 | 室内底噪，垫在混响前 |

关键工程点（否则听感会"电子"）：
- **必须做频带限制与缓慢调制**，裸露的 `anoisesrc` 是白噪嘶声，一听就假；
- **循环点必须做交叉淡化**（首尾 2 s 交叉），否则每 30 s 一个"咔"；
- 输出电平固定（例如 -30 LUFS），由声景层的 `gain_db` 统一衰减，不在生成端猜。

### 2.3 CC0 备选（当程序化不够用时）

- **Freesound（严格筛 CC0）**：可达（200）。只能补细节拟音，逐条登记作者与页面；
- **Sonniss GDC**：条款允许在商业作品中使用、无需署名，但**不允许再分发素材本身或用于训练** —— 本项目的用法（成片音轨）在允许范围内；但当前 403，获取路径待解决。

## 3. S3 垫乐：选源 + 平台条款

### 3.1 推荐的源（按风险从低到高）

| 源 | 协议 | 能否商用 | 备注 |
|---|---|---|---|
| **FreePD** | 全站 CC0 | ✅ | 可达（200）；无署名要求，最省事 |
| **Musopen** | PD / CC0 | ✅ | 古典/器乐；注意"录音版权"与"乐谱版权"是两件事，选录音已进入 PD 的条目 |
| Pixabay Music | Pixabay Content License | ✅（有条件） | 已在册；**注意 Content ID 误伤**，发布前要实测 |
| Mixkit | Mixkit License | ✅（有场景限制） | 已在册；条款限制"不得单独再分发" |
| ~~YouTube Audio Library~~ | — | ❌ | 见 §5.2：条款是为 YouTube 上传准备的 |

### 3.2 硬约束

- 每首曲子**必须**同时具备：来源页面 URL、协议名称、协议快照（PDF 或本地 TXT）、sha256；
- **商用允许与否逐曲核验**，不按站点默认；
- 首播平台（抖音/小红书）与曲库条款要交叉核对，YouTube 系曲库不覆盖这两个平台。

## 4. S4 参考音频：先诊断，再决策

### 4.1 "自己录得不好"要先变成数字

在买素材或换模型之前，先把"不好"拆开——它可能根本不是音色问题：

| 症状 | 可能的真实原因 | 能否自己修 |
|---|---|---|
| 发闷、像隔层布 | 混响尾巴长（房间反射） | 换房间/挂毯/衣柜，可修 |
| 有嘶声、齿音重 | 麦克风近场 + 无防喷罩 | 换距离/加防喷罩，可修 |
| 忽大忽小 | 朗读电平不稳 | 重录，可修 |
| 底噪高 | 环境噪声/增益过高 | 关空调/换时段，可修 |
| 音色不理想 | 声线本身 | **不可修**，只能换人、买声库或不克隆 |

建议新增 `scripts/voice_prompt_check.py`，对参考音频输出可判定的指标：

```
时长 / 采样率 / 位深
峰值与削波计数
静音段 RMS（底噪）
SNR（语音段 RMS − 静音段 RMS）
混响尾巴（尾部 300 ms 的能量衰减斜率）
分段 LUFS 标准差（电平稳定性）
```

判据示例：时长 5–12 s、无削波、SNR ≥ 30 dB、尾部衰减 ≥ 15 dB/300 ms、分段 LUFS 标准差 ≤ 2 dB。
不达标 → **先重录/换环境**；全达标仍不好听 → 是音色或模型的问题，换素材才有意义。

### 4.2 决策阶梯（成本从低到高）

| 级 | 方案 | 法律风险 | 成本 | 建议 |
|---|---|---|---|---|
| A | **不克隆**，用已验证的 SFT「中文男」/「中文女」 | 零（音色条款仍需核验，但已试听进片） | 0 | **先回到这一级**：zero-shot 未必值得 |
| B | 自录 + 按 §4.1 修录音条件 | 零（自持人格权） | 低 | 录音诊断通过后再评估 |
| C | 付费配音员 + 《声音权授权书》（不可撤销、全球、含 AI 克隆与推理） | 低 | 中 | 需要更高质量音色时选这条 |
| D | 商业声音库/数字人授权（ElevenLabs、PlayHT 等） | 低（但受服务条款） | 高 | 引入外部服务与订阅，另算 |
| E | 公共数据集切片（LibriTTS 等） | **高** | 低 | **不推荐**，见 §5.1 |

同时要承认一个技术事实：**CosyVoice-300M-SFT 的 zero-shot 相似度本来就弱**（[AUDIO_SOUNDSCAPE_PLAN.md](AUDIO_SOUNDSCAPE_PLAN.md) §5.3 已记录）。所以"录得不好"里，至少有一部分是模型能力，不是录音质量。**在换素材之前，先用同一段 prompt 分别在 SFT 与 CosyVoice2-0.5B 上各跑一次**，才能分清是"录得差"还是"模型差"；后者换什么素材都救不回来。

## 5. 对参考建议的逐条更正

### 5.1 LibriTTS / LibriVox 切片不是安全区

- LibriTTS 的发布许可是 **CC BY 4.0**，不是公有领域；引用时必须署名，且"数据集许可"约束的是**数据集**；
- LibriVox 的录音由**真实志愿者**朗读，每一位都有自己的人格权。数据集许可**不能**代替朗读者的声音授权；
- 用这类切片做零样本克隆，风险与"扒网上的播音员"同类，只是更难追。

结论：**不作为 S4 方案**。

### 5.2 YouTube Audio Library 只能用于 YouTube

它的条款是为 YouTube 上传准备的曲库；把同一首曲子用在小红书/抖音成片，不在授权范围内。本项目首播平台不是 YouTube，因此**不采用**。

### 5.3 Sonniss GDC 音效：可用于成片，不可再分发

其许可覆盖"在商业作品中使用"，但**不覆盖**把素材本身再分发、或用于训练模型。用于 S2 环境音属于允许范围；当前站点 403，获取路径需先解决。

### 5.4 "声音混合阻断溯源"不是法律屏障

把两个合法音色混合成一个"现实中不存在的声音"，作为**创作选择**没问题；但把它当作**规避人格权追溯的手段**，在多数法域不成立，且一旦被认定为规避意图，反而加重风险。本项目不采用这条作为合规依据。

### 5.5 关于 `mock_mode` 的一处修正

建议里把 mock 写在 `config/audio.yaml` 的 `assets.mock_mode`。本项目的原则是**配置字段必须有真实消费者**（`config/styles.yaml` 的 parallax 就是反例，刚从"死配置"改成有执行者）。所以 mock 不做开关，而是**目录约定**：

- `assets/audio/manifest.json` 里每条资产标注 `usage: "mock" | "production"`；
- 渲染前检查：`usage: mock` 的资产**只能**出现在 `experiments/` 的输出里，出现在正式成片即报错。

不需要新配置项，也就不会多一个没人读的开关。

## 6. 许可门禁（可直接实现）

### 6.1 资产清单

`assets/audio/manifest.json`，每条：

```json
{
  "id": "ambience_river_calm",
  "path": "assets/audio/ambience/river_calm.wav",
  "kind": "ambience",
  "usage": "production",
  "source": "programmatic:scripts/make_ambience.py",
  "source_url": null,
  "license_type": "none (self-generated)",
  "commercial_allowed": true,
  "attribution_required": false,
  "license_doc": null,
  "sha256": "…",
  "added_on": "2026-11-04"
}
```

### 6.2 门禁规则

`scripts/audio_assets_check.py`（或并入现有预检）：

| 编号 | 规则 | 拒绝条件 |
|---|---|---|
| L1 | 被引用的每个音频文件必须在 manifest 里 | 缺条目 |
| L2 | `commercial_allowed` 必须为 true | 非商用素材进入正式成片 |
| L3 | `sha256` 必须与文件一致 | 素材被替换未重新登记 |
| L4 | 非自生成素材必须有 `license_doc` | 只有 URL 没有协议快照 |
| L5 | `usage: mock` 不得出现在 `projects/` 或 `experiments/r3*` 之外的正式产物 | mock 混入成片 |
| L6 | `kind: prompt` 必须附 `voice_rights: "self" | "licensed"` | 克隆参考音频没有权利声明 |

门禁只在**正式构建路径**执行（`r3_build` / 工作台 `build.rebuild`），实验脚本不拦——否则会挡住实验。

## 7. 可以立刻做的三件事（零成本、零法律风险）

1. **`scripts/make_ambience.py`**：三种程序化环境音 + 循环交叉淡化 + 固定电平；S2 立刻可用；
2. **`scripts/voice_prompt_check.py`**：把"录得不好"量化为 SNR / 混响尾巴 / 电平稳定性，先决定要不要重录；
3. **`assets/audio/manifest.json` + `scripts/audio_assets_check.py`**：为 S3 引入 CC0 曲目时立刻有门禁可依。

三件事都不依赖下载、不依赖授权，做完之后管线对"素材"的依赖从"硬编码路径"变成"清单 + 门禁"。

## 8. 仍然需要人拍板的三件事

| 事项 | 选项 | 影响 |
|---|---|---|
| 是否还要 zero-shot 克隆 | 回到 A 级（不克隆）/ 继续 B–D | 决定是否需要采购配音或声库 |
| S3 选哪一首 | FreePD / Musopen / Pixabay | 逐曲条款核验后才能进成片 |
| S2 用程序化还是 CC0 实录 | 程序化 / Freesound CC0 | 程序化无风险但偏"合成感"；实录更真但要逐条登记 |

这三件都不阻塞工程：清单与门禁先立起来，素材随时替换，管线不动。

## 9. 实测：已有的自录 prompt（2026-11-04）

文件：`D:\AI\CosyVoice-Runtime/assets\my_voice_5s.wav`（**原文件未改动**，复制到
`assets/audio/prompts/source/my_voice_5s_src.wav` 后处理）。命名写的是 5s，实际 **3.35 s**。

### 9.1 诊断（`scripts/voice_prompt_check.py check`）

| 项 | 值 | 判断 |
|---|---|---|
| 格式 | 24 kHz / 单声道 / 16 bit | 够用（模型内部按 16 k 与 24 k 各取一次） |
| 峰值 | -4.32 dBFS，削波 0 点 | 无爆音 |
| 底噪（句间） | -54.0 dBFS | 这就是你听到的"杂音" |
| SNR | 38.8 dB | 可用，但不算干净 |
| 混响尾 | -11.5 dB / 300 ms | 干声，房间没问题 |
| F0 中位数 | 125.7 Hz | 男声，约 B2 |
| 6–11 kHz 相对主体 | -28.7 dB | 高频成分不高，嘶声主要在 8 k 以下 |
| 时长 | **3.35 s** | 低于建议的 5 s |

### 9.2 模型的取用方式（决定了怎么处理划算）

读 `CosyVoice-Runtime/app/cosyvoice/cli/frontend.py` 实测：

- `_extract_speech_token` → `load_wav(prompt_wav, **16000**)`（Whisper mel 128）
- `_extract_spk_embedding` → `load_wav(prompt_wav, **16000**)`（campplus，16 kHz）
- `_extract_speech_feat` → `load_wav(prompt_wav, **24000**)`

**结论：8 kHz 以上的内容进不了 token 与说话人嵌入**，因此对 prompt 做 8 kHz 低通是**零信息损失**的清理，专治嘶声。

### 9.3 处理链与效果

`highpass 70` → `anlmdn` → 定点去齿音（6.2 k / 7.8 k）→ `lowpass 8000` → `loudnorm -23`

| 指标 | 处理前 | 处理后 |
|---|---|---|
| 底噪 | -54.0 dBFS | **-84.7 dBFS** |
| SNR | 38.8 dB | **66.3 dB** |
| 峰值 | -4.32 dBFS | -7.73 dBFS（-23 LUFS） |
| F0 | 125.7 Hz | 127.0 Hz（未被改变） |
| 时长 | 3.35 s | 3.37 s |

降噪器对比（同一素材）：`afftdn` 39.8 dB / `anlmdn` **66.4 dB** / 两者串联 80.0 dB。
串联多出的 14 dB 大概率是二次平滑，有削薄音色风险，**默认只用 anlmdn**。

**过程中修正的一个错误**：第一版链里用了
`silenceremove=stop_periods=1:stop_duration=0.25`，它在第一个停顿处就把 3.35 s 截成 1.31 s。
prompt 的内部停顿是表演的一部分，**不能删**；只允许修首尾。

### 9.4 仍然存在的问题

1. **时长 3.35 s**：这是唯一剩下的硬问题。克隆相似度与 prompt 时长正相关，建议在**同一套录音条件**下补录到 8–10 s（这份素材本身条件不错：无削波、干声、电平稳定，值得沿用同一环境）；
2. **"声调"**：清理不会也不应该改变音高（F0 仍 125.7 Hz）。若想要不同的声调，只有三条路：
   - 生成端控制：`classical_recitation` 的语速与停顿（已实现）；
   - 换了声线的 prompt：`rubberband` 可做**保共振峰**的移调，但移了 prompt 就等于移了克隆出来的音色，会降低与原人的相似度；
   - 重新录一遍，用不同的发声方式。

   我**没有**默认做移调——那属于听感决策，需要先听一版才知道要不要。

### 9.5 资产登记

`assets/audio/manifest.json` 已登记三条（合成 IR、原始 prompt、清理后 prompt），
并附 `assets/audio/prompts/VOICE_RIGHTS.md`（自持声音权，`voice_rights: self`）。

## 10. 零样本克隆实测与本声线定版（2026-11-04）

### 10.1 链路已跑通

`src/drama_studio/voice/zeroshot.py` → `POST /tts/upload`（运行时没有
`/inference_zero_shot`）。参考音的文本在运行时目录已有 sidecar：`my_voice_5s.txt`
= 「希望你以后能够做的比我还好呦。」，与实际录音逐字一致。

实测（同一句「春江潮水连海平，海上明月共潮生。」，speed 0.82）：

| 样本 | 时长 | F0 | 峰值 | 语音电平 | 波峰因数 |
|---|---|---|---|---|---|
| 参考 prompt（清理版） | 3.37 s | 127.0 Hz | -7.7 | -18.4 | 10.6 |
| 零样本克隆（干声） | 4.74 s | 109.6 Hz | -8.7 | -23.5 | 14.9 |
| SFT 预置「中文男」 | 5.70 s | **76.2 Hz** | -12.3 | -27.1 | 14.8 |
| 克隆 + 播音级后处理 | 4.76 s | 112.7 Hz | -1.5 | -11.0 | **9.5** |

- 推理耗时 25.4 s 生成 4.74 s（RTF 5.36，纯 CPU）；
- 克隆的 F0 落在参考（127）与预置（76）之间、且明显偏向参考，说明音色确实跟了参考；
- 波峰因数 14.9 → 9.5 是压缩带来的"更平、更稳"，这是播音腔的**电平特征**，不是发声方式。

### 10.2 关于「播音腔」能做到什么程度

零样本克隆学的是**参考音的说话方式**，不只是音色。参考里那句是随口的一句话，
所以克隆出来也是随口朗读——**不是播音腔**。三条路：

| 路径 | 能得到什么 | 得不到什么 | 代价 |
|---|---|---|---|
| A. 用 SFT 预置「中文男」 | 真正的播音腔音色与播报节奏 | **不是你的声音** | 零成本，已可用 |
| B. 你的克隆 + 播音级后处理 | 你的音色 + 播音的电平与频谱（更稳、更亮、更近） | 播音腔的**发声方式**（气息、共鸣、字头处理） | 已跑通，可配置化 |
| C. 用播音腔的 prompt 克隆 | 你的音色 + 播音腔的发声方式 | 需要你真的用播音腔录一段 | 一段 8–10 s 的 `promo` 录音 |

结论：**B 现在就能用，C 才叫"用你的声音播音腔"，而 C 的前提是录一段播音腔的参考。**
本轮没有做 C，也没有替你做 A/B 的选择——三个样本在 `experiments/audio_probe/`，
听过再定。

### 10.3 产物

| 文件 | 内容 |
|---|---|
| `experiments/audio_probe/clone_poem_v1.wav` | 你的音色，随口朗读，poetry 0.82 |
| `experiments/audio_probe/sft_poem.wav` | 预置「中文男」，播音腔 |
| `experiments/audio_probe/clone_poem_broadcast.wav` | 你的音色 + 播音级后处理 |
| `experiments/audio_probe/zeroshot.json` | 克隆 provenance（prompt 哈希、文本、RTF） |

播音级后处理链（本轮为探针，未进配置）：
`highpass 80` → 200/3000/5500 Hz 提亮 → 7500 Hz 去齿 → `acompressor 3:1` →
`alimiter` → `loudnorm -16 / TP -1.5 / LRA 7`。

CosyVoice 服务由本轮启动，已停止（50000 已释放）。

## 11. 前后鼻音（-n / -ng）：定位到模型，不是 prompt（2026-11-04）

### 11.1 现象与第一轮排除

同一句「春江潮水连海平，海上明月共潮生。」用 Whisper small 转写：

| 声线 | 转写 | 判断 |
|---|---|---|
| 300M + 你的 prompt（清理版） | 群江朝嘴连海平,海上明月共朝**森** | 生 shēng → 森 sēn，丢 -ng |
| 300M + 你的 prompt（原始） | 同上 | 与清理无关 |
| 300M + 预置「中文男」 | 沉江,朝雪,涅海平,海上明月,**公朝深** | 生 → 深，同样丢 -ng |

**两种声线都丢**，所以不是你的 prompt，也不是我的降噪/低通。

### 11.2 一个差点误导结论的测试设计

第一版最小对立用了单字（生/森、平/贫、明/民）。结果 ASR 把「森」写成「生」、「贫」写成「平」——
这是 Whisper 的**同音字归一化**，测的是它的先验，不是模型的发音。改用双字词
（生活/森林、平安/贫穷、明天/民族）后，词义锁住韵尾，三个声线 **6/6 全对**。

结论：模型在孤立词上分得清 -n/-ng，问题只出现在**连读的诗句**里。

### 11.3 换成 CosyVoice2-0.5B 后

| 项 | 300M-SFT | **CosyVoice2-0.5B** |
|---|---|---|
| 同一句转写 | 群江朝嘴连海平,海上明月共朝森 | **春江潮水连海平,海上明月,共潮生。** |
| 前后鼻音 | 错 | **对** |
| 克隆 F0 | 109.6 Hz（参考 127.0） | **125.0 Hz（更接近参考）** |
| 同句时长（speed 0.82） | 4.74 s | 7.16 s（明显更慢） |
| RTF（CPU） | 5.36 | 3.54 |
| SFT 预置音色 | 有（中文男/女…） | **无**（`sft_available: false`） |

**这是模型能力差异，不是参数问题。** 0.5B 既修好了前后鼻音，也把音色相似度拉回来了。

### 11.4 取舍

- `start_cosyvoice.bat`（0.5B）与 `start_cosyvoice_sft.bat`（300M）**互斥占用 50000**；
- 0.5B 没有预置音色，R3-B 基线用的「中文男」只在 300M 上；
- 因此：诗词旁白走 **0.5B 零样本 + 你的 prompt**；如果需要预置音色，才切回 300M。

试听：`experiments/audio_probe/listen/05_克隆_你的声音_CosyVoice2-0.5B.wav`（-17.07 LUFS / -1.50 dBTP）。

复现：`scripts/ng_probe.py`（双字词最小对立 + ASR 比对）。

### 11.5 为什么 300M-SFT 比 0.5B 差这么多：可核对的证据

两个模型目录里的配置与权重清单（本机读取，非推测）：

| 项 | CosyVoice-300M-SFT | CosyVoice2-0.5B |
|---|---|---|
| 采样率 | 22 050 Hz | **24 000 Hz** |
| LLM 主干 | `cosyvoice.llm.llm.TransformerLM`（自研） | **`Qwen2LM`**（Qwen2 骨架） |
| 隐层维度 | 1024 | 896 |
| 语音 tokenizer | `speech_tokenizer_v1.onnx` | **`speech_tokenizer_v2.onnx`** |
| 预置说话人 | `spk2info.pt`（SFT 训练目标） | 无该文件 |
| 生成帧率 | — | 25 fps，`token_mel_ratio: 2` |

由此可以解释三处实测差异：

1. **音色跟不住**：300M 克隆的 F0 是 109.6 Hz，参考是 127.0（偏 -2.4 个半音）；0.5B 是 125.0–128.3（偏 ~1 Hz）。
   300M-SFT 的训练目标是"在给定 speaker embedding 下说好预置音色"，**它的 zero-shot 只是同一套权重的旁路**，不是优化目标。
2. **咬字丢韵尾**：v1 tokenizer 的时长建模较粗，`-ng` 这种短而弱的韵尾最容易先丢；v2 tokenizer 把码本与时长都换了一代。
3. **节奏不同**：同一句同一 speed，300M 出 4.74 s，0.5B 出 7.16 s——两代模型的时长分布本来就不一样，0.5B 更慢、更接近吟诵。

注意：以上是"配置差异 + 实测行为"的对应关系；我没有读论文原文，不把因果说成定论。

### 11.6 0.5B 的两个播音级后处理版本

| 版本 | 动态范围（p90-p10） | 中位电平 | 说明 |
|---|---|---|---|
| 05 原样 | 43.8 dB | -22.6 | 未处理 |
| **06 轻** | 39.9 dB | -19.5 | 提亮 + 3:1 轻压缩，保留自然起伏 |
| **07 强** | 33.2 dB | -17.5 | 4:1 压缩、更强提亮，接近播报的"贴耳、平稳" |

压缩的作用可量化：安静段的电平被抬起来（-22.6 → -17.5），峰值不动，所以"更稳"，而不是"更响"。
`crest`（峰值−语音均值）在三版里都接近，是因为 `loudnorm` 已把峰值钉在 -1.5 dBTP——衡量压缩要看**分位差**，不是 crest。

## 12. 定版：0.5B 默认 + 06 播音级（2026-11-04）

### 12.1 选择

- **模型**：CosyVoice2-0.5B（`start_cosyvoice.bat`）；
- **音色**：自录 prompt 的清理版（`assets/audio/prompts/my_voice_clean_v1.wav`）；
- **风格**：`broadcast_light`（试听编号 06）；
- **speed**：0.90（0.5B 偏慢，0.82 会把一句拉到 7.2 s）。

### 12.2 落地方式：**不修改 `D:\AI\CosyVoice-Runtime`**

项目的不变量要求该目录只读，因此所有选择都写在项目侧：

| 文件 | 作用 |
|---|---|
| `scripts/cosyvoice_server.ps1` | `-Action start/stop/status -Model cosyvoice2/sft`；单端口 50000、谁启动谁停止 |
| `config/audio.yaml` `tts.mode: zero_shot` + `tts.zero_shot` | 参考音、逐字文本、speed、期望的运行时 |
| `config/settings.yaml` `tts.mode: zero_shot` | 与上者保持一致，避免两个文件互相矛盾 |
| `config/audio.yaml` `soundscape.voice_style: broadcast_light` | 播音级 EQ + 压缩 |
| `src/drama_studio/voice/tts.py` | `zero_shot` 分支走 `/tts/upload`；`speaker_mode` 可显式覆盖 |

两个运行时互斥占用 50000，切换就是换一个 `-Model` 参数，**不改别人的文件**。

### 12.3 端到端实测

`.venv\Scripts\python.exe` 调 `tts.synthesize_narration`（两行《春江花月夜》）：

```
speaker zero_shot:my_voice_clean_v1 | speed 0.9 | mode classical_recitation
line 1 6.74s (合成 22.2s)   line 2 5.14s (合成 39.8s)   total 11.88s
```

manifest 里说话人记为 `zero_shot:<prompt 名>`，speed 取自配置，模式仍是朗读模式（二者独立）。

### 12.4 「之前一直声音不合适，是 300M 的锅吗」

**主要是。** 证据是同一句、同一 prompt、只换模型：

| | 300M-SFT | 0.5B |
|---|---|---|
| 前后鼻音 | 生 → 森/深（丢 -ng） | 正确 |
| 克隆 F0 vs 参考 127.0 | 109.6（偏 -2.4 半音） | 125.0–128.3（偏约 1 Hz） |
| 结构 | 自研 TransformerLM + tokenizer v1 | Qwen2LM + tokenizer v2 + 24 kHz |

但**不全是**：prompt 只有 3.35 s、且是随口一句，这两点限制了相似度上限与说话方式——换成 0.5B 后仍然成立。所以：
- 音色与咬字的锅，300M 占大头；
- 说话方式（随口 vs 播音腔）的锅，在 prompt，不在模型。

## 13. 音频为主时钟与标题段（2026-11-04）

### 13.1 「音频驱动」不是要新建的架构，而是既有契约

核实结果：项目**已经是** audio-first。

| 环节 | 实现 | 位置 |
|---|---|---|
| 镜头时长 | `_aligned_duration` 从 `audio_manifest` 的逐句时长 + 停顿 + 前导推出 | `production.py:231` |
| 时间轴 | `build_timeline(segments, leading_ms)`，逐段累计 | `voice/timeline.py:31` |
| 字幕 | SRT 由同一份 timeline 生成，毫秒级 | `voice/timeline.py:98` |
| 成片混音 | 每句按 timeline 的 `speech_start_ms` 做 `adelay` | `scripts/r3_build.py` |

所以不存在"预设镜头时长再削音频"的代码路径。**要补的是标题段，不是重写时钟。**

### 13.2 新增：标题段（header）与时间戳账本（ledger）

`narration.json` 现在支持：

```json
{
  "mode": "classical_recitation",
  "header": {"text": "登鹳雀楼。唐，王之涣。", "pause_ms": 1100},
  "lines": ["白日依山尽，黄河入海流。", "欲穷千里目，更上一层楼。"]
}
```

- 标题在正文之前单独合成（`header.wav`），**正文的行号不变**（line_001 仍是 line_001），镜头↔诗句的绑定不受影响；
- `audio_manifest.json` 新增 `header` 与 `ledger`：
  `[{header 0.00→3.20}, {line1 4.30→7.98}, {line2 8.98→12.44}]`；
- `r3_build` 把标题并进**前导静音**：`leading_ms += header.duration + pause_ms`，并把 header 音频放在原前导处 → 标题出现在片头，正文按时开始；
- `build_motion_plan` 同样把这段时长加到**第一个镜头的时长**上 →「标题段对应片头画面」自动成立。

实测（0.5B + 你的音色，speed 0.90）：

```
header   0.00 ->  3.20   (3.20s + 1100ms 停顿)
line1    4.30 ->  7.98
line2    8.98 -> 12.44
```

### 13.3 两个决定

| 项 | 决定 | 依据 |
|---|---|---|
| speed | **0.90 不动** | 音频驱动画面，不存在"装不下"；0.90 的从容骨架是吟诵需要的 |
| `soundscape.enabled` | **已开启** | 06 实测解决电平波动；`r3_build` 已具备响度单点接管 |

开启后的实测（两行拼接 + 1100 ms 停顿，48 kHz）：`-22.07 LUFS → -15.53 LUFS`，TP `-1.50 dBTP`。
与目标 -16 差 0.47 dB，在 ±0.5 容差内。

## 14. BGM 情绪选曲（2026-11-05）

用户反馈：频段指标干净的弦乐/钢琴仍然"阴间、压抑"。根因不是 EQ，而是**调式与织体**：

| 曲目 | Keynata track | 调式 | 处理 |
|---|---|---|---|
| `bgm_ink_strings_duo` | `classical_duo_24036` | **E 小调** | `REJECTED` |
| `bgm_shinkai_piano` | `classical_piano_6134` | **B 小调** | `REJECTED` |

替换规则：只选 `mode = major` 且和声/节奏完整的曲目；Keynata 索引直接给出 `mode`、`tonic`、`bpm`，再用 MIDI 音符直方图 + Krumhansl 调性模板复核，不靠频谱猜情绪。

| 新资产 | track | 音符直方图结论 | 频谱质心 |
|---|---|---|---|
| `bgm_warm_pop_canon` | `jpop_3piece_11623` | C major，r=0.946（次选 G major 0.889） | 4268 Hz |
| `bgm_warm_strings_c` | `classical_quartet_25041` | C major，r=0.910 | 2395 Hz |
| `bgm_warm_piano_c` | `classical_piano_4016` | G/C major，r=0.856/0.853 | 1268 Hz |

落地方式：`r3_build.py --bgm-id <asset_id>` 覆盖时间线 BGM 轨，实际时间线写入输出目录 `audio_timeline_effective.json`。只做 30 Hz 高通与峰值限制，不再用 EQ 修情绪。Shinkai 场景时间线同时移除了每 8–30 s 的钟磬事件，只保留转场 whoosh。

> 后续：这三条曲目试听后仍被用户判定"过于阴间，全部 pass"，已标 `REJECTED`。最终候选见 §15（Wikimedia Commons 公有领域/CC BY 真录音）。

## 15. 古典/民谣真录音（Wikimedia Commons，2026-11-05）

用户否定了 Keynata 的三条大调曲目（"过于阴间，全部 pass"），并要求直接对标经典动画原声。**商业影片原声不能扒**：那是受版权保护的录音与作品，切成 BGM 再标成自有/`APPROVED` 属于侵权，项目不做。替代方案是选用**公有领域或 CC BY 的真实录音**，同样经过历史检验、调性明亮。

| 资产 | 作品 | 许可 | 调性（音频直方图） | 用途 |
|---|---|---|---|---|
| `bgm_mozart_k330_piano` | Mozart K.330 第三乐章（Vadim Chaimovich / Musopen） | Public domain | G major r=0.794 | 新海诚 · 明亮钢琴 |
| `bgm_green_leaves_guitar` | GREEN LEAVES（Jason Shaw） | CC BY 3.0 US | D major r=0.777 | 吉卜力 · 木吉他 |
| `bgm_grieg_morning` | Grieg《晨曲》（Musopen Symphony） | Public domain | B major r=0.834 | 日出/云海 |
| `bgm_mozart_k525_strings` | Mozart K.525 第一乐章 | Public domain | D major r=0.788 | 工笔 · 弦乐 |
| `bgm_schubert_d664_piano` | Schubert D.664 第一乐章（Paul Pitman） | Public domain | E major r=0.790 | 水墨 · 钢琴 |
| `bgm_serenity_guitar` | SERENITY（Jason Shaw） | CC BY 3.0 US | A major r=0.755 | 吉卜力 · 备用 |

- CC BY 曲目**必须随片署名**：`GREEN LEAVES by Jason Shaw (audionautix.com), CC BY 3.0 US`；`SERENITY by Jason Shaw (audionautix.com), CC BY 3.0 US`。
- 处理：`highpass=f=30,alimiter=limit=0.95` → 48 kHz mono；不做 EQ/降噪。
- 证据与来源清单：`assets/audio/bgm/commons/LICENSE.md`。
- 拒绝项：任何电影/动画原声切片（《山水情》《秒速5厘米》《龙猫》《千里江山图》展演录音等）。未获书面授权不得登记为项目资产。
- 2026-11-05 用户试听反馈："好很多"。6 条 commons 曲目 `review_status=ACCEPTED_PENDING_FINAL`；最终采用哪一条随 2 分钟验收片确定。
