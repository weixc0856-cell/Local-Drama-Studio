# 影视化制作指南（Script-to-Film）

> 状态：`DECISION` / 2026-11-06 立项。
> 定位：本文件是制作方法论与数据契约的唯一入口；技术选型见 `TECH_STACK.md`，需求见 `PRD.md`。
> 结论先行：当前缺的不是更强的图像/视频模型，而是**图像生成与视频生成之间的影视制作层**。本文件定义这一层。

## 1. 为什么当前产物像 PPT

现有链路是「FLUX 出图 → Wan 加运动 → 拼接」。每个镜头独立生成，模型不知道上一个镜头发生了什么，因此出现：

- 镜头之间没有空间关系，观众看到的是四张图，不是一个世界。
- 人物、服装、光线、运动方向在镜头间漂移。
- 只有数字放大，没有真正的摄影机位移与视差。
- 旁白与画面各走各的时间轴。

电影感来自**被设计的镜头关系**，不是单帧质量或转场数量。

## 2. 制作等级

| 项目 | 5–15 秒 | 30–60 秒 | 2–5 分钟 |
|---|---|---|---|
| 剧本 | 单一意境 | 完整叙事 | 多章节叙事 |
| 镜头 | 1–3 | 6–12 | 20–50 |
| 关键帧 | 1–3 | 6–12 | 20–50 |
| 角色设定 | 可简化 | 必须 | 必须 |
| 场景资产 | 1 个 | 2–4 个 | 多个 |
| 配音 | 单段 | 分句 | 分段、多角色可选 |
| 连续性管理 | 简单 | 必须 | 严格 |

镜头数是规划区间，不是硬限制。**镜头 ≠ 生成次数**：一个连续动作可以拆成 3 个镜头分别生成，但必须共享同一场景、同一人物状态与同一光线。

## 3. 十个阶段

| # | 阶段 | 输入 | 输出 | 负责模块（规划） |
|---|---|---|---|---|
| 01 | 原始素材 | 诗词/主题/背景/时长 | `source.json` | 内容包 |
| 02 | 编剧 | 原诗、文学分析 | `screenplay.json` + `narration.json` | `film/scriptwriter` |
| 03 | 导演分镜 | 剧本、视觉圣经 | `storyboard.json` | `film/storyboard` |
| 04 | 视觉设计 | 分镜、视觉圣经 | `visual_bible.yaml` + 关键帧 | `aesthetics` + ComfyUI |
| 05 | 声音设计 | 朗诵稿 | 逐句 WAV + manifest | `voice/`（VoxCPM2） |
| 06 | 镜头动画 | 关键帧、运动提示词 | 镜头 MP4 | `production` + Wan |
| 07 | 连续性检查 | 分镜、关键帧、镜头 | `continuity_report.json` | `film/continuity` |
| 08 | 后期合成 | 镜头、音频、字幕 | `timeline.json` + 成片 | `film/timeline` + FFmpeg |
| 09 | 质量与交付 | 成片、清单 | `qc_report.json` | `quality` + 人工 |
| 10 | 成片 | — | 9:16 / 16:9 成片 | — |

**架构原则：剧本、分镜、声音、画面和剪辑时间轴共享同一份项目数据。** 任何环节不得各自维护一份「自己的理解」。

## 4. 数据契约

项目目录：

```
projects/<project_id>/
├── project.json          # 项目元数据、画幅、目标时长、章节
├── source.json           # 原始诗词/素材与来源
├── screenplay.json       # 故事主线、情绪曲线
├── narration.json        # 逐句朗诵稿（可进 TTS）
├── visual_bible.yaml     # 美术方向、人物、环境、镜头语言
├── storyboard.json       # 镜头表（唯一镜头事实源）
├── timeline.json         # 剪辑与声音时间轴
├── assets/
│   ├── characters/  environments/  keyframes/  audio/  videos/
├── shots/                # 每镜头的生成参数与产物
├── renders/              # 每次构建写新目录，不覆盖
└── qc/                   # 连续性、质量、授权报告
```

### 4.1 `narration.json`

```json
{
  "project_id": "deng_guan_que_lou",
  "language": "zh-CN",
  "segments": [
    {"id": "N001", "text": "登鹳雀楼。", "emotion": "solemn",
     "delivery": "calm", "speed": 0.9, "pause_after_ms": 1200}
  ]
}
```

`emotion` / `delivery` / `speed` 是本系统的内部控制字段；是否映射到模型指令由适配层决定，不得假设模型原生支持。

