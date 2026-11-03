# 双管线专项修复报告（水墨 Motion Mask / 青绿工笔风格校正）

> 执行日期：2026-11-03
> 环境：Intel Arc A750 8 GB / ComfyUI 0.43.0 / Wan2.2 TI2V 5B Q4 / FLUX.2 klein 4B Q4 / FFmpeg 8.1
> 状态口径：`docs/PRD.md` §0.2。**技术检查通过不等于风格验收通过；人工看片前一律 `PARTIAL`。**

## 1. 修改前检查

### 1.1 仓库与工作流

- 分支 `main`，HEAD `e21dc0d`；工作区有大量未提交的 P0/P1/S1/S2/管线验证修改。本轮未重置、未覆盖、未提交。
- 静帧：`workflows/r0_flux_t2i_api.json`（FLUX.2 klein 4B，4 步，CFG 1.0，**无负向提示词**）。
- 参考图编辑：`workflows/r1_flux_edit_api.json`（`ReferenceLatent`，**无局部 inpaint 遮罩**）。
- Wan：`workflows/r0_wan_i2v_api.json`（Wan2.2 TI2V 5B、UMT5、Wan2.2 VAE、`Wan22ImageToVideoLatent`、KSampler `uni_pc/simple`、20 步、CFG 5、shift 8、576×1024×73）。**只有 `start_image`，没有 mask / control_video / tracks 输入。**

### 1.2 模型与节点能力

- `D:\AI\models` 仅有 Wan2.2 TI2V 5B、FLUX.2 klein 4B、Qwen3-4B、UMT5、两个 VAE；**没有 ControlNet、LoRA、VACE、Wan Move、SAM**。
- 自定义节点只有 `ComfyUI-GGUF`。ComfyUI 核心存在 `WanVaceToVideo` / `WanTrackToVideo` / `WanFirstLastFrameToVideo` 类，但没有对应模型，也未接入当前工作流；不能据此声称具备 Motion Mask。

| 能力 | 是否具备 | 实际实现 | 是否运行过 |
|---|---|---|---|
| 区域运动遮罩（Wan 内） | **否** | 当前 I2V 无 mask 输入 | 否 |
| 主体保护遮罩（Wan 内） | **否** | 同上 | 否 |
| 局部区域控制 | **否** | 无 control_video / tracks / ControlNet | 否 |
| 视频区域合成 | **是** | FFmpeg RGBA 图层 `overlay` | 是 |
| 遮罩羽化 | **是** | Pillow GaussianBlur / FFmpeg `gblur` | 是 |
| 时序一致性控制 | **部分** | 确定性图层稳定；Wan 内无时序 mask | 是（确定性图层） |

### 1.3 关于上一轮审查素材

上一轮被审查的水墨样片（`experiments/pipeline_a/renders/build-20261103-212100/`）是 **FFmpeg 确定性图层合成，没有使用 Wan**。仓库里没有同一张 IA4 的 Wan 全片基线。为做真正的 A/B，本轮先用原始 Wan I2V 工作流生成 73 帧基线，再与保护版同分辨率、同帧率、同时长比较。

## 2. 水墨管线：Motion Mask 可行性 + 主体保护

### 2.1 A/B 设计

- 同一输入：`experiments/pipeline_a/static/IA4/IA4_ink_landscape_00001_.png`（SHA-256 `819dab72…5e5727`）。
- **A（Wan 原始全片）**：73 帧 / 576×1024 / 20 步 / CFG 5 / shift 8 / seed 5501，Lanczos 放大到 1080×1920、24 fps、3.000 s。耗时 1555 s，峰值显存 5.51 GiB。
- **B（保护版）**：静态主体保护 + 局部图层 + 确定性合成，1080×1920 / 24 fps；同输入、同分辨率、同帧率。3 秒版用于 A/B；10 秒版是稳定交付片段。

### 2.2 B 的具体修复

