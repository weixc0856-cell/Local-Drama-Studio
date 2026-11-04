# M7 最终交付报告：双风格代表样片

> 执行日期：2026-11-04
> 环境：Windows 11 / i7-13700K / 64 GB / Intel Arc A750 8 GB / FFmpeg 8.1
> 本轮只使用 CPU + Pillow/FFmpeg/CosyVoice CPU；CosyVoice 50000 已停止。
> 状态口径：`docs/PRD.md` §0.2。**技术质检通过不等于审美验收通过。**

## 0. 结论

M7 交付两支 1080×1920 / 24 fps 双风格代表样片，均通过构建质检、音频 QA 与运动质检。

| 样片 | 时长 | 转场 | 技术状态 | 路径 |
|---|---|---|---|---|
| 水墨（ink_wash） | 10.087 s | ink_dissolve 1.2 s | `PASS_VERIFIED`（技术 + 人工） | `experiments/m7_final/ink/renders/final_9x16.mp4` |
| 青绿工笔（court_green_fine_line） | 9.583 s | crossfade 0.8 s | `PASS_VERIFIED`（技术 + 人工） | `experiments/m7_final/court/renders/final_9x16.mp4` |

人工最终审片已于 2026-11-04 全项通过（视觉、时序、整句发音、门禁）；本轮 M1–M7 基线封板。

## 1. 音频管线平滑化

### 1.1 改动

- **废除段内硬切**：不再把 7 言诗拆成 2/2/3 独立 WAV，不再生成数字静音并拼接。
- **整句/整联推理**：每行诗词只发一次 `/tts` 请求；`parts` 只有一个整句条目。
- **破折号气口**：`breath_text()` 在 7 言句第 4 字后、5 言句第 2 字后插入 `——`，保留原标点：

```text
春江潮水连海平，海上明月共潮生。
→ 春江潮水——连海平，海上明月——共潮生。
```

- **行间停顿**：`narration` 800 ms、`recitation` 950 ms、`classical_recitation` 1000 ms；只由时间轴在整句之间插入，不在句内拼静音。
- **5 条谐音转 verified**：扁舟→偏舟、似霰→似线、青枫浦→青枫普、碣石→节石、潇湘→消湘；`audio_test: PASS`、`human_review: APPROVED`。`display_text` 仍逐字不变。

### 1.2 平滑版全篇

- 路径：`experiments/m6_pronunciation/poem_smooth/`
- 18 联 / 36 句，18 次整句请求，每行 1 段；音频合计 80.159 s。
- 整段试听（1000 ms 行间停顿）：`experiments/m6_pronunciation/poem_smooth/full_poem_smooth.mp3`（97.156 s）。
- ASR（Whisper base + 拼音 TONE3）：**18/18 通过，最大拼音 CER 0.143**；第 17 联「碣石潇湘无限路」拼音 CER **0.0**。
- 无 `line_XX_part_XX.wav`、无 `silence_XXXX.wav`、无 220 ms 段间硬静音。

## 2. 水墨代表片

### 2.1 内容

| 镜头 | 源图 | 运动 | 时长 | 局部层 |
|---|---|---|---|---|
| shot_001 | 水墨孤舟（白天） | slow_push_in | 5.340 s | 水面/倒影/云雾/植物，船体 locked |
| shot_002 | 月夜孤舟 | push_in_with_pan（2% 横向漂移） | 4.747 s | 水面/倒影/云雾/芦苇，船体 locked |

- 转场：`ink_dissolve` 1.2 s；`left_start=5.340`，右起点 0。
- 配音：诗词第 1、2 联，`recitation` 0.92，整句 + 破折号气口；行间 800 ms。
- 字幕：繁体 `春江潮水連海平，海上明月共潮生。` / `灩灩隨波千萬里，何處春江無月明？`
- 时长：10.087 s。

### 2.2 质检

| 项 | 结果 |
|---|---|
| build quality | PASS（1080×1920 / 24 fps / 10.087 s / 解码 PASS） |
| audio QA | PASS（2 行，0 failed / 0 clipped / 0 quiet / 0 broken silence；timeline PASS） |
| motion quality | PASS（`MOTION_QUALITY_OK`） |
| 刚体 boat sh1 | 帧差均值 1.96、峰值 10.44、边缘漂移 1.04% → PASS |
| 刚体 boat sh2 | 帧差均值 2.59、峰值 11.36、边缘漂移 0.00% → PASS |
| 时序 | 无未豁免帧间跳变；转场段振荡率 0.074 → 不判频闪 |

## 3. 青绿工笔代表片

### 3.1 内容

| 镜头 | 源图 | 运动 | 时长 | 局部层 |
|---|---|---|---|---|
| shot_001 | G3 青绿长卷 | scroll_pan 30 px/s，x 336→503 | 4.771 s | 无（纯长卷横移） |
| shot_002 | A1 青绿长卷 | scroll_pan 30 px/s，x 492→348（rtl） | 4.805 s | 无 |

- 转场：`crossfade` 0.8 s；左起点 4.771，右起点 0。
- 配音：诗词第 9、17 联，`recitation` 0.92，整句 + 破折号气口；行间 800 ms。
- 字幕：繁体 `白雲一片去悠悠，青楓浦上不勝愁。` / `斜月沉沉藏海霧，碣石瀟湘無限路。`
- 时长：9.583 s。

