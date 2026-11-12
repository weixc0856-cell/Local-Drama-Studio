# Pending Prompt Audio

这些文件是 **候选**，不是已批准的生产资产。`APPROVED` 之前不得被正式 TTS 生产流程调用。

| 文件 | 来源 | 时长 | 文本 | 状态 | 阻断 |
|---|---|---|---|---|---|
| `librivox_tang5_01_20261104.wav` | LibriVox《鹿柴》 | 5.25 s | 返景入深林，复照青苔上。 | `PENDING_REVIEW` | 美国公有领域；录制者法域/表演者邻接权/中国辖区商用待复核 |
| `aishell3_ssb1711_20261104.wav` | AISHELL-3 Sample SSB1711 | 3.83 s | 杭州之江金都极地海洋公园 | `REJECTED` | 2026-11-04 项目所有者驳回：许可/表演者商业权利冲突未明确 |
| `aishell3_ssb0009_20261104.wav` | AISHELL-3 Sample SSB0009 | 5.07 s | 不仅在赛事热身阶段安排型男教练带动热身 | `REJECTED` | 2026-11-04 项目所有者驳回：许可/表演者商业权利冲突未明确 |

- 所有候选均曾用 CosyVoice2-0.5B zero-shot 实测通过（技术可用，不代表审美/商用通过）。AISHELL 两条已 `REJECTED`，LibriVox 一条 `PENDING_REVIEW`；当前外部 `APPROVED` = 0。
- 详细来源、哈希与阻断项见 `docs/proposals/VOICE_ASSET_SOURCE_REVIEW.md`。
- 正式资产登记只能扩展 `assets/audio/manifest.json`，不要另建第二套 registry。

## Mozilla Common Voice 27.0（2026-11-04 筛选）

从本机 `C:/Users/99236/Downloads/1789498250119-cv-corpus-27.0-2026-09-11-zh-CN.tar.gz` 中筛选；
未镜像/再分发数据集，仓库只登记候选元数据，WAV 留在本地。Common Voice 为 CC0-1.0，
但 README 明确要求不得反推说话人身份；本项目只使用数据集自带标签，不做身份推断。

| 文件 | 角色 | 时长 | 性别/年龄标签 | QA | 状态 |
|---|---|---|---|---|---|
| `cv27_zh_25007250_20261104.wav` | primary | 5.72 s | female_feminine / thirties | SNR 24.58 dB（REVIEW）；zero-shot PASS | `TECHNICALLY_VALIDATED` / review `PENDING_REVIEW` |
| `cv27_zh_32901597_20261104.wav` | primary | 5.87 s | male_masculine / twenties | SNR 28.54 dB（REVIEW）；zero-shot PASS | `TECHNICALLY_VALIDATED` / review `PENDING_REVIEW` |
| `cv27_zh_27532467_20261104.wav` | alternate | 6.70 s | female_feminine / twenties | SNR 24.79 dB（REVIEW） | `PENDING_REVIEW` |
| `cv27_zh_32901020_20261104.wav` | alternate | 7.02 s | male_masculine / twenties | SNR 19.17 dB（REVIEW） | `PENDING_REVIEW` |

- 筛选规则：validated、up_votes ≥ 2、down_votes = 0、4.5–7.5 s、文本 8–40 字、16 kHz mono。
- 未做身份推断；gender/age 仅为 Common Voice 自报标签。
- 未批准生产；需人工试听 + 角色适配 + 许可/条款复核。
- 清洗版 SNR 反而下降（anlmdn + 24 kHz 输出），已拒绝，保留原始 16 kHz 版本。
