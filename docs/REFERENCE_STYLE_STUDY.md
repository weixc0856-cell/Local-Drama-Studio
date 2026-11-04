# 参考风格研究：东方仙境 / 水墨梦境

> 日期：2026-11-04
> 性质：**参考研究 / previs**，不是正式产品风格，不改变 `PRD.md` 的双核心风格边界。
> 参考：[A Dream - AI Film in Chinese Ink Wash Style](https://www.youtube.com/watch?v=bISRsGyNd-M) 与 [云上天宫｜AI打造的东方仙境](https://www.youtube.com/watch?v=fwcECmI1mYs)。
> 原则：只提取**镜头语言、色彩、节奏、材质与声音策略**，不复制原片画面、音乐、字幕、文案或具体镜头。

## 1. 从参考片提取的“可抄”规则

### 1.1 云上天宫型（东方神话 / 仙宫）

- 低饱和冷青灰为主，少量金色/朱红点景；
- 云海占画面 1/3 以上，白玉栏、飞檐、斗拱、琼楼玉宇；
- 大全景 + 低角度仰视 + 局部结构特写；
- 空气透视强：近景石阶/栏杆、中景宫殿、远景群山没入云海；
- 运镜慢：缓慢推近、轻微俯仰、云层漂移；
- 无人物或极小人物，强调“天地尺度”；
- 无台词、无字幕，声音以低频铺底 + 环境风声为主。

### 1.2 水墨梦境型（A Dream / ink wash）

- 墨分五色，生宣渗染，留白占画面 30–50%；
- 大面积静，局部墨扩散/云气漂移；
- 少量朱砂或淡花青点景，避免高饱和；
- 超现实空间：漂浮山体、月轮、孤舟、云海楼阁；
- 镜头近乎静帧，靠墨迹、雾气、水面与飞鸟产生运动；
- 无台词；音乐极简、留白多。

## 2. 本机已产出的 previs

### 2.1 仙宫型

- 成片：`experiments/reference_study/renders/palace/final_9x16.mp4`
- 时长：21.3 s / 1080×1920 / 24 fps
- 分镜：白玉天门 → 朱栏石阶 → 云海宫殿全景 → 飞檐斗拱特写
- BGM：`bgm_court_elegant_60s`
- quality：`PASS`
- 响度：约 -15.7 LUFS / True Peak -6.4 dBFS

### 2.1.1 Wan I2V hybrid（palace）

- 第一批 `palace_wide`：576×1024 / 73 帧 / 20 步；1992.33 s（约 33.2 min），峰值 VRAM 5.90 GB。
- 第二批 `palace_gate`：1442.94 s（约 24.0 min），峰值 VRAM 5.77 GB。
- 首尾帧平均绝对差约 11.58/255，云海与雾气有真实连续变化，建筑保持刚性。
- 片段：`experiments/reference_study/clips/palace_03.mp4`
- 1-Wan hybrid：`experiments/reference_study/renders_hybrid/palace/final_9x16.mp4`
- 2-Wan hybrid：`experiments/reference_study/renders_hybrid2/palace/final_9x16.mp4`
- quality：两条均 `PASS`；BGM + SFX 已混入。

### 2.2 水墨梦境型

- 成片：`experiments/reference_study/renders/ink/final_9x16.mp4`
- 时长：21.3 s / 1080×1920 / 24 fps
- 分镜：月下孤舟 → 漂浮楼阁 → 青绿山水 → 月轮云海
- BGM：`bgm_ink_serene_60s`
- quality：`PASS`
- 响度：约 -15.7 LUFS / True Peak -7.0 dBFS

### 2.3 关键静帧

- `experiments/reference_study/images/palace_wide/`
- `experiments/reference_study/images/palace_gate/`
- `experiments/reference_study/images/palace_stairs/`
- `experiments/reference_study/images/palace_detail/`
- `experiments/reference_study/images/ink_dream_01/` ~ `ink_dream_04/`

### 2.4 声音（不复制原片音频）

- BGM：`bgm_court_elegant_60s` / `bgm_ink_serene_60s`（自生成）。
- SFX：`sfx_wind_soft_30s`、`sfx_water_flow_20s`、`sfx_chime_single_6s`、`sfx_whoosh_2s`（自生成，已登记 manifest）。
- 参考片只提供“低频铺底 + 风声/水声/钟磬 + 极简留白”的声音策略，不复制其音乐、录音或音效。
- 带 SFX 的版本：`experiments/reference_study/renders_sfx/palace|ink/final_9x16.mp4`（quality PASS）。

### 2.2.1 Wan I2V hybrid（ink）

- 第一批 `ink_dream_03`：576×1024 / 73 帧 / 20 步；2313.34 s（约 38.6 min），峰值 VRAM 5.82 GB。
- 第二批 `ink_dream_04`：1743.12 s（约 29.1 min），峰值 VRAM 5.82 GB。
- 片段：`experiments/reference_study/clips/ink_02.mp4`
- 1-Wan hybrid：`experiments/reference_study/renders_hybrid/ink/final_9x16.mp4`
- 2-Wan hybrid：`experiments/reference_study/renders_hybrid2/ink/final_9x16.mp4`
- quality：两条均 `PASS`；BGM + SFX 已混入。
- 墨色/红点/楼阁结构保持稳定，雾气与墨扩散为连续变化。

## 3. 当前实现方式与边界

- 静帧由本机 FLUX.2 klein 生成（576×1024，4 步，CFG 1.0）。
- 动画契约已支持 `ScriptShot.type=video`：FLUX 关键帧作为结构锚点，`scripts/video_jobs.py` 生成 Wan I2V jobs；`build_segments` 可混合 Wan 片段与静帧。
- 当前 previs 仍以 `r3_build` 的确定性 Ken Burns（zoompan）为主；每条片现有 2 个 Wan I2V 镜头（`palace_gate` + `palace_wide`；`ink_dream_04` + `ink_dream_03`）+ 2 个静帧；hybrid2 已通过 quality。
- 混合方式：`scripts/reference_hybrid.py --segments ... --clips ... --out ...` 把已有 Wan 片段按镜头时长裁剪/循环后替换静帧来源；缺片段仍保留静帧。
- Wan 输出是 PNG 序列时，用 `scripts/frames_to_clip.py --frames <dir> --out <mp4> --fps 24` 先合成为片段，再交给 `reference_hybrid.py`。
- 声音：BGM + 自生成 SFX（wind/water/chime/whoosh），不复制参考片音频；无旁白、无字幕文本。
- 因此当前版本是 **previs / animatic**，不是参考片那种全片连续 AI 视频。
- 参考片的画面、音乐、文案、具体镜头均未复制；“抄”的是结构规则和声音气质。

## 3.1 原先为什么只能“图片晃来晃去”

原契约的三处限制：

1. `DraftShot.type` 只允许 `image`，`script_engine` 写死 `type="image"`；
2. `production.build_jobs` 明确拒绝非 image 镜头；
3. `build_segments` 传 `clips_dir` 时要求每个镜头都有 mp4，不能“部分 Wan + 部分静帧”。

2026-11-04 已改：

- `DraftShot` / `ScriptShot` 支持 `type=image|video` 和 `video_prompt`；
- `build_jobs` 为所有镜头生成 FLUX 关键帧；`build_video_jobs` / `scripts/video_jobs.py` 为 video 镜头生成 Wan I2V jobs；
- `build_segments` 新增 `allow_partial_clips`；显式 video 镜头缺片段仍报错，不允许静默降级；
- 工作台新增 `video.jobs`（只生成 jobs，不执行生成）。

这才是“连续动画”的入口；Wan 的实际生成仍需逐段跑，不能靠静帧 zoompan 冒充。

## 4. 下一阶段要补的

1. 每个样片选 1–2 个 hero shot 用 Wan I2V（20 步），其余保留确定性运动；
2. 增加云层/水纹/衣袂局部微动（`motion/` RegionSpec）；
3. 加入环境风声/钟磬/水声 SFX（需先登记资产）；
4. 决定是否要旁白；参考片是无声/音乐型，若要旁白需重新配节奏；
5. 人工审片：镜头顺序、色彩、云海层次、BGM 是否压画面；
6. 若确认要成为正式产品风格，必须另立 PRD 风格编号；当前仍是 previs，不进入 `config/styles.yaml` 的两种正式风格。

## 5. 复现

生成参数在：

`experiments/reference_study/params/*.json`

分镜与音频编排在：

- `experiments/reference_study/segments_palace.json`
- `experiments/reference_study/segments_ink.json`
- `experiments/reference_study/audio_timeline_palace.json`
- `experiments/reference_study/audio_timeline_ink.json`

这些是本地实验产物，按仓库边界不进入 Git；本文件保留方法、路径与结论。
