# 声音意境增强模块 · 详细方案

> 起草日期：2026-11-04
> 状态：`DESIGN`（仅方案，未实现；本文件不改变任何代码或配置）
> 前置事实：本机实测，见 §2。凡是与实测不符的外部建议，一律以实测为准并注明差异。

## 0. 一页结论

| 建议 | 判定 | 处理 |
|---|---|---|
| 用优质参考音频做 zero-shot 克隆（方案 A） | **方向可行，但接口写错了** | 本机没有 `/inference_zero_shot`；zero-shot 走 `/tts/upload`（multipart）或 `/tts` + `prompt_wav`，见 §2.2 |
| 用 `aecho` 做"板式混响" | **不成立** | `aecho` 是离散回声，不是混响；本机 FFmpeg 8.1 无 freeverb `reverb` 滤镜，真正的空间卷积要用 `afir` + 脉冲响应，见 §4.2 |
| 响度统一到 -18 LUFS | **与项目规范冲突** | 项目规范是 **对白 -16 LUFS / TP ≤ -1.5 dBTP**（`docs/CONTENT_SPEC.md`），且 `r3_build` 已在总线做过一次 `loudnorm`，见 §4.5 |
| 侧链避让 3 dB | **配置里有、代码里没有** | 用 `sidechaincompress` 实现，见 §4.4 |
| 混响挂在每句上 | **会错** | 混响必须挂在**拼接后的整段对白**上，否则气口与尾音互相污染，见 §3.2 |
| 克隆"名家吟诵" | **有授权风险** | 真人声音克隆涉及人格权/表演者权；只能使用自录、合成或明确授权的参考音频，见 §6 |

一句话：**这套方案的两层拆分是对的，落地细节几乎全要按本机事实重写。** 本文给出可直接开工的版本。

## 1. 目标与边界

**目标**：让成片配音"不像贴耳念稿"，具备江面空间深度与极弱的环境与国乐衬托，同时不增加任何显存占用。

**边界**：
- 只动音频。不动画面、不动 ComfyUI、不动视频合成链路。
- CPU only：CosyVoice 服务是 CPU，FFmpeg 是 CPU，**零显存**。
- 不新增 Python 依赖（`httpx` 已在 `pyproject.toml`）。
- 不引入新的音频模型（不做歌声合成、不做 AI 混响）。

## 2. 本机实测事实（方案的前提）

### 2.1 CosyVoice 运行时

| 项 | 实测 |
|---|---|
| 服务 | `D:\AI\CosyVoice-Runtime\api_server.py`，FastAPI，`127.0.0.1:50000` |
| 端点 | **只有** `/health`、`/speakers`、`/tts`、`/tts/upload`。**没有 `/inference_zero_shot`** |
| `/tts` 的两种模式 | 带 `speaker` → SFT 预置音色；不带 `speaker` → 走 `prompt_wav` + `prompt_text` 的 zero-shot |
| `/tts/upload` | multipart：`text` + 可选 `prompt_wav` 文件 + `prompt_text` + `speed`；上传的 wav 落到 `assets/` 临时文件，用完即删 |
| `/health` | 返回 `modes: ["sft", "zero_shot"]`、`sample_rate`、`speakers`、`stats` |
| 已装模型 | `CosyVoice-300M-SFT`（当前 SFT 启动脚本用它）、`CosyVoice2-0.5B` |
| 启动脚本 | `start_cosyvoice_sft.bat`（SFT）与 `start_cosyvoice.bat`（zero-shot）**互斥占用 50000** |
| 现有项目用法 | `src/drama_studio/voice/tts.py` 默认 zero-shot（CosyVoice2-0.5B），SFT 显式可选；`config/audio.yaml` `tts.mode: zero_shot` |

**结论**：方案 A 不需要新服务，只需要换调用方式；但要不要切到 `CosyVoice2-0.5B` 是独立决策（见 §5.1）。

### 2.2 FFmpeg 音频滤镜（8.1-full_build）

