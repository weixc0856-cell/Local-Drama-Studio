# Pending Prompt Audio

这些文件是 **候选**，不是已批准的生产资产。`APPROVED` 之前不得被正式 TTS 生产流程调用。

| 文件 | 来源 | 时长 | 文本 | 状态 | 阻断 |
|---|---|---|---|---|---|
| `librivox_tang5_01_20261104.wav` | LibriVox《鹿柴》 | 5.25 s | 返景入深林，复照青苔上。 | `TECHNICALLY_VALIDATED` | 美国公有领域；中国辖区/读者身份/人工试听未复核 |
| `aishell3_ssb1711_20261104.wav` | AISHELL-3 Sample SSB1711 | 3.83 s | 杭州之江金都极地海洋公园 | `TECHNICALLY_VALIDATED` | AISHELL 许可待书面确认；sample 无性别标签 |
| `aishell3_ssb0009_20261104.wav` | AISHELL-3 Sample SSB0009 | 5.07 s | 不仅在赛事热身阶段安排型男教练带动热身 | `TECHNICALLY_VALIDATED` | AISHELL 许可待确认；female 为第三方标签，非 sample 官方 |

- 所有候选均已用 CosyVoice2-0.5B zero-shot 实测通过（技术可用，不代表审美/商用通过）。
- 详细来源、哈希与阻断项见 `docs/proposals/VOICE_ASSET_SOURCE_REVIEW.md`。
- 正式资产登记只能扩展 `assets/audio/manifest.json`，不要另建第二套 registry。
