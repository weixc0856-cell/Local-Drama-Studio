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