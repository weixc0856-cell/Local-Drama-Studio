# BGM 资产（CC0 Keynata Commons，2026-11-05）

之前的正弦波/粉噪 drone 已被用户明确拒绝：持续低频与高频毛刺会产生嗡嗡声和烦躁感，**禁止进入生产**。这些旧文件保留在 `assets/audio/bgm/` 仅作历史，manifest 状态已改为 `REJECTED`。

当前生产 BGM 全部来自 **Keynata Commons**（机器作曲，CC0 1.0，无需署名，可商用）：

| 本地 WAV | Keynata track | 风格 | 时长 |
|---|---|---|---|
| `keynata/ink_strings_duo.wav` | `classical_duo_24036` | 水墨 · 小提琴/大提琴 | 244 s |
| `keynata/court_strings_duo.wav` | `classical_duo_24015` | 工笔 · 小提琴/大提琴 | 353 s |
| `keynata/shinkai_piano.wav` | `classical_piano_6134` | 新海诚 · 钢琴独奏 | 160 s |
| `keynata/ghibli_quartet.wav` | `classical_quartet_25010` | 吉卜力 · 弦乐四重奏 | 320 s |

- 来源/许可：`assets/audio/bgm/keynata/LICENSE.md`；CC0 1.0，无署名要求，可商用。
- 处理：`highpass=70`、`equalizer=180 -3dB`、`equalizer=4200 -3dB`、`lowpass=14000`、`afftdn=-40`、`alimiter`；48 kHz mono PCM。
- 原始 MP3 与清洗 WAV 按仓库规则本地保留；manifest 记录 SHA-256，重跑用 `scripts/fetch_bgm.py`。
- `review_status=PENDING_HUMAN_REVIEW`：权利清晰不代表人工听感已通过。
- **禁止**再使用持续 drone 的生成方式；旧 `scripts/make_bgm.py` 已删除。