| 滤镜 | 是否可用 | 用途 |
|---|---|---|
| `afir` | ✅ | 与外置脉冲响应做**卷积混响**（真正的空间感） |
| `aiir` | ✅ | 系数式 IIR 滤波 |
| `sidechaincompress` | ✅ | 侧链压缩（环境/BGM 避让人声） |
| `loudnorm` | ✅ | EBU R128 |
| `aecho` | ✅ | 离散回声，**不是混响** |
| `firequalizer` | ✅ | 精细 EQ（去齿音/低切） |
| `reverb`（freeverb） | ❌ 本构建没有 | — |

### 2.3 现有音频链路

| 项 | 现状 |
|---|---|
| `config/audio.yaml` | `tts.mode: zero_shot`、`loudness.dialogue_lufs: -16.0`、`bgm_lufs: -26.0`、`true_peak_db: -1.5` |
| 朗读模式 | `narration` / `recitation`(0.92) / `classical_recitation`(0.82)；`chant` 明确不支持 |
| `scripts/r3_build.py` | 逐句 `adelay` → `amix(normalize=0)` → `alimiter` → `loudnorm(I=-16:TP=-1.5:LRA=11)` → `apad` → 单声道 48 kHz |
| 音频资产 | **`assets/audio/` 不存在**：没有环境音、没有 BGM、没有 IR |
| 授权状态 | `docs/ROADMAP.md` R3-D：BGM/音效与商用授权均为 `NOT_RUN` |

## 3. 架构

### 3.1 两层，但不是一个类

外部建议把"克隆"和"混音"塞进同一个 `SoundscapeMaster`。这会把生成与母带耦合在一起，也无法复用现有 `tts.py` 的发音层与 QA。改为两个模块：

```
文本（含破折号气口）
   │
   ▼
voice/tts.py            ← 已有：四层文本、发音词典、朗读模式、per-line QA
   │  （新增 zero-shot 分支）
   ▼
voice/zeroshot.py       ← 新：把 prompt 音频送到 /tts/upload，产出干音
   │
   ▼  逐句 WAV + audio_manifest.json（已有格式）
   │
   ▼
r3_build.py 的音频段   ← 已有：adelay + amix + alimiter（不动）
   │
   ▼  拼接后的整段对白（单声道 48 kHz）
   │
   ▼
voice/soundscape.py     ← 新：混响 + 环境 + 垫乐 + 侧链 + 响度（两遍法）
   │
   ▼
史诗母带 → 回到 r3_build 的 -map 音频输入
```

### 3.2 为什么混响必须挂在整段上

- 逐句加混响：每句的尾音在句间静默期被截断，气口变成"每句重新起一次房间"，听感像换房间。
- 逐句加混响还会让 `adelay` 之后的混响尾巴落在下一句的起始处，与下一句重叠，无法用统一参数控制。
- 整段加混响：房间只有一个，气口长度由脚本决定，混响自然延续。

**唯一例外**：如果将来做"画外音/旁白"与"角色对白"分轨，则每轨各自整段处理，再在总线上混合。

## 4. 合成层设计（方案 B，重写版）

### 4.1 输入

| 轨 | 来源 | 要求 |
|---|---|---|
| 对白 | `r3_build` 的 `mixed.wav`（已对齐到视频时间轴、单声道 48 kHz） | 必须**未做 loudnorm**，响度留到本模块统一做 |
| 环境 | `assets/audio/ambience/*.wav` | 无缝循环 ≥30 s，48 kHz，无版权负担 |
| 垫乐 | `assets/audio/bgm/*.wav` | 同上；**授权未落实前不得进入成片** |
| IR | `assets/audio/ir/*.wav`（或由 `make_ir` 生成的合成 IR） | 见 §4.2 |

### 4.2 "板式混响"的正确做法

外部建议的 `aecho=0.8:0.7:60|120:0.25|0.15` 是两次离散回声（60 ms、120 ms），听感是"山谷回声"或"双声"，不是厅堂/水榭的空间感，而且会在 60/120 ms 处产生可辨识的梳状染色。

正确做法：`afir` 与脉冲响应卷积。

```text
[vocal_dry] asplit [v_dry][v_conv]
[v_conv] afir=ir_gain=<g>:ir_path?  ← 本构建支持从文件读 IR
[v_dry][v_conv] amix=inputs=2:normalize=0:weights='0.85 0.18' [vocal_space]
```