### 3.2 质检

| 项 | 结果 |
|---|---|
| build quality | PASS（1080×1920 / 24 fps / 9.583 s / 解码 PASS） |
| audio QA | PASS（2 行，0 failed / 0 clipped / 0 quiet / 0 broken silence；timeline PASS） |
| motion quality | PASS（`MOTION_QUALITY_OK`）；无 locked 区域；时序 PASS |
| 横移速度 | 两个镜头均 30.0 px/s，方向一正一反 |

## 4. 交付路径

### 4.1 成片

| 内容 | 路径 |
|---|---|
| 水墨软字幕 | `experiments/m7_final/ink/renders/final_9x16.mp4`（4.1 MB） |
| 水墨烧录字幕 | `experiments/m7_final/ink/renders/final_9x16_burned.mp4`（4.3 MB） |
| 青绿软字幕 | `experiments/m7_final/court/renders/final_9x16.mp4`（6.1 MB） |
| 青绿烧录字幕 | `experiments/m7_final/court/renders/final_9x16_burned.mp4`（7.2 MB） |
| 首/中/末帧对照（双片） | `experiments/m7_final/review_sheet.png` |

### 4.2 质检与证据

| 内容 | 路径 |
|---|---|
| 水墨 build 质检 | `experiments/m7_final/ink/renders/quality_report.json` |
| 水墨 audio QA | `experiments/m7_final/ink/audio_qa_report.json` |
| 水墨 motion QA | `experiments/m7_final/ink/work/motion/build-20261104-115220/motion_quality_report.json` |
| 青绿 build 质检 | `experiments/m7_final/court/renders/quality_report.json` |
| 青绿 audio QA | `experiments/m7_final/court/audio_qa_report.json` |
| 青绿 motion QA | `experiments/m7_final/court/work/motion/build-20261104-115419/motion_quality_report.json` |
| 平滑全篇试听 | `experiments/m6_pronunciation/poem_smooth/full_poem_smooth.mp3` |

### 4.3 说明：被替换的中间版本

- `experiments/m7_final/ink/renders_subtitle_clipped/`、`court/renders_subtitle_clipped/`：末句 `pause_after_ms=0` 时字幕超出音频尾部 200 ms 的初版；最终版恢复 800 ms 末行停顿并让 segment 时长等于音频时间轴，已通过 audio QA。
- `experiments/m7_final/ink/work/motion/build-20261104-114907/` 等为早期时长版本，最终以 `115220` / `115419` 为准。

## 5. 资源与环境

- CosyVoice-300M-SFT CPU，50000；加载 9.0–28.5 s；合成完成后已停止，端口 50000 空闲，health 不可达。
- 未启动 GPU 生成；XPU 显存 0（CosyVoice 为 CPU）。
- 水墨序列 4+5 个局部层、约 242 帧；青绿 0 局部层、约 230 帧。
- 全量测试：`246 passed, 1 warning in 22.13s`。

## 6. Git

未提交、未推送、未 reset、未 clean；HEAD 仍为 `651c7dd`。

本轮修改：

- `src/drama_studio/voice/recitation.py`：整句 + 破折号气口，废除 2/2/3 硬切。
- `src/drama_studio/voice/tts.py`：每行一次整句请求，无段级静音拼接。
- `config/audio.yaml`：行间停顿 800/950/1000 ms，关闭句内 split。
- `config/pronunciation.yaml`：5 条谐音 `verified` / `PASS` / `APPROVED`。
- `src/drama_studio/voice/pronunciation.py`：整体 review 状态按 verified 计算。
- 新增：`docs/M7_FINAL_DELIVERY_REPORT.md`、`experiments/m7_final/`、`experiments/m6_pronunciation/poem_smooth/`。
- 测试：`tests/test_recitation.py`、`tests/test_pronunciation_engine.py`、`tests/test_voice_tts.py` 更新为整句/破折号语义。

## 7. 限制与风险

- 水墨片 10.087 s，比 10 s 目标长 0.087 s；来自整句音频 + 800 ms 行间停顿，属于帧量化范围。
- 水墨 shot_002 为 `push_in_with_pan`：9:16 源图没有纯横移空间，用 2% 横向漂移 + 3–6% 推近近似“平推”；不是纯 lateral track。
- 青绿两镜头无局部微动，只验证长卷横移与转场；不是全量局部动态样片。
- 成片有 0.6 s 淡入 / 0.9 s 淡出；review sheet 的最后一帧因此偏暗，属于成片行为，不是尾部异常衰减。
- 人工审美、听感、字幕可读性仍 `PENDING`。
- 未进入 M6 的 chant/音高；未改 Wan。

## 8. 最终验收结论

2026-11-04 人工最终审片全项通过：

1. 两支 `final_9x16_burned.mp4` 的风格、运镜、转场、繁体字幕通过。
2. `full_poem_smooth.mp3` 与两支成片整句朗诵自然，无“报站感”。
3. 水墨 10.087 s 与 `push_in_with_pan` 近似“平推”被接受。
4. 青绿纯横移基线被接受，不追加局部云水微动。
5. M1–M7 基线冻结；后续扩展（Wan motion mask、chant、BGM/SFX、商用授权）另行立项。
