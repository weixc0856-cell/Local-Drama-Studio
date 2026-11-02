# R1-A：现有项目审查

> 审查日期：2026-11-02
> 范围：R0 已验证的 FLUX 工作流、参考图/图像编辑能力、API 自动化参数、16:9 可行性、一致性约束。
> 原则：本阶段只审查与实验，不重构架构、不改动已验证的 Wan 工作流。

## 1. 现有 FLUX 工作流的真实输入输出

文件：[workflows/r0_flux_t2i_api.json](../workflows/r0_flux_t2i_api.json)

| 节点 | class_type | 作用 |
|---|---|---|
| 1 | `UnetLoaderGGUF` | 加载 `flux-2-klein-4b-Q4_K_M.gguf` |
| 2 | `CLIPLoader` | 加载 `qwen_3_4b.safetensors`，`type=flux2`，`device=cpu` |
| 3 | `VAELoader` | 加载 `flux2-vae.safetensors` |
| 4/5 | `CLIPTextEncode` | 正向提示词 / 空负向 |
| 6 | `ConditioningZeroOut` | 负向置零（CFG=1.0 时实际不参与） |
| 7 | `EmptyFlux2LatentImage` | 输出尺寸，step=16 |
| 8 | `Flux2Scheduler` | 4 步经验 mu 调度 |
| 9/10/11/12 | `KSamplerSelect` / `CFGGuider` / `RandomNoise` / `SamplerCustomAdvanced` | 采样链 |
| 13 | `VAEDecode` | 解码 |
| 14 | `SaveImage` | 输出 PNG，`filename_prefix` 控制子目录与文件名 |

参数入口（[params 示例](../workflows/r0_flux_t2i_params.json)）：

```text
positive_prompt, seed, width, height, steps, cfg, filename_prefix
```

实际输出：**单张 PNG**，512×512，写入 ComfyUI `output/<filename_prefix>_00001_.png`；R0 探针再通过 `/view` 下载到 `--out` 目录。

R0 实测：冷启动约 95-100 秒/张，峰值显存 2.61 GiB，文本编码器在 CPU，扩散模型/VAE 在 XPU。

## 2. 参考图与图像编辑能力

ComfyUI 0.43.0 已内置：

- `ReferenceLatent`：`conditioning` + 可选 `latent`，把参考图 latent 追加到条件。
- `VAEEncode` / `ImageScaleToTotalPixels`：编码前缩放参考图。
- 官方模板 `runtime/ComfyUI/.venv/Lib/site-packages/comfyui_workflow_templates_json/templates/image_flux2_klein_image_edit_4b_distilled.json`：
  - `LoadImage → ImageScaleToTotalPixels → VAEEncode → ReferenceLatent`
  - `CLIPTextEncode(编辑指令) → ReferenceLatent`
  - `EmptyFlux2LatentImage + Flux2Scheduler + CFGGuider(1.0) + SamplerCustomAdvanced`
- 同一模板还演示了多参考图（两个 `ReferenceLatent` 链式追加）。

**结论：能力存在，但尚未在本机验证。** 官方模板使用 `flux-2-klein-4b-fp8.safetensors`，本项目使用对应的 GGUF Q4；需要把 `UNETLoader` 换成 `UnetLoaderGGUF`，文本编码器继续放 CPU。R1-C 将实际验证单参考图与图像编辑，不把“节点存在”当成“能力通过”。

## 3. API 参数与自动化现状

现有自动化入口：[scripts/r0_comfy_probe.py](../scripts/r0_comfy_probe.py)

已具备：

| 能力 | 状态 | 说明 |
|---|---|---|
| 提交 API 工作流 | ✅ | `POST /prompt` |
| 修改提示词 / seed / 尺寸 | ✅ | `--params` 对整个 JSON 树做 `{{placeholder}}` 类型保留替换 |
| 指定输出路径 | ✅ | `--out` 下载目录 |
| 自动获取结果 | ✅ | 轮询 `/history/{id}`，下载 `outputs` 中所有文件 |
| 记录生成参数 | ✅ | `run.json`：prompt_id、耗时、峰值显存、输出路径、system_stats |
| 失败恢复 / 断点续跑 | ❌ | 探针只执行一次；无 job 清单、无跳过已完成、无自动重试上限 |

**结论：R1-E 需要一个很薄的批处理层复用该探针**，补齐 job 清单、完成判断、最多 2 次重试、失败记录；不重写 HTTP 客户端。

## 4. 16:9 生成是否需要改工作流

不需要改节点结构，只需改参数：

- `EmptyFlux2LatentImage` 的 `width/height` step=16。
- 768×432 满足 16:9 且均为 16 的倍数。
- `Flux2Scheduler` 使用同样尺寸计算 `seq_len`。
- 输出文件仍是 768×432；最终 1920×1080 由后续阶段（R3 超分/放大）完成，本阶段不承诺原生 1080p。

需要在 R1-C 实测 768×432 的耗时与显存；若显存或质量不合适，再退到 640×360。

## 5. 人物/场景一致性约束

现有项目：

- 没有角色资产、没有锁定参考图、没有一致性检查。
- R0 只验证了“同 seed 可复现”，没有验证“同一人物/场景在不同提示词下保持一致”。

本阶段题材是山水诗词，**没有人脸特写**，可以先把一致性限定在“场景与画风”：

1. 统一的 style bible（在 R1_VISUAL_DESIGN 中定义）。
2. 参考图条件（`ReferenceLatent`）用于关键帧之间的风格延续。
3. 人工检查关键帧的空间关系与时间逻辑。
4. 不把“重复同一段提示词”当作一致性证据。

**结论：一致性是 R1 的核心实验项，不是已有能力。**

## 6. 审查结论

| 问题 | 结论 |
|---|---|
| 现有 FLUX 工作流输入输出 | 提示词/seed/尺寸/步数 → 单张 PNG；已验证 |
| 参考图与编辑 | 节点与官方模板存在；本机未验证，R1-C 必测 |
| API 是否能支撑自动化 | 能；缺断点续跑，R1-E 补薄批处理层 |
| 16:9 是否要改工作流 | 不改结构，只改尺寸参数；需实测 |
| 一致性约束 | 尚无；本阶段用参考图 + 视觉规范 + 人工检查 |

不重构架构，不修改已有 Wan 工作流，不升级 PyTorch/ComfyUI。
