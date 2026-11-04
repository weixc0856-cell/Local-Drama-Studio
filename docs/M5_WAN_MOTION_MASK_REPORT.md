# M5 Wan 运动遮罩能力核验报告

> 执行日期：2026-11-04
> 环境：Windows 11 / i7-13700K / 64 GB / Intel Arc A750 8 GB
> 本轮**未启动 ComfyUI**、未加载 Wan/FLUX 模型、未占用 XPU 显存。
> 状态口径：`docs/PRD.md` §0.2。

## 0. 结论

**M5 = `NOT_RUN (UNSUPPORTED_WORKFLOW)`。**

项目使用的 Wan2.2 TI2V 5B 工作流（`workflows/r0_wan_i2v_api.json`）没有任何 `mask` / `motion_mask` 输入端口，也没有任何遮罩类节点。`Wan22ImageToVideoLatent` 内部的 `noise_mask` 只把**起始图对应的前几帧 latent** 置零，是首帧条件，不是空间运动遮罩。

按任务约束，未启动 ComfyUI、未做无遮罩裸跑、未进行 512×512 最小切片生成。当前生产管线继续使用：

```text
高精静态首帧 + 2.5D/局部几何微动（M1/M2） + M3 质量门禁 + M4 转场时间轴
```

## 1. 静态审计范围

| 对象 | 结论 |
|---|---|
| `workflows/r0_wan_i2v_api.json` | 11 个节点，无 mask 输入、无 mask 节点 |
| `workflows/r0_wan_t2v_api.json` | 无 mask 输入、无 mask 节点 |
| `workflows/` 全部 JSON | 没有任何 `*Mask*` class_type，也没有名为 `*mask*` 的输入 |
| `Wan22ImageToVideoLatent` | 输入只有 vae / width / height / length / batch_size / start_image |
| `SetLatentNoiseMask` | ComfyUI 核心有该通用节点，但**不在项目 Wan 工作流中** |
| Wan Animate `motion_mask` | 属于 Wan Animate 模型内部，非 TI2V 5B |
| VACE `control_masks` | 属于 Wan2.1 VACE 工作流，非本项目 5B TI2V |
| 自定义节点 | 仅 `ComfyUI-GGUF`（模型加载），无 Wan 遮罩节点 |
| 官方 blueprint | `Image to Video (Wan 2.2).json` 也没有遮罩输入 |

完整机器可读审计：`experiments/m5_wan/audit.json`。

## 2. 节点拓扑证据

### 2.1 项目 Wan I2V 工作流

`workflows/r0_wan_i2v_api.json`：

```text
1  UnetLoaderGGUF
2  CLIPLoader
3  VAELoader
4  CLIPTextEncode (positive)
5  CLIPTextEncode (negative)
6  LoadImage
7  ModelSamplingSD3
8  Wan22ImageToVideoLatent  [vae, width, height, length, batch_size, start_image]
9  KSampler                 [model, seed, steps, cfg, sampler, scheduler,
                             positive, negative, latent_image, denoise]
10 VAEDecode
11 SaveImage
```

- 节点 8 到节点 9 只传 `latent_image`；没有 `SetLatentNoiseMask`、`LatentCompositeMasked` 或任何遮罩分支。
- 节点 9 的 `latent_image` 直接来自节点 8，采样覆盖整个 latent。
- 工作流中不存在可按像素限制扩散区域的端口。

### 2.2 `Wan22ImageToVideoLatent` 的真实输入

`runtime/ComfyUI/comfy_extras/nodes_wan.py:1418-1459`：

```python
node_id="Wan22ImageToVideoLatent",
inputs=[
    io.Vae.Input("vae"),
    io.Int.Input("width", ...),
    io.Int.Input("height", ...),
    io.Int.Input("length", ...),
    io.Int.Input("batch_size", ...),
    io.Image.Input("start_image", optional=True),
]
```

没有 `mask` 或 `motion_mask`。

内部的 `noise_mask` 是：

```python
mask[:, :, :latent_temp.shape[-3]] *= 0.0      # 只作用于起始图的 temporal latent
out_latent["noise_mask"] = mask.repeat(...)
```

