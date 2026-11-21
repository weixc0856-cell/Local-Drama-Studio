# Z-Image Turbo 风格图谱实测结论 (Style Atlas Findings)

> 人工可读的实测结论沉淀。配方与词典见 [Z_IMAGE_TURBO_STYLE_ATLAS.md](Z_IMAGE_TURBO_STYLE_ATLAS.md)（自动生成）；
> 逐图原始数据见输出根 `experiments/z_image_styles/<run>/benchmark_manifest.json`。

## 一、本轮实测范围与条件

| 项目 | 值 |
| :-- | :-- |
| 日期 | 2026-11-20 |
| 引擎 | `z_image_turbo` · `z-image-turbo-Q4_K_M.gguf` · Qwen3-4B-Q4_K_M (lumina2) · `ae.safetensors` |
| 设备 | Intel Arc A750 8GB (XPU)，ComfyUI 0.43.0 / PyTorch 2.15.0+xpu |
| 参数 | 1024×1024 · 8 steps · CFG 1.0 · euler/simple · **无负面提示词** |
| 任务 | 38 套原生配方 × seed 42 + 8 套风格 × 统一人像主体 × seed {42, 2026} + 3 组跨风格组合 + 1 组色偏修法验证 |
| 结果 | **58 张全部生成成功，0 失败**，主扫 54 张图片哈希互不重复 |
| 评分 | 五维 1~5 分，`reviewer=claude-visual-review`（模型看图初评，**待人工复核定稿**） |

### 吞吐实测（重要运维结论）

- 主扫 38 张：均值 **213.9s**，累计 135.4 min。
- 全 54 张：均值 **192.3s**，最快 **36.1s**，最慢 **249.5s**，累计 173.1 min。
- 6 倍以上的耗时差不是随机噪声，而是**显存驻留差异**：DiT + 文本编码器 + VAE 全部驻留 8GB 显存时约 36s；
  文本编码器被挤到 CPU 时约 200~250s。**排产按 200s/张 估算**，不要按最好情况估。

## 二、可以直接进生产的风格（均分 5.0）

工笔花鸟、宋代青绿山水、宋式美学、日系动画背景、手绘奇幻动画、3D 家庭动画、
奢侈品广告、护肤品广告、美食广告、杂志编辑插画、波普艺术、太阳朋克、水彩、彩铅绘本，
以及 6 个 2026 趋势方向（直闪抓拍、触感拼贴、戏剧化舞台布光、怀旧漏光、有机侘寂极简、超现实商业隐喻）。

**本项目最值得押注的方向：宋式美学（12）与工笔（10）。** 两者在原生配方和统一主体对照下都稳定 5.0，
且组合实验证明它们能直接吃下现代商业布光——这正是"中国传统审美 × 现代商业视觉"的可行路径。

## 三、五类实测失败模式与修法

### 1. 未指定的文字一律乱码（最高优先级）

- **23 瑞士平面设计**：网格与橙色几何完全成立，但整版文字是 `RI I iEE / GI LE / CI ?` 一类乱码字母。
  可用性打 2 分——平面类不锁文字就不可交付。
- **07 黑色电影 / 27 赛博朋克**：霓虹招牌出现 `HRBL`、`HLAD` 等伪字母。
- **14 木版年画**：匾额出现伪汉字。

**修法**：需要文字时用 `atlas compile --text "原文"`（自动加英文双引号）；不需要文字时，
在 constraints 里写明 `a clean frame without graphic overlays`，并在交付前裁掉招牌区域。
这条实测直接印证了官方"画面文字必须双引号标明"的规则不是可选项。

### 2. 描述灯具会把灯具画进画面

- **20 汽车商业广告**：车身比例、缝隙、金属反射都准确，但 prompt 里的 `large softbox lighting`
  被字面执行，两只柔光箱连同灯架直接入画，可用性打 3 分。

**修法**：描述**光质**而非**器材**——用 `broad even soft light with controlled specular reflections`，
或补 `lighting equipment out of frame`。词典 `lighting:large_softbox_commercial` 已按此原则改写措辞使用。

### 3. 山水主体会触发青绿设色先验

- **09 水墨山水**（原生配方）：笔法、留白、宣纸质感都对，但混入青绿与赭石色块，
  尽管 `color_texture` 明写 `monochromatic black and charcoal tones`。纯度打 3 分。
- **同风格统一主体对照**（主体换成人物）：反而是纯黑白，无色偏。
- **组合实验 水墨 × 武侠构图**（主体仍是山）：色偏复现。

**结论**：色偏来自**山水主体的设色先验**，不是构图或配方措辞遗漏。

