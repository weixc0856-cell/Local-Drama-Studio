# Literary Intelligence — LI-1

独立的最小文学证据链原型。它不接入 R3/S3 视频生产链路，也不把 HanLP/Jiayan 作为依赖。

## 当前状态

| 项 | 状态 |
|---|---|
| 原文与来源登记 | `PARTIAL`（原文公有领域；Wikisource 页面转录为 CC BY-SA 4.0/GFDL） |
| Pydantic 数据模型 | `PASS_VERIFIED` |
| FTS5 检索 | `PASS_VERIFIED`（trigram + 2 字 LIKE 回退） |
| 证据校验 | `PASS_VERIFIED`（测试） |
| 五轮 Mock LLM | `PASS_VERIFIED`（fixture only） |
| 真实本地 LLM | `PARTIAL`：30B/64k 五轮已跑通、5/5 JSON、证据校验通过；存在 1 次角色违规和 skeptic 质量问题；人工审核 `NOT_RUN` |
| 人工审核 | `NOT_RUN`；`reviews.json` 为空 |
| 内容导出 | 仅 approved；当前无 approved claim，导出为空 |
| 视频生产链路 | 未修改 |

**Mock 通过不代表真实 LLM 通过；引用匹配不代表历史事实正确；JSON Schema 通过不代表文学解释正确。**

## 目录

```text
literary_intelligence/
├── schemas/                 # Pydantic 模型与 JSON Schema 导出
├── harness/                 # 规范化、来源、检索、校验、状态机、Mock LLM
├── skills/                  # 四个分析/研究/审核/写作 Skill
├── corpus/luoshen_fu/       # 固定原文、规范化文本、来源、claims、reviews
└── tests/                   # 49 项测试 + mock fixture
```

## 原文来源

- 作品：曹植《洛神賦》
- 来源：Wikisource `oldid=7908816`（2026-07-19）
- 底本标注：昭明文選（四部叢刊本）卷19 / 曹子建集（四部叢刊本）卷3
- 本仓库保存目标段落及邻近上下文，不保存整篇作品。
- 原始繁体、规范化简体、字符映射和 SHA-256 均保留。
- 古代原文属公有领域，可用于商业创作；Wikisource 页面转录为 CC BY-SA 4.0/GFDL，发布时可能需要署名/相同方式共享。未使用现代整理、注释或今译。

来源登记：

- `corpus/luoshen_fu/source_registry.json`
- `corpus/luoshen_fu/original_text.txt`（权威引文）
- `corpus/luoshen_fu/normalized_text.txt`（检索/比较）
- `corpus/luoshen_fu/segments.json`
- `corpus/luoshen_fu/claims.json`（全部 `unreviewed`）
- `corpus/luoshen_fu/reviews.json`（空）

## 使用

```powershell
# 运行 LI-1 测试
.venv\Scripts\python.exe -B -m pytest literary_intelligence/tests -q -p no:cacheprovider

# 导出 JSON Schema
.venv\Scripts\python.exe -B -m literary_intelligence.schemas.export_schemas --out literary_intelligence/schemas/json
```

Mock 五轮流程在测试中运行；真实 LLM 在 8080 在线时通过 `run_li15.py` 调用；LI-1.5 运行器会在结束后停止自己启动的服务、释放端口。

## LI-1.6-B 角色合同

- `text_analyst` 必须覆盖 `context.target`；目标 claim 的 locator 必须等于 target.locator 且 `scope=target`；邻近 claim 必须 `scope=contextual`，不能冒充目标句。目标无法分析时使用 `coverage=not_analyzable`。
- `researcher` 禁止 `original_text`、禁止回显已有 claim；无来源 `historical_fact` 直接失败。
- `skeptic` 必须返回 `findings` 或 `no_material_risk`；findings 必须包含结构化风险字段，不能只给标签。
- `editor` 没有 approved claim 时必须空 `draft_text`；任何 LLM 输出仍为 `unreviewed`。

程序级检查在 `literary_intelligence/harness/pipeline.py`；不是只依赖提示词。

## 关键规则

- `original_text` / `historical_fact` 必须有有效来源；`creative` 不要求来源，但必须保留 `creative` 标签。
- `quote` 必须出现在规范化来源文本；`source_quote` 必须出现在原始繁体文本。
- `locator` 必须是来源登记中的有效段落。
- 未知 `source_id`、伪造引文、缺失来源、无效 locator 均拒绝。
- LLM 输出只能是 `unreviewed`；LLM 不能执行审核。
- 只有人工审核 + 有效证据才可 `approved`。
- 导出只读取 approved claim，保留 `claim_id` 和 `claim_type`。

## 真实 LLM

项目本地端点 `http://127.0.0.1:8080/v1` 于 2026-11-03 核验在线：`Qwen3-30B-A3B-Instruct-2507`（CPU-only `-ngl 0`，64K 上下文 `-c 65536`）。默认模型与路径来自 `config/settings.yaml`（`llm.model` / `llm.model_path` / `llm.context_size`），不在代码里硬编码。

`harness/llm_client.py` 提供：

- `OpenAICompatibleLLMClient`：真实调用（默认通道）；
- `MockLLMClient`：fixture 测试用；
- `UnavailableLLMClient`：服务不可用时明确失败；
- `LocalLLMClient`：由调用方注入经过核验的 `invoke(pass_name, context)` 适配器。

运行入口：

```powershell
.venv\Scripts\python.exe -m literary_intelligence.run_li15
```

五轮真实输出写入 `literary_intelligence/runs/li15/`；原始输出、失败记录和检查记录均保留。真实模型质量仍为 `PARTIAL`，未获人工批准。

LI-1.5 真实运行命令（8080；服务未启动时运行器会自动拉起，结束后自动停止）：

```powershell
.venv\Scripts\python.exe -B -m literary_intelligence.run_li15 `
  --model Qwen3-30B-A3B-Instruct-2507 `
  --max-tokens 1600 --timeout 900
```

运行结果写入 `literary_intelligence/runs/li15/`。原始输出和失败记录都保留，不会自动批准。

运行器会检查 8080：服务未启动时自动拉起项目实例（`scripts\llm_server.ps1 -Action start`），结束后只停止自己启动的实例并释放端口；服务已由其他程序启动时不动它。需要手动管理时加 `--no-manage-server`。

## 已知限制

- 只有一篇作品、一个目标段落。
- 没有真实 LLM 分析质量证据。
- 没有真实人工审核；所有 claims 仍为 `unreviewed`。
- 没有历史事实 approved；文化关联尚未建立。
- 没有视频输出或生产链路接入。
- 2 字查询使用 LIKE 回退，不是语义检索。
- 来源转录的 CC BY-SA 义务仍需复核。
