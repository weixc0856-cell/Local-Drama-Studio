# M8-B(1) 图层来源实验：能否用 FLUX 补出干净的背景板

> 执行日期：2026-11-04
> 前置：[M8_A_PARALLAX_REPORT.md](M8_A_PARALLAX_REPORT.md)（人工判定 C 优于 A/B；2×2 归因：优势来自分层）
> 状态口径：`docs/PRD.md` §0.2
> **本轮不修改生产代码、配置、质量门；新增一个实验工作流与一个实验脚本。**

## 0. 结论

**M8-B(1) = `PARTIAL`。能力部分成立，但适用范围比预期窄得多。**

| 问题 | 答案 |
|---|---|
| 现有引擎能不能把画面上的物体抹掉并补出同风格的内容？ | 能。`workflows/m8_flux2_inpaint_api.json` 走 `VAEEncode → SetLatentNoiseMask → SamplerCustomAdvanced`，576×1024 / 6 步 / CFG 1.0，单次 30-52 s |
| 补底可靠吗？ | **只在"洞小、且落在均质无结构区域"时可靠。** 船（小、纯水面）一次成功；右前景枯树（占画面 9%、跨水面与土坡、贴着边框）**彻底失败**，模型在原位长出一丛挺水植物 |
| 那就用它替代 M8-A 的插值补底？ | 对孤舟这一镜**没有必要**：补底只在 53 px 宽的带子里被看见，两版差值平均 10/255，低于可辨识阈值 |
| 对 M8-B 契约意味着什么？ | **前景层必须走"独立生成/独立绘制的前景资产"，不能靠从压平的静帧里抠 + 补底。** 背景板可以补，前景板不能补 |

这条结论直接推翻了 M8-A 报告里"先解决图层来源"的默认路径（"把树抠掉再补底"）。正确的路径是：**前景用带 alpha 的独立资产叠在完整背景上**，而不是把前景从背景里挖出来。这也正是项目里 `petal_drift` / `bird_motion` 已经强制要求的形态。

## 1. 做法

1. 复用 M8-A 的两块图层掩膜，膨胀 12 px（覆盖 M8-A 实测的露洞带，最大 53 px），得到重绘掩膜。
2. 新增 API 工作流 `workflows/m8_flux2_inpaint_api.json`：在已验证的 FLUX.2 klein 图（R0 同款）上，把 `EmptyFlux2LatentImage` 换成 `LoadImage → VAEEncode → SetLatentNoiseMask`，采样链路不变（`Flux2Scheduler` + `CFGGuider(1.0)` + `SamplerCustomAdvanced`，无 `FluxGuidance`，负向条件 `ConditioningZeroOut`）。
3. 只把掩膜内的像素替换回原图（`Image.composite(generated, source, blur(mask))`）——VAE 往返会让整幅解码后的画面变软，掩膜外必须保持逐像素不变。
4. 脚本 `scripts/m8_plates.py`：`masks` / `inpaint` / `build`，全部产物落 `experiments/m8_plates/`。

## 2. 三次尝试与结果

| # | 掩膜 | 提示要点 | 结果 |
|---|---|---|---|
| 1 | 船 + 树（合并） | 水面 + 远岸土坡 + 稀疏杂草 | 船位正确抹除；**船首位置凭空出现一小块沙洲与草丛** |
| 2 | 船（单独） | 只要平静水面；显式排除沙洲/石头/草丛/鸟 | **可用**：船完全消失，水面连续，无新物体 |
| 3 | 树（单独） | 江岸、浅滩、极稀疏枯草；显式排除树/枝干/石头 | **失败**：原树位置长出一丛挺水植物并带长倒影 |

第 1 次失败是**提示词设计错误**——合并提示里同时要了"浅滩土坡与稀疏杂草"，模型把它按字面放进了船位。把两个语义不同的洞放进一次生成，提示词必然互相污染。

第 3 次失败是**能力边界**，不是提示词问题：掩膜占画面 9%，横跨水面、土坡与山石三种材质，岸线在树后被截断，模型没有任何依据推断"背后应该是什么"，于是自行构图。要求"不要任何新物体"并不能阻止它把整块区域重画成另一幅画。

## 3. 量化

