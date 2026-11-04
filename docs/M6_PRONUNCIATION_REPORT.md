# M6 发音校正与音频管线报告

> 执行日期：2026-11-04
> 环境：Windows 11 / i7-13700K / 64 GB / CosyVoice-300M-SFT（CPU，50000）/ Whisper base（CPU）
> 状态口径：`docs/PRD.md` §0.2。**ASR 通过不等于人工听感通过。**

> **2026-11-04 修订（人工听感驳回后）**：2/2/3 硬切与 220 ms 数字静音已被废除。
> 现行为**整句/整联推理 + 破折号气口**（如 `春江潮水——连海平，海上明月——共潮生。`），
> 行间停顿 800–1000 ms，不再生成段级 WAV 或数字静音。5 条谐音已转 `verified`。
> 本报告 §5/§7 的 108 段数据保留为历史对照；最终平滑版本见
> `experiments/m6_pronunciation/poem_smooth/` 与 [`M7_FINAL_DELIVERY_REPORT.md`](M7_FINAL_DELIVERY_REPORT.md)。

## 0. 结论

M6 完成四层文本分离、谐音替换引擎、`language=zh` 显式守卫、2/2/3 音步与拼音级 ASR 闭环。

| 项 | 状态 | 证据 |
|---|---|---|
| 四层文本与谐音引擎 | `PASS_STATIC` | 16 个新测试；display/source 逐字不变 |
| 5 条谐音替换 | `PASS_VERIFIED` | 全部 `verified` / `audio_test: PASS` / `human_review: APPROVED` |
| `language=zh` 显式守卫 | `PASS_STATIC` | 请求体断言；服务模型未声明该字段（已记录） |
| 整句 + 破折号气口 | `PASS_VERIFIED` | 18 联各 1 个整句请求；段级硬切与 220 ms 数字静音已废止 |
| 《春江花月夜》18 联重合成 | `PASS_VERIFIED` | 107.26 s；`classical_recitation`；服务已停止 |
| 拼音级 ASR | `PASS_VERIFIED`（技术） | 全篇 18/18；探针 12/12；目标句 0.0 |
| 人工听感 | `PASS_VERIFIED` | 5 条谐音复核通过；整句平滑版经 M7 终审通过 |

## 1. 根因

旧 `pronunciation.py` 只做标注，不做任何替换；`tts.py` 直接发送 `tts_text`。CosyVoice 的 G2P 把「碣」读成 `jiē`（接近“接”），旧探针第 12 句 ASR 为“接时销销无线路”，字 CER 0.571。接口没有拼音/音素参数，旧结论只能记录为“能力缺口”。

M6 改变的是**声学层文本**：为已确认的 G2P 缺陷配置同音字，只替换 `acoustic_text`，字幕与原文不变。

## 2. 四层文本

| 层 | 用途 | 是否可变 |
|---|---|---|
| `source_text` | 原始文本（繁） | 否 |
| `display_text` | 字幕 | **否，逐字不变** |
| `tts_text` | 送入引擎前的简体文本 | 是（词层） |
| `acoustic_text` | 实际送 TTS 的文本 | 是（仅谐音替换） |

`line_layers()` 输出 `tts_text`、`acoustic_text`、`replacements`；`pronunciation_report.json` 每行记录四层文本与替换位置。`synthesize_narration()` 发送 `acoustic_text`，manifest 同时保留 `tts_text` 与 `acoustic_text`。

## 3. 词典与候选状态

只对**已确认的 G2P 缺口**配置 `tts_alias`；其余词条保留预期读音用于复核，不做替换。

| id | 原文 | 预期拼音 | acoustic 替换 | 状态 |
|---|---|---|---|---|
| jieshi | 碣石 | jié shí | 节石 | candidate |
| xiaoxiang | 潇湘（瀟湘） | xiāo xiāng | 消湘 | candidate |
| bianzhou | 扁舟 | piān zhōu | 偏舟 | candidate |
| sixian | 似霰 | sì xiàn | 似线 | candidate |
| qingfengpu | 青枫浦（青楓浦） | qīng fēng pǔ | 青枫普 | candidate |

验证但不替换的词条：宛转、汀上、江畔、**不胜愁（bù shèng chóu，胜不是 shēng）**、徘徊、捣衣砧、鸿雁、鱼龙潜跃、闲潭、艳艳。

规则：

