# Local-Drama-Studio

本地 AI 短剧自动化生产实验室。目标链路：

```
剧本 → 分镜 → 人物/场景资产 → 首帧 → 视频片段 → 配音 → 字幕 → 剪辑 → MP4
```

这不是"装一个 ComfyUI 然后生成几段视频"，而是一套**有数据契约、有状态、可断点续跑**的生产流水线：

| 层 | 职责 | 技术 |
|---|---|---|
| 调度层 | 剧本解析、任务状态、资产复用、质量门、断点续跑 | Python 3.12 + Pydantic + SQLite + Typer |
| 生成层 | 静态图、图生视频/文生视频 | ComfyUI + FLUX.2 klein 4B + Wan2.2 TI2V 5B |
| 语音层 | 角色对白、旁白 | 已有 CosyVoice CPU 服务（`D:\AI\CosyVoice-Runtime`） |
| 文本层 | 剧本结构化、分镜、提示词 | 已有 llama.cpp 服务（`D:\AI`，Qwen3） |
| 合成层 | 拼接、混音、字幕、转码 | FFmpeg 8.1 |

**ComfyUI 只是底层生成引擎，不是项目本体。**

---

## 当前状态（2026-11-02）

| 项目 | 状态 |
|---|---|
| 根目录 `.venv`（调度环境） | ✅ 已创建（Python 3.12.10，uv 0.10.8） |
| 配置 / 数据契约 / doctor | ✅ 已实现，11 项测试通过 |
| R0-A 硬件与依赖诊断 | ✅ `PASS_VERIFIED`（见 [R0_TEST_REPORT](docs/R0_TEST_REPORT.md)） |
| R0-B ComfyUI + PyTorch XPU | ✅ `PASS_VERIFIED`：ComfyUI 0.43.0 / torch 2.15.0+xpu / xpu:0 Arc A750 7.75 GiB |
| R0-C FLUX 静态图 | ✅ `PASS_VERIFIED`：512×512 / 4 步 / 99.5s / 峰值 2.61 GiB |
| R0-D Wan 视频 | ✅ `PASS_VERIFIED`：T2V/I2V 512×512×33 帧，20 步；I2V 约 10 分钟 |
| R0-E 模型互斥 / 重载 | ✅ `PASS_VERIFIED`：3 轮 FLUX↔Wan 切换无 OOM |
| R1-A 项目审查 | ✅ `PASS_VERIFIED`（[R1_AUDIT](docs/R1_AUDIT.md)） |
| R1-B 视觉规范 | ✅ `PASS_VERIFIED`（[R1_VISUAL_DESIGN](docs/R1_VISUAL_DESIGN.md)） |
| R1-C FLUX 16:9 资产 | ✅ `PASS_VERIFIED`：11 次生成，768×432，70-102 s/张，峰值 2.84 GiB |
| R1-D 关键帧 | ✅ `PASS_VERIFIED`（保留 KF4 光源歧义） |
| R1-E 批处理/续跑/恢复 | ✅ `PASS_VERIFIED` |
| R2-A 1024×576 边界测试 | ✅ 73 帧 `PASS_VERIFIED`；121 帧 `PASS_LIMITED`（A4 漂色） |
| R2-B 英雄镜头 | ✅ 4/4 技术成功；H2 `PASS_VERIFIED`，H1/H3/H4 `PASS_LIMITED` |
| R3-R7 | ⛔ 按约束停在 R2-B |

```powershell
# 任何时候查看真实状态（不会猜测，未执行即 NOT_RUN）
scripts\doctor.ps1
```

### R1 结论摘要

- 16:9（768×432）可直接生成，无需改工作流；约 70-102 秒/张，峰值 2.84 GiB。
- `ReferenceLatent` 参考图编辑在本机 Q4 + XPU 上可用；它保留河湾/远山/色板，提示词控制时间与内容。
- 四张关键帧：江畔初月、花林月照、孤舟远行、落月晨曦；见 [assets/keyframes/](assets/keyframes/)。
- 一致性对比：参考图辅助在空间锚点上更稳，纯文字色板接近但地貌会漂移。
- 明确未做：1080p、视频、人物一致性。下一步 R2 必须先解决 Wan 的 /32 分辨率约束（1024×576）。

