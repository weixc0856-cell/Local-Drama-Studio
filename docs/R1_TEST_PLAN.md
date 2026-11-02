> 执行结果：见 [R1_TEST_REPORT.md](R1_TEST_REPORT.md)。全部计划任务已执行。

# R1 测试计划：视觉资产与古典诗词短片预研

> 题材：张若虚《春江花月夜》
> 目标：验证 16:9 关键帧生产、参考图/编辑能力、批处理自动化与场景一致性。
> 本阶段不进入 R2，不生成视频，不做 1080p 超分。

## 0. 前置

- R0 已验证环境保持不动：ComfyUI 0.43.0、torch 2.15.0+xpu、FLUX.2 klein 4B Q4、Wan2.2 TI2V 5B Q4。
- 使用根 `.venv` 的 `scripts/r0_comfy_probe.py` 作为 HTTP 客户端；新增代码只做任务编排。
- 视觉规范：[R1_VISUAL_DESIGN.md](R1_VISUAL_DESIGN.md)。
- 审查结论：[R1_AUDIT.md](R1_AUDIT.md)。

## 1. R1-A：现有项目审查

已完成，见 [R1_AUDIT.md](R1_AUDIT.md)。不改架构。

## 2. R1-B：视觉设计

已完成，见 [R1_VISUAL_DESIGN.md](R1_VISUAL_DESIGN.md)。产出：

- `assets/visual_style/style_bible.md`
- `assets/visual_style/style_bible.json`
- `assets/visual_style/reference/`（选定后复制）

## 3. R1-C：FLUX 资产实验

### 3.1 工作流

| 用途 | 文件 |
|---|---|
| 文生图 | `workflows/r0_flux_t2i_api.json`（已验证，复用） |
| 参考图/编辑 | `workflows/r1_flux_edit_api.json`（R1 新增，`ReferenceLatent + VAEEncode`） |

### 3.2 任务表

| Job | 目的 | 输入参考 | 尺寸 | seed | 说明 |
|---|---|---|---|---|---|
| J1 | 512 基准 | 无 | 512×512 | 1101 | 江面月夜，验证基准 |
| J2 | 16:9 横屏 | 无 | 768×432 | 1101 | 同一提示词，比较构图 |
| J3 | 参考图辅助 | J2 | 768×432 | 1201 | 同一河湾，花林月照 |
| J4 | 图像编辑 | J2 | 768×432 | 1301 | 在江面加入孤舟 |
| J5 | 参考图辅助 | J2 | 768×432 | 1401 | 同一河湾，落月晨曦 |
| J6 | 纯文生图对照 | 无 | 768×432 | 1201 | 花林月照（与 J3 对比） |
| J7 | 纯文生图对照 | 无 | 768×432 | 1301 | 孤舟远行（与 J4 对比） |
| J8 | 纯文生图对照 | 无 | 768×432 | 1401 | 晨曦（与 J5 对比） |

> J3/J4/J5 用参考图；J6/J7/J8 只用文字且 seed 对齐。对比的是“参考条件是否带来一致性”，不是“提示词重复”。

### 3.3 记录字段

每个任务写入 `experiments/r1/runs/<job>/`：

```text
run.json             prompt_id / 耗时 / 峰值显存 / 输出列表 / system_stats
workflow.submitted.json
history.json
<输出>.png
job.json             原始 prompt / seed / 尺寸 / 参考图 / 工作流哈希 / 输出 sha256
```

### 3.4 验收

- 512×512 与 768×432 均能生成，文件可解码、非全黑/全白。
- 768×432 的耗时与峰值显存有记录。
- 参考图任务能加载参考图并成功出图；失败时保留错误，不伪装成功。
- 图像编辑任务至少成功一次；如失败，记录 `FAIL` 并分析原因。
- 纯文字对照与参考图结果可人工比较；不做“提示词重复即一致”的结论。

## 4. R1-D：关键帧设计

四个关键帧：

| ID | 名称 | 时间 | 月亮位置 | 候选来源 |
|---|---|---|---|---|
| KF1 | 江畔初月 | 日落后 | 左侧低空 | J2 / 重生成 |
| KF2 | 花林月照 | 入夜 | 左上方 | J3 或 J6 |
| KF3 | 孤舟远行 | 深夜 | 上方偏左 | J4 或 J7 |
| KF4 | 落月晨曦 | 黎明前 | 右侧低空 | J5 或 J8 |

要求：

- 全部 16:9（768×432）。
- 人工检查：河湾结构、远山轮廓、月亮方向、雾气浓度、现代物件。
- 关键帧之间不得出现空间跳变（孤舟换岸、远山消失、花林跑到对岸）。
- 选定资产复制到 `assets/keyframes/`，每个带 `.meta.json`。
- 关系写入 `assets/keyframes/relationships.json`。

## 5. R1-E：自动化能力

新增 `scripts/r1_batch.py`，复用 `scripts/r0_comfy_probe.py`，验证：

| 能力 | 验证方式 |
|---|---|
| 提交 FLUX API 工作流 | 批量任务实际进入 ComfyUI 队列 |
| 修改提示词 / seed / 尺寸 | 每个 job 的 `workflow.submitted.json` 不同 |
| 指定输出路径 | `experiments/r1/runs/<job>/` |
| 自动获取结果 | 输出文件落盘并记录哈希 |
| 记录生成参数 | `job.json` / `run.json` |
| 失败恢复 | 已完成任务再次运行被跳过；失败重试最多 2 次 |

断点续跑测试：

1. 跑完 J1。
2. 再次执行同一批任务，确认 J1 被 skip。
3. 人为删除 J1 输出后重跑，确认 J1 重新生成。

## 6. 安全边界

- 不升级 PyTorch / ComfyUI / 节点。
- 不修改 `workflows/r0_wan_*.json`。
- 不安装 SeedVR2 或其他未验证模型。
- 不修改系统 Python，不动 `D:\AI` 现有脚本与模型顶层文件。
- 模型权重不进 Git。
- 新增依赖：R1 不新增 Python 依赖；批处理只用标准库 + 现有 `.venv`。

## 7. 交付物

- `docs/R1_VISUAL_DESIGN.md`
- `docs/R1_TEST_PLAN.md`
- `docs/R1_TEST_REPORT.md`
- `assets/visual_style/`
- `assets/keyframes/`
- `experiments/r1/`（原始运行记录与对比图）
- `scripts/r1_batch.py`
- `workflows/r1_flux_edit_api.json`

## 8. 停止条件

完成 R1-A ~ R1-E 并写报告后停止，不进入 R2。
