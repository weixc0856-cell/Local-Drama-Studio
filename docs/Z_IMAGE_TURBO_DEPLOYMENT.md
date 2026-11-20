# Z-Image Turbo & FLUX.3 Klein 双管线工程化落地与测试部署规范

> **设备基线**：Intel Arc A750 (8GB VRAM) + 64GB DDR5 RAM + Windows 11  
> **核心原则**：底层模型目录隔离 + API 工作流 JSON 解耦 + Python 统一配置路由

---

## 一、物理权重存放与 ComfyUI 路径映射（<AI_HOME_ROOT>/）

为确保 8GB 显存安全并杜绝模型误加载，所有权重统一收敛于外部模型根目录 `<DRAMA_MODELS_ROOT>/`：

```text
<DRAMA_MODELS_ROOT>/
├── diffusion_models/
│   ├── flux3/
│   │   └── flux-3-image-klein-Q4_K_M.gguf      # 管线 A：FLUX.3 Klein
│   └── z_image/
│       └── z-image-turbo-Q4_K_M.gguf          # 管线 B：Z-Image Turbo 主模 (~4.2GB)
├── text_encoders/
│   ├── qwen3vl_4b_int8_convrot.safetensors    # FLUX.3 配套编码器
│   └── zimage_qwen3_4b_Q4.gguf                # Z-Image 配套 Qwen3-4B (~2.7GB)
└── vae/
    └── flux2-vae.safetensors                  # 两者通用 16通道 VAE
```

### ComfyUI `extra_model_paths.yaml` 映射状态
在项目 `config/comfyui_extra_model_paths.yaml` 中已配置：
* `diffusion_models` 映射到 `diffusion_models/`。ComfyUI 会自动识别子目录为 `flux3/xxx.gguf` 与 `z_image/xxx.gguf`。
* `text_encoders` 映射到 `text_encoders/`。
* `vae` 映射到 `vae/`。

---

## 二、工作流 API 解耦（8GB 显存核心安全线）

> [!CAUTION] 
> **严禁在一个工作流大图中使用 Switch 或 Bypass 节点同时挂载两个大模型！**  
> 在 Intel Arc A750 (8GB 显存) 上，ComfyUI 可能会在初始化时尝试预加载非激活分支的文本编码器与权重，极易直接触发 Out Of Memory (OOM) 崩溃。

### 解耦后独立的 API JSON
1. **`workflows/flux3_klein_api.json`**：
   * 专攻欧美街拍、杂志硬照、Leica 光学颗粒。
   * 支持挂载 Realism / 东方微调 LoRA（`strength: 0.35~0.40`）。
   * 采样 16 步（或极速 6~8 步），CFG 1.0，`er_sde` + `simple`。
2. **`workflows/z_image_turbo_api.json`**：
   * 专攻东亚纪实写实、电影雨夜、江南/东京/首尔街头自然光影。
   * **零 LoRA 裸跑**（完全剥离旧 FLUX LoRA，防止架构维度不匹配报错及面具感）。
   * 采样 8 步（6~9 步），CFG 1.0（禁止调高），`euler` + `simple`。
   * **文本编码器 CPU 卸载**：`device: "cpu"` 借助 64GB 内存轻松承载，将完整的 8GB 显存留给单流 DiT 与 Latent 解码。

---

## 三、参数路由与自动化调用入口

### 1. 统一配置文件：`config/pipelines.yaml`
包含完整路由表、默认步数、CFG、采样器及关键词自动分流规则。

### 2. 生成入口：`scripts/generator.py`
支持手动指定引擎或根据提示词内容全自动路由：

```bash
# 1. 自动分流：提示词含 Tokyo / 雨夜，自动路由到 z_image_turbo
python scripts/generator.py --prompt-file prompts/day04_tokyo.txt --batch 4

# 2. 自动分流：提示词含 Paris / Saint-Germain，自动路由到 flux3_klein
python scripts/generator.py --prompt-file prompts/day04_paris.txt --batch 4

# 3. 手动显式指定管线
python scripts/generator.py --engine z_image_turbo --prompt-file prompts/day04_shanghai.txt --batch 2
```

### 3. 公共后处理：`scripts/postprocess.py`
无缝衔接两条管线的出图产物：
```bash
# 执行元数据剥离、导出 Patreon 纯净原图、导出社媒 Web 优化图并拼装四宫格色板
python scripts/postprocess.py
```
* **`outputs/raw_4k/`**：剥离 ComfyUI 提示词与本地路径等私有信息的高清纯净无水印原图（Patreon 会员交付）。
* **`outputs/social_web/`**：Lanczos 重采样 + 高保真压缩的 Web 格式图（X / 小红书引流发布）。
* **`outputs/social_web/latest_showcase_4grid.jpg`**：自带 35mm 纪实胶片色板与排版的四宫格大图。

---

## 四、Z-Image Turbo 提示词习惯微调

Z-Image Turbo 底层接入 **Qwen3-4B** 语言模型，与传统 SDXL / FLUX 区别显著：
* **善用自然长句**：描述人物姿态、镜头焦段、空间层次（前景/中景/背景）、光影漫反射物理逻辑。
* **无需负面词堆砌**：原生少步数蒸馏模型，负面提示词置空即可。
* **东亚骨相原生直出**：无需外部人像 LoRA 纠偏，原生长相清秀自然，微孔与皮肤通透感极佳。
