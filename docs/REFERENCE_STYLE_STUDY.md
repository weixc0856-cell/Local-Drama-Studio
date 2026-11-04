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

## 3. 当前实现方式与边界

- 静帧由本机 FLUX.2 klein 生成（576×1024，4 步，CFG 1.0）。
- 运动由 `r3_build` 的确定性 Ken Burns（zoompan）完成；**没有使用 Wan**。
- 声音只有 BGM，无旁白、无音效、无字幕文本。
- 因此这是 **previs / animatic**，不是参考片那种连续 AI 视频。
- 参考片的画面、音乐、文案、具体镜头均未复制；“抄”的是结构规则。

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