要点：
- **wet 18% 靠显式权重实现**：`amix` 默认 `normalize=1` 会把权重归一化，`weights` 的绝对值没有意义；必须 `normalize=0` 并自行保证总和不削波（后面有 limiter）。
- IR 取 0.6–1.2 s 的衰减，太长会把字糊掉。
- 若暂时没有 IR：先用合成 IR（指数衰减噪声 + 少量早期反射），由脚本生成并登记哈希；**不要退回 `aecho` 冒充混响**。

### 4.3 人声处理链

```text
[vocal] highpass=f=80,                       # 去低频轰鸣
        firequalizer=gain_entry='entry(6500,-2);entry(8000,-3)',  # 轻去齿音
        alimiter=limit=0.95,
        afir 混响（§4.2）,
        [vocal_space]
```

齿音处理用 EQ 而不是 `lowpass=f=7500`：整条 7.5 kHz 以上切掉会让"诗"字彻底失去空气感，过度发闷。

### 4.4 环境与垫乐：音量 + 侧链避让

```text
[ambience] volume=-24dB, highpass=f=120, lowpass=f=4000,   # 只留水面与风
           [amb_loop]
[bgm]      volume=-22dB, [bgm_loop]
[bgm_loop][vocal_space] sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400:makeup=1 [bgm_ducked]
[amb_loop][vocal_space] sidechaincompress=threshold=0.05:ratio=3:attack=30:release=500:makeup=1 [amb_ducked]
```

侧链的"压低 3 dB"不是靠一个数字参数，而是 `threshold/ratio` 的实际结果；因此验收要**实测**：人声段与环境段的能量差必须落在 2.5–3.5 dB 之间。

### 4.5 响度：只有一次，两遍法

现状冲突：`r3_build` 已在对白总线上做 `loudnorm(I=-16:TP=-1.5:LRA=11)`；若声景模块再做一次，会让两次归一化互相打架。

处理：
1. `r3_build` 的音频段改为**不做** loudnorm，只做对齐与混音（`amix(normalize=0)` + `alimiter`）。
2. 声景模块用 **两遍法**：第一遍 `loudnorm=...:print_format=json` 测量，第二遍用测得值做线性归一化。
3. 目标值取项目规范：**对白 -16 LUFS、TP ≤ -1.5 dBTP**（不是外部建议的 -18）。若将来对齐平台，改 `config/audio.yaml` 一处。
4. 若 `soundscape.enabled: false`，则由 `r3_build` 退回原来的单遍 loudnorm，行为与今天完全一致（可回滚）。

### 4.6 输出

- 单声道 48 kHz `pcm_s16le`（与现有 `mixed.wav` 一致），时长与视频对齐。
- 同时输出 `soundscape_report.json`：IR 哈希、各轨增益、实测 LUFS/TP、侧链实测压降、口径与参数。

## 5. 生成层设计（方案 A，修正版）

### 5.1 接口

不存在 `/inference_zero_shot`。两种合法调用：

| 方式 | 请求 | 适用 |
|---|---|---|
| A1 | `POST /tts` JSON：`{"text": "...", "prompt_wav": "<runtime 内路径>", "prompt_text": "...", "speed": 0.82}` | 参考音频已放在 `D:\AI\CosyVoice-Runtime\assets\` 下 |
| A2 | `POST /tts/upload` multipart：`text` + `prompt_wav` 文件 + `prompt_text` + `speed` | **推荐**：项目侧持有参考音频，不必往 runtime 目录里放东西（符合"不修改别人环境"的不变量） |

A2 的代价是每次请求上传一次 wav（3–8 s，几百 KB），可在进程内缓存同一份参考音。

### 5.2 与现有 `tts.py` 的关系

`tts.py` 已有四层文本（source/display/tts/acoustic）、发音词典、朗读模式、per-line QA。zero-shot 分支只在**最后一步**替换"SFT 说话人"：

```python
# 伪代码：改动点最小
def _synthesize_line(text, mode, speaker, prompt):
    if prompt is None:
        return _post_sft(text, speaker, speed)      # 现状
    return _post_zero_shot(text, prompt, speed)     # 新增，A2