即“首帧条件区域不参与重绘”，不是用户可提供的空间运动遮罩。把它当作 Motion Mask 会误报能力。

### 2.3 其他模型里的 `mask` 不能算作本项目 Wan2.2 能力

- `runtime/ComfyUI/comfy/ldm/wan/model_animate.py:180` 的 `motion_mask` 位于 Wan Animate 的 motion-vector attention 内，模型/工作流不同。
- `runtime/ComfyUI/comfy_extras/nodes_wan.py:308` 的 `control_masks` 属于 `WanVaceToVideo`（Wan2.1 VACE），不是 5B TI2V。
- `runtime/ComfyUI/nodes.py:1567` 的 `SetLatentNoiseMask` 是通用 latent 噪声遮罩；它不在项目工作流中，且对视频 latent 的时序维度处理是 batch 化 reshape，不能直接等同于 Wan 运动遮罩。

### 2.4 自定义节点与 blueprint

- `runtime/ComfyUI/custom_nodes/` 只有 `ComfyUI-GGUF`，没有 WanVideoWrapper、Wan 遮罩或视频 inpainting 扩展。
- `runtime/ComfyUI/blueprints/Image to Video (Wan 2.2).json` 只有一个工作流节点，输入为 `start_image / text / width / height / length / unet_name / lora_name / clip_name / vae_name`，无 mask。

## 3. 为什么没有执行最小切片

任务明确要求：**只有确认工作流具备遮罩接入能力，才做 512×512 / 20 步 / 33 帧切片**；不具备时标记 `NOT_RUN`，严禁无遮罩裸跑全图。

- 当前工作流没有 mask 端口；
- 用 `SetLatentNoiseMask` 临时插入属于未验证的通用 workaround，不是 Wan 原生能力，也会改变 latent 时序语义；
- 强行裸跑只能得到“整图重绘”的结果，无法回答“能否限制扩散区域”的问题，反而会消耗 GPU 时间并产生误导性样片。

因此本轮：

| 项 | 结果 |
|---|---|
| ComfyUI 启动 | 否 |
| 模型加载 | 否 |
| 512×512 / 20 步 / 33 帧生成 | `NOT_RUN` |
| XPU 显存峰值 | N/A（0 占用） |
| 刚体保护复检 | 未执行（没有生成物） |

## 4. 对生产管线的影响

- Wan 在本项目中仍只作为“非脚本化局部动态的补充”，不得声称具备运动遮罩或主体保护。
- 需要主体稳定、局部微动的镜头继续走确定性管线：M1 区域契约 + M2 算法 + M3 门禁 + M4 转场。
- 若未来要重新评估 Wan，需要满足以下任一条件，并重新做 W1（水面）/ W2（云雾）/ W3（船体保护 + 水面）单变量实验：
  1. Wan2.2 TI2V 工作流出现原生 `mask` / `motion_mask` 输入；
  2. 引入并验证支持遮罩采样的 Wan 节点包（例如 VACE 或 Animate 的对应工作流），且确认遮罩作用于目标采样区域；
  3. 用 `SetLatentNoiseMask` 做受控 A/B，证明它在该模型上确实限制空间扩散且不破坏时序一致性。

在满足条件前，M5 保持 `NOT_RUN (UNSUPPORTED_WORKFLOW)`。

## 5. 测试与资源

```text
.venv\Scripts\python.exe -m pytest
231 passed, 1 warning in 21.63s
```

本轮未新增生产代码；仅新增审计 JSON 与报告。GPU 0、无网络、无 ComfyUI 进程。

## 6. Git

未提交、未推送、未 reset、未 clean；HEAD 仍为 `651c7dd`。

新增：

- `experiments/m5_wan/audit.json`（本地证据）
- `docs/M5_WAN_MOTION_MASK_REPORT.md`

## 7. 待人工审查

1. 接受 `NOT_RUN (UNSUPPORTED_WORKFLOW)` 的结论与证据链。
2. 确认不把 `SetLatentNoiseMask` 临时插入当作 Wan 运动遮罩能力。
3. 确认继续以“静态首帧 + 确定性局部微动”为主力管线。
4. 确认后再进入 **M6 发音校正**；本轮不进入 M6。
