# BGM 资产（自生成，2026-11-05）

四条 BGM 是用 FFmpeg 在本机合成的**程序化环境铺底**，不是第三方录音，也不包含任何外部采样或旋律片段。项目所有者可将其用于本项目及商业成片；生成命令保留在 `scripts/make_bgm.py`，便于复现和替换。

| 文件 | 风格 | 时长 | 响度 | 峰值 |
|---|---|---|---|---|
| `ink_serene_60s.wav` | 水墨、幽远、慢速 | 60 s | -25.7 LUFS | -16.0 dBFS |
| `court_elegant_60s.wav` | 工笔、典雅、明亮 | 60 s | -25.7 LUFS | -15.2 dBFS |
| `shinkai_piano_60s.wav` | 新海诚、钢琴/情绪 | 60 s | -25.7 LUFS | -15.3 dBFS |
| `ghibli_pastoral_60s.wav` | 吉卜力、田园、温暖 | 60 s | -25.6 LUFS | -14.9 dBFS |

- 格式：48 kHz / mono / PCM s16le。WAV 按仓库规则本地保留（`*.wav` 忽略），manifest 记录 SHA-256；克隆后可用 `scripts/make_bgm.py` 重建。
- 合成与清理：五声音阶正弦层 + 极低粉噪 + 慢速 tremolo + `highpass=70` + `equalizer=180 -3dB` + `equalizer=4200 -4dB` + `lowpass` + `afftdn=-30` + 淡入淡出 + loudnorm。
- `assets/audio/manifest.json` 中登记 SHA-256、时长、`status=APPROVED`、`commercial_allowed=true`、`style_tags`、`review_status=PENDING_HUMAN_REVIEW`。
- **人工听感仍未验收**：`APPROVED` 只代表权利来源清晰、可进入技术混音；不等于审美通过。
- 外部 CC0/公有领域录音替换时，必须登记来源 URL、许可证据与 SHA-256，并重新做听感与 ducking 检查。