```

发音层、气口、QA、manifest 全部沿用。**不得**为 zero-shot 另建一套文本处理。

### 5.3 模型选择（独立决策）

| 选项 | 现装 | 优点 | 风险 |
|---|---|---|---|
| `CosyVoice-300M-SFT`（现状） | ✅ 正在跑 | 已验证「中文男」进过成片；内存小 | zero-shot 相似度弱，克隆效果一般 |
| `CosyVoice2-0.5B` | ✅ 已装 | zero-shot 明显更好 | 需换启动脚本；与「谁启动谁停止 / 50000 单实例」冲突，必须先停 SFT；耗时未测 |

建议：**先只用 SFT 的 zero-shot 跑一遍**，听是否已达标；不达标再评估切 0.5B，并把切换做成配置项而不是改脚本。

### 5.4 参考音频的硬要求

| 项 | 要求 |
|---|---|
| 时长 | 3–8 s；太短克隆不稳，太长拖慢推理 |
| 内容 | 与 `prompt_text` **逐字对齐**（多一个字都会跑偏） |
| 质量 | 无 BGM、无混响、无底噪、无爆音；48 kHz 或原生采样保留 |
| 授权 | 见 §6 |

## 6. 授权与合规（外部建议完全没提，但它是**阻塞项**）

| 资产 | 风险 | 结论 |
|---|---|---|
| 参考音频（用于声音克隆） | 真人声音的人格权/表演者权。克隆"名家吟诵"= 使用特定自然人的声音特征 | **不得**使用未授权的第三方诵读录音。只接受：① 自有录制；② 合成音（例如自建 TTS 生成后当参考）；③ 明确书面授权并登记 |
| 环境音（水声/夜风） | 多为唱片库素材 | 需可商用授权；优先使用 CC0 或自录 |
| 国风垫乐（古琴） | 音乐版权最严 | 授权未落实前**不进成片**；可用自生成/公版演奏 |
| 脉冲响应（IR） | 商业 IR 库通常禁商用 | 优先用脚本生成的合成 IR（无版权负担） |

所有资产必须登记到 `docs/ASSET_AND_LICENSE_REGISTRY.md`，并在 `soundscape_report.json` 里记录哈希——与项目现有资产规则一致。

## 7. 配置（在现有 `config/audio.yaml` 上扩展，不另起文件）

```yaml
# 现有字段保留：tts.mode / speakers / loudness / narration_modes
tts:
  mode: sft
  zero_shot:                      # 新增：mode: zero_shot 时生效
    enabled: false                # 默认关闭，切之前先做 §8 的单句验收
    prompt_audio: "assets/audio/prompts/prompt_01.wav"
    prompt_text: ""               # 必须与参考音频逐字一致
    speed: 0.82                   # 与 classical_recitation 一致，不另立一套节奏
    upload: true                  # true=走 /tts/upload；false=走 /tts + runtime 内路径

soundscape:                       # 新增
  enabled: false                  # 默认关闭：没有资产与授权时不得启用
  ir:
    path: "assets/audio/ir/synthetic_hall_0.9s.wav"
    wet: 0.18                     # amix normalize=0 下的显式权重
    dry: 0.85
  voice_eq:
    highpass_hz: 80
    deess: [{hz: 6500, gain: -2}, {hz: 8000, gain: -3}]
  ambience:
    track: "assets/audio/ambience/night_river_loop.wav"
    gain_db: -24.0
    highpass_hz: 120
    lowpass_hz: 4000
  bgm:
    track: ""                     # 授权落实前留空
    gain_db: -26.0                # 与 loudness.bgm_lufs 对齐
  ducking:
    enabled: true
    ambience: {threshold: 0.05, ratio: 3, attack_ms: 30, release_ms: 500}
    bgm:      {threshold: 0.05, ratio: 4, attack_ms: 20, release_ms: 400}
  loudness:
    two_pass: true
    target_lufs: -16.0            # 取自 loudness.dialogue_lufs，不重复定义
