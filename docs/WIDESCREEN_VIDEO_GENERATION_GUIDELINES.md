# 16:9 电影级横屏视频生成与清晰度控制工程规范

> **适用模型**：Wan 2.2-14B / Wan 2.1-14B I2V (ComfyUI-GGUF 渲染管线)  
> **适用产线**：Local-Drama-Studio 电影感短片、CourseWorkspace 技术科普演示  
> **核心目标**：彻底解决 16:9 横屏“面部糊化、高频杂乱、背景算力分散”的痛点，确保横屏成片获得与竖屏一致的高清毛孔与眼神光质感。

---

## 1. 为什么横屏会“糊”？（物理与算力三要素）

1. **垂直像素与潜空间有效载荷**：
   - 9:16 竖屏（480×832）：高度有 **832 像素**，VAE 压缩后高度有 **52 个 Latent Token**。
   - 16:9 横屏（832×480）：高度仅 **480 像素**，VAE 压缩后高度仅剩 **30 个 Latent Token**（垂直分辨率缩水 42%）。
2. **镜头景别与主体像素占比**：
   - 竖屏特写：人脸高约 350~400px，潜空间占 22~25 个 Token，五官与毛孔信息充足；
   - 横屏全身/大远景：人脸高仅 35~45px，潜空间仅占 **2~3 个 Token**，无论扩散去噪多少步，五官在解码时必然被平均化糊成一团。
3. **高频背景与去噪算力稀释**：
   - 横屏画面通常包含街头落叶、远处砖墙、车流等海量高频信息，蒸馏扩散模型（6 步 LoRA）会将有限注意力分散到全屏背景，导致人物动态帧清晰度出现断崖式下跌（实测边缘能量衰减 24.2%）。

---

## 2. 横屏视频生成的 4 项核心工程规范

### 规范一：首帧镜头景别控制（最重要的零成本措施）
* **禁止**：在 480P 规格下使用“全身站立远景”、“大场景街拍人物全身漫步”。
* **推荐**：
  * **中景胸像 (Medium Close-Up)**：人物腰部以上，人脸高度占画面高度的 **30%~40%**（约 150~200px）；
  * **电影级特写 (Close-Up / Cowboy Shot)**：好莱坞式横向宽银幕特写，强调眼神、微表情与发丝，人脸占画面高度 **50% 以上**（240px+）。
* **收益**：人脸在潜空间占 12~16 个 Token 以上，彻底杜绝“无五官面具脸”。

### 规范二：景深与背景虚化控制（引导注意力算力）
* **提示词策略**：横屏首帧生图与视频提示词中，显式加入电影级大光圈参数：
  * `shallow depth of field`, `cinematic bokeh`, `f/1.4 aperture`, `soft blurred autumn street background`
* **工程逻辑**：迫使背景变为低频柔和色块，将扩散模型的去噪算力 100% 集中在人物面部、服饰动态与首饰反光上。

### 规范三：分辨率档位与硬件权衡
针对 Intel Arc A750 8GB VRAM + 64GB DDR5 内存的硬件配置：

| 档位 | 分辨率 | 潜空间尺寸 | 渲染耗时 (49帧) | 显存/内存开销 | 适用场景 |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **标准档 (480P)** | `832 × 480` | $52 \times 30$ | ~28-30 min | 显存 6.5GB / 内存 34GB | **搭配中近景特写使用**（日常主力高效档） |
| **进阶档 (720P)** | `1280 × 720` | $80 \times 45$ | ~50-60 min | 显存 7.2GB / 内存 46GB | **必须使用中远景/全身复杂运动镜头时使用** |

### 规范四：后处理增强与人脸修复流水线
* **基础流程**：ComfyUI Wan 14B (16fps) $\rightarrow$ FFmpeg 2x Lanczos 超分至 1664×960 $\rightarrow$ minterpolate 光流 32fps 补帧。
* **人脸保真增强扩展**：若镜头必须包含中远景，在视频导出后，通过 CPU 批处理挂载 `CodeFormer` 或 `GFPGAN` 对人脸执行 `face_restore`，单帧仅需 80ms，无额外显存开销。

---

## 3. 标准 16:9 横屏工作流首帧提示词模板

```text
[主体描述] A cinematic medium close-up of a sophisticated 25-year-old East Asian woman,
[景别与构图] 16:9 widescreen composition, waist-up framing, centered subject,
[光影与质感] golden hour autumn sunlight glancing across cheekbones, authentic skin pores, intricate hair strands blowing gently in wind,
[背景处理] softly blurred Parisian avenue background, creamy bokeh, shallow depth of field,
[画质约束] 35mm film photography, Wong Kar-wai style, master lighting, no plastic skin, no doll-face.
```
