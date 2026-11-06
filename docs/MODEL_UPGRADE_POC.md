# 三模型替换方案：本机可行性核验与 POC 任务书

- 核验日期：2026-11-06
- 核验对象：FLUX.3 Image Klein、VoxCPM2、MiniMax H3 / VDN-H3
- 核验方式：本机实测 + 官方仓库文件清单 + 现有运行时源码检查
- 结论状态词沿用 `docs/README.md`：`PASS_VERIFIED / PASS_LIMITED / FAIL / NOT_RUN`

## 0. 结论摘要

| 替换项 | 模型真实存在 | 在本机（A750 8 GB / i7-13700K / 64 GB RAM）可运行性 | 建议 | 优先级 |
|---|---|---|---|---|
| 图像 FLUX.2 Klein → FLUX.3 Klein | 是（2026-10 发布） | **中高**：ComfyUI 0.43.0 已内置 flux3 节点；GGUF 与 int8 两条路径都在；XPU 上 int8 矩阵乘实测可用；端到端未测 | 做 POC | P0 |
| 配音 CosyVoice2 → VoxCPM2 | 是 | **中**：官方只列 CUDA；本机只能走 CPU（RTF 未知）或未验证的 XPU；与现有 TTS 层耦合深 | 做 POC，独立服务 | P1 |
| 视频 Wan2.2 TI2V 5B → MiniMax H3 | 是 | **低**：33B；最小本地集约 40 GB；GGUF 被现有节点直接拒绝（实测）；文本编码器 15.7 GB 已超出显存 2 倍；无任何 XPU 证据 | 暂不部署，只做一次受控探测 | P2 / 暂缓 |

一句话判断：**粘贴方案里“三项全换风险很高”的结论成立；但它对 FLUX.3 的可行性低估了，对 H3 的低显存路径高估了。** 本机最该先做的是 FLUX.3，其次是 VoxCPM2，H3 应当被明确挡在生产线之外。

## 1. 本机实测基线（本次核验采集）

| 项 | 实测值 |
|---|---|
| GPU | Intel Arc A750，ComfyUI 报告 `vram_total = 8,321,540,096` B（≈ 8.32 GB） |
| CPU / RAM | i7-13700K / 64 GB（核验时可用 26.1 GB，ComfyUI 当时占用中） |
| 系统盘余量 | D: 382 GB 可用 |
| ComfyUI | 0.43.0，`torch 2.15.0+xpu`，`triton 3.9.0`，`comfy-kitchen 0.2.40` |
| 自定义节点 | 仅 `ComfyUI-GGUF 2.0.0`（2026-01 提交） |
| 现有图像链路 | FLUX.2 Klein 4B Q4_K_M 2.60 GB + Qwen3-4B TE 8.04 GB + FLUX.2 VAE 0.34 GB |
| 现有视频链路 | Wan2.2 TI2V 5B Q4_K_M 3.43 GB + UMT5 6.73 GB + Wan VAE 1.41 GB |
| 现有语音链路 | CosyVoice 运行时（CPU，端口 50000），`voice/tts.py` 与 CosyVoice 的 `/tts` 契约强耦合 |

## 2. 逐项核验

### 2.1 FLUX.3 Image Klein（P0）

**事实（官方仓库文件清单，实查）**

| 角色 | 文件 | 大小 |
|---|---|---|
| 扩散模型（蒸馏，推荐） | `flux3-image-klein-int8-convrot.safetensors` | 5.83 GB |
| 扩散模型（蒸馏 bf16） | `flux3-image-klein-bf16.safetensors` | 11.10 GB |
| 扩散模型（社区 GGUF Q4_K_M） | `flux-3-image-klein-Q4_K_M.gguf`（unsloth） | 3.67 GB |
| 文本编码器 | `qwen3vl_4b_int8_convrot.safetensors` | 4.86 GB |
| 文本编码器（bf16） | `qwen3vl_4b_bf16.safetensors` | 8.88 GB |
| Prompt 放大器（可选） | `qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors` | 6.72 GB |
| VAE | `flux2-vae.safetensors` | 0.34 GB —— **本机已有，无需重下** |

**本机兼容性核验**

| 检查项 | 结果 | 证据 |
|---|---|---|
| ComfyUI 版本要求 0.41.0+ | 满足（0.43.0） | `/system_stats` |
| `flux3` 模型类 | 已内置 | `comfy/ldm/flux3/`、`supported_models.py` 中 `image_model: flux3` |
| `CLIPLoader` 支持 `flux3` | 是 | `/object_info` 的 type 枚举含 `flux3` |
| Prompt 放大器节点 | 模板用 `CLIPLoader(flux3)` + `TextGenerate`，两点均在 | `/object_info` |
| 蒸馏版本参数 | 16 步 / CFG 1 / `er_sde` | 官方模板 |
| GGUF 能否被现有 GGUF 节点接受 | **能**：该 GGUF 的 `general.architecture = "flux"`，在 `IMG_ARCH_LIST` 白名单内 | 实测读取 GGUF 头部 |
| XPU int8 矩阵乘 | **可用**：`mm_int8()` 在 `xpu` 上返回 int32 正确结果 | 实测调用 `comfy_kitchen.backends.eager.quantization.mm_int8` |
| 端到端出图 | **未测**（未下载权重） | — |

**两个关键判断**

