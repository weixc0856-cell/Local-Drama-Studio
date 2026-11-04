# SFX 资产（自生成，2026-11-04）

四条程序化音效，使用 FFmpeg 合成，无第三方采样：

| 文件 | 用途 | 时长 | 状态 |
|---|---|---|---|
| `sfx_wind_soft_30s.wav` | 高空/云海风声 | 30 s | `APPROVED`（听感 PENDING） |
| `sfx_water_flow_20s.wav` | 江面/水声 | 20 s | `APPROVED`（听感 PENDING） |
| `sfx_chime_single_6s.wav` | 单声钟磬 | 6 s | `APPROVED`（听感 PENDING） |
| `sfx_whoosh_2s.wav` | 转场风声 | 2 s | `APPROVED`（听感 PENDING） |

- 48 kHz / mono / PCM s16le；SHA-256 在 `assets/audio/manifest.json`。
- 由 `scripts/make_sfx.py` 重建；WAV 本地保留。
- `APPROVED` 只代表权利清晰；人工听感与与 BGM/旁白的相对响度仍待审。
