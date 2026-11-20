# 视觉风格与 LoRA 工业化调用指南 (V2.0)

> **核心结论**：彻底终结“纯 Prompt 许愿式开发”。在 FLUX.3 架构下，全面采用 **“双 LoRA 物理注入（角色槽位 + 美学槽位） + 4 大二次元/国风流派”** 工业级生产管线。

---

## 一、 为什么必须干掉“许愿式开发”？

在旧体系中，系统曾维护了 23 套纯文本提示词风格包，试图通过在 Prompt 里拼接 `porcelain skin, 8k raw, xuanji 3d, makoto shinkai` 等修饰词来让量化底模“碰运气”。

**实测证明，这种“许愿式开发”存在三大死穴**：
1. **面容不可控（恐怖谷与素人苦相）**：底模没有对应特征权重，AI 只能在极端畸形的大头塑料外星人与苦涩呆滞的素人间剧烈摇摆；
2. **多镜头完全漂移**：每个镜头的脸部骨相、五官、发型完全随机，根本无法剪辑成连贯叙事短剧；
3. **与视频模型（Wan2.2）严重冲突**：写实人脸在 8GB 显存下生成视频时五官融化变形（导致一直处于 `BLOCKED` 状态）。

**新体系解法**：用 **几十兆的轻量 LoRA** 对底模进行物理级特征收束，彻底把“随机抽卡”转变为“确定性工业级输出”。

---

## 二、 4 大二次元与国风插画流派（全景指南）

二次元与国风插画由于**线条与色块容忍度极高，天然规避肖像权纠纷，且对 Wan2.2 视频生成动态极其友好**，是诗词古典短剧的最高优先级方向。

| 流派方向 | 视觉特征与审美质感 | 检索关键词 (Civitai/HF) | 推荐美学 LoRA 权重 | 提示词核心锚点 (Prompt Anchors) |
|---|---|---|---|---|
| **1. 国风古韵厚涂 / 唯美仙侠** | 二次元精致骨相 + CG厚涂光影，衣袂流光，极具东方神话史诗感。 | `Chinese Anime`, `Guofeng`, `Xianxia`, `Semi-realistic Anime` | `0.65 ~ 0.75` | `chinese anime, guofeng illustration, refined lineart, flowing silk drapery, luminous lighting` |
| **2. 新海诚式光影 / 唯美壁纸流** | 积雨云、丁达尔光线、高饱和通透蓝金对撞与空间透视。适合大景山水与诗词空镜。 | `Makoto Shinkai`, `Scenery Anime`, `Vibrant Lighting` | `0.50 ~ 0.65` | `scenery anime, makoto shinkai style, dramatic cumulus clouds, volumetric sunlight, atmospheric depth` |
| **3. 赛璐璐 / 现代番剧平涂** | 干净的二分阴影、利落深色描边，经典电视动画胶片质感。适合轻快叙事。 | `Anime Screencap`, `Cel Shading`, `Retro Anime` | `0.60 ~ 0.70` | `anime screencap, cel shading, clean crisp outlines, flat color, authentic animation still` |
| **4. 东方水墨手绘 / 绘本插画风** | 宣纸纸纹肌理、低饱和高级灰、水墨水彩自然渗染，掩盖 AI 细微瑕疵。 | `Watercolor Anime`, `Ink Wash Illustration`, `Ghibli style` | `0.55 ~ 0.70` | `traditional ink wash illustration, watercolor anime, aged rice paper texture, soft diffuse edges, zen aesthetic` |

---

## 三、 双 LoRA 黄金法则与调用规范

在 8GB 显卡安全线（`--profile safe8g`）下，**最多挂载 2 个 LoRA，总权重严格限制在 1.20 ~ 1.40**。

### 1. 槽位配置标准

```text
[FLUX.3 Klein GGUF 底模]
       │
       ├─► 槽位 A：角色 LoRA (0.75 ~ 0.80) ──► 仅人物镜头挂载，纯风景空镜自动置空
       │
       ├─► 槽位 B：美学 LoRA (0.45 ~ 0.55) ──► 全片统一应用，轻量铺底不抢脸部权重
       │
       └─► 场景与构图：彻底剔除 LoRA ──► 完全由 Python 编译层的镜头语言接管
```

