# Literary Intelligence — L0 工具与数据来源可行性审计

> 日期：2026-11-03
> 范围：L0 only；不安装依赖、不下载模型权重/大型语料、不进入 L1
> 结论先行：**HanLP 古汉语模型技术上存在，但默认非商业许可和 torch 依赖构成生产阻塞；Jiayan 模型许可/分发不明确；CTP/CNKGraph 均不能直接作为商业数据源。L0 建议有条件继续研究，不能直接接入正式生产。**

## 1. Git 与环境基线

```text
branch: main
HEAD: ad921ed
staged: empty
tracked modifications:
  docs/*.md (S3-B.1/S3-B.2)
  scripts/r3_build.py (S3-A.5/S3-B.2)
untracked:
  assets/fonts/, config/fonts.yaml, docs/R3D_*.md,
  experiments/r3d/, src/drama_studio/fonts.py,
  src/drama_studio/voice/, tests/test_fonts.py
```

本阶段没有执行 `git reset`、`git checkout`、`git clean`，没有覆盖现有 S3-A/S3-B 修改，没有暂存或提交。

## 2. Python 与 SQLite 环境

实际检查：

```text
Python 3.12.10
sqlite3 3.49.1
torch: absent
tensorflow: absent
hanlp: absent
jieba: absent
transformers: absent
onnxruntime: absent
```

项目 `.venv` 的依赖来自 `pyproject.toml`：typer、rich、pydantic、pyyaml、httpx、websockets、pysubs2、pillow、pytest。没有 torch，也没有 HanLP/Jiayan 相关包。

## 3. SQLite FTS5 实测

实际执行了临时数据库创建、虚拟表创建、插入和 `MATCH` 查询：

```text
CREATE VIRTUAL TABLE docs USING fts5(work, body, tokenize='trigram');
INSERT ... ('洛神赋', '翩若惊鸿，婉若游龙。')
INSERT ... ('春江花月夜', '春江潮水连海平。')
MATCH '若惊鸿' -> 1 行
MATCH '春江潮' -> 1 行
```

同时观察到：

```text
unicode61 tokenizer: MATCH '惊鸿' -> 0 行
trigram tokenizer:   MATCH '惊鸿' -> 0 行（少于 3 个字符）
```

结论：

- **FTS5 创建、写入和检索在本机可用**：`PASS_VERIFIED`。
- 默认 `unicode61` 对中文双字查询不能直接满足需求。
- `trigram` 适合 3 字及以上中文子串；2 字查询需要单独的 `LIKE` 回退、辅助 bigram 表或扩大查询上下文。
- L1 不得把“FTS5 可用”误解为“中文语义检索已完成”。

## 4. HanLP 核验

### 4.1 官方事实

| 项 | 结果 |
|---|---|
| 官方仓库 | https://github.com/hankcs/HanLP |
| 最新 Release | `v2.1.1`，2025-01-13 |
| 代码许可证 | Apache License 2.0 |
| Python 包 | `hanlp==2.1.1`，要求 Python >=3.6 |
| 关键依赖 | `torch>=1.6.0`、`transformers>=4.1.1`、`hanlp-common`、`hanlp-downloader`、`sentencepiece` 等 |
| 古汉语模型 | `KYOTO_EVAHAN_TOK_LEM_POS_UDEP_LZH` |
| 模型任务 | 分词、词形还原、词性标注、依存句法分析 |
| 模型大小 | `450,378,307` bytes（约 429.5 MiB） |
| 模型下载 | `https://file.hankcs.com/hanlp/mtl/kyoto_evahan_tok_lem_pos_udep_bert-ancient-chinese_lr_1_aug_dict_20250112_154422.zip` |
| 模型页明确 NER | **没有**；古汉语模型条目只列四项任务 |
| 代码许可 vs 模型许可 | 代码 Apache-2.0；官方 README 明确“除非另有说明，所有模型为 **CC BY-NC-SA 4.0**” |
| 训练数据许可 | EvaHan/UD 数据许可未在模型页单独确认；不得由模型许可推断训练数据无限制 |

### 4.2 判断

本阶段**未下载模型、未安装 torch、未执行推理**；HanLP 运行时状态是 `NOT_RUN`，只有官方静态证据。

- **技术能力**：官方确实发布了古汉语模型，支持分词、词形还原、POS、依存；不支持该模型条目下的 NER。
- **运行时**：必须依赖 torch，根 `.venv` 明确不能安装 torch。只能在独立 Runtime 中评估，且会引入大型依赖。
- **许可**：模型默认 **CC BY-NC-SA 4.0**，即非商业、相同方式共享；古汉语模型页未给出单独的宽松许可。代码 Apache-2.0 不能推出模型可商用。
- **当前状态**：`PARTIAL`（官方能力有静态证据；未下载模型、未运行、商业许可不满足）。
- **建议**：不进入正式生产；如仅做学术/内部研究，必须另建隔离环境并取得明确的模型使用/商业许可结论。

## 5. Jiayan 核验

| 项 | 结果 |
|---|---|
| 官方仓库 | https://github.com/jiaeyan/Jiayan |
| 代码许可证 | MIT |
| 最新 PyPI | `jiayan 0.0.21`，2019-09-16 |
| 最近代码 push | 2021-11-02（维护活跃度低） |
| 功能 | 词库构建、分词、POS、断句、标点 |
| 模型分发 | README 指向百度网盘 / Google Drive，非官方 Release |
| 模型大小/哈希 | 未提供 |
| 模型许可 | 未在 README/仓库中明确；模型与代码许可需分开判断 |
| 训练数据许可 | 未说明；不得由代码 MIT 推断模型/训练数据可商用 |
| 运行依赖 | README 要求额外安装 KenLM（GitHub 源码） |
| 当前状态 | `PARTIAL`（代码 MIT 有证据；模型许可、体积、哈希、可重复获取均未确认） |

