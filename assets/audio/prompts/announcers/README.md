# 第三方朗诵参考音（男 / 女）

2026-11-07 新增。原目录名 `prompts/0` 无语义，现按「性别 + 表演者」拆分：

| 目录 | 性别 | 表演者 | 作品 | 时长 | 来源 |
|---|---|---|---|---|---|
| `male_sun_daolin/` | 男 | 孙道临 | 唐诗欣赏·绝句（《望庐山瀑布》片段） | 29.96 s | [YouTube INsXb8IRcNs](https://www.youtube.com/watch?v=INsXb8IRcNs) |
| `female_ya_kun/` | 女 | 雅坤 | 张若虚《春江花月夜》片段 | 30.16 s | [YouTube npKK3E6wLzI](https://www.youtube.com/watch?v=npKK3E6wLzI) |

- 格式：48 kHz / mono / PCM；仅截取 30 s 片段，未做降噪或 EQ。
- ASR 文本（供 `prompt_text` 参考，仍需人工校对）：
  - 男：「遥看瀑布挂前川，飞流直下三千尺，疑是银河落九天。」
  - 女：「江天一色无纤尘，皎皎空中孤月轮。江畔何人初见月？江月何年初照人？」

## 权利状态

- 两段均来自第三方上传的朗诵录像，**不是本人录音**。
- 表演者权、录音制作者权、平台条款均未取得授权；`commercial_allowed=false`。
- 仅可用于本地试听、音色研究与内部对比；**不得进入生产合成、成片发布或再分发**。
- 声音克隆还涉及表演者人格权/声音权；在获得书面授权前，不把这两段用于任何对外作品。

## 生产门禁

- `config/voices.yaml` 中对应 profile 状态为 `BLOCKED`，`ready=false`。
- `assets/audio/manifest.json` 中 asset 状态为 `PENDING_REVIEW`，`commercial_allowed=false`。
- 若要转正，需要：表演者/录音授权文件 + 中国辖区商用意见 + 人工听感与完整性复核。
