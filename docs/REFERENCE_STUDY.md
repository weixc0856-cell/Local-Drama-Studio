# 参考研究：对标片拆解与风格 previs

> 性质：**参考研究**，仅用于提取镜头语言、色彩、节奏、材质与声音策略；不复制原片画面、音乐、字幕、文案或具体镜头，也不进入成片。
> 两份原始研究已于 2026-11-06 合并到本文件：两分钟对标片实测拆解 + 东方仙境/水墨梦境 previs。

## 1. 两分钟对标片实测拆解

用户给出的三条对标片，均用 `yt-dlp` 下载到 `本地参考片目录\`（仅作拉片分析，不进入成片、不提取音轨）。测量数据来自本机 `ffprobe` + FFmpeg 场景检测。

| # | 视频 | 时长 | 分辨率/帧率 | 镜头数（scene>0.30） | 平均镜长 | 语法 |
|---|---|---|---|---|---|---|
| 1 | `2HDuwM60Qt0` Harvest（水墨动画） | 300.0 s | 640×360 / 25 | ~40 | 7.5 s | 水墨花鸟/公鸡/昆虫，长镜头，留白，极慢推拉 |
| 2 | `fwcECmI1mYs` 云上天宫（AI 东方仙境） | 141.0 s | 854×480 / 30 | ~44 | 3.2 s | 写实 CG 天宫、云海瀑布、微小人影，快切广角 |
| 3 | `bISRsGyNd-M` A Dream（水墨） | 138.3 s | 640×360 / 25 | 24 | 5.7 s | 水墨静景 + 诗意字幕卡 + 梦境人物，慢节奏 |

## 可复用的镜头语法

- **时长**：120–141 s；镜头 3–8 s，平均 5 s 左右。
- **构图**：大留白、远景为主；人物/舟船很小，靠环境叙事。
- **运动**：极慢推近、横移、墨色扩散、水波与雾；没有手持抖动和快速甩镜。
- **转场**：水墨晕染/淡入淡出，不做硬切花活。
- **声音**：音乐铺底 + 水/风环境声，无对白；参考 #3 用字幕卡承担叙事。
- **颜色**：宣纸米白、墨黑、赭石、淡青；低饱和，无高光溢出。

## 本项目的验收标准（`ACCEPTANCE-2MIN-001`）

1. 成片 120–141 s，1080×1920 / 24 fps，H.264，quality `PASS`。
2. **每个镜头都是真实生成的视频**（Wan I2V），不允许静帧推拉冒充动画。
3. 水墨风格：`ink_wash`，四风格隔离；不混入动画/3D/写实。
4. 镜头 20–24 个，平均 5 s；运镜只用 `slow_push_in` / `slow_lateral_track` / 墨色扩散。
5. 音乐使用已登记的 PD/CC BY 资产；水/风 SFX 来自本机 `assets/audio/sfx`；无钟磬循环、无 drone。
6. 无对白；如需叙事，用 3–5 张字幕卡，不配音。
7. 成片可追溯到每个镜头的 keyframe、Wan job、seed、workflow hash。

## 生产计划

- 24 个水墨镜头 × 5 s = 120 s；关键帧 FLUX 576×1024，Wan I2V 73 帧 / 20 步，逐镜拉伸到 5 s。
- 参考 #3 的节奏（24 切 / 138 s）与本计划一致。
- 当前 GPU 正在跑 `experiments/shinkai_scene/wan24_jobs.json` 的 18 个镜头；结束后由 `scripts/run_ink_film.sh` 自动接续水墨批次。
- 输出：`experiments/ink_dream/renders_24/final_9x16.mp4`。

---

## 2. 参考风格研究（东方仙境 / 水墨梦境 previs）

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

### 1.3 吉卜力手绘田园

- 手绘不透明水彩/水粉厚涂，笔触与纸张颗粒可见；
- 温润高饱和的草木绿、泥土棕与天空蓝，漫射自然光；
- 田园、老式砖木房屋、杂木林、田埂与夏日积云；
- 无刺眼数码高光、无镜头光晕、无赛博/水墨/绢本；
- 运镜以慢推、轻横移、前景草叶微摆为主。

## 2. 本机已产出的 previs

### 2.1 仙宫型

- 成片：`experiments/reference_study/renders/palace/final_9x16.mp4`
- 时长：21.3 s / 1080×1920 / 24 fps
- 分镜：白玉天门 → 朱栏石阶 → 云海宫殿全景 → 飞檐斗拱特写
- BGM：`bgm_mozart_k525_strings`（莫扎特 K.525，Public domain）；古典重混：`experiments/reference_study/renders_full_classical/palace/final_9x16.mp4`
- quality：`PASS`
- 响度：约 -15.7 LUFS / True Peak -6.4 dBFS

### 2.1.1 Wan I2V hybrid（palace）

- 第一批 `palace_wide`：576×1024 / 73 帧 / 20 步；1992.33 s（约 33.2 min），峰值 VRAM 5.90 GB。
- 第二批 `palace_gate`：1442.94 s（约 24.0 min），峰值 VRAM 5.77 GB。
- 首尾帧平均绝对差约 11.58/255，云海与雾气有真实连续变化，建筑保持刚性。
- 片段：`experiments/reference_study/clips/palace_03.mp4`
- 1-Wan hybrid：`experiments/reference_study/renders_hybrid/palace/final_9x16.mp4`
- 2-Wan hybrid：`experiments/reference_study/renders_hybrid2/palace/final_9x16.mp4`
- Full-Wan：`experiments/reference_study/renders_full/palace/final_9x16.mp4`（4/4 镜头均为 Wan；`palace_stairs` 23.98 min / 5.82 GB，`palace_detail` 34.94 min / 5.86 GB）
- quality：三条均 `PASS`；BGM + SFX 已混入。

### 2.2 水墨梦境型

- 成片：`experiments/reference_study/renders/ink/final_9x16.mp4`
- 时长：21.3 s / 1080×1920 / 24 fps
- 分镜：月下孤舟 → 漂浮楼阁 → 青绿山水 → 月轮云海
- BGM：`bgm_schubert_d664_piano`（舒伯特 D.664，Public domain）；古典重混：`experiments/reference_study/renders_full_classical/ink/final_9x16.mp4`
- quality：`PASS`
- 响度：约 -15.7 LUFS / True Peak -7.0 dBFS

### 2.3 关键静帧

- `experiments/reference_study/images/palace_wide/`
- `experiments/reference_study/images/palace_gate/`
- `experiments/reference_study/images/palace_stairs/`
- `experiments/reference_study/images/palace_detail/`
- `experiments/reference_study/images/ink_dream_01/` ~ `ink_dream_04/`

### 2.4 声音（不复制原片音频）

- BGM：`bgm_mozart_k525_strings`（palace）/ `bgm_schubert_d664_piano`（ink），均为 Public domain 真录音；Keynata 小调与暖色大调曲目均被否决。
- SFX：`sfx_wind_soft_30s`、`sfx_water_flow_20s`、`sfx_chime_single_6s`、`sfx_whoosh_2s`（自生成，已登记 manifest）。
- 参考片只提供“低频铺底 + 风声/水声/钟磬 + 极简留白”的声音策略，不复制其音乐、录音或音效。
- 带 SFX 的版本：`experiments/reference_study/renders_sfx/palace|ink/final_9x16.mp4`（quality PASS）。

### 2.2.1 Wan I2V hybrid（ink）

- 第一批 `ink_dream_03`：576×1024 / 73 帧 / 20 步；2313.34 s（约 38.6 min），峰值 VRAM 5.82 GB。
- 第二批 `ink_dream_04`：1743.12 s（约 29.1 min），峰值 VRAM 5.82 GB。
- 片段：`experiments/reference_study/clips/ink_02.mp4`
- 1-Wan hybrid：`experiments/reference_study/renders_hybrid/ink/final_9x16.mp4`
- 2-Wan hybrid：`experiments/reference_study/renders_hybrid2/ink/final_9x16.mp4`
- Full-Wan：`experiments/reference_study/renders_full/ink/final_9x16.mp4`（4/4 镜头均为 Wan；`ink_dream_01` 36.72 min / 5.85 GB，`ink_dream_02` 37.08 min / 5.82 GB）
- quality：三条均 `PASS`；BGM + SFX 已混入。
- 墨色/红点/楼阁结构保持稳定，雾气与墨扩散为连续变化。

## 2.5 两分钟新海诚式场景片（24 镜头）

- 静帧：`experiments/shinkai_scene/images/shot_01..24`，FLUX 576×1024 / 4 步 / CFG 1.0，24/24 成功。
- 内容：夏日积云、空教室、铁道口、电车、雨后街道、天台、神社、便利店、星空、樱花河岸、隧道出口等；无人物、无对白。
- 2 分钟静帧版：`experiments/shinkai_scene/renders/final_9x16.mp4`
- 2 分钟 2-Wan 版：`experiments/shinkai_scene/renders_hybrid2/final_9x16.mp4`；清理 BGM 版：`renders_hybrid2_music/final_9x16.mp4`
  - 121.3 s / 1080×1920 / 24 fps
  - 24 个 5 s 镜头（末镜 6.3 s）
  - quality：`PASS`
  - 响度约 -16.2 LUFS / True Peak -1.7 dBFS
  - BGM + SFX（风/水/钟磬/转场）
- `shot_01`（积云翻涌）与 `shot_05`（雨街倒影）的 Wan 均已完成并接入：`experiments/shinkai_scene/renders_hybrid2/final_9x16.mp4`（2 Wan + 22 静帧，121.3 s，quality PASS）。Wan 分别 32.3 min / 5.83 GB 与 36.3 min / 5.92 GB。
- 新增场景风格 ID：`shinkai_scenery`，`category: scene`；它不改变两种 core 风格（`ink_wash` / `court_green_fine_line`）的产品边界。

## 2.6 30 秒全 Wan 剧情样片（`PASS_VERIFIED` 技术）

为了验证“连续剧情”，不再用 24 张静帧拼贴，而是做 6 镜头 / 30 秒全 Wan vertical slice：

1. `shot_01` 积云翻涌（已有 Wan）
2. `shot_03` 铁道口列车接近（Wan）
3. `shot_04` 电车车厢夕阳（Wan）
4. `shot_12` 黄昏站台（Wan）
5. `shot_05` 雨后街道倒影（已有 Wan）
6. `shot_19` 夜色小镇（Wan）

- 叙事线：黄昏 → 列车 → 站台 → 雨 → 夜，一条“归途”视觉线。
- 6 个镜头全部 Wan 视频，无静帧；音频为 BGM + SFX。
- 成片（旧 BGM）：`experiments/shinkai_scene/renders_story/final_9x16.mp4`（31.3 s / 1080×1920 / quality PASS）。
- 古典/民谣重混（2026-11-05，quality PASS）：`renders_story_classical_piano/final_9x16.mp4`（Mozart K.330 钢琴）、`renders_story_acoustic_guitar/final_9x16.mp4`（Jason Shaw 木吉他）、`renders_story_orchestral/final_9x16.mp4`（Grieg《晨曲》）。三版共用同一画面，只换 BGM。
- Wan 耗时：`scene_01` 32.3 min、`scene_02` 24.2 min、`scene_03` 36.3 min、`scene_04` 35.4 min、`scene_05` 36.3 min、`scene_06` 35.8 min；峰值 VRAM 5.82–5.95 GB。
- 2 分钟全 Wan 成片：24/24 镜头，121.3 s / 1080×1920 / quality PASS；`experiments/shinkai_scene/renders_24/final_9x16.mp4`；BGM `bgm_mozart_k330_piano`（Public domain）。

## 3. 当前实现方式与边界

- 静帧由本机 FLUX.2 klein 生成（576×1024，4 步，CFG 1.0）。
- 动画契约已支持 `ScriptShot.type=video`：FLUX 关键帧作为结构锚点，`scripts/video_jobs.py` 生成 Wan I2V jobs；`build_segments` 可混合 Wan 片段与静帧。
- 每条片现有 4/4 个 Wan I2V 镜头；`renders_full/palace` 与 `renders_full/ink` 均为 21.3 s、quality PASS。静帧 + Ken Burns 仍保留为无 Wan 时的 fallback。
- 混合方式：`scripts/reference_hybrid.py --segments ... --clips ... --out ...` 把已有 Wan 片段按镜头时长拉伸（默认 `--mode stretch`，避免短片段循环接缝）后替换静帧来源；缺片段仍保留静帧。
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