结论：不作为生产候选；若后续研究，必须先取得模型文件的来源、大小、SHA-256 和明确许可，不能使用网盘文件直接进入可发布流程。

## 6. 古籍数据源核验

### 6.1 Chinese Text Project（CTP）

官方页面：https://ctext.org/tools/api

实际页面可读到的关键点：

- “Subscription gives access to a very easy to use JSON API and Python module.”
- “Web scraping of this site is in violation of our terms of service.”
- “you do not have authorization to scrape this page.”
- 对抓取行为会“intermittently intentionally return corrupted data”。

结论：

- API 是订阅/授权制，未看到公开发布的商业使用或再分发许可。
- 明确禁止网页抓取；不得用爬虫绕过。页面未给出可公开引用的固定数值频率上限，实际限制由订阅/服务端控制。
- 当前状态：`PARTIAL` / 商业使用 `NOT_RUN`。
- 若 L1 使用 CTP，必须先确认订阅、API Key、缓存和引用条款；不能批量抓取或缓存全文后再分发。

### 6.2 中国知识图谱网（CNKGraph）

官方页面：https://api.cnkgraph.com/Home/OpenResources

关键点：

- 明确“仅限非商业用途”（研究、学习）。
- 诗文库约 488 MB；古籍库约 2 GB。
- 页面没有提供可替代的商业许可。
- 未看到明确的再分发授权。

结论：**不得作为商业发布链路的数据源**。可作研究参考，但必须记录限制；当前 `NOT_RUN`（商业用途）。

### 6.3 结构化古籍语料：Gujilab / chinese-classical-corpus

官方仓库/数据卡：

- https://github.com/gujilab/chinese-classical-corpus
- https://huggingface.co/datasets/gujilab/chinese-classical-corpus

已核实的事实：

- 数据卡标注 `cc0-1.0`；README 说明结构化数据和代码分别为 CC0/MIT。
- 约 1,970,924 行、823 MB；三个配置：corpus、translate、punctuate。
- 来源包括殆知阁、chinese-poetry、Wikisource、**ctext.org**、NiuTrans/Classical-Modern 等。
- README 明确上层文本为公共领域，但也注明第三方来源各自 license 详见 LICENSE。

风险：

- 数据集对“结构化处理”声明 CC0，不等于所有上游来源的访问/再分发条款都自动清空。
- 来源中明确包含 ctext.org，而 CTP 禁止抓取；可能存在上游条款冲突。
- 823 MB 的下载量在未获批准前不得下载。
- 当前状态：`PARTIAL`，高风险；只能作为候选，不可直接作为商业发布证据库。

## 7. 本地 LLM 现状

- 原审计（2026-11-02）：`config/settings.yaml` 指向 `http://127.0.0.1:8081/v1`，模型名 `Qwen3.5-4B`；8081 未监听；`src/drama_studio` 只有 `LLMSettings` 和 `doctor.py` 探测。
- **2026-11-03 更新**：服务已在 `8080`（ADR-013 后的唯一端口）在线，提供 `Qwen3-30B-A3B-Instruct-2507`（CPU-only `-ngl 0`，`-c 65536` 即 64K，已验证可用）；`config/settings.yaml` 已改为该别名 + GGUF 路径 + `context_size: 65536`。调用结束后由 `scripts/llm_server.ps1` 停止服务、释放端口。
- 文学客户端已实现：`literary_intelligence/harness/llm_client.py` 的 `OpenAICompatibleLLMClient`，入口 `literary_intelligence/run_li15.py`。
- 结论：服务与客户端均可用；五轮真实输出尚未落盘（`literary_intelligence/runs/li15/` 为空），真实模型质量证据仍为 `NOT_RUN`。

## 8. L0 结论

1. FTS5 可用，但中文双字查询需要额外设计。
2. HanLP 古汉语模型存在，但模型默认非商业许可 + torch 依赖，不能直接进入项目根环境或商业生产。
3. Jiayan 代码 MIT，但模型分发/许可/哈希不明确，不值得优先接入。
4. CTP 禁止抓取、API 订阅制；CNKGraph 仅非商业；Gujilab 语料 CC0 声明但上游含 CTP，存在来源风险。
5. 当前最稳妥的路线是：先建立本地、可追溯、证据优先的小型语料；不下载大型数据集，不接 NLP 生产依赖。
6. L1 尚未执行，等待人工审查 L0 后另行批准。

## 9. 证据来源

- HanLP repo: https://github.com/hankcs/HanLP
- HanLP v2.1.1 release: https://github.com/hankcs/HanLP/releases/tag/v2.1.1
- HanLP ancient model docs: https://hanlp.hankcs.com/docs/api/hanlp/pretrained/mtl.html
- HanLP PyPI metadata: https://pypi.org/project/hanlp/2.1.1/
- Jiayan repo: https://github.com/jiaeyan/Jiayan
- Jiayan PyPI: https://pypi.org/project/jiayan/0.0.21/
- CTP API: https://ctext.org/tools/api
- CNKGraph open resources: https://api.cnkgraph.com/Home/OpenResources
- Gujilab corpus: https://github.com/gujilab/chinese-classical-corpus
- Gujilab HF: https://huggingface.co/datasets/gujilab/chinese-classical-corpus