| 对象 | 做法 |
|---|---|
| 孤舟 | 独立 RGBA 图层；**整数像素**平移，10 s 内 6 px（0.6 px/s）；无旋转、缩放、形变 |
| 倒影 | 独立图层；与舟体使用**同一组 x/y 位移**；不单独漂移 |
| 水面 | 运动区下移到 y 0.80 以下；排除舟体/倒影包围盒；±4 px / 8 s |
| 近岸树丛 | 不进入任何运动层；水面运动区不再覆盖树影带 |
| 山腰云雾 | 云层上移到树冠以上（y 0.46–0.63）；模糊亮度遮罩；±32 px / 16 s |
| 山体/远山 | 冻结；首帧→中帧差异 0.015/255（B 10 s 版 0.0036/255） |
| 纸本 | 生宣纹理 `overlay 0.14` |

图层参数：`experiments/pipeline_a/layers.json`；实现：`scripts/pipeline_ink.py`。

### 2.3 A/B 结果

| 指标 | A（Wan） | B（保护版） |
|---|---|---|
| 舟体暗像素面积（首/中/末） | 31805 / 31658 / 31759；波动 0.46% | 32055 / 32054 / 32082；波动 **0.09%** |
| 舟体像素质心 x（首/中/末） | 389.07 / 389.54 / 387.25（末帧向左漂） | 390.54 / 390.89 / 391.29（单调微移） |
| 静态山体区域首帧→中帧差异 | 2.73/255（Wan 重绘/漂移） | **0.015/255** |
| 树带区域首帧→中帧差异 | 6.67/255 | 1.70/255（含舟体位移；树区单独 0.20/0.46） |
| 云带区域首帧→中帧差异 | 3.94/255 | 2.92/255 |
| 倒影 | 随 Wan 逐帧重绘变化 | 与舟体同偏移，无独立漂移 |

说明：差分值只表示像素变化，不能单独判定形变；上表结合了舟体面积/质心、对齐后的局部放大和目视检查。A 的静态区域变化说明 Wan 会重绘本应冻结的山体与树丛；B 的静态区域几乎不变。B 的树带差异主要来自舟体位移，不是树叶闪烁。

### 2.4 验收对照

| 项目 | 结果 | 说明 |
|---|---|---|
| 孤舟无明显形变、缩放、旋转 | `PARTIAL`（技术通过，人工待审） | 面积波动 0.09%，刚性贴片，仅整数像素平移 |
| 倒影不独立漂移、不异常闪烁 | `PARTIAL`（技术通过，人工待审） | 与舟体同偏移；局部放大未见脱节 |
| 云雾能观察到连续缓慢流动 | `PARTIAL` | 云带差异 2.92/255；运动克制但偏弱 |
| 水面有轻微动态、不影响船体 | `PARTIAL` | 水面 ±4 px/8 s；船体/倒影已排除 |
| 树丛无明显高频闪烁 | `PARTIAL`（技术通过，人工待审） | 树区差异 0.20/0.46/255，较上一版 5.26 明显下降 |
| 山体主体稳定 | `PASS`（技术） | 0.0036/255（10 s） |
| 保留水墨留白与静谧感 | `PASS`（技术） | 末帧留白约 59% |
| 人工看片 | **PENDING** | 需确认云气速度/幅度、水面幅度、舟体位移是否自然 |

### 2.5 片段与证据

- **B 10 秒稳定版**：`experiments/pipeline_a/renders/build-20261103-214235/final_9x16.mp4`（10.0 s / 1080×1920 / 24 fps / 解码 0 / 黑帧 0）
- B 3 秒 A/B 版：`experiments/pipeline_a/renders/build-20261103-214243/final_9x16.mp4`
- A Wan 3 秒版：`experiments/pipeline_a/wan_baseline/A_wan_1080.mp4`
- A/B 全帧对照：`experiments/pipeline_a/compare_wan_vs_protected/frames_A_vs_B.png`
- A/B 舟体/树丛局部对照：`experiments/pipeline_a/compare_wan_vs_protected/crops_A_vs_B.png`
- 完整指标：`experiments/pipeline_a/compare_wan_vs_protected/compare.json`
- B 10 秒指标：`experiments/pipeline_a/renders/build-20261103-214235/motion_metrics.json`

## 3. 青绿工笔管线：风格校正

### 3.1 已确认的问题（A1）

- 山脊、屋脊、松树有较粗的深色闭合轮廓，整体偏日式木版画/浮世绘。
- 右下与礁石周围水纹呈规则同心圆/等高线状。
- 山石坡面有平行的赭/绿色带，设色平涂感强。