### 4.2 `storyboard.json` 的镜头结构

```json
{
  "shot_id": "S04",
  "scene_id": "SC02",
  "narration_ids": ["N002"],
  "duration_seconds": 6.0,
  "shot_size": "ws",
  "camera": {"move": "tracking", "angle": "eye", "lens_mm": 35, "dof": "deep"},
  "layers": {
    "foreground": "tree branches, softly blurred",
    "midground": "mountain ridge",
    "background": "sunset sky, atmospheric haze"
  },
  "motion": {"primary": "camera_lateral", "secondary": ["cloud_drift", "branch_sway"]},
  "continuity": {
    "previous_shot": "S03", "next_shot": "S05",
    "lighting": "golden_hour", "environment": "SC02",
    "character_state": "poet_on_tower", "motion_direction": "left_to_right",
    "match_cut_to": null
  },
  "generation": {"image_model": "flux3", "video_model": "wan2.2_ti2v_5b", "status": "planned"}
}
```

规则：

- `shot_id` 必须匹配 `S\d{2,3}`，唯一且连续。
- `narration_ids` 必须能在 `narration.json` 中解析。
- `duration_seconds` 是**剪辑目标时长**，不保证模型原始产物等长。
- `continuity.previous_shot/next_shot` 必须与镜头顺序一致；首镜无前、末镜无后。
- 同一 `scene_id` 内的 `lighting` 与 `environment` 必须一致，除非显式换场。

## 5. 摄影语言

### 5.1 景别

| 代码 | 名称 | 用途 |
|---|---|---|
| `ews` | 大远景 | 交代世界观、山河、空间尺度 |
| `ws` | 远景 | 环境与主体的关系 |
| `fs` | 全景 | 人物全身与动作 |
| `ms` | 中景 | 人物与环境的关系 |
| `mcu` | 中近景 | 表情与动作细节 |
| `cu` | 近景 | 情绪 |
| `ecu` | 特写 | 眼神、手、器物 |
| `ots` | 过肩 | 把观众放进人物视野 |

叙事顺序常见规律：环境 → 人物 → 人物视角 → 情绪 → 空间扩展 → 主题表达。

### 5.2 运镜

| 代码 | 名称 | 用途 |
|---|---|---|
| `static` | 固定 | 留白、庄重 |
| `dolly_in` | 推 | 强调主体、增强沉浸 |
| `dolly_out` | 拉 | 展示空间、释放情绪 |
| `tracking` | 跟拍 | 跟随人物/物体 |
| `pan` | 摇 | 展示场景、跟随视线 |
| `tilt` | 俯仰 | 建筑高度、天空 |
| `crane` | 升降 | 局部到宏观 |
| `orbit` | 环绕 | 主体与空间关系 |
| `handheld` | 手持 | 真实感与临场感 |

**关键区分**：提示词里的 `camera slowly zooms in` 不等于电影推镜头。真正的 Dolly In 是摄影机在空间中移动，产生前景/中景/背景的视差。只有数字放大而没有视差的镜头，不得标记为电影级运镜。

### 5.3 空间层次

每个场景至少拆三层：

- 前景：树枝、栏杆、花草、云雾、衣袖。
- 中景：人物、建筑、船只。
- 背景：山脉、太阳、河流、天空。

景深（对焦范围）、焦外虚化、大气透视、视差是四件不同的事，组合起来才有空间感。

### 5.4 镜头时长（默认区间）

| 类型 | 时长 |
|---|---|
| 环境建立 | 5–8 s |
| 人物动作 | 3–6 s |
| 情绪特写 | 3–5 s |
| 大场景 | 6–10 s |
| 运动衔接 | 4–6 s |

## 6. 连续性

### 6.1 本机能力边界（实测约束）

- 原生 `WanFirstLastFrameToVideo` 主要在 Wan2.2 **14B** 上验证；本机是 **TI2V 5B**，不能假设首尾帧节点可用。
- 因此 Phase 1 的连续性依靠：**关键帧继承 + 匹配剪辑 + 剪辑规则**，而不是模型级首尾帧锁定。
- 社区的多镜头方案（如 `Wan-SVI2Pro-FLF`、`VideoChunkTools`）依赖额外节点与 14B 权重，只能作为 Phase 2 的候选，不进入当前依赖。

### 6.2 必存字段

每个镜头保存：`scene_id`、`character_state`、`camera_position`、`camera_direction`、`lighting`、`motion_direction`、`start_frame`、`end_frame`、`match_cut_to`。

