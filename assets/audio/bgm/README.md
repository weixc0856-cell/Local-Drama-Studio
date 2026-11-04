# BGM 资产（自生成，2026-11-04）

这两条 BGM 是用 FFmpeg 在本机合成的**程序化环境铺底**，不是第三方录音，也不包含任何外部采样或旋律片段。项目所有者可将其用于本项目及商业成片；代码与生成命令保留在仓库中，便于复现和替换。

| 文件 | 用途 | 时长 | 响度 | 峰值 |
|---|---|---|---|---|
| `ink_serene_60s.wav` | 水墨、幽远、慢速 | 60 s | -25.7 LUFS | -15.3 dBFS |
| `court_elegant_60s.wav` | 工笔、典雅、明亮 | 60 s | -25.8 LUFS | -15.9 dBFS |

- 格式：48 kHz / mono / PCM s16le。WAV 按仓库规则本地保留（`*.wav` 忽略），manifest 记录 SHA-256；克隆后需用同一命令重建或从备份恢复。
- 合成方式：五声音阶正弦层 + 粉噪纹理 + 慢速 tremolo + 低通/高通 + 3 s 淡入/淡出 + loudnorm。
- `assets/audio/manifest.json` 中登记 SHA-256、时长、`status=APPROVED`、`commercial_allowed=true`、`review_status=PENDING_HUMAN_REVIEW`。
- **人工听感仍未验收**：状态 `APPROVED` 只代表权利来源清晰、可进入技术混音；不等于审美通过。
- 替换为外部 CC0/公有领域录音时，必须登记来源 URL、许可证据与 SHA-256，并重新做听感与 ducking 检查。