局部证据：`experiments/pipeline_b/static/A1_water_bottom.png`、`A1_slope.png`、`A1_roof.png`、`A1_pines.png`。

### 3.2 实验设置

- **ControlNet 0.5 无法执行**：当前没有 ControlNet 模型、节点或工作流；该项标记 `NOT_RUN`，没有伪造。
- 只改提示词（G1/G2）或用 A1 做参考图编辑（G3），其他参数保持：1024×1024、4 步、CFG 1.0。没有同时改采样器、分辨率或 LoRA。
- 提示词新增：宋代院体、绢本、铁线描/游丝描、分层罩染、皴法随结构、水纹疏密断续；明确写 `not ukiyo-e / not Japanese woodblock print / not thick black outlines / not vector illustration / not cel shading`。
- 当前 FLUX t2i 工作流**没有负向提示词输入**，上述英文只能作为正向文本中的排除描述，不能等同于真正的 negative prompt。

| 候选 | 方式 | 选择 |
|---|---|---|
| G1 | 改提示词，seed 5201 | 构图变化大，水纹改善但仍有粗轮廓；未选 |
| G2 | 改提示词，seed 5401 | 山体平涂感仍强，构图变化；未选 |
| G3 | 以 A1 为参考图编辑，seed 5402 | **选用**：保持 A1 构图，线条变细、设色更柔和 |

### 3.3 G3 静态门

文件：`experiments/pipeline_b/static/G3_static_quality.json`

| 检查 | 结果 | 说明 |
|---|---|---|
| 线条 | `PASS` | 粗黑闭合外框明显减少，线条更细；仍有少量深色轮廓 |
| 建筑 | `PASS` | 楼阁结构与 A1 基本一致 |
| 山石 | `PARTIAL` | 平行色带减弱，但仍存在重复 |
| 水纹 | `PARTIAL` | 同心圆减弱、范围变小，但礁石周围仍有规则环线 |
| 树木 | `PASS` | 枝干稳定，轮廓更细 |
| 人物/花鸟 | `PASS`（N/A） | 无 |
| 色彩 | `PASS` | 石青石绿赭石更柔和，分层罩染感增强 |
| 材质 | `PASS` | 绢本/纸本底色保留，无塑料高光 |
| 整体 | `PARTIAL` | 木版画感明显减弱；山石/水纹仍需继续修 |
| **总状态** | **`PARTIAL`** | 风格改善，但未完全达标 |

### 3.4 A1 vs G3

- 对照图：`experiments/pipeline_b/static/A1_vs_G3_contact.png`
- 客观指标：`experiments/pipeline_b/static/A1_vs_G3_metrics.json`
  - A1 边缘密度 0.1625 / 高频比 0.0567 / 饱和度 0.1243
  - G3 边缘密度 0.1844 / 高频比 0.0642 / 饱和度 0.1592
  - **注意**：G3 的全局边缘/高频指标更高，是因为细线、树叶和纹理更多，不等于粗轮廓更多；线条粗细必须看局部放大图，不能用全局指标替代。

目视结论：G3 的屋脊、松树、山脊轮廓更细，颜色更分层，日式木版画感明显减弱；礁石水纹和山石条带仍有残留。

### 3.5 G3 长卷样片

- 产物：`experiments/pipeline_b/renders_fix/build-20261103-220644/final_9x16.mp4`
- 28.000 s / 1080×1920 / 24 fps / H.264 + AAC；解码 0；黑帧 0；8,112,906 B
- 与上一版 A1 样片使用同一脚本、同一时长、同一横移参数（840 px / 28 s ≈ 30 px/s）、同一绢纹强度；仅替换源图。
- 运镜/时序结构保持一致；首/中/末帧结构稳定，未发现拉伸或跳变。

### 3.6 验收对照

| 项目 | 结果 | 说明 |
|---|---|---|
| 粗黑闭合轮廓明显减少 | `PARTIAL` | 目视明显减少；仍有少量深色轮廓 |
| 不再呈现明显日式木版画观感 | `PARTIAL` | 木版画/浮世绘感明显减弱，但未完全消失 |
| 山石纹理不再明显机械重复 | `PARTIAL` | 条带减弱，仍有重复 |
| 水纹不再规则矢量同心圆 | `PARTIAL` | 同心圆减弱，礁石周围仍有环线 |
| 建筑/山体/植被结构稳定 | `PASS`（技术） | 与 A1 构图一致，无新变形 |
| 保留运镜与时序一致性 | `PASS`（技术） | 同脚本、同 28 s、同 30 px/s；人工待审 |
| 人工看片 | **PENDING** | 需确认风格是否达到宋代院体标准 |

