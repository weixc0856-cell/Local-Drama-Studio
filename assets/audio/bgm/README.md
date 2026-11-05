# BGM 资产（CC0 Keynata Commons，2026-11-05）

之前的正弦波/粉噪 drone 已被用户明确拒绝：持续低频与高频毛刺会产生嗡嗡声和烦躁感，**禁止进入生产**。这些旧文件保留在 `assets/audio/bgm/` 仅作历史，manifest 状态已改为 `REJECTED`。

BGM 全部来自 **Keynata Commons**（机器作曲，CC0 1.0，无需署名，可商用）。第一版 4 条中，E 小调（ink）与 B 小调（shinkai 钢琴）因听感"阴间"被 `REJECTED`，不再进入生产：

| 本地 WAV | Keynata track | 调式 | 状态 |
|---|---|---|---|
| `keynata/ink_strings_duo.wav` | `classical_duo_24036` | E 小调 | `REJECTED` |
| `keynata/court_strings_duo.wav` | `classical_duo_24015` | E 大调 | `APPROVED`（备用） |
| `keynata/shinkai_piano.wav` | `classical_piano_6134` | B 小调 | `REJECTED` |
| `keynata/ghibli_quartet.wav` | `classical_quartet_25010` | F 大调 | `APPROVED`（备用） |

- 来源/许可：`assets/audio/bgm/keynata/LICENSE.md`；CC0 1.0，无署名要求，可商用。
- 处理：`highpass=70`、`equalizer=180 -3dB`、`equalizer=4200 -3dB`、`lowpass=14000`、`afftdn=-40`、`alimiter`；48 kHz mono PCM。
- 原始 MP3 与清洗 WAV 按仓库规则本地保留；manifest 记录 SHA-256，重跑用 `scripts/fetch_bgm.py`。
- `review_status=PENDING_HUMAN_REVIEW`：权利清晰不代表人工听感已通过。
- **禁止**再使用持续 drone 的生成方式；旧 `scripts/make_bgm.py` 已删除。

## 暖色大调替换（2026-11-05）

用户认定上一版（E 小调弦乐二重奏、B 小调钢琴）"阴间、压抑"：技术指标干净，但调式是小调、织体稀疏。新增 `warm/` 三首**大调**曲目，仅做 30 Hz 高通与峰值限制，不再用 EQ 去修情绪：

| 资产 ID | 本地 WAV | Keynata track | 调式/织体 |
|---|---|---|---|
| `bgm_warm_pop_canon` | `warm/pop_canon_major.wav` | `jpop_3piece_11623` | 大调 canon 进行；钢琴/吉他/贝斯/鼓 |
| `bgm_warm_strings_c` | `warm/strings_c_major.wav` | `classical_quartet_25041` | C 大调；弦乐四重奏 |
| `bgm_warm_piano_c` | `warm/piano_c_major.wav` | `classical_piano_4016` | C 大调；立式钢琴 |

- 许可：CC0-1.0，无署名，可商用；明细见 `warm/LICENSE.md`。
- 选曲依据：Keynata 索引中的 `mode= major` + MIDI 调号；不再依据频谱猜情绪。
- 人工指定：`scripts/r3_build.py --bgm-id <asset_id>` 会覆盖时间线里的 BGM 轨道，并把实际用的时间线写到输出目录 `audio_timeline_effective.json`。