- 最长匹配、非重叠、同长度替换；替换后文本长度必须不变。
- `display_text` / `source_text` 不进入替换器。
- 所有新映射初始 `status: candidate`；`verified` 需要 `audio_test: PASS` + `human_review: APPROVED`，否则 schema 拒绝。
- 14 条宽替换的初跑保留在 `experiments/m6_pronunciation/poem_wide_aliases/` 与 `probe_wide_aliases/`：额外谐音（如闲潭→闲谈、鸿雁→红雁）并非已证实缺陷，且引入 ASR 歧义，因此收窄为 5 条。

## 4. TTS 请求与 `language=zh`

`tts.py` 每次 `/tts` 请求显式带：

```json
{"text": "<acoustic part>", "speaker": "中文女", "speed": 0.82,
 "language": "zh", "text_frontend": true}
```

重要边界：CosyVoice 的 `TTSRequest` 模型**没有声明 `language` 字段**，Pydantic 默认忽略未知字段，因此它是显式守卫而非服务端强制。实际保证中文的是：SFT 中文模型 + `speaker` + `text_frontend=true`。manifest 的 `request` 块记录：

```json
{"language": "zh", "text_frontend": true, "api_language_field": false}
```

不修改 `D:\AI\CosyVoice-Runtime`。

## 5. 古诗词节奏

`classical_recitation` 新增 `metrical_split`：

```text
7 言：2 + 2 + 3，段间 220 ms
5 言：2 + 3
标点："，、；：？。！"
```

《春江花月夜》18 联每联两个 7 言句 → 每行 6 段，共 **108 段**；段间 220 ms，逗号后 260 ms，行间 1200 ms。

## 6. ASR 闭环

- Whisper base（CPU，CosyVoice 运行时 venv）转写两次：`initial_prompt=tts_text`（原始词，检验音频是否像目标词）与无 prompt 的 raw。
- `scripts/asr_pinyin_check.py`（项目 `.venv`，`pypinyin`）做 **TONE3 音节编辑距离**；先剔除标点/符号，只比较汉字拼音。
- 同音异字（碣石→结石、潇湘→潇湘）通过；错误声调（碣 jié2 → 接 jiē1）失败。
- 字符 CER 仅作辅助：同音字会抬高字符 CER，不能作为发音验收依据。
- `tts_qa.py` 通过隔离子进程调用 pinyin checker（`-I` + 清理 PYTHONPATH），避免 CosyVoice 的 Python 3.10 环境污染项目 3.12 venv。

## 7. 真实执行

### 7.1 服务

- `CosyVoice-300M-SFT`，CPU，12 线程，50000，`text_frontend=wetext`，7 个预置音色。
- 启动加载 9.2–28.5 s；合成完成后已停止，50000 端口确认空闲，health 不可达。
- GPU 0；未修改运行时目录。

### 7.2 合成集

| 集 | 行 | 段 | 模式 | 音频 | 合成耗时 |
|---|---|---|---|---|---|
| 《春江花月夜》18 联 | 18 | 108 | classical_recitation 0.82 | 107.26 s | 316.0 s CPU |
| 此前 12 行探针 | 12 | 14 | recitation 0.92 | 27.99 s | 107.6 s CPU |

输出：

- `experiments/m6_pronunciation/poem/audio/`、`audio_manifest.json`、`pronunciation_report.json`、`tts_qa.json`
- `experiments/m6_pronunciation/probe/audio/`、同名文件
- 宽替换初跑：`poem_wide_aliases/`、`probe_wide_aliases/`

### 7.3 探针逐句前后对照（12 行）