## 4. 修改/新增文件

- `scripts/pipeline_ink.py`：舟体/倒影拆分、整数像素位移、水面下移并排除主体、云层上移。
- `scripts/compare_motion.py`：A/B 舟体面积/质心、树带差异、云带/静态区差异与局部裁切。
- `scripts/static_quality.py`：工笔检查表新增“水纹”。
- `experiments/pipeline_a/layers.json`：本样片图层参数。
- `experiments/pipeline_a/params/A_wan_baseline.json`、`jobs_wan_baseline.json`：Wan A 基线。
- `experiments/pipeline_b/params/G1.json`、`G2.json`、`G3.json`、`jobs_gongbi_fix.json`：工笔候选。
- `experiments/pipeline_b/static/G3_manual_review.json`、`G3_static_quality.json`、`A1_vs_G3_contact.png`、`A1_vs_G3_metrics.json`。
- 原始 A1、IA4、workflow、旧样片全部保留，未覆盖。

## 5. 复现命令

```powershell
# Wan A 基线（约 26 分钟）
scripts\start.ps1
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments/pipeline_a/jobs_wan_baseline.json --timeout 3600

# A -> 1080x1920 3 s
ffmpeg -y -v error -framerate 24 -i experiments/pipeline_a/wan_baseline/A_wan_baseline_%05d_.png ^
  -vf "scale=1080:1920:flags=lanczos,fps=24,format=yuv420p" -t 3.0 ^
  -c:v libx264 -crf 18 -preset medium -movflags +faststart -an experiments/pipeline_a/wan_baseline/A_wan_1080.mp4

# B 保护版（10 s 稳定 / 3 s A/B）
.venv\Scripts\python.exe scripts\pipeline_ink.py --source experiments/pipeline_a/static/IA4/IA4_ink_landscape_00001_.png ^
  --layers experiments/pipeline_a/layers.json --static-quality experiments/pipeline_a/static/IA4/static_quality.json ^
  --duration 10 --out experiments/pipeline_a/renders
.venv\Scripts\python.exe scripts\pipeline_ink.py --source experiments/pipeline_a/static/IA4/IA4_ink_landscape_00001_.png ^
  --layers experiments/pipeline_a/layers.json --static-quality experiments/pipeline_a/static/IA4/static_quality.json ^
  --duration 3 --out experiments/pipeline_a/renders

# A/B
.venv\Scripts\python.exe scripts\compare_motion.py --a experiments/pipeline_a/wan_baseline/A_wan_1080.mp4 ^
  --b experiments/pipeline_a/renders/build-20261103-214243/final_9x16.mp4 ^
  --out experiments/pipeline_a/compare_wan_vs_protected --duration 3

# 工笔候选（GPU 空闲时）
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments/pipeline_b/jobs_gongbi_fix.json --timeout 1800
.venv\Scripts\python.exe scripts\static_quality.py --image experiments/pipeline_b/static/G3/G3_court_green_ref_00001_.png ^
  --style court_green_fine_line --manual experiments/pipeline_b/static/G3_manual_review.json ^
  --out experiments/pipeline_b/static/G3_static_quality.json

# G3 长卷
.venv\Scripts\python.exe scripts\s2_build.py --style court_green_fine_line ^
  --source experiments/pipeline_b/static/G3/G3_court_green_ref_00001_.png --duration 28 --out experiments/pipeline_b/renders_fix

scripts\stop.ps1
```

## 6. 遗留问题

1. **云雾运动仍偏弱**：B 云带差异 2.92/255；可考虑从 Wan 输出中提取云雾局部素材，或提高云层位移/覆盖，但需重新验证是否带动山体。
2. **水面运动偏弱**：±4 px/8 s，属于“轻微生命感”，人工看片确认是否足够。
3. **山石条带、水纹同心圆仍有残留**：当前没有局部 inpaint 工作流；继续靠提示词/seed 的收益有限。下一步建议单独评估一个 inpaint 工作流（需要新工作流，不在本轮范围）。
4. **ControlNet 0.5 未测试**：当前没有 ControlNet 模型/节点；这是环境限制，不是参数选择。
5. **Wan A 只有 3 秒**：73 帧是当前已验证规格；更长基线需要多次生成或改变帧数，成本高且未验证。
6. **人工审查未完成**：所有修复项均为 `PARTIAL`，需看片后才能决定升为 `PASS_VERIFIED` 或调整重跑。