### 6.3 检查规则（硬规则）

1. 相邻镜头的 `lighting` 不一致且未换场 → 失败。
2. 同一场景的 `environment` 不一致 → 失败。
3. 相邻镜头的 `motion_direction` 相反且 `transition_in != cut` 未声明 → 警告，需人工确认。
4. 人物 `character_state` 跳变（如从「站立」到「已登顶」）必须有中间镜头或换场声明。
5. 末帧衔接：`next_shot` 的首帧参考应来自 `previous_shot` 的末帧，或显式声明 `match_cut_to`。

### 6.4 匹配剪辑

用相似形状/运动连接两个独立镜头：夕阳 → 眼中倒影；河流 → 云层；抬头 → 天空；楼梯向上 → 仰拍楼阁。

## 7. 声音设计

四层轨道，缺一层就会「只有配乐和旁白」：

| 轨道 | 内容 | 来源 |
|---|---|---|
| A1 旁白 | 逐句朗诵 | VoxCPM2 |
| A2 环境 | 风、水、鸟、树叶 | SFX 资产 |
| A3 音乐 | 古琴、箫、弦乐、氛围 | BGM 资产 |
| A4 拟音 | 脚步、衣袖、木梯、栏杆 | SFX 资产 |

规则：

- 旁白先定稿，剪辑时间轴围绕旁白调整，不为迁就画面强行压缩语速。
- 逐句生成、逐句保存，单句失败只重做该句。
- 音乐与环境音保留 2–3 秒尾音，不要硬切。

## 8. 剪辑

| 方式 | 使用场景 |
|---|---|
| 直接剪切 `cut` | 常规叙事、视角切换 |
| 动作匹配 | 动作连续 |
| 视线匹配 | 人物看向某方向 |
| 匹配剪辑 `match_cut` | 两画面形状/运动相似 |
| 叠化 `dissolve` | 时间流逝、回忆 |
| 遮挡转场 | 树枝/建筑/人物经过镜头 |
| 黑场 `fade_black` | 章节结束、留白 |

**不要给每个镜头都加转场。** 电影感来自剪辑，不是特效。

## 9. 质量控制

| 维度 | 检查 |
|---|---|
| 视觉 | 清晰度、构图、光线、色彩 |
| 空间 | 前中后景、透视、景深 |
| 动画 | 运动自然、无抖动、无变形 |
| 连续性 | 人物、服装、建筑、环境一致 |
| 摄影 | 运镜自然、景别合理 |
| 叙事 | 画面与文本对应 |
| 声音 | 发音、情绪、停顿、音量 |
| 剪辑 | 节奏、接镜、留白 |
| 合规 | 音乐、音效、字体、素材授权 |

五条硬规则：

1. 人物或建筑明显结构变形 → 退回重做。
2. 镜头间人物/服装/光线漂移 → 不得进入成片。
3. 旁白与画面严重错位 → 不得靠加速语速解决。
4. 只有数字放大、没有视差 → 不得标记为电影级运镜。
5. 字幕错误、诗词错误、爆音、明显闪烁 → 不得交付。

自动指标只做筛选，最终判断必须有人工审片记录。

## 10. 本机生产现实

| 项 | 实测 |
|---|---|
| FLUX.3 576×1024 | 约 2–2.5 分钟/张 |
| Wan 5B 576×1024 / 73 帧 | 约 36 分钟/镜 |
| VoxCPM2 | CPU RTF ≈ 9–12 |

按 40 分钟/镜估算：6 镜 ≈ 4 小时，8 镜 ≈ 5.3 小时，12 镜 ≈ 8 小时，30 镜 ≈ 20 小时，不含重试与人工审核。

策略：**先做少量高质量镜头**。2–5 分钟作品可以用少量真实运动镜头 + 局部动画 + 环境动态降低生成量，但不能让静态图平移成为主要画面。

## 11. 分阶段实施

| 阶段 | 交付物 | 状态 |
|---|---|---|
| Phase 1 影视化基础 | 统一数据模型、编剧、分镜、视觉圣经、逐句配音、镜头提示词、人工审核、多轨合成；《登鹳雀楼》45–60 s | **已实现制作层**（见下方 11.1）；成片待生成 |
| Phase 2 连续性 | 角色/场景参考、首末帧管理、上一镜状态传递、匹配剪辑、一致性检查 | 规划 |
| Phase 3 工作台 | 分镜编辑器、资产库、时间轴、音频轨、质量面板 | 规划 |
| Phase 4 长视频 | 多章节、续接、多场景连续性、自动调度、断点恢复 | 规划 |