**已验证的失败修法**：新增排他性正向词条 `color_texture:ink_pure_monochrome`
（"整幅画面只有墨黑、灰晕与纸白"）+ `constraints:ink_monochrome_discipline`
（"山石树木一律只以墨笔写出"），重跑同主体同 seed——**色偏依旧存在**。
提示词层面压不住这个先验，词条保留作措辞参考，但不要指望它解决问题。

**已验证的有效修法（已内建）**：色偏只在**色度**上——原图平均饱和度 18.9/255，
只有 5.7% 的像素 S>40，墨稿的明暗结构完全正确。转灰度即还原为干净可信的纯水墨。
因此 `chinese_ink_wash` 在 YAML 里声明 `postprocess: grayscale`，
测试台生成后自动附一张 `*_MONO.png` 纯墨交付版，报告里给出「纯墨」链接。
旧 run 用 `--resume` 重跑会自动补齐该变体，不会重复消耗 GPU。

### 4. 摄影布光借进平涂媒介会变成光斑

- **组合实验 工笔 × 时尚人像布光**：工笔人物与绢本花卉极佳，但借来的
  `soft directional daylight` 在平涂颜料媒介上被理解成脸上的**literal 亮斑**，而不是造型明暗。

**修法**：跨媒介借光时必须追加 `constraints:pigment_medium_shading`
（以颜料叠染与线密度造型，保持画面平整），已加入词典。

### 5. 超现实空间指令会被规整成合理建筑

- **26 超现实主义**：要求"海中纪念碑式阶梯升入云端 + 漂浮建筑碎片"，
  实际输出是水上白色小教堂带台阶，**没有漂浮碎片**，读起来像建筑摄影而非超现实。辨识度打 2 分。
- 对照 **38 超现实商业隐喻**（沙漏内森林）：5.0 满分。

**结论**：Turbo 能做好**具体物件的超现实并置**（沙漏 + 森林），
但做不好**抽象空间不可能性**（无限阶梯、漂浮碎片）。写超现实要给物件清单，不要给空间形容词。

## 四、Turbo 模型特性验证

- **多样性确实低**：01 高级时尚人像两个 seed（42 / 2026）构图几乎一致——同机位、同姿态、同裁切。
  换 seed 不等于换构图。要换构图必须改 `composition` / `scene` / `lighting` 维度本身。
- **但多样性按风格分层**：15 日系动画背景两个 seed 的道口位置与人物姿态差异明显，
  动画类比写实摄影类更容易出变化。
- **风格可跨主体迁移**：03 黑白电影配方主体是中年男性，换成年轻女性后明暗对照法依然成立；
  10 工笔从花鸟换成人物同样稳定。说明这些风格学到的是**媒介语言**而非主体绑定。
- **半写实混合风险**：09 水墨与 29 水彩在统一人像主体下，环境是纯媒介语言，
  但人物面部偏写实柔焦，媒介纯度降到 4 分。国风人像要纯，工笔（10）比水墨（09）稳。

## 五、跨风格组合实验（文章重点推荐方向）

| 组合 | 借用维度 | 均分 | 结论 |
| :-- | :-- | --: | :-- |
| 宋式美学 × 奢侈品广告 | lighting, color_texture | 5.0 | **成立且可直接商用**。青瓷开片、梅枝、深色木案 + 黑背景金色吊灯 |
| 水墨山水 × 武侠电影 | composition, lighting | 4.2 | 电影式前中后景分层明显强于原配方；色偏问题仍在（见三·3） |
| 工笔花鸟 × 时尚人像 | composition, lighting | 4.4 | 工笔人物极佳；需补平涂造型约束消除光斑（见三·4） |

**组合纪律（实测得出）**：
1. 一次只保留一个主媒介，`medium_style` 不轻易借。
2. 借来的维度里可能藏着**原主体专属名词**——宋式 × 奢侈品那组，借来的光线词条含
   `glass facets` 与 `amber internal liquid`（香水专属），模型就真给画了个玻璃吊灯。借之前先清洗名词。
3. 借摄影光进平涂媒介，必须同时借/加平涂造型约束。

## 六、复现与复核

```powershell
# 复现全量实测（断点续跑，已完成的图不会重跑）
python src/produce.py atlas benchmark --mode recipe --all --seeds 42 --size square --live --resume
python src/produce.py atlas benchmark --mode controlled --seeds 42,2026 --size square --live --resume

# 人工复核评分：填 scores.csv 后回填
python src/produce.py atlas score-import --run-dir "<run>" --csv "<run>\scores.csv" --reviewer <你的名字>

# 重建拼版与报告
python src/produce.py atlas board  --run-dir "<run>"
python src/produce.py atlas report --run-dir "<run>"
```

产出位置（输出根，非仓库）：