### 2. 提示词互斥净化规则
当切换到二次元/插画风格包时，编译层必须自动过滤写实词汇：
- ❌ **严禁词**：`photorealistic`, `8k raw photo`, `35mm film still`, `skin pores`, `realistic human anatomy`
- ✅ **替换词**：`illustration`, `anime aesthetic`, `clean outlines`, `painterly texture`, `masterpiece artwork`

---

## 四、 本地已就绪资产与调用模板

### 1. 已验证就绪的角色 LoRA 资产（位于 `runtime/ComfyUI/models/loras/`）
- `girlslikeflux_jjy.safetensors`：鞠婧祎（仙侠灵动美少女，触发词 `girlslikeflux_jjy`）
- `girlslikeflux_lyf5.safetensors`：刘亦菲（清冷脱俗神仙姐姐，触发词 `girlslikeflux_lyf5`）
- `girlslikeflux_cdl.safetensors`：陈都灵（温婉古典书卷白月光，触发词 `girlslikeflux_cdl`）

### 2. 生产级双 LoRA 调用示例（Python / CLI）
```powershell
# 使用通用双 LoRA 工作流
.venv\Scripts\python.exe scripts\r0_comfy_probe.py `
  --workflow workflows\flux3_dual_lora_t2i_api.json `
  --params experiments\actors_test\params_dual.json `
  --out experiments\actors_test\output_dual `
  --timeout 600
```

`params_dual.json` 配置标准：
```json
{
  "positive_prompt": "girlslikeflux_cdl, chinese anime, guofeng illustration, breathtaking scenery...",
  "lora_name_1": "girlslikeflux_cdl.safetensors",
  "lora_strength_1": 0.78,
  "lora_name_2": "chinese_ink_style_flux.safetensors",
  "lora_strength_2": 0.50,
  "width": 576,
  "height": 1024,
  "seed": 20261125,
  "steps": 18,
  "cfg": 1.0,
  "filename_prefix": "demo_dual"
}
```


---

## 五、 商业广告、海报设计与 VFX 特效 LoRA 工业化指南

### 1. 4 大商业高价值 LoRA 规范
| LoRA 类别 | 核心价值与解决痛点 | 适用场景 | 推荐权重 |
|---|---|---|---|
| **商业影棚光影**<br>*(Studio Lighting)* | 注入软箱漫射高光、金属高光反光、暗调奢华光影，消除塑料感。 | 3C 数码、高端护肤、酒水饮料、汽车主视觉。 | `0.55 ~ 0.70` |
| **平面排版网格**<br>*(Poster Layout / Grid)* | 强制底图产生瑞士网格布局，预留大面积负空间（留白区）。 | 商业海报 KV、电商首图、杂志封面背景。 | `0.50 ~ 0.65` |
| **微观物理材质**<br>*(Macro Texture)* | 精准生成飞溅水滴（Splash）、磨砂玻璃、丝绸流转等微观物理质感。 | 饮品动感、精华液护肤、微距工业细节。 | `0.50 ~ 0.65` |
| **粒子能量特效**<br>*(VFX / Particle)* | 批量产出金色粒子流、火焰、烟雾缭绕等非实体元素素材。 | 商业片头、高燃转场、科技宣发底图。 | `0.55 ~ 0.75` |

### 2. 海报与排版工程解耦法则（严禁 LoRA 排版）
- **AI 生图层**：Prompt 必须包含 `clean negative space on top and bottom, minimalist composition, uncluttered area for typography`，仅输出干净视觉底图；
- **确定性排版层**：使用 Python Pillow / SVG 模板叠加高清晰度中文标题（如思源黑体/等线）、副标、英文、辅助网格线，实现 **100% 无错字、可批量脚本替换**；
- **VFX 调度层**：由 `r3_build` / FFmpeg `filter_complex` 进行毫秒级时间轴混合（`screen/add` 混合模式），不依赖静态 LoRA。