### 11.1 已实现（2026-11-06）

| 能力 | 命令 / 模块 | 状态 |
|---|---|---|
| 项目数据与校验 | `drama film validate` / `film/project.py` | 已实现，示例项目 8 镜头 |
| 导演节拍 → 分镜 | `drama film plan` / `film/storyboard.py` | 已实现 |
| 连续性检查 | `film/continuity.py` | 已实现（光线/环境/旁白/假运镜/运动反向/状态跳变） |
| 剪辑时间轴 | `drama film timeline` / `film/timeline.py` | 已实现，8 镜 47 s |
| 关键帧提示词 | `drama film prompts` / `film/prompts.py` | 已实现，8 组 |
| FLUX 关键帧任务 | `drama film keyframes` / `film/jobs.py` | 8/8 已执行（2026-11-06 18:04–18:21，水墨包） |
| Wan 镜头任务 | `drama film wan-jobs` / `film/jobs.py` | 任务已按镜头时长重算；S01 单镜头验证执行中 |
| 逐句配音 | `drama film voice` / `film/voice.py` | **已真实合成** 6 句；标准 `audio_manifest.json` 实测 22.2 s（VoxCPM2，50000） |
| 统一合成 | `drama film assemble` / `film/assemble.py` | 已出 47.0 s / 1080×1920 粗剪；quality PASS（见 11.2） |
| 测试 | `tests/test_film*.py` | 56 项 |

### 11.2 2026-11-07 制作链闭环（本机实测）

本轮把「生成 → 镜头 → 成片」之间缺失的装配层补齐，并把 `r3_build` 作为唯一合成引擎。

| 能力 | 命令 / 模块 | 状态与证据 |
|---|---|---|
| 任意文本入口 | `film init` / `film script` / `film/script.py` | 诗句、散文、长篇按标点分句；自动生成旁白、视觉圣经、导演节拍与分镜；镜头语言受风格包允许列表约束 |
| 标准音频契约 | `film voice` → `audio_manifest.json` | 逐行 WAV 实测时长；不再写第二套 manifest |
| Audio-first 时间轴 | `film timeline` / `film/timeline.py` | 旁白时长决定镜头下限；`gap_before_ms` 保证字幕、混音、画面同一套毫秒边界 |
| Wan 帧序列编码 | `film clips` / `film/clips.py` | 121 帧 PNG → MP4；`source/target/effective` 三个时长分开记录 |
| 确定性运镜 | `film motion` / `film/motion_plan.py` | 8 个静帧 → 8 个 `*_motion.mp4`；逐镜 `check=PASS`；首尾帧平均差 9.1–16.5（不是静帧） |
| 统一合成 | `film assemble` / `film/assemble.py` | 只准备 `segments.json` + `audio_manifest.json`，调用 `scripts/r3_build.py` |
| 字幕 / 字体 / 响度 | `r3_build.py` | 软字幕 + 烧录字幕；`mov_text` 流 39.03 s；混音 47.21 s，峰值 -1.5 dB |
| 静帧质量门 | `film static` / `film/static_gate.py` | 8 镜客观指标已记录；语义清单 PENDING（H2 人工） |
| 多轨 BGM + ducking | `film assemble --bgm-id bgm_mozart_k330_piano` | 47.21 s 混音，峰值 -1.5 dB；quality PASS（`renders/build-20261107-190756/`，听感待人工） |
| 质量门 | `film qc` / `quality.check_build` | `final` / 8 个镜头 / 音频全部 PASS |
| 生产状态 | `film status` / `film/status.py` | 从文件与人工审核派生；H2/H3 结论写 `qc/reviews.json` |
| 工作台任务 | 10 个 `film.*`（keyframes / wan / timeline / voice / static / clips / motion / assemble / status / qc） | 与 CLI 同一套命令；GPU 任务走 `gpu:comfy` 单飞锁 |
| 首次成片 | `projects/deng_guan_que_lou/renders/build-20261107-183625/` | 47.0 s / 1080×1920 / 24 fps / 8 镜头 / 6 句旁白 / quality PASS |

补充：成片时长由文本量和 TTS 语速决定。`film init --duration` 只决定镜头规划节奏（默认上限 12 s/镜），不会把一段 30 秒的文本拉成 5 分钟；要更长成片需要更多文本或显式放慢语速。

关键约束（本轮新增）：