## 7. 状态汇总

| 项 | 状态 |
|---|---|
| Wan 区域运动遮罩 / 主体保护遮罩 | `NOT_RUN`（无兼容模型/工作流） |
| 孤舟主体保护（刚性 + 整数像素） | `PARTIAL`（技术通过，人工待审） |
| 倒影随舟体 | `PARTIAL`（技术通过，人工待审） |
| 云雾横移 | `PARTIAL`（偏弱） |
| 水面微动 | `PARTIAL`（偏弱） |
| 树丛闪烁修复 | `PARTIAL`（差异降至 0.20/0.46） |
| 工笔风格校正（G3） | `PARTIAL`（线条/色彩改善，山石/水纹残留） |
| ControlNet 0.5 实验 | `NOT_RUN`（无 ControlNet） |
| 工笔运镜/时序保持 | `PASS`（技术；同脚本同参数） |
| 人工审查 | `PENDING` |

---

## 8. 第二轮 C1/C2 调优（2026-11-03）

本轮未运行 ComfyUI/Wan；只改 `scripts/pipeline_ink.py` 与图层参数。G3 未修改。

### 8.1 基线

- B 原始保护版：`experiments/pipeline_a/renders/build-20261103-214235/final_9x16.mp4`（10 s / 1080×1920 / 24 fps），保留不动。
- B 指标：云带 3.5971、水面 5.0963、树带 3.5262、静态山体 0.0152（均为首帧→中帧平均差异，0–255）。

### 8.2 关键发现：水面遮罩取反

`subtract_box()` 原实现为 `Image.composite(zero, alpha, hole)`，参数顺序反了：**框外被清零、框内保留**。因此 B 的水面层实际只覆盖船体/倒影排除框内部，开放水面几乎没有进入动画层；B 的 5.10/255 水面差异主要来自船体与倒影位移，不是水面运动。这解释了人工审查“水面运动过弱、倒影基本静止”的根因。

本轮已改为 `Image.composite(alpha, zero, hole)`（框外保留、框内清零）。修复后 C1/C2 的开放水面层覆盖率从接近 0 恢复到 mean 0.08–0.10。

### 8.3 C1：只调云雾

参数（`experiments/pipeline_a/layers_c1_final.json`）：

| 项 | 值 |
|---|---|
| 云层运动 | 单向缓动 `96*(1-cos(t/10*π/2))`，10 s 位移 96 px |
| 透明度 | 0.82–0.98，周期 10 s |
| 云带 | y 0.46–0.63；羽化 35 px；水平边缘羽化 50 px |
| 云层增益 | 1.0（不放大原图云雾，避免拖出山脊） |
| 云雾补充层 | 程序化柔雾 plate，opacity 0.40，band 0.48–0.64，noise div 3，位移 160 px |
| 水面 | 位移 0（C1 只改云雾） |
| 舟体 | `anchored_boat`，0.6 px/s，整数像素，无旋转/缩放 |

产物：`experiments/pipeline_a/renders/build-20261103-224249/final_9x16.mp4`（10 s，解码 0，黑帧 0）。

| 指标 | B | C1 |
|---|---:|---:|
| 云带区域差异 | 3.5971 | **3.9148** |
| 水面区域差异 | 5.0963 | 5.0868（水面未动，差异来自舟体） |
| 树带区域差异 | 3.5262 | 3.5387 |
| 树区左/右（排除舟体） | 0.20 / 0.46 | 0.17 / 0.46 |
| 静态山体差异 | 0.0152 | 0.0075 |

目视：首/中/末帧无水印、无接缝；单向位移方向成立；未出现 160–220 px 大位移版本的“山脊/云雾双影”。

**素材限制**：把原图云雾层直接推到 160–220 px 或 alpha 增益 1.5–1.8 时，云带会拖出山脊与树线的重影；这是当前静帧云雾集中在树线、对比度低造成的，不是参数没调够。C1 选择不强行放大，云带指标 3.91，未达到 6.0–9.0 的观察区间。