- `experiments/z_image_styles/atlas_v1/` — 54 张主扫 + 分类拼版 + 报告 + `scores.csv`（含 09 号纯墨交付版）
- `experiments/z_image_styles/mixes/` — 3 组组合实验 + 拼版 + 报告
- `experiments/z_image_styles/fix_ink_monochrome/` — 色偏提示词修法验证（负面结果，保留作证据）
## 七、片头字体：从「官方通告感」到电影质感（实测对比）

结论前置：**画面文字必须合成，不能交给扩散模型**（见三·1）。合成用什么字、怎么排，
实测差异同样巨大。基线是思源宋体 Bold + 纯白实心 + 紧字距，观感像学术 PPT 而非片头。

### 授权核实（不采信推荐文，逐个查上游）

| 字体 | 上游 | 授权核实结果 |
| :-- | :-- | :-- |
| 霞鹜文楷 LXGW WenKai | `lxgw/LxgwWenKai` v1.530 | GitHub license 字段 `OFL-1.1` + 上游 `OFL.txt` 正文 ✓ |
| 朱雀仿宋 Zhuque Fangsong | `TrionesType/zhuque` v0.212 | 同上 ✓（zip 仅 5.7 MB） |
| Cinzel / Cormorant Garamond / Marcellus / Playfair Display | `google/fonts` 的 `ofl/` 目录 | 目录分类 + 各自 `OFL.txt` 正文 ✓ |
| **汇文明朝体 Huiwen-mincho** | 推荐文给的仓库名 | **三个名称变体全部 404**，搜索仅得无授权声明的镜像 → **不采用** |
| 演示春风楷 / 悠然小楷 | 非 OFL 的「免费商用」声明 | 授权来源不够硬，未采用 |

全部字体已登记进 `assets/fonts/font_manifest.json`（含 sha256、上游 URL、授权），
`python scripts/fetch_fonts.py --check` 可校验，二进制不入 git。

### 中文字体实测

- **思源宋体 Bold（基线）**：横细竖粗、刀切感强，确实"生硬、像官方通告"。
- **霞鹜文楷 Light**：最飘逸，但大标题在深色底上偏薄，撑不住画面。
- **霞鹜文楷 Medium**：温润笔锋 + 足够分量，**定为片头默认**。
- **朱雀仿宋 Regular**：清秀文人气，适合安静的章节卡/副标题，不适合撑主标题。

### 英文副标题：一个需要纠正的前提

推荐文判断当前英文是"偏细的普通现代衬线体"——**实测不是**。
`PIL.ImageFont.getname()` 返回 `('Cinzel', 'Regular')`，可变轴 `Weight 400–900`。
也就是说**字体本来就是 Cinzel，只是可变字体默认落在 400**。
所以不需要换字体，`set_variation_by_axes([500])` 即可，推荐文的字重建议是对的、family 诊断是错的。

五个候选同条件对比后：
- **Cinzel 500**：古罗马石刻大写，横向张力最足，与文楷 Medium 的厚度最平衡 → **默认**。
- Marcellus 400：微衬线、最干净，安静内容的备选。
- Cormorant Garamond 600：**同字号下视觉明显偏小**（字身高度不同），换用它必须额外放大。
- Playfair Display 500：粗细对比强，小屏播放最锐利。

### 排版微调（都已实装进 `scripts/render_title_card.py`）

1. 中文字距 `0.34em`，四个字拉开呼吸感。
2. 暖金竖向渐变填充 `#F7F1E3 → #D8C39E` + 极淡同色柔光晕，字"融"进深色底而不是贴在上面。
3. 英文副标题提亮到香槟金 `#C8B085`，字号从主标题的 0.26 提到 0.29。
4. 分隔横线改**两端渐隐**（1px，240px 宽），不再齐平切断。

### 一个实装时踩到的坑

渐隐横线用 `Image.alpha_composite` 会返回**新图像对象**，此前的 `ImageDraw` 句柄仍指向被丢弃的旧图。
之后画的字体标签全部丢失且不报错。合成后必须重建 `Draw` 句柄——已加注释与回归测试。

### 复现

```powershell
python scripts/render_title_card.py --preview       --out cmp_cjk.jpg
python scripts/render_title_card.py --latin-preview --out cmp_latin.jpg
python scripts/render_title_card.py --font lxgw_wenkai_medium --latin cinzel --latin-weight 500 --out card.png
```

## 八、Wan 14B 运动控制：程度副词无效，首尾状态锁定有效

「云上天宫」5 镜实测（832×480 / 49 帧 / 6 步 LightX2V / CFG 1.0 / shift 5）。

### 吞吐实测（修正文档旧值）