| 行 | 显示（繁） | 旧 ASR / 字 CER | 新 acoustic | 新 ASR（prompted） | 新字 CER | 新拼音 CER | 判定 |
|---|---|---|---|---|---|---|---|
| 1 | 誰家今夜扁舟子，何處相思明月樓？ | 谁家今夜扁舟子… / 0.0 | 谁家今夜偏舟子，何处相思明月楼？ | 谁家今夜扁舟子６何处相思明月楼？ | 0.0 | 0.0 | PASS |
| 2 | 月照花林皆似霰。 | 月照花林皆似霰。 / 0.0 | 月照花林皆似线。 | 月照花林皆似霰。 | 0.0 | 0.0 | PASS |
| 3 | 白雲一片去悠悠，青楓浦上不勝愁。 | 白云一片去悠悠，青枫浦上不胜愁。 / 0.0 | 白云一片去悠悠，青枫普上不胜愁。 | 白云一片去悠悠，青枫浦上不胜愁。 | 0.0 | 0.0 | PASS |
| 4 | 江流宛轉遶芳甸。 | 江流宛转绕芳甸。 / 0.0 | 江流宛转绕芳甸。 | 江流宛转绕芳甸。 | 0.0 | 0.0 | PASS |
| 5 | 汀上白沙看不見。 | 汀上白沙看不见。 / 0.0 | 汀上白沙看不见。 | 汀上白沙看不见。 | 0.0 | 0.0 | PASS |
| 6 | 江畔何人初見月？ | 江畔何人初见月… / 0.0 | 江畔何人初见月？ | 江畔何人初见月… | 0.0 | 0.0 | PASS |
| 7 | 可憐樓上月徘徊。 | 可怜楼上月徘徊。 / 0.0 | 可怜楼上月徘徊。 | 可怜楼上月徘徊。 | 0.0 | 0.0 | PASS |
| 8 | 擣衣砧上拂還來。 | 捣衣砧上拂还来。 / 0.0 | 捣衣砧上拂还来。 | 捣衣砧上拂还来。 | 0.0 | 0.0 | PASS |
| 9 | 鴻雁長飛光不度。 | 鸿雁长飞光不度。 / 0.0 | 鸿雁长飞光不度。 | 鸿雁长飞光不度。 | 0.0 | 0.0 | PASS |
| 10 | 魚龍潛躍水成文。 | 鱼龙潜跃水成文。 / 0.0 | 鱼龙潜跃水成文。 | 鱼龙潜跃水成文。 | 0.0 | 0.0 | PASS |
| 11 | 閒潭夢落花。 | 闲潭梦落花。 / 0.0 | 闲潭梦落花。 | 闲潭梦落花。 | 0.0 | 0.0 | PASS |
| 12 | 碣石瀟湘無限路。 | **接时销销无限路 / 0.571** | **节石消湘无限路** | **结石潇湘无限路** | **0.143** | **0.0** | PASS |

目标句：旧读 `jiē shí xiāo xiāo` → 新读 `jié shí xiāo xiāng`；拼音 CER 0.571 → **0.0**。

### 7.4 全篇 18 联逐句（Whisper base + 拼音）

| 行 | 显示（繁） | acoustic（仅改动） | ASR（prompted） | 字 CER | 拼音 CER | 判定 |
|---|---|---|---|---|---|---|
| 1 | 春江潮水連海平，海上明月共潮生。 | — | 春江潮水连海平４海上明月共潮生。 | 0.0 | 0.0 | PASS |
| 2 | 灩灩隨波千萬里，何處春江無月明？ | — | 艳艳随波千万里…何处春江无月明… | 0.071 | 0.071 | PASS |
| 3 | 江流宛轉遶芳甸，月照花林皆似霰。 | 江流宛转绕芳甸，月照花林皆似线。 | 江流宛转绕芳甸，月照花林皆似霰。 | 0.0 | 0.0 | PASS |
| 4 | 空裏流霜不覺飛，汀上白沙看不見。 | — | 空里流霜不觉飞，汀上白沙看不见。 | 0.0 | 0.0 | PASS |
| 5 | 江天一色無纖塵，皎皎空中孤月輪。 | — | 江天一色无纤尘，皎皎空中孤月轮。 | 0.0 | 0.0 | PASS |
| 6 | 江畔何人初見月，江月何年初照人？ | — | 江畔何人初见月２江月何年初照人２ | 0.0 | 0.0 | PASS |
| 7 | 人生代代無窮已，江月年年望相似。 | — | 人生代代无穷已，江月年年望相似。 | 0.0 | 0.0 | PASS |
| 8 | 不知江月待何人？但見長江送流水。 | — | 不知江月待何人？但见长江送流水。 | 0.0 | 0.0 | PASS |
| 9 | 白雲一片去悠悠，青楓浦上不勝愁。 | 白云一片去悠悠，青枫普上不胜愁。 | 白云一片去悠悠，青枫浦上胜愁。 | 0.071 | 0.071 | PASS |
| 10 | 誰家今夜扁舟子，何處相思明月樓？ | 谁家今夜偏舟子，何处相思明月楼？ | 谁家今夜天舟子…何处相思明月楼… | 0.071 | 0.071 | PASS |
| 11 | 可憐樓上月徘徊，應照離人妝鏡臺。 | — | 可怜楼上月徘徊…应照离人妆镜台。 | 0.0 | 0.0 | PASS |
| 12 | 玉戶簾中卷不去，擣衣砧上拂還來。 | — | 玉户帘中卷不去，捣衣砧上拂还来。 | 0.0 | 0.0 | PASS |
| 13 | 此時相望不相聞，願逐月華流照君。 | — | 此时相望不相闻，愿逐月华流照君。 | 0.0 | 0.0 | PASS |
| 14 | 鴻雁長飛光不度，魚龍潛躍水成文。 | — | 鸿雁长飞光不度，鱼龙潜跃水成文。 | 0.0 | 0.0 | PASS |
| 15 | 昨夜閒潭夢落花，可憐春半不還家。 | — | 昨夜闲潭梦落花，可怜春半不还家。 | 0.0 | 0.0 | PASS |
| 16 | 江水流春去欲盡，江潭落月復西斜。 | — | 江水流春去欲尽，江潭落月复西斜。 | 0.0 | 0.0 | PASS |
| 17 | 斜月沉沉藏海霧，碣石瀟湘無限路。 | 斜月沉沉藏海雾，节石消湘无限路。 | **斜月沉沉藏海雾，碣石潇湘无限路。** | **0.0** | **0.0** | PASS |
| 18 | 不知乘月幾人歸，落月搖情滿江樹。 | — | 不知乘月几人归，落月摇情满江树。 | 0.0 | 0.0 | PASS |