- 镜头不得短于自身旁白；不足时由时间轴自动延长，而不是压缩语速。
- 没有旁白的镜头保留分镜时长；`no_narration_seconds` 只作下限。
- Wan 产物是 PNG 帧，必须先经过 `film clips`；`segments` 会拒绝把帧序列当成视频。
- 静帧必须经过 `film motion` 或 `r3_build` Ken Burns；不得直接生成无运动的长静帧。
- 成片只写新的 `renders/build-<time>/`，不覆盖历史。

### 11.3 2026-11-07 二次制作：文本清洗、真实运动与叠化

第一版成片暴露了两个可复现缺陷：TTS 把 `(emotion, delivery)` 读成台词；Wan 失败后成片只剩 2% 推近的静帧。本轮按根因修复。

| 问题 | 修复 | 证据 |
|---|---|---|
| 情绪/导演备注被朗读 | `film/text.py` 括号、方括号、中文括号、`《》`、中文项目中的拉丁词全部剥离；`render_text` 不再拼接 direction 前缀；`film validate` 增加 `spoken_text_cleaned` 告警 | 干净 manifest 6 句时长 1.60–2.70 s（旧版 2.13–6.06 s）；`qc/tts_qa_clean.json` pinyin 6/6、max pinyin CER 0.0 |
| 8 GB 显存跑 121 帧丢卡 | `--profile safe8g`：448×768、49/65 帧；可被 32 整除；`WAN_FRAMES` 增加 49/65/81 | S01 121 帧旧任务在 KSampler 报 `UR_RESULT_ERROR_DEVICE_LOST`（`shots/S01/job.json`） |
| Wan 尾帧伪影 | `wan_qc.py`：全局黑像素/亮度突变/亮度漂移/边缘 + 顶部/底部暗带检测；`wan_chain` 只用干净前缀，并记录接缝亮度差 | S01 第 40 帧顶带暗像素 0.75% → 截到第 39 帧；第 41 帧起黑像素 1.2%/亮度降 6.2，正式截断 |
| 单段 Wan 不足 6 s | `film wan-chain`：前段末帧作为后段首帧，最后编码为一个镜头；第一段可复用已生成帧 | `shots/<shot>/chain_manifest.json` |
| 全片清一色推镜 | `film/motion_plan.py`：`static` 也做 2% 缓推；`script.py` 按景别/运镜阶梯生成镜头；`continuity.py` 增加 `same_shot_size` / `camera_vector_jump` 告警 | `film validate` 对示例项目的同景别/反推向给出告警 |
| Wan 提示词只有名词 | `prompts.py`：摄影机运动置顶（dolly/jib/pan），环境流体动词（水流、云涌、风摆、光影），静态死词不进入视频提示词 | `jobs/shots/params/S01.json` 的 `positive_prompt` |
| “crane” 被 Wan 画成机械吊车 | 风格引擎与 film 层全部改为隐藏机位（`hidden rig`）描述，并加入 `construction crane / machinery / metal pipes` 负向词；运动 id 展开为自然语言（`camera_descent` → “the camera descends slowly”） | 65 帧首测出现金属管道横穿（`qc/wan_S01_montage.png`），该批帧已废弃；修正后重跑 49 帧 |
| 硬切像 PPT | `r3_build.py --crossfade`：同景别、反推向、换场使用 0.5 s `xfade=fade`；所有片段加 handle，总时长与音频不变 | `renders/build-20261107-193612/video_raw.mp4` = 47.000 s；4 个 dissolve 切点 |
| 切镜声音突变 | `film/segments.py` 增加持续 ambience 轨（`sfx_wind_soft_30s`，-26 dB，1 s 淡入淡出）；BGM 仍可叠加并 ducking | `audio_timeline.json`：narration + ambience；quality PASS，峰值 -1.5 dB |

默认音色（2026-11-07 用户指定）：`config/voices.yaml` 的 `narrator_blend_my80_sun20`，参考音 `assets/audio/prompts/my_voice_clean_v2.wav`（7.52 s，参考文本「清晨的山谷里，风穿过竹林，远处传来水声。」），状态 `APPROVED`，用户已确认可正常使用。