### 8.4 C2：云雾 + 水面

参数（`experiments/pipeline_a/layers_c2_final.json`）：C1 基础上

| 项 | 值 |
|---|---|
| 水面 ROI | y 0.68–1.0 |
| 排除区 | 左岸/树 0–0.34、右岸/树 0.62–1.0（y 0.68–0.80）；船体/倒影包围盒 |
| 水面位移 | ±2 px / 10 s（低幅） |
| 水面波纹 | 叠加层 opacity 0.25、幅度 12 px、周期 3.333 s（0.3 Hz）、波长 40 px、亮度 ±10、边缘羽化 30 px |
| 舟体 | 仍为 `anchored_boat` 6 px / 10 s，整数像素 |

产物：`experiments/pipeline_a/renders/build-20261103-224331/final_9x16.mp4`（10 s，解码 0，黑帧 0）。

| 指标 | B | C2 |
|---|---:|---:|
| 云带区域差异 | 3.5971 | **4.0020** |
| 水面区域差异 | 5.0963 | **5.2173**（低水位区 5.4357） |
| 树带区域差异 | 3.5262 | 3.6973 |
| 树区左/右（排除舟体） | 0.20 / 0.46 | 0.37 / 0.53 |
| 静态山体差异 | 0.0152 | 0.0836 |

目视：水面及倒影出现轻微连续变化，未见果冻式整体变形、边界空洞或水面侵入岸线；舟体局部放大无旋转/缩放/形变。

**舟体刚性**：舟体/倒影是独立 RGBA 图层，几何面积不随帧变化；对齐后暗像素质心随 6 px 位移平移。原始像素面积在 10 s 内波动约 0.18–0.29%，来自 H.264 压缩与背景交界，不是形变；3 s A/B 的舟体面积波动为 0.09%。

### 8.5 输出与对照

- B：`experiments/pipeline_a/renders/build-20261103-214235/final_9x16.mp4`
- C1：`experiments/pipeline_a/renders/build-20261103-224249/final_9x16.mp4`
- C2：`experiments/pipeline_a/renders/build-20261103-224331/final_9x16.mp4`
- B/C1 指标：`experiments/pipeline_a/compare_B_vs_C1_final/compare.json`
- B/C2 指标：`experiments/pipeline_a/compare_B_vs_C2_final/compare.json`
- 全帧/云/水/舟对照：`experiments/pipeline_a/compare_B_C1_C2_final/frames_B_C1_C2.png`、`cloud_B_C1_C2.png`、`water_B_C1_C2.png`、`boat_B_C1_C2.png`
- C1/C2 参数：`experiments/pipeline_a/layers_c1_final.json`、`layers_c2_final.json`
- 本轮所有构建的 manifest 均记录 argv、图层哈希、输入哈希、ffprobe 与抽样帧。

### 8.6 状态

| 项 | 状态 |
|---|---|
| 水面遮罩取反修复 | `PASS_STATIC`（代码修复 + C1/C2 实际运行） |
| C1 云雾单向缓动 | `PARTIAL`（3.91/255；方向成立、无重影；未达 6–9 观察区间） |
| C2 水面微动 | `PARTIAL`（5.22/255，落在 3.5–5.5 观察区间；人工待审） |
| C2 舟体/倒影保护 | `PARTIAL`（刚性图层；3 s A/B 面积波动 0.09%） |
| 树丛/山体/岸线静态 | `PARTIAL`（树区 0.37/0.53，山体 0.084；低但未完全为 0） |
| 云雾 6–9 目标 | `NOT_MET`（素材限制） |
| 人工审查 | `PENDING_HUMAN_REVIEW` |

### 8.7 建议

推荐以 **C2** 作为人工复审候选：水面已从“几乎不动”变为可感知的低频微动，舟体/倒影保持刚性，树区与山体没有明显退化。云雾仍是弱项：当前静帧的云雾集中在树线、空间纹理不足，继续加大位移或透明度会产生重影；若手机端仍看不出云气流动，下一轮应使用独立云雾 plate 或复用已生成的 Wan A 云雾局部素材（不是重新跑 Wan），而不是继续推当前云雾层。
