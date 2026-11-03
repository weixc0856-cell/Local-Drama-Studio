# S3-A.1 CosyVoice 本地男女声音色试听报告

> 执行日期：2026-11-03
> 范围：仅本地 CosyVoice SFT；未调用云端 API、未开户、未购买、未下载新模型、未修改生产脚本。
> 基线：HEAD `ad921ed`；R3-D 未执行。
> 后续：S3-A.3 的人工试听结论与默认方案见 [R3D_VOICE_PROSODY_REPORT.md](R3D_VOICE_PROSODY_REPORT.md)；本文件保留 S3-A.1 技术记录。

## 1. 技术结果

| 项 | 中文男（基线） | 中文女（候选） |
|---|---|---|
| speaker ID | `中文男` | `中文女` |
| 模型 | CosyVoice-300M-SFT | 同左 |
| 运行方式 | 本地 CPU，12 threads | 同左 |
| API | `POST /tts` | 同左 |
| 参数 | `speed=1.0`，`text_frontend=true` | 同左 |
| 原始采样率 | 22,050 Hz / mono / PCM s16le | 同左 |
| 原始时长 | 24.335 s | 20.155 s |
| 原始字节 | 1,073,196 | 888,876 |
| 生成墙钟 | 189.04 s | 139.58 s |
| `X-Synth-Seconds` | 189.02 | 139.57 |
| 响度副本 mean / max | -17.9 dB / -1.5 dB | -16.8 dB / -1.5 dB |
| ≥0.3 s 停顿数（silencedetect -35dB:0.3s） | 12 | 1 |
| 停顿总时长 | 5.171 s | 0.495 s |

同一文本：6 句《春江花月夜》，96 字符（84 汉字 + 标点），与 S3-A 准备文本一致。

## 2. 客观观察

1. **中文女可正常调用**：`spk2info.pt` 与 `/health` 均列出 `中文女`，SFT 接口成功返回 WAV。
2. **女声更短、更快**：20.155 s vs 24.335 s；按 96 字符计算，女声约 4.76 字符/s，男声约 3.95 字符/s。
3. **停顿行为差异明显**：男声检测到 12 处 ≥0.3 s 停顿（总计 5.17 s），女声仅 1 处（0.50 s）。
   - 这可能意味着女声对换行/标点的停顿处理更弱，句子更连读。
   - 也可能只是该音色的韵律风格；**必须人工试听判断是否可接受**。
4. **响度副本已按 `loudnorm I=-16` 生成**：男 -17.9 dB mean，女 -16.8 dB mean；峰值均 -1.5 dB。表中 mean/max 来自 `volumedetect`，是电平参考，**不是 Integrated LUFS / True Peak 测量**。原始文件未做破坏性处理。
5. 女声并非“天然更好”；本次只证明可生成，未证明更适合本项目。

## 3. ASR 抽查（仅参考）

使用已缓存的 Whisper base 本地转写（未下载新模型）：

- `experiments/r3d/voice/asr_male.txt`
- `experiments/r3d/voice/asr_female.txt`

两段转写都出现较多古典诗词识别错误，且女声转写缺少停顿/标点。Whisper base 对文言/古典诗词不可靠，**不能据此判定 TTS 错读或吞字**；它只能作为“需要人工听”的提示。

## 4. 授权核验状态

| 项 | 状态 |
|---|---|
| CosyVoice 代码许可证 | `Apache-2.0`（本地 `app/LICENSE`） |
| 模型权重许可证 | `UNVERIFIED` |
| 预置 speaker「中文男/中文女」使用条件 | `UNVERIFIED` |
| 生成音频商用权 | `UNVERIFIED` |

官方 GitHub README 声明“仅供学术目的演示技术能力”；没有单独确认模型权重或预置音色的商用条款。
**不得**因代码 Apache-2.0 推断模型/音色/生成音频可商用。发布前必须单独解决授权。

## 5. 试听文件

| 文件 | 用途 |
|---|---|
| [male_raw.wav](experiments/r3d/voice/male_raw.wav) | 男声原始 WAV（22.05 kHz，未改） |
| [female_raw.wav](experiments/r3d/voice/female_raw.wav) | 女声原始 WAV（22.05 kHz，未改） |
| [male_48k.wav](experiments/r3d/voice/male_48k.wav) / [female_48k.wav](experiments/r3d/voice/female_48k.wav) | 48 kHz mono 副本 |
| [male_norm.wav](experiments/r3d/voice/male_norm.wav) / [female_norm.wav](experiments/r3d/voice/female_norm.wav) | 响度统一副本（-16 LUFS 目标） |
| [male_then_female.wav](experiments/r3d/voice/male_then_female.wav) | 男→女连续对比 |
| [female_then_male.wav](experiments/r3d/voice/female_then_male.wav) | 女→男连续对比 |
| [blind_A.wav](experiments/r3d/voice/blind_A.wav) / [blind_B.wav](experiments/r3d/voice/blind_B.wav) | 盲听文件；映射在 `blind_map.json` |
| [audition_manifest.json](experiments/r3d/voice/audition_manifest.json) | 全部参数、哈希、时长、停顿、授权标记 |
| [resource_usage.json](experiments/r3d/voice/resource_usage.json) | 本地资源占用 |

## 6. 本地资源占用（近似）

| 项 | 值 |
|---|---|
| 模型加载 | 25.9 s |
| 进程工作集（加载后/两次合成后） | 3.83 → 3.86 GiB |
| 系统可用内存（前/后） | 32.3 → 32.7 GiB |
| 进程 CPU 时间（前/后） | 23.84 → 5596.8 CPU-s |
| 两次请求墙钟合计 | 328.62 s |

CPU 计数器包含库线程，未采样峰值工作集；以上为近似占用，不作为峰值承诺。

## 7. 人工试听与决策（S3-A.3 已完成）

以下保留 S3-A.1 当时的试听建议；实际决策结果见 [R3D_VOICE_PROSODY_REPORT.md](R3D_VOICE_PROSODY_REPORT.md) §0。

建议按以下顺序：

1. 先听 `blind_A.wav` / `blind_B.wav`，不看 `blind_map.json`。
2. 按准备文档的 8 项指标打分：自然度、咬字、停顿、情绪、韵律、稳定性、授权清晰度、成本。
3. 再听 `male_then_female.wav` / `female_then_male.wav` 确认差异。
4. 决定中文女的停顿/连读是否可接受；若不接受，下一步应讨论“逐句合成 + 手动停顿”或换音色，而不是继续调同一段。
5. 在发布前单独解决模型/音色/生成音频授权；技术试听结果不构成商用许可。

## 8. 工作区状态

```text
HEAD: ad921ed
未提交新增：
  docs/R3D_VOICE_SELECTION_PREP.md
  docs/R3D_VOICE_AUDITION_REPORT.md
  experiments/r3d/
```

- 未修改 `scripts/`、`workflows/`、模型或 R3 男声资产。
- 未提交 Git；未调用云端 API；未购买；未下载新模型。
- CosyVoice 服务已在完成后停止，50000 端口关闭。