### R2-A 结论摘要

- 1024×576 可行：73 帧 40-43 分钟 / 3 秒，121 帧 66-69 分钟 / 5 秒，峰值 ≤6.12 GiB，无 OOM。
- **默认 73 帧**；121 帧的 A4 花林出现肉眼可见的绿色漂移。
- 动作幅度普遍偏小；“孤舟漂移”几乎没有位移。
- 全 Wan 的 90 秒片约 20 小时；4-6 个 Wan 镜头 + 静帧推拉的混合方案约 4-5 小时。
- R2-B 随后执行（见下一节）；R2-B 后停在 R3 之前。

### R2-B 结论摘要

- 4 个英雄镜头全部生成，总耗时 2.62 小时，峰值 ≤5.66 GiB。
- H2 花林推近可直接使用。
- H3 孤舟有 24.6 px 主体位移，但方向向右下（靠近镜头），不是向远山；不能用于“远去”叙事。
- H1/H4 可作为近静态空镜，但推近/暖光变化未实现。
- 结论：Wan 适合“缓慢推近”类英雄镜头；精确主体位移需后期或改镜头设计。

### R0 结论摘要

- 两个模型都能在 A750 8 GB 上实际推理：FLUX 约 95-100 秒/张，Wan 约 9-10 分钟/1.375 秒片段。
- Wan **必须 20 步**；10 步会产生彩虹伪影。
- 文本编码器（Qwen3-4B / UMT5）放在 CPU，扩散模型与 VAE 在 XPU；峰值显存约 5 GiB。
- 45 秒成片按实测外推约 7-10 小时/集，属于挂机批处理，不是交互式创作。
- 完整证据与限制见 [docs/R0_TEST_REPORT.md](docs/R0_TEST_REPORT.md) §6。

---

## 环境边界（必须保持）

```
Local-Drama-Studio\
├─ .venv\                    # 调度环境：只装 httpx / pydantic / typer / FFmpeg 调用
├─ runtime\
│  └─ ComfyUI\
│     ├─ .venv\              # 生成环境：PyTorch XPU + ComfyUI + GGUF 节点，独立
│     ├─ custom_nodes\
│     └─ extra_model_paths.yaml
├─ config\                   # 全局配置（模型、生成参数、音频）
├─ workflows\                # ComfyUI API 格式工作流
├─ src\drama_studio\
├─ projects\                 # 每个短剧一个目录，含 state.db
└─ scripts\                  # setup / doctor / start / stop
```

两条硬规则：

1. **根 `.venv` 永远不安装 torch。** Torch/XPU 只存在于 `runtime/ComfyUI/.venv`，ComfyUI 升级不会污染其他项目。
2. **模型权重不复制、不进 Git。** 统一存放在 `D:\AI\models`，ComfyUI 通过 `extra_model_paths.yaml` 引用。

`D:\AI\models` 的顶层文件**不能移动**：`D:\AI\start_server.bat` 只扫描顶层 `*.gguf`。新增的文本编码器/VAE 放到 `text_encoders\`、`vae\` 子目录，ComfyUI 同时映射顶层和子目录。

---

## 快速开始

```powershell
# 1. 创建调度环境（幂等）
uv sync --python 3.12

# 2. 健康检查（写 logs\doctor-*.json）
scripts\doctor.ps1

# 3. 安装生成引擎（独立 venv，下载 PyTorch XPU）
scripts\setup.ps1 -WithComfyUI

