# 混合参考音（80/20）

2026-11-07 生成。目标：在本人参考音与孙道临朗诵之间做两种比例的声音参考，供后续 TTS 试听与音色实验。

## 方法

VoxCPM2 官方文档没有「多参考音加权混合」参数：`reference_wav_path` 只接受单个文件，`prompt_wav_path` + `prompt_text` 是续写克隆；官方建议的混合方式就是**先在音频层做好混合，再作为单个参考音传入**。因此这里没有做说话人向量插值，而是：

1. 两条源音统一到 48 kHz / mono，截到 29.96 s（较短者长度）。
2. 按幅度加权：`0.8 × A + 0.2 × B`，`amix` 不做自动归一化，末端 `alimiter=0.891` 防削波。
3. 不做降噪、不做 EQ；保留原始房间感与口型噪声。

生成文件：

| 文件 | 配比 | 用途 |
|---|---|---|
| `blend_my80_sun20_ref.wav` | 本人 80% + 孙道临 20% | 参考音 |
| `blend_sun80_my20_ref.wav` | 孙道临 80% + 本人 20% | 参考音 |
| `blend_my90_sun10_ref.wav` | 本人 90% + 孙道临 10% | 参考音 |
| `blend_my95_sun05_ref.wav` | 本人 95% + 孙道临 5% | 参考音 |
| `blend_my99_sun01_ref.wav` | 本人 99% + 孙道临 1% | 参考音 |
| `sample_blend_my80_sun20_ref.wav` | 用上面参考音合成 | 试听样音（7.52 s） |
| `sample_blend_sun80_my20_ref.wav` | 用上面参考音合成 | 试听样音（8.48 s） |
| `sample_blend_my90_sun10_ref.wav` | 用上面参考音合成 | 试听样音（8.32 s） |
| `sample_blend_my95_sun05_ref.wav` | 用上面参考音合成 | 试听样音（8.48 s） |
| `sample_blend_my99_sun01_ref.wav` | 用上面参考音合成 | 试听样音（5.12 s） |

样音文本：「清晨的山谷里，风穿过竹林，远处传来水声。」VoxCPM2 以 `reference_only` 模式合成；Whisper small 回听五条均能识别为同一句，说明混合参考没有把发音带坏。

## 权利

- 本人参考音为自录、可商用；但混合文件含孙道临朗诵成分，整体属于**第三方表演/录音的衍生物**。
- `commercial_allowed=false`，只能本地试听与研究；不得进入生产、成片发布或再分发。
- 孙道临源文件的权利说明见 `../announcers/README.md`。

## 复现

```powershell
ffmpeg -y -i <my.wav> -i <sun.wav> -filter_complex `
  "[0:a]atrim=0:29.96,volume=0.8[a0];[1:a]atrim=0:29.96,volume=0.2[a1];`
  `[a0][a1]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.891" `
  -ar 48000 -ac 1 -c:a pcm_s16le blend_my80_sun20_ref.wav
```

样音通过 `POST /tts`（`reference_wav` 指向混合文件，`speed=1.0`）生成。
