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
| 短剧业务功能（R1-R7） | ⛔ R0 已完成，按约束停在这里 |

```powershell
# 任何时候查看真实状态（不会猜测，未执行即 NOT_RUN）
scripts\doctor.ps1
```

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
| [docs/R0_TEST_REPORT.md](docs/R0_TEST_REPORT.md) | 实际执行结果与证据 |