# 4. 启动/停止 ComfyUI
scripts\start.ps1
scripts\stop.ps1
```

模型配套文件（文本编码器、VAE）的下载清单与目标路径见 [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)。

---

## CLI 规划

R0 只实现 `doctor`，其余命令随阶段验收逐个加入：

```text
drama doctor                 # 环境/服务/模型真实状态        [已实现]
drama create <project>       # 创建短剧项目                  [R4]
drama script <project>       # 剧本 → storyboard.json        [R4]
drama assets <project>       # 人物/场景/道具参考图           [R5]
drama images <project>       # 分镜首帧                      [R5]
drama videos <project>       # Wan 批量生成镜头片段          [R2/R3]
drama audio <project>        # 配音 + 字幕                   [R6]
drama render <project>       # 剪辑 + 输出 MP4               [R6]
drama run <project>          # 完整流水线                    [R7]
drama resume <project>       # 断点续跑                      [R7]
```

第一个可验收目标不是"一分钟大片"，而是：**30-45 秒、3-5 个镜头、有人物对白、有配音、有字幕、可稳定重复产出的完整 MP4。**

---

## 阶段路线

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| R0 | 硬件 / XPU / ComfyUI / 两个 GGUF 模型 | A750 上实际推理成功，有日志与产物 |
| R1 | FLUX.2 klein 静态图 | 角色参考图 + 场景图可复现 |
| R2 | Wan2.2 TI2V 视频 | 2-3 秒短片段可生成、可播放 |
| R3 | ComfyUI API 调度 | Python 提交 → 等待 → 取回，含失败重试 |
| R4 | 剧本 / 分镜引擎 | 本地 LLM 输出通过 Pydantic 校验的 JSON |
| R5 | 人物资产管理 | 多镜头复用同一角色参考图 |
| R6 | 配音 / 字幕 / 剪辑 | 自动输出完整 MP4 |
| R7 | 端到端 | 一条命令，断点续跑，10 镜头重开只补未完成部分 |

每个阶段必须实际运行、保留退出码与日志，通过后才进入下一阶段。

---

## 明确不做

- 不做网页管理后台（先 CLI）
- 不引入 LangChain / 向量数据库 / 多 Agent 框架
- 不自己训练或微调生成模型
- 不承诺首阶段的电影级人物一致性与口型同步
- 不在 8GB 显存上同时加载 LLM、FLUX、Wan

---

## 文档

| 文档 | 内容 |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统设计、数据契约、状态机、失败恢复 |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | 已核实硬件、双 venv、模型仓库、端口与显存预算 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | 关键设计决策（ADR） |
| [docs/R0_TEST_PLAN.md](docs/R0_TEST_PLAN.md) | R0-A ~ R0-E 测试步骤与验收标准 |
| [docs/R0_TEST_REPORT.md](docs/R0_TEST_REPORT.md) | R0 实际执行结果与证据 |
| [docs/R1_AUDIT.md](docs/R1_AUDIT.md) | R1 现有工作流/编辑能力审查 |
| [docs/R1_VISUAL_DESIGN.md](docs/R1_VISUAL_DESIGN.md) | 《春江花月夜》视觉规范 |
| [docs/R1_TEST_PLAN.md](docs/R1_TEST_PLAN.md) | R1 实验与关键帧计划 |
| [docs/R1_TEST_REPORT.md](docs/R1_TEST_REPORT.md) | R1 实际结果、对比与限制 |
| [docs/R2_TEST_PLAN.md](docs/R2_TEST_PLAN.md) | R2-A/R2-B 计划 |
| [docs/R2_TEST_REPORT.md](docs/R2_TEST_REPORT.md) | R2-A 实测结果与生产预算 |
| [docs/R2B_TEST_PLAN.md](docs/R2B_TEST_PLAN.md) | 4 个英雄镜头设计与验收口径 |
| [docs/R2B_TEST_REPORT.md](docs/R2B_TEST_REPORT.md) | R2-B 逐镜头结果与 H3 位移分析 |
| [docs/CONTENT_PACKS.md](docs/CONTENT_PACKS.md) | 通用主题包与共享层边界 |