```

## 8. 验收（可执行、可复核）

| 编号 | 项 | 判据 |
|---|---|---|
| E1 | 单句试听 | `logs/test_soundscape.wav`，1 句（"春江潮水连海平，海上明月共潮生。"），48 kHz |
| E2 | 响度 | 两遍法实测 **-16.0 ± 0.5 LUFS**，TP ≤ -1.5 dBTP |
| E3 | 侧链 | 人声段 vs 静默段的 BGM/环境能量差 **2.5–3.5 dB** |
| E4 | 混响 | 无 60/120 ms 梳状回声（对 impulse 响应做 FFT 或听感确认；若用 `afir` 应无离散回声） |
| E5 | 可回滚 | `soundscape.enabled: false` 时输出与当前 `r3_build` **逐字节一致**（同参数下） |
| E6 | 资源 | 全程 CPU；CosyVoice 与 FFmpeg 峰值内存记录；结束后 50000 端口释放 |
| E7 | 授权 | 参考音频/环境/垫乐/IR 四项均在许可清单内，否则 `enabled` 必须为 false |

## 9. 风险与未知

| 编号 | 风险 | 处理 |
|---|---|---|
| R1 | SFT 300M 的 zero-shot 相似度可能达不到"名家"级 | 先用 E1 试听；不达标再评估 0.5B，且切换要停机重启 50000 |
| R2 | 参考音频授权拿不到 | 用自有录制或合成参考；拿不到就不启用 zero_shot |
| R3 | 环境音/垫乐无授权 → 整条 B 层不可上线 | 先只做"混响 + EQ + 响度"（不含环境与垫乐），这部分零版权风险 |
| R4 | `afir` 对 CPU 的开销 | 6 s 对白 × 1 s IR 卷积在 CPU 上可接受；需实测 |
| R5 | 两遍 loudnorm 与 `apad` 的顺序 | 先 `apad` 到视频时长再测，否则尾段静音会把 LUFS 拉低 |
| R6 | 侧链压缩对人声本身的影响 | 侧链只作用于环境/BGM 轨，人声是 key，不被压缩 |

## 10. 分阶段实施（建议）

| 阶段 | 内容 | 依赖 | 回滚 |
|---|---|---|---|
| S1 | **仅 B 层不含资产**：EQ + `afir` 混响 + 两遍 loudnorm，接进 `r3_build` | 合成 IR（脚本生成） | `soundscape.enabled: false` |
| S2 | 加入环境音 + 侧链避让 | 一处可商用环境音资产 | 同上 |
| S3 | 加入 BGM | 一处授权垫乐 | 同上 |
| S4 | zero-shot 克隆（**先单句验收**） | 合法参考音频 | `tts.mode: zero_shot` 为默认；显式 SFT 用 `--tts-mode sft` + `-Model sft` |

**顺序理由**：S1 与 S3 的授权风险为零，能立刻改善"发干发飘"；zero-shot 是收益最大但风险（授权、相似度、停机）也最大的一步，放最后。

## 11. 与外部建议的逐条差异

| 外部建议 | 本方案 | 原因 |
|---|---|---|
| `/inference_zero_shot` | `/tts/upload`（multipart） | 本机运行时没有前者 |
| `aecho` 当板式混响 | `afir` + IR | `aecho` 是离散回声 |
| -18 LUFS | -16 LUFS / TP -1.5 | 项目规范 `CONTENT_SPEC.md`，且现有链路已按 -16 实现 |
| 湿声 18% 用 `amix weights` | `amix=normalize=0:weights='0.85 0.18'` | 默认 normalize 会重标定权重 |
| 侧链写在配置里 | `sidechaincompress` 实现并实测压降 | 配置不等于实现 |
| 混响逐句 | 混响整段 | 气口与尾音会互相污染 |
| 一个 `SoundscapeMaster` 类管两件事 | 两个模块：`zeroshot.py` + `soundscape.py` | 生成与母带职责不同，且要复用现有 `tts.py` |
| `lowpass=f=7500` 去齿音 | `firequalizer` 定点衰减 | 整条切高频会让诗词失去空气感 |
| `speed: 0.88` | 沿用 `classical_recitation: 0.82` | 已有同一机制，不应出现两套节奏 |

## 12. 交付物清单（实施后）

| 文件 | 说明 |
|---|---|
| `src/drama_studio/voice/zeroshot.py` | `/tts/upload` 封装 + 参考音频缓存 |
| `src/drama_studio/voice/soundscape.py` | `afir` + 侧链 + 两遍 loudnorm + 报告 |
| `scripts/make_ir.py` | 生成合成 IR（确定性、无版权） |
| `config/audio.yaml` | 新增 `tts.zero_shot` 与 `soundscape` 段 |
| `scripts/r3_build.py` | 音频段拆分：混音 → 声景 → 单次响度 |
| `tests/test_soundscape.py` | 滤镜图字符串、权重、两遍法、回滚一致性 |
| `docs/ASSET_AND_LICENSE_REGISTRY.md` | 四类音频资产登记与许可状态 |

## 13. 现在就能做的最小一步

在不引入任何资产、不碰授权的条件下：**S1 的"EQ + 合成 IR 混响 + 两遍 loudnorm"**。它解决的是"发干发飘"最直接的那一半，且完全可回滚。

zero-shot 克隆与 BGM 都在拿到合法素材之前保持 `enabled: false`——这既是工程顺序，也是合规要求。

## 14. S1 实施与实测修正（2026-11-04）

S1（不含任何外部音频资产的那一层）已经落地：`scripts/make_ir.py` + `src/drama_studio/voice/soundscape.py`
+ `config/audio.yaml` 的 `soundscape` 段 + `scripts/r3_build.py` 接线。`enabled: false` 时输出与改动前一致。

实施中推翻了方案里的两处设计：

### 14.1 `afir` 卷积混响在本机不可用（阻塞，已实测）

本机 FFmpeg 8.1-full_build 的 `afir` **对任何输入形式都输出数字静音**。实测矩阵：

| 输入形式 | 结果 |
|---|---|
| 单声道 IR（wav s16） | 静音（-inf） |
| 立体声 IR | 静音 |
| float32 IR | 静音 |
| 单位脉冲 IR + 正弦输入 | 静音 |
| `precision=double` / `irfmt=mono` / `length=0.9` / `minp=maxp=64` / `nbirs=1:ir=0` | 全部静音 |

`-v verbose` 显示两条输入流都已正确接到 `afir`，没有任何告警。结论：这是该构建的缺陷，不是接法问题。

因此默认实现改为 **`early_reflections`**：8 个密集衰减抽头（11–173 ms）的 `aecho`。
它在配置里被明确标注为"早期反射模型，**不是卷积**"，`reverb.method` 可切回 `convolution`（换到能用的 FFmpeg 构建后再启用）。

### 14.2 -16 LUFS 在这份素材上需要压缩

实测（`experiments/m7_final/ink/audio/line_01.wav`）：

| 阶段 | LUFS | True Peak |
|---|---|---|
| 处理前 | -22.44 | -3.34 |
| EQ + 早期反射 + 两遍响度 | **-18.26** | -1.50 |
| 再加 `acompressor -20dB / 2.5:1` | **-16.54** | -1.50 |

原因：这份人声的波峰因数比 -16 LUFS @ -1.5 dBTP 所允许的高约 4.6 dB，任何归一化器都只能靠限幅到达目标。
`loudnorm` 的 linear/dynamic 两种模式都止步于 -18.26。

因此新增 `soundscape.voice_dynamics.enabled`（默认 false）。**压缩会改变音色，属听感决策，不由脚本替人做。**

### 14.3 与方案的三处差异

| 方案 | 实现 | 原因 |
|---|---|---|
| `afir` 卷积混响 | 默认早期反射，`convolution` 保留但标记阻塞 | §14.1 |
| 湿声靠 `amix weights` | `aecho` 自带的 in/out gain | `amix` 默认 normalize 会重标定权重 |
| 一次 `loudnorm` | 两遍法 + 可选压缩 | 单遍不准；-16 需要压缩 |

验收：`logs/test_soundscape_0.wav`（无压缩，-18.26）、`logs/test_soundscape_1.wav`（有压缩，-16.54）。