1. 粘贴文本认为“社区 GGUF 不能说明问题、A750 未知”。实际上 GGUF 是这里最稳的路径：本机已经用 `UnetLoaderGGUF` 跑通 FLUX.2 与 Wan，FLUX.3 的 GGUF 声明架构为 `flux`，能通过现有节点白名单；Q4_K_M 只有 3.67 GB，接近现有 FLUX.2 的 2.60 GB。**风险比粘贴方案估计的低一档。**
2. Prompt 放大器不是可忽略项。BFL 文档明确写 “Always run a prompt upsampler”，因为 Klein 是在长描述上训练的。本项目已有 `aesthetics.py` 的有序提示词编译器，能部分替代，但必须用同一组镜头做“开/关放大器”的对照，不能直接假设可省。

**授权变化（重要）**

- FLUX.3 Klein 是 **FLUX Kommunity License**：年营收低于 500 万美元可免费商用，且要求内容过滤与必要的 AI 标注；不得用于训练其他模型。
- 现有的 FLUX.2 Klein 4B 在台账里登记为 **Apache-2.0**。
- 也就是说，这次替换在能力上可能是升级，在**授权自由度上是降级**。必须同步登记到 `docs/ASSET_AND_LICENSE_REGISTRY.md`，不能只记“可商用”。

### 2.2 VoxCPM2（P1）

| 项 | 事实 |
|---|---|
| 权重 | `model.safetensors` 4.58 GB + `audiovae.pth` 0.38 GB（另有 tokenizer ≈ 3.7 MB） |
| 授权 | Apache-2.0（代码与权重）；TOS 另附伦理条款（禁止冒充、需 AI 音频披露） |
| 官方设备 | `auto / cpu / mps / cuda / cuda:N` —— **没有 xpu** |
| 官方显存 | ≈ 8 GB（bf16） |
| 官方速度 | RTF ≈ 0.30（RTX 4090），Nano-vLLM ≈ 0.13；无 CPU 数据 |
| 本机可用路径 | CPU（确定可用，速度未知）或先试 `xpu`（未验证） |
| 与现有生产线的距离 | 远：`voice/tts.py` 直接按 CosyVoice 的 `/tts`、`model_class`、`model_dir` 校验；换后端要新增适配层与运行时校验分支 |

**判断**：这是三项里唯一“边界清楚、可独立验收”的。它不占 GPU、不进 ComfyUI，做成独立服务后与主线的耦合只有一条 HTTP 契约。但要注意：**2B 不等于更好听**。现有 `narrator_self` 零样本用的是项目所有者本人参考音，CosyVoice2-0.5B 已经在生产中；VoxCPM2 的真实增量是 48 kHz 输出、声音设计、方言与情绪控制，而不是“音质必然更好”。必须盲听 A/B，不能按参数量预设结论。

### 2.3 MiniMax H3 / VDN-H3（P2，暂缓）

| 项 | 事实 |
|---|---|
| 规模 | 约 33B 全模态（文本/图/视频/音频 → 视频 + 原生立体声） |
| 最小本地集 | pruned int8 DiT 20.97 GB + Qwen3-VL-32B TE 15.69 GB + 视频 VAE 2.81 GB + 音频 VAE 0.61 GB ≈ **40.1 GB** |
| 完整集 | Comfy-Org 重打包仓库合计约 433 GB |
| ComfyUI 支持 | 0.43.0 已内置 `MiniMaxH3*` 节点，版本不是障碍 |
| GGUF 能否被现有节点加载 | **不能**。unsloth 的 H3 GGUF 没有 `general.architecture` 元数据，进入 `detect_arch`；用 532 个张量名实测返回 `AssertionError: Unknown model architecture!` |
| 显存 | 单 DiT 20.97 GB ≈ 显存的 2.5 倍；单文本编码器 15.69 GB ≈ 显存的 1.9 倍 |
| 内存 | DiT + TE 工作集约 37 GB；本机 64 GB 总量，但 8080 的 CPU LLM 常驻约 19 GB —— **两者不可同时运行** |
| XPU 证据 | **零**。官方文档只写 NVIDIA（3060 起步），社区硬件表只覆盖 NVIDIA 与 Apple Silicon |
| 低显存实测只来自 | NVIDIA 8 GB 笔记本（sm_120）+ 16 GB RAM：10 s / 768×1024 / 8 步 ≈ 14.3 min，20 步 ≈ 33.8–43.5 min |
| 授权 | MiniMax H3 Community License：适用地域**排除 EU/UK/韩国/美国**；年营收 2000 万美元以下可商用；商用产品界面需显著标注 “MiniMax H3”；不得用输出改进其他模型 |

**判断**：H3 的价值主张（多模态参考、原生音频、15 s 长镜头）确实不是 Wan 能给的，但在本机上它是“换硬件平台”而不是“换模型”。仅文本编码器就装不进 8 GB 显存，所有路径都退化为逐层换入换出；而现有 Wan 是 5B / 3.43 GB，能完整驻留。**在拿到 XPU 上成功跑完一段 5 s 片段的证据之前，不应把它写进任何生产计划。**

另有一条本项目特有的反对理由：H3 的原生音频与我们现有的 CosyVoice/VoxCPM2 旁白层、`audio_timeline` 多轨混音是两套东西。引入它等于同时引入一套新的音频 QA，而音频并不是当前瓶颈。

## 3. 与粘贴方案的差异（需要纠正的地方）