最终稳定版（S01 Wan + 其余镜头确定性运镜/局部大气运动）：`projects/deng_guan_que_lou/renders/build-20261107-225921/`。注意：这不是全 Wan 生成动画；S02–S08 仍是静帧运动。S02/S03/S04 的 Wan 尝试分别出现塔楼墨团、白色块状伪影、第 2 段仅 4 干净帧，已确认 A750 8 GB + Wan 5B 无法稳定覆盖 5 s 级多镜头。，47.0 s / 1080×1920 / 24 fps / 6 字幕事件，起点与 6 句旁白完全一致；S01 为 3 段 Wan 续接（137 干净帧，截掉 10 帧污染帧，接缝 3.31/2.80 均 PASS），其余镜头为确定性运镜；`quality.check_build` PASS，`film_acceptance` 技术检查 PASS。

### 11.4 低清时序生成 + 后置超分：现状与取舍

**现状**：我们已经是“低分辨率算运动、后置升采样”的结构，但后置只用了 FFmpeg Lanczos，不是学习型超分。

```text
Wan 448x768 / 576x1024（算运动与结构）
  → film clips（帧序列 → MP4，时长统一）
  → r3_build scale=1080x1920:flags=lanczos（当前唯一的升采样）
  → 字幕 / 混音 / 叠化 / 成片
```

评估：

- 这个解耦方向是合适的。8 GB A750 在 448×768 跑 49 帧已经稳定；121 帧会触发 `UR_RESULT_ERROR_DEVICE_LOST`。低分辨率负责时序与物理，后置负责纹理，是当前硬件的工程解。
- Lanczos 不是“脑补纹理”，它只做重采样；优点是零闪烁、零幻觉、零额外模型，缺点是不会增加岩石、水纹、纸纤维的细节。
- 学习型超分（Real-ESRGAN / ncnn-vulkan）可以补细节，但有两个真实风险：逐帧独立超分会产生时序闪烁；过度锐化会放大 Wan 的底噪与纸纹。因此必须低强度、加轻度时域降噪，并在短片段上人工看片后再全片使用。
- 仓库当前**没有** SR 权重、`realesrgan`/`basicsr` 依赖，也没有 SR 模型；根 `.venv` 不允许装 torch。直接用 PyTorch 版会破坏双环境约束。
- 848×480 不是 32 的倍数；Wan 要求宽高能被 32 整除。竖屏用 448×768（9:16 近似），横屏用 832×480 或 864×480。

实现（本轮新增，默认不改变现有产物）：

| 能力 | 命令 / 模块 | 状态 |
|---|---|---|
| 后端探测 | `drama film upscale --check` / `film/upscale.py` | `lanczos` 可用；`realesrgan-ncnn` 未安装，明确显示 `available=false` |
| Lanczos + 轻度时域降噪 | `film/upscale.py` | 已验证；`hqdn3d=1.2:1.2:5:5` 后接 Lanczos |
| 外部 ncnn 超分 | `REALESRGAN_NCNN` 或 `D:/AI/tools/realesrgan-ncnn-vulkan` | 适配器已写；缺可执行文件时**报错，不静默回退** |
| 合成接入 | `project.json production.upscale_backend` | 默认 `lanczos`（r3_build 一次完成）；设为 `realesrgan-ncnn` 时先写 `<shot>_sr.mp4` 再进 build |

建议的下一步：安装 ncnn-vulkan 版 Real-ESRGAN（外部可执行文件，不碰根 venv），先对 S01 的 6 秒 Wan 片段做 A/B，人工确认无闪烁、无过度锐化后，再设 `upscale_backend=realesrgan-ncnn`。

## 12. 与现有模块的边界

| 现有模块 | 在影视化流程中的角色 |
|---|---|
| `production.py` | 生成 FLUX/Wan 任务与参数；不承担叙事与连续性 |
| `voice/tts.py` | 逐句合成与 manifest；不决定朗诵设计 |
| `voice/audio_timeline.py` / `mix.py` | 多轨混音；输入来自 `timeline.json` |
| `quality.py` | 技术质量与门禁；不替代人工审片 |
| `motion/` | 静态图微动；属于镜头内动效，不替代摄影机运动 |
| `film/`（新增） | 项目数据、分镜、连续性、剪辑时间轴；**不直接调用 ComfyUI** |

## 13. 验收标准（Phase 1）

以《登鹳雀楼》45–60 秒为例，验收不是「生成了多少张图」，而是：

1. 是否有真正的摄影机运动（有视差，不是数字放大）。
2. 是否有前景/中景/背景的层次。
3. 人物与环境是否有自然运动。
4. 镜头语言是否表达了诗词内容。
5. 不同镜头是否属于同一个视觉世界。
6. 旁白是否有感情与节奏。
7. 成片是否像一部完整短片，而不是幻灯片。

以上任一项不满足，Phase 1 不得标记完成。