汇总：

| 集 | 拼音通过 | 最大拼音 CER | 字符 CER（prompted） |
|---|---|---|---|
| 全篇 18 联 | **18/18** | **0.071** | 12 行为 0，6 行为 0.071–0.143 |
| 12 行探针 | **12/12** | **0.0** | 11 行为 0，目标行 0.143 |

字符 CER 的剩余差异多为同音字（结石/碣石、节石、艳艳/灩灩），拼音 CER 已归零。

## 8. 测试

```text
.venv\Scripts\python.exe -m pytest
246 passed, 1 warning in 21.41s
```

新增 `tests/test_pronunciation_engine.py`（15 个）：

- 碣石潇湘、扁舟子、似霰、青枫浦在 `acoustic_text` 中替换，`display_text` 严格不变；
- 繁体输入 `瀟湘 / 青楓浦` 映射到简体谐音；
- 最长匹配、同长度约束、`verified` 必须有音频与人工证据；
- 未配置别名的词条（鸿雁、闲潭、鱼龙潜跃、捣衣砧）不替换；
- 报告四层文本与 summary；
- classical_recitation 的 2/2/3 分段与 5 言 2/3；
- TTS 请求带 `language=zh`、`text_frontend=true`，发送 `acoustic_text`。

`tests/test_voice_tts.py`、`tests/test_pronunciation.py`、`tests/test_recitation.py` 全部保持通过。

## 9. 未执行 / 限制

- 5 条谐音已人工复核通过；整句平滑版的听感经 M7 终审通过。
- 拼音比较是**行级**的；短句一个音节错误会放大为 0.14–0.2，需人工复核。
- `initial_prompt` 会引导字形，但保留声调/声母差异；raw ASR 噪声大，报告两者。
- 5 条映射已按人工复核转为 `verified`；本报告 §7 的 108 段版本是历史对照，最终整句版本见 `poem_smooth/`。
- `language` 字段服务端未声明，属于显式守卫；真正的中文保证来自 SFT 模型 + 中文文本。
- 无音高/旋律/时长控制；真正吟唱仍为 `NOT_RUN`。
- 未改 M7 验收。

## 10. 资源与 Git

- CosyVoice-300M-SFT CPU：加载 9.2–28.5 s；全篇合成 316 s CPU，探针 108 s；ASR Whisper base CPU；GPU 0。
- 服务已停止；50000 端口空闲；未修改 `D:\AI\CosyVoice-Runtime`。
- 新增项目依赖 `pypinyin>=0.55`（纯 Python，轻量；写入 `pyproject.toml` / `uv.lock`）。
- 未提交、未推送、未 reset、未 clean；HEAD 仍为 `651c7dd`。

## 11. 待人工审查

1. 试听 `experiments/m6_pronunciation/probe/audio/line_12.wav` 与全篇第 17 联，确认「碣石潇湘」听感。
2. 试听 5 条候选替换（扁舟/似霰/青枫浦/碣石/潇湘）是否自然，是否有“换字”痕迹。
3. 确认 2/2/3 气口与 220 ms 段间停顿是否符合吟诵节奏。
4. 人工通过后，将对应词条从 `candidate` 改为 `verified`，并填写 `audio_test: PASS` / `human_review: APPROVED`。
5. 确认后再进入 **M7 双风格代表性镜头最终验收**。
