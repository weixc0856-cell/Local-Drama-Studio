# 暖色大调 BGM（Keynata Commons，CC0 1.0）

2026-11-05，用户明确指出此前的弦乐二重奏/小调钢琴“阴间、压抑、瘆人”。问题不在频段，而在调式与织体：`classical_duo_24036` 是 E 小调，`classical_piano_6134` 是 B 小调。本目录改用**大调、和声饱满、节奏清晰**的曲目，仅做 30 Hz 高通与峰值限制，不做 EQ 塑形。

| 本地 WAV | Keynata track | 调式/主音 | BPM | 时长 | 织体 |
|---|---|---|---|---|---|
| `pop_canon_major.wav` | `jpop_3piece_11623` | 大调 · canon 进行 | 128 | 186.3 s | 钢琴/吉他/贝斯/鼓 |
| `strings_c_major.wav` | `classical_quartet_25041` | C 大调 | 108 | 251.5 s | 弦乐四重奏 |
| `piano_c_major.wav` | `classical_piano_4016` | C 大调 | 119 | 35.4 s | 立式钢琴 |

- 来源：Keynata Commons（机器作曲），`n_tracks=203`，索引 `https://carf-coder.github.io/keynata-commons/release/index.json`。
- 许可：**CC0 1.0 Universal**，无署名要求，可商用。
- 文件地址：`https://carf-coder.github.io/keynata-commons/release/tracks/<track_id>/<track_id>.mp3`。
- 处理：`highpass=f=30,alimiter=limit=0.95` → 48 kHz mono PCM。**不做**降噪/EQ 手术。
- 状态：权利 `APPROVED`；人工听感 `PENDING_HUMAN_REVIEW`。用户选定后可把 `review_status` 改为 `APPROVED` 并去掉 PENDING 备注。