| 指标 | 值 |
|---|---|
| 掩膜外平均变化（重建后） | **0.0000/255**（逐像素不变，符合设计） |
| 掩膜内平均变化（船位） | 46.2/255（即船被抹掉本身） |
| 高频能量（`mean｜img − blur2｜`，0-255）内插值补底 | 1.33 |
| 同上，FLUX 补底 | 2.09 |
| 同上，原画周围水面 | 3.62 |
| 两版补底在洞内的平均差 | 10.0/255 |
| 单次耗时 | 船 46.1 s / 树 30.1 s（576×1024、6 步、CFG 1.0，含模型加载） |

FLUX 补底比逐行插值更像水（2.09 vs 1.33，真实水面 3.62），但仍偏平；两者差值 10/255，而 M8-A 实测补底只在最宽 53 px 的带子里被看见——**这一镜没有可见收益**。

## 4. 对 M8-B 契约的影响

| 编号 | 结论 | 依据 |
|---|---|---|
| C1 | `PlateSpec` 必须区分图层**来源**：`interpolated` / `inpainted` / `independent_asset` / `generated_background`，并把来源写进快照 | 三种来源质量差一个档次，混用会让质量门失去意义 |
| C2 | 前景层只允许 `independent_asset`（带 alpha 的独立生成/绘制资产） | 本报告 §2 第 3 次尝试 |
| C3 | 补底只允许用于背景层，且掩膜覆盖率设上限（本机经验：≤4% 且落在单一材质内） | 船 2% 成功、树 9% 失败 |
| C4 | 补底必须掩膜外逐像素还原原图 | VAE 往返会让整幅变软 |
| C5 | 提示词必须按"洞的语义"分别描述，不同材质的洞不得合并成一次生成 | 本报告 §2 第 1 次尝试 |
| C6 | 每块板的 provenance 必须含：来源类型、工作流哈希、seed、steps、掩膜哈希、耗时 | 与现有资产规则一致 |

## 5. 追加的负面结论（写给后续设计）

- **"把主体抠出来"不是 2.5D 的可扩展路线。** 主体越大、周围结构越复杂，补底越不可用；而前景之所以是前景，恰恰因为它大且遮挡多。
- 因此 2.5D 镜头的**分镜设计**要配合图层能力：前景元素尽量是"能独立生成的东西"（芦苇、云雾、飞鸟、枝条、窗棂），而不是"画面里已经长好的一棵大树"。
- 青绿工笔的长卷横移更依赖这条：建筑与山体不能切，能动的只有云雾与水，以及可独立生成的前景。

## 6. 产物

| 内容 | 路径 |
|---|---|
| 新增工作流 | `workflows/m8_flux2_inpaint_api.json` |
| 实验脚本 | `scripts/m8_plates.py` |
| 掩膜 | `experiments/m8_plates/masks/` |
| 生成结果与 provenance | `experiments/m8_plates/runs/{all,boat,tree}-*/`（`run.json` 含 workflow/source/mask 哈希、seed、steps、耗时） |
| 合成后的背景板 | `experiments/m8_plates/plates/plate_{boat,tree,all}.png` |
| 对照图 | `experiments/m8_plates/inspect_plate_boat2.png`（成功）、`inspect_plate_tree.png`（失败） |

## 7. 运行与资源

```powershell
.venv\Scripts\python.exe scripts\m8_plates.py masks --dilate 12
scripts\start.ps1                      # ComfyUI 8188，本次由本实验启动，结束时已停止
.venv\Scripts\python.exe scripts\m8_plates.py inpaint --region boat --steps 6 --seed 8100
.venv\Scripts\python.exe scripts\m8_plates.py inpaint --region tree --steps 6 --seed 8100
.venv\Scripts\python.exe scripts\m8_plates.py build --region all
scripts\stop.ps1
```

ComfyUI 已停止，8188 已释放（`curl.exe` 返回 000）。三轮生成合计约 128 s，未触及 8080 与 CosyVoice。

## 8. 下一步（尚未执行）

1. 按 C2 做一块**独立前景资产**（例如生成一张带 alpha 的芦苇/枝条），叠在完整背景上，验证"不挖洞"的分层路线是否可行——这才是 M8-B 的正确起点。
2. 用 `PlateSpec` 收口（C1-C6）之前，先用 1 镜样片证明路线，而不是先写契约。
3. 本报告不改变 M8-A 的任何结论；M8-A 仍是 `PARTIAL`（技术通过 + 人工判定 C 优于 A/B）。
