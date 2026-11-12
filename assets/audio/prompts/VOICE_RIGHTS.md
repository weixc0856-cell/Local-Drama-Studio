# 声音权声明

`assets/audio/prompts/source/my_voice_5s_src.wav` 及其派生文件
（`my_voice_clean_v1.wav`）为项目所有者本人录制的干声。

- 权利人：项目所有者本人（self）
- 授权范围：本项目内的 TTS 零样本参考、克隆推理与成片发布
- 不含：向第三方再分发原始录音
- 记录日期：2026-11-04

原始文件位于 `CosyVoice-Runtime/assets\my_voice_5s.wav`，本项目未改动该文件，仅复制后处理。

## 第三方朗诵参考音（2026-11-07）

`assets/audio/prompts/announcers/` 下两段 30 s 朗诵片段来自公开视频，不是本人录音：

- 男声：孙道临，唐诗朗诵，[YouTube INsXb8IRcNs](https://www.youtube.com/watch?v=INsXb8IRcNs)
- 女声：雅坤，《春江花月夜》朗诵，[YouTube npKK3E6wLzI](https://www.youtube.com/watch?v=npKK3E6wLzI)

权利状态：表演者权、录音制作者权与平台条款均未取得授权；`commercial_allowed=false`，对应 voice profile 为 `BLOCKED`。
仅可用于本地试听与音色研究，不得进入生产合成、成片发布或再分发。详见 `assets/audio/prompts/announcers/README.md`。

## 混合参考音（2026-11-07）

`assets/audio/prompts/blends/` 下两条 30 s 参考音由本人录音与孙道临朗诵按 80/20 幅度混合：

- `blend_my80_sun20_ref.wav`：本人 80% + 孙道临 20%
- `blend_sun80_my20_ref.wav`：孙道临 80% + 本人 20%
- `blend_my90_sun10_ref.wav`：本人 90% + 孙道临 10%
- `blend_my95_sun05_ref.wav`：本人 95% + 孙道临 5%
- `blend_my99_sun01_ref.wav`：本人 99% + 孙道临 1%

VoxCPM2 官方不支持多参考音加权，官方建议先做音频混合再作为单个参考音；本目录按此实现。
因含第三方表演/录音成分，整体 `commercial_allowed=false`、状态 `BLOCKED`，仅本地试听与研究，不得生产或再分发。
样音 `sample_blend_*.wav` 为 VoxCPM2 `reference_only` 合成结果，仅用于试听。


## 默认参考音（2026-11-07）

`my_voice_clean_v2.wav` 为项目所有者指定并确认可正常使用的默认参考音。
