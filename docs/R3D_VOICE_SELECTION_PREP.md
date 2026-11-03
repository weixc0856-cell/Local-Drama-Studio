# S3-A 女声音色选型准备与试听对比方案

> 状态：`DECISION` / `NOT_RUN`（仅准备，尚未试听、未开户、未购买、未合成）
> 核验日期：2026-11-03
> 基线：HEAD `ad921ed`（v1.0 文档已提交）；工作区 clean；R3-D 未执行。
> 原则：官方来源优先；不把代码/模型许可、具体音色使用权、生成音频商用权混为一谈；不预设任何候选可商用。

## 1. 环境与现有能力核实

| 项 | 实测结果 |
|---|---|
| Git | HEAD `ad921ed`；开始复核时工作区 clean |
| CosyVoice 运行时 | `D:\AI\CosyVoice-Runtime`，独立 Python 3.10 venv |
| SFT 模型 | `pretrained_models\CosyVoice-300M-SFT` 存在 |
| 预置音色 | `spk2info.pt` 实际键：中文女、中文男、日语男、粤语女、英文女、英文男、韩语女 |
| CosyVoice 本地接口 | `speaker`、`speed`、`text_frontend`；**没有 emotion 参数** |
| 现男声基线 | `experiments/r3b/audio_manifest.json`：7 句、29.99 s，仅中文男 |
| 中文女 | 本地存在，但**未试听、未合成、未验收** |
| 云 API Key | 环境变量中未发现 DASHSCOPE / Volcengine / ElevenLabs Key |
| ComfyUI / 生成任务 | 未启动；本阶段不运行 |

**结论：本地具备“中文女”候选的技术入口，但没有试听证据；云服务均需开户/密钥/授权确认。**

## 2. 候选清单