1. **FLUX.3 的 GGUF 路径被低估。** 实测其 GGUF 架构字段为 `flux`，现有 `ComfyUI-GGUF` 白名单接受；Q4_K_M 3.67 GB，与现有链路同量级。
2. **FLUX.3 的授权被高估。** 不是 Apache-2.0，是 FLUX Kommunity（500 万美元门槛 + 内容过滤 + AI 标注）；现有 FLUX.2 Klein 4B 反而是 Apache-2.0。
3. **Prompt 放大器不能默认省略。** 官方要求始终运行；只能做对照实验来证明“我们的长提示词可以替代它”。
4. **H3 的“8 GB 可跑”不能套到本机。** 那个结论来自 NVIDIA 笔记本 + 16 GB RAM 的实测，且绑定 NVIDIA 的 int8/自定义 kernel；本机是 XPU，且连 GGUF 都被现有加载器拒绝。
5. **H3 的 GGUF 在本机是硬阻断。** 不是“慢”，是 `UnetLoaderGGUF` 直接抛异常。
6. **VoxCPM2 官方不支持 xpu。** RTF 0.30 是 RTX 4090 的数，本机只能先按 CPU 估算。
7. **“三项全换会失去问题定位能力”这一条成立**，应当坚持新旧双轨。

## 4. 本地 AI 服务 放置方案

原则：不移动、不覆盖现有文件；新增模型一律进子目录；顶层只允许 llama.cpp 的 `.gguf`（`start_server.bat` 只扫顶层）。

```
models\
  diffusion_models\
    flux3\        flux-3-image-klein-Q4_K_M.gguf                 3.67 GB   (P0)
                  flux3-image-klein-int8-convrot.safetensors    5.83 GB   (P0 备选)
    minimax_h3\   minimax_h3_fl2va_pruned_int8_convrot.safetensors 20.97 GB (P2)
  text_encoders\
                  qwen3vl_4b_int8_convrot.safetensors           4.86 GB   (P0)
                  qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors 6.72 GB (P0 对照用)
                  qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors  15.69 GB  (P2)
  vae\
                  minimax_h3_video_vae_int8_convrot.safetensors 2.81 GB   (P2)
                  minimax_h3_audio_vae_fp32.safetensors         0.61 GB   (P2)
  voxcpm2\        model.safetensors 4.58 GB + audiovae.pth 0.38 GB + tokenizer (P1)
```