| 镜头 | 耗时 |
| :-- | --: |
| S01 云廊 | 22.5 min |
| S02 孤松 | 29.7 min |
| S03 白衣 | 28.8 min |
| S04 天阶 | 29.2 min |
| S05 远阙 | 28.9 min |

均值 **27.8 min/镜**，5 镜合计 139.1 min。与 `WIDESCREEN_VIDEO_GENERATION_GUIDELINES.md`
记的「~28–30 min」一致；S01 的 22.5 min 是显存全驻留的快档。
后处理（2x Lanczos + 32fps 光流）每镜仅 **13–14 秒**，成本可忽略。

### 核心发现：「very slow / extremely slow」不约束幅度

| 镜头 | 运动提示词写法 | 结果 |
| :-- | :-- | :-- |
| S01 | `Extremely slow cinematic push-in` | ✓ 推进克制，对称保持 |
| S02 | `Very slow lateral drift to the right` | ✗ **变成大幅推近**，末帧只剩树干特写，孤岛与台面全部出画 |
| S03 | `Static camera` + 微风 | ✓ 镜头几乎不动（袖子张开略超预期，可接受） |
| S04 | `Very slow tilt down` + `clouds pour over the steps` | ✗ **云雾过量涌起**，末帧几乎吞掉两侧阙楼 |
| S05 | `Very slow lateral reveal` | ✓ 缓慢横移，楼阁刚性 |

**规律**：唯一稳定的是 `Static camera`（S03）。凡给了移动动词，程度副词都压不住幅度，
而且**同一写法在不同镜头上表现不一致**（S01 的 push-in 克制，S02 的 drift 失控）。
大气元素同理——`clouds pour` 会被执行到淹没主体。

**修法（已实装）**：把程度描述换成**首尾状态锁定 + 显式禁止**：

```text
Static camera, locked framing. The whole pine tree and its rocky island stay fully
visible and centred at the same size in the last frame as in the first frame.
Only the thin needles sway gently. No zoom, no dolly, no close-up, no change of shot scale.
```

大气也要给**空间上界**，而不是只说"慢"：

```text
Only a thin low layer of mist drifts across the bottom steps; the mist never rises
above the base of the buildings and never covers them.
```

负面提示词同步加入 `zoom in, dolly in, extreme close-up, cropping the subject out of frame`。

### 其它两条

- **480P 大远景惩罚对「场景」不成立**。5 镜首尾帧质检显示斗拱、栏杆、屋檐、台阶全部刚性保持，
  云海自然推移，大理石倒影正确跟随几何。Widescreen Guard 的人脸 token 理由在无脸场景下不适用，
  本次**有意不套用 guard** 是成立的。守则应限定为「画面内有需要保真的人脸时」。
- **光流补帧会缩短时长**：49 帧 @16fps = 3.0625s，`minterpolate` 后得 95 帧 @32fps = **2.968s**，
  每镜少约 0.09s，5 镜累计约 0.47s。按帧数估算总片长会偏长，需以 ffprobe 实测为准。

### 关键帧侧的一条指令偏移

S02 提示词要「悬于云海中的岩岛」，Z-Image 把它放到了大理石台面上——
**风格配方里的场景元素压过了 shot 级的 scene 覆盖**。观感不差，但说明
`compile(style, scene=...)` 的覆盖不是硬约束，主体与场景冲突时风格先验会赢。

### 修法验证结果（take2 重渲，同 seed 同关键帧）

| 镜头 | take1 | take2（首尾锁定） | 判定 |
| :-- | :-- | :-- | :-- |
| S02 孤松 | 末帧只剩树干特写，孤岛出画 | 全树首尾同大小、居中、完整可见，台面与孤岛都在画内 | **完全修复** |
| S04 天阶 | 云雾吞没两侧阙楼 | 左楼完全清晰，右楼薄雾半掩但结构可读，构图保住 | **大幅改善、可用**；空间上界只被部分遵守 |

**结论**：首尾状态锁定对**镜头运动**是硬有效的（S02 完全修复）；
对**大气元素的空间范围**只是软约束（S04 改善但仍越界）。
要彻底压住雾气范围，恐怕得靠更短帧数或后处理遮罩，而不是提示词。

失败 take 保留在 `frames/S02_take1`、`frames/S04_take1` 作为证据，未被覆盖。
重渲成本：S02 29.0 min + S04 28.5 min。

### 最终交付

`experiments/cloud_palace/deliver/cloud_palace_master.mp4`
**17.34 s / 1664×960 / 32 fps / H.264 + AAC / 8.5 MB**（片头 2.5s + 5 镜 × ~2.97s）
时间线抽检确认拼接顺序正确、接缝无异常。