| ID | 提供方 | 音色 | 模型 / voice_type | 官方来源 | 当前状态 |
|---|---|---|---|---|---|
| C1 | CosyVoice 本地 | 中文女 | CosyVoice-300M-SFT | 本机 `spk2info.pt`；[GitHub](https://github.com/FunAudioLLM/CosyVoice) | `NOT_RUN` |
| C2 | 阿里云 Qwen TTS | 温怀清 | `qwen-audio-3.1-tts-flash` / `wenhuaiqing_v3.1` | [音色列表](https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list) | `NOT_RUN` |
| C3 | 阿里云 Qwen TTS | 于小云 | `qwen-audio-3.1-tts-flash` / `yuxiaoyun_v3.1` | 同上 | `NOT_RUN` |
| C4 | 火山引擎 | 古风少御 | `BV115_streaming` | [音色列表](https://docs.volcengine.com/docs/DoubaoVoice/Tonelist?lang=zh) | `NOT_RUN` |
| C5 | 火山引擎 | 温柔淑女 | `BV104_streaming` | 同上 | `NOT_RUN` |
| C6 | 火山引擎 | 知性女声 | `BV009_streaming` | 同上 | `NOT_RUN` |
| C7 | ElevenLabs | 中文女性（待选） | Voice Library 选定后记录 | [Pricing](https://elevenlabs.io/pricing) / [TTS docs](https://elevenlabs.io/docs/capabilities/text-to-speech) | `NOT_RUN` |

### 名称更正

- 官方中文音色页写 **于小云**（`yuxiaoyun_v3.1`），不是“余小云”。
- **温怀清** 对应 `wenhuaiqing_v3.1`；`wenhuaizhi_v3.1` 对应 **闻怀之**，两者不是同一音色。
- 火山官方名称是 **知性女声**（`BV009_streaming`）；“知性女生”是常见误写。

## 3. 官方能力与授权核验

### 3.1 CosyVoice 本地中文女

- 本机 `spk2info.pt` 确有 `中文女`。
- 当前 SFT API 支持 `speaker`、`speed`、`text_frontend`；不支持独立 emotion 参数。
- CPU 推理；不占 GPU，不产生 API 费用。
- 代码仓库为 Apache-2.0；README 声明“仅供学术目的演示技术能力”，**没有**单独确认模型权重或预置音色的商用条款。
- **不能**因为代码 Apache-2.0 就推定「中文女」音色或生成音频可商用。

### 3.2 阿里云 Qwen TTS

官方音色页确认（2026-11-03）：

| 音色 | voice 参数 | 语言 | 页面描述 |
|---|---|---|---|
| 温怀清 | `wenhuaiqing_v3.1` | 中文普通话 | 清亮、柔和 |
| 于小云 | `yuxiaoyun_v3.1` | 中文普通话 | 自然、亲切 |
| 闻怀之 | `wenhuaizhi_v3.1` | 中文普通话 | 稳重、成熟（备选） |

- 这些精品中文音色列在 `qwen-audio-3.1-tts-flash` 之下；页面注明“以下音色仅支持中文普通话”“不能跨模型混用”。
- 支持 SSML、Instruction control、Timestamps；页面没有单列 emotion/pace 参数。
- 英文官方页注明精品中文音色**仅北京地域**；免费额度**仅新加坡地域**。这意味着：**免费额度不能用于北京专属的精品中文音色**，试听/使用需以北京地域的付费调用为准（或改用支持其他音色的模型）。
- 定价页（官方，2026-11-03）：
  - `qwen-audio-3.1-tts-flash`：新加坡输入 $0.23/百万 token、输出 $1.87/百万 token，免费 100 万 token；北京输入 $0.212/百万 token、输出 $1.696/百万 token，无免费额度。
  - `qwen-audio-3.1-tts-plus`：新加坡 $0.3/万字，免费 1 万字；北京 $0.2/万字，无免费额度。
  - 中文汉字按 2 字计费（按字符计费的模型）；试听文本约 96 字符，单样本成本预计 **<$0.01**，以实际账单为准。
- 服务条款：Model Studio 试用/模型测试输出**仅可用于评估，不得商用、不得向第三方提供**，且不可主张知识产权；AI 内容需标识。付费输出权利是**有条件的**，需按 Model Studio 服务条款/账号区域复核，不能视为已获商用许可。

### 3.3 火山引擎豆包语音

官方音色页确认（2026-11-03）：

| 音色 | voice_type | 情感/风格 | 免费音色列表 |
|---|---|---|---|
| 古风少御 | `BV115_streaming` | 8 种情感（旁白、平和、开心、悲伤、生气、害怕、厌恶、惊讶） | **在 21 款免费音色内**（有声阅读） |
| 温柔淑女 | `BV104_streaming` | 同上 8 种情感 | 不在免费列表 |
| 知性女声 | `BV009_streaming` | 5 种情感/风格（通用、愉悦、抱歉、专业、严肃） | 不在免费列表 |

- 支持中文及中英文混合；支持 SSML；情感通过 `emotion` 参数，语言通过 `language` 参数。
- 官方体验服务条款：试用生成内容**仅可体验，不可商用**；不可主张知识产权；须显著标识“AI生成”；不得去除平台标识。
- 正式商用需开通正式版 API，并确认具体音色授权/计费；**BV104/BV009 不在免费音色列表**，可能需要单独音色授权。
- 官方公开计费页（`docs.volcengine.com/docs/6561/79841`）在当前抓取中只返回导航壳，未能取得可引用的价目表；试听前需在控制台确认正式版价格、免费额度和音色授权费。二级资料中的“1.2 万元/音色/年”**不作为官方结论**。

### 3.4 ElevenLabs

官方 Pricing（2026-11-03）：

| 计划 | 月费 | 额度 | 商用 |
|---|---|---|---|
| Free | $0 | 10,000 credits | 页面未列 Commercial License |
| Starter | $6（首月 $1） | 30,000 credits | **Commercial License** |
| Creator | $22（首月 $11） | 121,000 credits | 含 Starter 商用 |
| Pro | $99 | 600,000 credits | 含 Creator |
| Scale/Business/Enterprise | $299 / $990 / 定制 | 更多 | 含前档 |

- TTS 文档确认支持 Chinese（`zh`）；具体中文女声质量未试听。
- 官方 capabilities 页提到 stability、similarity；speed/style 等参数需以当前 API 参考/控制台为准，不在准备阶段假定。
- 免费额度不支持商用；商用至少 Starter。Voice Library 对免费 API 用户不可用（官方 capabilities 页说明）。
- **不购买**；先用免费额度/试听流程，商用测试需人工批准 Starter。

## 4. 授权分层

| 层 | 需要确认 | 当前结论 |
|---|---|---|
| 代码许可证 | CosyVoice/Qwen/Volcengine/ElevenLabs 的代码/服务条款 | 部分已读；不构成音色商用许可 |
| 模型权重许可 | 本地模型/云端模型 | Qwen/Volcengine/ElevenLabs 以服务条款为准；CosyVoice 未确认权重条款 |
| 具体音色使用权 | 预置/云端音色是否允许商业发布 | 全部未确认 |
| 生成音频使用权 | 输出音频能否商用、是否需标识/署名 | Qwen/Volcengine 试用禁止商用；ElevenLabs 需 Starter+；CosyVoice 未确认 |
| 平台发布 | 抖音/小红书对 AI 音频/音乐/AI 标识要求 | 待平台规则复核 |

**任何候选在完成音色级授权核验前，都只能用于内部试听，不得进入可发布成片。**

## 5. 统一试听方案

### 5.1 文本与参数

- 文本：`experiments/r3d/voice/test_text.txt`，6 句《春江花月夜》，96 字符（84 汉字 + 标点）。
- 不使用 SSML，避免供应商能力差异影响可比性。
- 语速目标 1.0；CosyVoice 用 `speed=1.0`；云端用默认/1.0（若支持），第一轮不做逐家调参。
- 原始输出保留供应商原生格式，不覆盖。
- 比较副本统一转 48 kHz 单声道 PCM s16le WAV；仅对比较副本做 `loudnorm I=-16 TP=-1.5 LRA=11`，原始文件不动。
- 每候选先生成 1 条；进入决赛的候选重复 3 次做稳定性检查。

### 5.2 盲听与评分

- 盲听标签随机化；至少两轮；同一评审不先看供应商。
- 1-5 分：自然度、普通话咬字、停顿、情绪、古典诗词韵律、稳定性、授权清晰度、单位成本。
- 通过线（建议）：无系统性错读/漏字；停顿自然；不出现明显播音腔或过度甜腻；三次重复差异可接受；授权路径可落地。

### 5.3 预计成本（仅试听）

| 候选 | 当前试听成本 | 商用前置 |
|---|---|---|
| CosyVoice 中文女 | $0 API；CPU 约 2-4 分钟/条（按男声基线估算，未实测女声） | 音色/模型商用条款待确认 |
| Qwen 温怀清 / 于小云 | 北京地域付费；96 字符预计 <$0.01/条；免费额度不适用于北京精品中文音色 | 付费条款/账号区域复核 |
| Volcengine BV115 | 试用可试听；试用输出不可商用 | 正式版 + 音色授权 |
| Volcengine BV104/BV009 | 试用可试听；非免费音色 | 正式版 + 单独音色授权（价格待控制台） |
| ElevenLabs | 免费额度可试听；免费不可商用 | Starter $6/月（首月 $1） |

**本阶段未购买、未开户、未产生费用。**

## 6. 需要人工决策

1. 是否批准开通阿里云/火山引擎账号；选择北京还是新加坡区域。
   - 注意：Qwen 精品中文音色北京专属，而免费额度仅新加坡；二者不能同时满足。
2. 是否接受“试用输出仅内部评估、不可发布”。
3. 是否批准 Qwen 北京付费试听（预计 <$0.01/条）。
4. 是否批准火山正式版/音色授权预算；BV104/BV009 可能产生额外授权费。
5. 是否批准 ElevenLabs Starter（$6/月，首月 $1）做商用对照；或先只用免费试听。
6. 女声人设方向：成熟清透 vs 古风角色感 vs 知性旁白。
7. 是否把 CosyVoice 中文女纳入首轮（本地零成本，但商用条款不明）。
8. 是否加入“闻怀之”作为温怀清的备选。
9. 盲听评审人员与最终决定人。
10. 是否在试听后修改生产脚本/接口；本阶段不改。

## 7. 本阶段未做的事

- 未合成任何女声音频。
- 未启动 CosyVoice 服务。
- 未创建云账号、未购买套餐、未调用付费 API。
- 未修改 `scripts/`、`workflows/`、模型或男声基线。
- 未提交 Git。

## 8. 官方来源

- Qwen-Audio-TTS 音色列表（中文）：https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list
- Qwen 模型价格：https://www.alibabacloud.com/help/en/model-studio/model-pricing
- Model Studio 服务说明（试用限制）：https://help.aliyun.com/en/model-studio/bailian-service-notes
- 火山引擎音色列表：https://docs.volcengine.com/docs/DoubaoVoice/Tonelist?lang=zh
- 火山引擎体验服务条款：https://docs.volcengine.com/docs/DoubaoVoice/VolcanoEngine-SpeechModelExperienceServiceDisclaimerandServiceRulesDescription?lang=zh
- 火山引擎产品计费（公开页抓取不完整，需控制台）：https://docs.volcengine.com/docs/6561/79841
- ElevenLabs Pricing：https://elevenlabs.io/pricing
- ElevenLabs TTS capabilities：https://elevenlabs.io/docs/capabilities/text-to-speech
- CosyVoice GitHub：https://github.com/FunAudioLLM/CosyVoice

> 价格、免费额度、音色可用地域与服务条款会变化；实际试听/商用前以控制台和当期条款为准。