- ComfyUI 已通过 `extra_model_paths.yaml` 映射 `diffusion_models`、`text_encoders`、`vae`，子目录可递归扫描，**不需要改 yaml**。
- VoxCPM2 不是 ComfyUI 模型，放 `models\voxcpm2\`，由独立服务加载。
- 磁盘预算：P0 最小 8.53 GB（+6.72 GB 放大器）；P1 4.96 GB；P2 40.08 GB。全部下载约 60.3 GB，D: 现有 382 GB，充足。
- 内存预算：P0/P1 与现有链路同量级；P2 需要约 37 GB 工作集，且**必须确认 8080 的 CPU LLM 未运行**。
- 授权门：BFL 官方仓库是 gated，需要先在 Hugging Face 接受许可再下载；unsloth 的 GGUF 不受此限，但授权仍按 BFL 原许可执行。

## 5. POC 任务书

所有 POC 独立于生产配置；**验收通过前不写入 `config/models.yaml`**，不改 `config/styles.yaml`，不覆盖任何现有模型。

### POC-A：FLUX.3 Klein（建议立即执行）

1. 下载最小集：`flux-3-image-klein-Q4_K_M.gguf` + `qwen3vl_4b_int8_convrot.safetensors`；VAE 复用。
2. 用现有 `comfy.batch` 的 API 工作流格式，先跑 1 张 576×1024，记录：加载方式、单张耗时、峰值显存、是否回退 CPU。
3. 同一组 4 个镜头、同一提示词、同一随机种子，与 FLUX.2 Klein 做 A/B；输出到新的 `experiments/flux3_poc/`，不覆盖 `experiments/r1`。
4. 对照项：
   - 关放大器 vs 开放大器（同一提示词），判断能否用现有长提示词替代 6.72 GB 的 9B 放大器。
   - 2~3 张参考图编辑，与现有 `ReferenceLatent` 结果对比工笔细线与风格漂移。
5. 晋级条件：
   - 576×1024 单张 ≤ 3 min，且无 OOM；
   - 人工盲评在“细节/构图/风格一致性”至少一项明确更好，且没有更差项；
   - 授权登记完成（Kommunity License、营收门槛、内容过滤、AI 标注）。
6. 停止条件：单张 > 5 min、OOM 无法通过降低分辨率规避、或质量无可见提升 → 保留 FLUX.2，结论写 `PASS_LIMITED` / `FAIL` 并记录日志路径。

### POC-B：VoxCPM2（POC-A 之后或并行）

1. 独立 venv（不并入根 `.venv`，不装进 ComfyUI venv）；先尝试 `xpu`，失败则固定 `cpu`。
2. 独立端口（建议 50001，仅实验期，用完即停），不改 `config/settings.yaml` 的 50000 契约。
3. 参考音沿用已授权的 `assets/audio/prompts/my_voice_clean_v1.wav`（本人录音），保证声音权利不变。
4. 同一段 7 句旁白，CosyVoice2 与 VoxCPM2 各生成 3 次，盲听比较：咬字、韵律、断句、音色稳定性、时长漂移、48 kHz 与 24 kHz 混音后的差异。
5. 晋级条件：盲听在中文诗词韵律上不劣于 CosyVoice2 且至少一项明确更好（须有人工评审记录）；接口适配层能复现现有 manifest/断点续跑。RTF 只记录、不作门槛——2026-11-06 决策：质量优先，速度不作为否决条件。
6. 停止条件：中文韵律明显更差（“盲听不劣于基线”不成立）、或适配层需要改动 `tts.py` 的生产校验语义。

### POC-C：MiniMax H3（暂缓，需先满足前置条件）

1. 前置条件（缺一不做）：拿到“非 NVIDIA 设备上 H3 完成一次前向”的公开证据，或接受一次纯探针式失败测试。
2. 若执行：只下载 `pruned_int8_convrot` DiT + `nvfp4_awq` TE + 两个 VAE（40.08 GB）；跑 1 段 5 s、576×1024；记录墙钟时间、RAM 峰值、是否发生磁盘换页。
3. 硬性停止条件：单段 > 90 min、OOM、或任何算子回退到 CPU 导致不可接受 —— 结论记为 `A750_NOT_SUPPORTED`，不再重复尝试。
4. 即使通过，也必须先回答“原生音频与现有旁白层如何共存”，否则不进入生产。

### 晋级后的收尾（三项通用）

- 写入 `config/models.yaml`（含精确 `sizes`，沿用现有“大小不符即失败”的契约）。
- 更新 `docs/ASSET_AND_LICENSE_REGISTRY.md`（文件、哈希、许可、营收门槛、内容过滤义务）。
- 保留旧模型与旧工作流，所有产物记录模型版本、工作流哈希、种子与提示词。
- 只在有人工评审记录后才允许把风格质量标为 `PASS_VERIFIED`。

## 6. 明确不做的事

1. 不把三项一起切到生产；一次只晋级一个，保留回退。
2. 不在验收前删除或替换 `flux-2-klein-4b-Q4_K_M.gguf`、`Wan2.2-TI2V-5B-Q4_K_M.gguf`。
3. 不因为 H3 是 33B 就假设它比 Wan 5B 更快或更好。
4. 不在 8080 的 CPU LLM 运行时启动 H3 探测（内存会撞车）。
5. 不用厂商在 4090/5090 上的数字替代本机实测。

## 7. POC-A 执行记录（2026-11-06，阶段一：不开提示词放大器）

### 7.1 文件与完整性

| 文件 | 放置位置 | 大小 | SHA-256 校验 |
|---|---|---|---|
| `flux-3-image-klein-Q4_K_M.gguf` | `models\diffusion_models\flux3\` | 3,666,908,064 B | 与官方 LFS `a0fe17e2…` 一致 |
| `qwen3vl_4b_int8_convrot.safetensors` | `models\text_encoders\` | 4,858,559,240 B | 与官方 LFS `32de113c…` 一致 |
| `flux2-vae.safetensors` | 复用现有 | 336,211,292 B | 未变 |

BFL 官方仓库为 gated（未授权返回 401），实际从同名镜像 `ml-resources/flux-3-image-klein-comfy` 下载，再用官方 LFS 的 SHA-256 逐字节校验，全部一致。

### 7.2 首次运行失败（非模型问题）

第一次提交时 ComfyUI 进程在 `comfy/samplers.py:1435`（`set_steps` 里的 `.to(xpu)`）触发 `Windows fatal exception: access violation` 并退出。日志显示同一进程在此之前刚被全局中断过一个 Wan 任务（`Global interrupt`），中断后未重启就继续提交新任务。重启 ComfyUI 后，同一份工作流一次成功。

结论：这是 XPU 在任务被中断后的脏状态，不是 FLUX.3 的问题；但它是一条可复用的操作规则——**中断 GPU 任务后应重启 ComfyUI，再提交新任务**。

### 7.3 实测耗时（576×1024，16 步，CFG 1，er_sde，GGUF Q4_K_M）

| 任务 | 耗时 | 说明 |
|---|---|---|
| 冒烟（首次） | 189.55 s | 含 TE 加载与 CPU 文本编码 |
| ink_001 | 2.07 s | ComfyUI 节点缓存命中（与冒烟输入完全相同），不计入性能 |
| ink_002 | 147.60 s | 模型常驻后的代表值 |
| court_001 | 111.04 s | |
| court_002 | 151.27 s | |

代表值 **110–190 s/张**（含 CPU 上的 4B 文本编码）；模型常驻后约 2–2.5 分钟。现有 FLUX.2 竖屏实测为 22–53 s/张，FLUX.3 约为其 **3–4 倍耗时**。显存占用：DiT 加载后 3,550.99 MB，ComfyUI 报告可用余量 6,516.84 MB，未 OOM；文本编码器在 CPU（4,633.34 MB）。

### 7.4 客观指标（FLUX.2 基线 → FLUX.3，同提示词/同种子/同尺寸）

| 镜头 | 亮度均值 | 留白 | 边缘密度 | 高频比 | 饱和度 | LAB b\* |
|---|---|---|---|---|---|---|
| ink_001 | 203.99 → 155.21 | 0.468 → 0.0005 | 0.0878 → 0.0925 | 0.0382 → 0.0354 | 0.0352 → 0.1305 | 1.31 → 7.07 |
| ink_002 | 193.64 → 139.69 | 0.3351 → 0.0095 | 0.0926 → 0.0824 | 0.0401 → 0.0318 | 0.0223 → 0.0826 | −0.76 → 4.78 |
| court_001 | 162.99 → 129.84 | 0.0905 → 0.0000 | 0.1685 → 0.1438 | 0.0613 → 0.0468 | 0.1533 → 0.2063 | 6.51 → 11.49 |
| court_002 | 145.52 → 138.11 | 0.1246 → 0.0002 | 0.2198 → 0.1721 | 0.0835 → 0.0582 | 0.1813 → 0.2079 | 4.09 → 11.61 |

四组方向一致：**更暗、留白几乎归零、饱和度与暖色偏移上升、细线/高频信息下降**（court_002 边缘密度下降 22%）。水墨与工笔两种风格都出现同一模式，说明不是单一风格配置的问题。

### 7.5 人工观察（对比图：`experiments/flux3_poc/compare/contact_sheet.png`）

FLUX.3 的优点：宣纸纹理、墨色渗化、山石与建筑体量感明显更强，更像“画的”而不是“生成的插图”。

FLUX.3 的问题：

1. **不遵守留白与构图约束。** 提示词明确写了留白 38%、主体居中、高角度俯视，四张全部偏离；工笔两张的主体位置与取景也变了。
2. **画面内自行生成书法文字。** ink_001、ink_002 左上角出现题跋与印章。我们的字幕是后期叠加，画面内文字会破坏排版，且平台合规上属于要清理的内容。
3. **色调漂移。** 工笔的青绿被推向暖赭与米黄（LAB b\* +5 左右），超出 `court_green` 的连续性组；水墨也偏暖。
4. **细线减少。** 工笔的游丝描/铁线描密度下降，这对 pipeline B 是核心缺陷。

### 7.6 阶段一判定

| 维度 | 结论 |
|---|---|
| 能否在 A750 上运行 | **PASS_LIMITED**：XPU + GGUF Q4_K_M + CPU 文本编码，实测 4/4 成功，无 OOM |
| 速度 | 约为现有 FLUX.2 的 3–4 倍耗时，但仍远低于单镜 Wan 的 36 min，不是生产线瓶颈 |
| 风格与提示词遵循 | **未通过**：当前提示词契约下 4/4 偏离留白/构图/色调约束，且引入画面内文字 |
| 静态门禁 | 客观层 4/4 `objective_passed=true`（该层只拦空图/黑图/尺寸）；留白与构图问题属于人工清单项，需记为 FAIL 备注 |

**因此：FLUX.3 目前不能替换 FLUX.2，但值得继续做完放大器对照，再决定是否投入提示词重标定。**

### 7.7 待补：提示词放大器对照

官方文档要求 “Always run a prompt upsampler”，本次 A/B 未启用（6.72 GB 的 Qwen3.5-9B w4a8）。这是当前结论唯一的主要混淆项：留白与构图偏离有可能部分来自缺少放大器，而非模型本身。

下一步（进行中）：下载 `qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors`，用 `CLIPLoader(flux3, device=cpu)` + `TextGenerate` 复跑同样的 4 个镜头，比较：

- 留白是否回到 `[0.25, 0.55]`（ink_wash）/ `[0.10, 0.35]`（court_green_fine_line）区间；
- 画面内文字是否消失；
- 单张总耗时增加多少（9B 在 CPU 上的放大开销）。

只有放大器对照仍不达标，才可以把“FLUX.3 不适合当前生产线”作为最终结论。

### 7.8 切换线（预注册，跑之前先定，防止事后调门槛）

| 验收项 | 通过线 | 判据 |
|---|---|---|
| 留白 | 4/4 落入风格区间 | 客观：ink `[0.25, 0.55]`，court `[0.10, 0.35]` |
| 画面内文字 | 4/4 无题跋、印章、字幕 | 人工 |
| 构图/取景 | ≥3/4 符合主体位置与机位 | 人工，对照提示词逐条 |
| 色调 | court 的 LAB b\* ≤ 基线 +3，饱和度 ≤ 基线 +0.05 | 客观 |
| 细线密度 | court 的 edge_density ≥ 基线 90% | 客观 |
| 单张耗时 | ≤ 6 min（含放大器与 CPU 文本编码） | 实测 |

六项中 **≥5 项通过**才进入切换；否则保留 FLUX.2，或先做提示词重标定再复测。

### 8. 切换预演（尚未执行，仅在 7.8 通过后做）

1. `config/models.yaml` 增加 `flux_3_klein`（精确 `sizes`、文件路径、VAE 复用）；现有 `flux_2_klein_4b` 保留为回退项。
2. `workflows/` 新增 FLUX.3 工作流（是否带放大器由 7.8 结果决定）；`production.py` 按模型键选择工作流，不写死单一模型。
3. `docs/ASSET_AND_LICENSE_REGISTRY.md` 登记 FLUX Kommunity License、营收门槛、内容过滤与 AI 标注义务，替换原来 FLUX.2 的 Apache-2.0 条目（旧条目保留并标注停用）。
4. `tests/test_config.py` 增加新模型键与尺寸断言；不改变现有 `<=` 子集断言。
5. 回退能力：FLUX.2 权重、工作流、参数全部保留；切换只改默认值，不删旧路径。
6. 状态词：只有跑出真实产物并留存日志路径，才写 `PASS_VERIFIED`；风格质量仍需人工评审记录。

集长与镜头数由质量、预算和排期权衡决定，不写入任何配置常量。

## 9. 阶段二：官方提示词放大器与短提示词对照（2026-11-06）

### 9.1 官方放大器在本机不可用（三路径实测）

| 路径 | 结果 |
|---|---|
| XPU（`device=default`） | 两次 `access violation`，均在 `comfy/model_prefetch.py` 的 `prefetch_queue_pop`；第二次是干净重启后立刻复现，排除“中断残留”解释 |
| CPU（fp16） | **51.3 s/token**；1024 token 预计 14.5 小时 |
| CPU（bf16，`--bf16-text-enc` 重启） | **56–66 s/token**，无改善，说明瓶颈不是精度而是 w4a8 的 CPU 执行路径 |

结论：不是配置问题，9B w4a8 在本机没有可用执行路径。BFL 允许的“自写完整描述”例外因此成为唯一可行路线。

### 9.2 长提示 vs 短提示（同模型、同种子 8101、同 576×1024、16 步）

| 样本 | 亮度均值 | 白像素 ≥220 | 白像素 ≥240 | 边缘密度 | LAB b\* |
|---|---|---|---|---|---|
| FLUX.2 基线（长提示） | 203.99 | 0.6502 | 0.4704 | 0.0878 | 1.31 |
| FLUX.3 长提示（750 字） | 155.21 | 0.1045 | 0.0003 | 0.0925 | 7.07 |
| FLUX.3 短提示（英文 30 词） | 194.69 | 0.4931 | 0.0001 | 0.0438 | — |
| FLUX.3 短提示（中文 60 字） | 188.09 | 0.4836 | 0.0001 | 0.0646 | — |
| FLUX.3 工笔短提示 | 150.79 | 0.0002 | 0.0000 | 0.1399 | 11.30 |

人工观察：

- **水墨短提示基本符合契约**：上方大片纸面留白、孤舟居中、无题跋、笔触简练。长提示则密集、偏暗、带书法。
- **工笔短提示**：青绿与游丝描明显更接近 pipeline B，建筑结构也更合理；但画面依旧填满，没有留白，且偏暖（b\* 11.3 vs 基线 6.5）。
- 结论：**偏离主要来自我们那套指令式长提示词，而不是模型先验**；FLUX.3 对“自然语言短描述”响应良好。

### 9.3 度量口径问题（切换前必须处理）

`image_metrics.whitespace_fraction` 以 `L ≥ 240` 计白。FLUX.2 的纸面接近纯白（240+），FLUX.3 的纸面是米白（约 225–235），于是出现“视觉上大片留白、指标却是 0”的系统性误判。短提示两张水墨在 `≥220` 阈值为 0.49，已落在风格区间，但在 `≥240` 阈值为 0.0001。

切换前需要把留白改成**相对纸面**的定义（例如以图像亮度 95 分位作为纸面基准，`≥ 基准 − 10` 视为留白），否则新模型会被门禁系统性判负。

### 9.4 修订结论

| 维度 | 结论 |
|---|---|
| 可运行性 | **PASS_LIMITED**（GGUF Q4_K_M + XPU + CPU 文本编码，5/5 成功） |
| 长提示下的风格遵循 | **FAIL**（4/4 偏离留白与构图，2/4 出现画面内书法） |
| 短提示下的风格遵循 | 水墨基本成立；工笔部分成立（色彩改善、留白仍无） |
| 官方放大器 | **不可用**（本机无可行执行路径） |
| 是否满足 §7.8 切换线 | **未满足**，因此不切换 |

**切换不是改一行配置，而是三件事：**

1. 为 FLUX.3 增加一个独立的提示词 profile：短、自然语言、少指令堆叠（现有 750 字编译器输出不适用）。
2. 把留白指标改成相对纸面口径，并重新标定两种风格的阈值。
3. 增加“画面内文字”检查项（题跋/印章在 FLUX.3 上是高频缺陷）。

三项完成并重新跑够 §7.8 的六项，才进入 §8 的切换清单。

## 10. 阶段三：本地 Qwen 替代 9B 放大器（2026-11-06）

### 10.1 方案

- 系统提示词：`config/upsampler/system_prompts.json` 的官方 `t2i` 原文（从 `black-forest-labs/flux-3-image-klein-pup` 原样下载，未改写）。
- 追加约束：按风格从 `config/styles.yaml` 读取留白区间与主体位置，配固定材质/色板描述，要求“空白区域以画面相对位置命名”“全画面无题跋、印章、水印”。
- 执行：本地 `Qwen3-30B-A3B-Instruct-2507`，8080，CPU，`temperature=0.3`，`max_tokens=900`，关闭 thinking。
- 脚本：`scripts/poc_upsampler.py`；输出英文单段 caption，直接作为 FLUX.3 的正向提示，跳过 9B。

### 10.2 实测

| 镜头 | caption 词数 | caption 耗时 | 出图耗时 |
|---|---|---|---|
| ink_001 | 495 | 97.3 s | ~150 s |
| ink_002 | 416 | 54.9 s | ~150 s |
| court_001 | 475 | 67.0 s | ~150 s |
| court_002 | 415 | 54.0 s | ~150 s |

单张端到端约 **3.5–4 分钟**（Qwen CPU + FLUX.3），低于 §7.8 的 6 分钟上限。

### 10.3 指标（纸面相对留白 = 以亮度 95 分位为纸面基准，≥基准−10 计为留白）

| 样本 | 留白（相对纸面） | 边缘密度 | LAB b\* | 饱和度 |
|---|---|---|---|---|
| ink_001 FLUX.2 基线 | 0.470 | 0.0878 | 1.31 | 0.035 |
| ink_001 长提示 | 0.275 | 0.0925 | 7.07 | 0.131 |
| **ink_001 本地 Qwen** | **0.311** | 0.0681 | 10.29 | 0.160 |
| ink_002 FLUX.2 基线 | 0.348 | 0.0926 | −0.76 | 0.022 |
| ink_002 长提示 | 0.110 | 0.0824 | 4.78 | 0.083 |
| **ink_002 本地 Qwen** | **0.316** | 0.0618 | 4.43 | 0.070 |
| court_001 基线 | 0.179 | 0.1685 | 6.51 | 0.153 |
| court_001 长提示 | 0.022 | 0.1438 | 11.49 | 0.206 |
| **court_001 本地 Qwen** | 0.038 | 0.1287 | 8.35 | 0.232 |
| court_002 基线 | 0.160 | 0.2198 | 4.09 | 0.181 |
| court_002 长提示 | 0.145 | 0.1721 | 11.61 | 0.208 |
| **court_002 本地 Qwen** | 0.154 | 0.1523 | 13.23 | 0.256 |

### 10.4 按 §7.8 判定

| 验收项 | 结果 | 说明 |
|---|---|---|
| 留白 4/4 | ✗ 3/4 | 水墨 2/2 达标；court_001 仅 0.038（区间 0.10–0.35） |
| 画面内文字 4/4 | ✓ | 四张均无题跋、印章 |
| 构图 ≥3/4 | ✓ | 水墨两张符合；court_001 符合；court_002 取景偏移 |
| 色调 | ✗ | court_002 b\* +9.14（上限 +3）；court 饱和度 +0.079/+0.075（上限 +0.05） |
| 细线密度 ≥90% | ✗ | court_001 76%、court_002 69% |
| 单张 ≤6 min | ✓ | 约 3.5–4 min |

**3/6 通过，未达到切换线。**

### 10.5 结论

- 本地 Qwen 替代 9B 在**工程上成立**：官方接口允许、CPU 零显存占用、单张端到端 3.5–4 分钟、题跋缺陷被消除。
- **水墨管线（A）基本收敛**：留白回到区间、构图与无字要求满足；细节密度低于 FLUX.2，但这与“写意水墨”的目标一致，需要人工确认。
- **工笔管线（B）未收敛**：留白不足、饱和度与暖色偏移超标、细线密度不足。需要注意的是，本地 Qwen 生成的两张工笔在**视觉上更贴近配置里写的“石青石绿 + 朱柱”**，而 11-04 已批准的 FLUX.2 基线更偏淡青绿；这不是单纯的“变差”，而是与已批准基线不同的视觉语言，需要人工裁决。
- 本地 Qwen 的 caption 有一处偏离官方规则：出现了 “vertical 9:16 composition” 字样，而官方系统提示明确禁止提及画布比例。属可修问题（后处理或加强约束）。

### 10.6 待决选项

1. **调优工笔 addendum 后复测**（推荐，成本约 20 分钟/轮）：色板改用配置中的具体色名并明确“低饱和绢本、铁线描密度”，限定屋面为深青灰陶瓦，避免石青被理解为亮蓝。
2. **分模型生产**：水墨切 FLUX.3（配本地 Qwen caption），工笔继续 FLUX.2；模型选择进配置，不在代码里按风格分支。
3. **工笔走 LoRA 或等官方风格适配**：成本最高，需另立项。

## 11. POC-B：VoxCPM2 语音模型（2026-11-06）

### 11.1 环境与授权

| 项 | 值 |
|---|---|
| 运行时 | `VoxCPM-Runtime`（独立 venv，不并入根 `.venv` 与 ComfyUI venv） |
| 权重 | `models\voxcpm2`，`model.safetensors` 4,580,080,592 B + `audiovae.pth` 376,951,122 B |
| 完整性 | SHA-256 与 HF 官方 LFS 一致（`f7f964cf…` / `94b5d51e…`） |
| 授权 | Apache-2.0（代码与权重）；TOS 附伦理条款；参考音权利沿用 `VOICE_RIGHTS.md` |
| 参考音 | `assets/audio/prompts/my_voice_clean_v1.wav`（本人录音，16 s） |

### 11.2 CPU 实测

| 项 | 实测 |
|---|---|
| 加载 | 21.45 s（常驻后不重复） |
| 单句冒烟 | 3.04 s 音频 / 29.99 s，RTF 9.87 |
| 七句批量 | 29.92 s 音频 / 276.8 s，平均 RTF 9.26（9.13–9.45） |
| 输出 | 48 kHz 单声道，峰值 0.49，无削波 |

### 11.3 与 CosyVoice2-0.5B 的盲听对照

先核实对照对象：运行时 `/health`、启动脚本与 `logs/server.log` 三处一致显示 `CosyVoice2-0.5B`，走 zero-shot，参考音同上；**不是 300M-SFT**（该目录存在，但只有传 `speaker` 时才加载）。为公平，CosyVoice 本次用 `speed=1.0`（VoxCPM2 无语速参数）；生产默认是 0.90。

| 指标 | CosyVoice2-0.5B | VoxCPM2 |
|---|---|---|
| 采样率 | 24 kHz | 48 kHz |
| 七句总音频 | 38.0 s | 29.9 s |
| 七句总耗时 | 138.9 s | 276.8 s |
| 平均 RTF | 3.64 | 9.26 |

盲听设置：每句 A/B 随机分配（种子 20261106），统一 `loudnorm=I=-16:TP=-1.5`、48 kHz 单声道，映射表单独存放。

结果：**7/7 全部选择 VoxCPM2**（第 3、5 句为“略好但两版都有发音错误”，第 4 句 CosyVoice 版本被判为不可用）。

### 11.4 XPU 实测：不可用

| 步骤 | 结果 |
|---|---|
| `device="xpu"` | 被 `voxcpm/model/utils.py::resolve_runtime_device` 直接拒绝，只接受 auto/cpu/mps/cuda |
| 最小补丁（只加 xpu 分支） | 模型可加载，预热阶段在 `voxcpm2.py::_inference` 触发 XPU 断言，随后 `access violation`，exit 139 |
| 结论 | VoxCPM2 的推理算子路径在 Arc A750 上不完整；补丁已还原，运行时保持原样 |

因此在本机 **VoxCPM2 只能走 CPU**，代价是比 CosyVoice2 慢约 2.5 倍。

换装 XPU 版 torch（`2.15.0+xpu`）后复验 CPU 回退：加载 21.61 s，同句 3.20 s 音频 / 27.84 s，RTF 8.70，与换装前的 9.87 属同一量级，未退化。运行时保留该组合。

### 11.5 待办

1. 第 3、5 句的发音修正（“灩灩”“宛轉遶”“霰”等），VoxCPM2 不接受音素，只能靠文本改写；项目已有 `pronunciation.py` 词表机制。
2. 语速差异：VoxCPM2 七句总时长短约 21%，接入生产时需要重排镜头/字幕时长。
4. 2026-11-06 决策：剔除 POC-B 原「CPU RTF ≤ 4×」门槛。速度只记录、不进验收；交付质量以盲听对照（咬字、韵律、断句、音色稳定性）与 48 kHz 成片试听为准。
3. **2026-11-06 决策：语音后端采用 VoxCPM2**，服务端口沿用 50000（由使用者侧改造服务）。项目侧待办：以新的 `/health` 与合成契约替换 `voice/tts.py` 中的 CosyVoice 模型类校验，并退休 SFT 预置音色。

## 12. MiniMax H3 可行性核验（2026-11-06，未下载权重）

### 12.1 模型与 ComfyUI 支持

| 项 | 事实 |
|---|---|
| 规模 | 约 33B 全模态（文本/图/视频/音频输入 → 视频 + 原生立体声），最长 15 s |
| 变体 | FL2VA（首尾帧）、Ref2VA（最多 9 图 + 3 视频 + 3 音频参考） |
| ComfyUI | 0.43.0 已内置 `MiniMaxH3*` 节点；核心按 `video_patch_proj.weight` + `audio_patch_proj.weight` 识别模型 |
| 识别键 | 已在 unsloth 的 `minimax_h3_fl2va_pruned-Q3_K.gguf` 中确认存在（另有 `blocks.0.attn.q_norm`、`final_layer.video_out`） |
| GGUF 路径阻断点 | 仅 `ComfyUI-GGUF 2.0.0` 的 `loader.py` 架构白名单与 `tools/convert.detect_arch`；补丁约 10 行即可放行，不涉及 ComfyUI 核心 |
| 官方 int8 路径 | 原生 `UNETLoader` 可直接加载，无需补丁 |

### 12.2 体积与下载成本（按本机实测 1.5 MB/s）

| 方案 | 组成 | 合计 | 预计下载 |
|---|---|---|---|
| 官方 int8（最保守） | DiT pruned int8 20.97 + TE nvfp4 15.69 + 视频 VAE 2.81 + 音频 VAE 0.61 | 40.08 GB | 约 7.4 h |
| GGUF 可用质量 | DiT Q3_K 8.76 + TE Q2_K_XL 9.57 + 两个 VAE 3.42 | 21.75 GB | 约 4 h |
| GGUF 最小（画质差） | DiT IQ1_S 3.78 + TE IQ2_XXS 6.91 + 两个 VAE 3.42 | 14.11 GB | 约 2.6 h |

### 12.3 本机硬件约束

- 显存 8.32 GB；DiT Q3_K 8.76 GB、TE Q2 9.57 GB **各自都超过显存**，必须整体走 ComfyUI 的 offload 流式加载。
- 官方 int8 方案更极端：DiT 20.97 GB + TE 15.69 GB，两者合计约 37 GB，必须全部驻留内存并逐层换入。
- 内存 64 GB 够用，但 **8080 的 CPU LLM（约 19 GB）不能同时运行**。
- DiT 使用标准 `operations.*` 层，无 CUDA 专属算子；VAE 的 CUDA 快速路径有通用回退。
- 文本编码器路径：用现有的 Qwen3-VL-4B 在 XPU 上做纯编码探针，**成功**（见 `experiments/h3_probe/te_xpu_probe.py`）。之前 9B 放大器的崩溃发生在 `generate` 路径，而 H3 的 TE 只做编码，因此该风险显著降低。
- 仍未验证：32B TE 在 8 GB 显存上的编码耗时、DiT 逐层换入的采样耗时、音频 VAE。

### 12.4 时间预估（推算，非实测）

以已验证的 Wan2.2 TI2V 5B（576×1024 / 73 帧 / 20 步 ≈ 36 min）为基准，按参数（33/5≈6.6×）、步数（8/20=0.4×）、时长（15 s/3 s=5×）粗算，H3 单段约 **13× Wan**，即数小时量级；在 8 GB 显存下还要叠加换入开销。该数字只是量级推算，必须用实测替换。

### 12.5 授权

MiniMax H3 Community License：适用地域为全球**除 EU、英国、韩国、美国**；年营收 2000 万美元以下可商用；商用产品界面需显著标注 “MiniMax H3”；不得用其输出改进其他模型。

### 12.6 结论

- **技术上不是死路**：ComfyUI 原生支持、识别键齐全、XPU 上编码路径可用、DiT 无 CUDA 专属算子。
- **实践上大概率不可用于生产**：8 GB 显存要同时承载 8.76 GB DiT 与 9.57 GB TE 的流式加载，单镜耗时按量级推算为小时级；我们现有 Wan 单镜 36 min 已经是瓶颈。
- 若要给出确定答案，最小有意义实验为 GGUF 可用质量组合（21.75 GB，约 4 h 下载）+ 单段 5 s 测试，并设硬停止线：**单段超过 90 min 即判不可用**。

**2026-11-06 决策**：用户决定中止 H3 权重下载，不做实测。H3 的状态保持 **`NOT_RUN`**，§12 的结论只停留在代码与硬件分析层面，不得写成“已验证不可用”。已下载的部分文件（约 194 MB）已删除，`models` 未留下 H3 权重。

若日后硬件变化（显存 ≥ 24 GB）或需要重新评估，按 §12.2 的组合重开，并沿用同一停止线。
