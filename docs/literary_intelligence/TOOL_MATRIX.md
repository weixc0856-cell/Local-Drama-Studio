# Literary Intelligence — L0 工具与数据源矩阵

> 日期：2026-11-03
> 状态规则：`PASS_VERIFIED` / `PASS_STATIC` / `PARTIAL` / `NOT_RUN`
> 本矩阵不把“有官方介绍”写成“已可生产使用”。

| 对象 | 核验内容 | 许可证 | 商业使用 | 依赖/运行要求 | 主要风险 | 状态 |
|---|---|---|---|---|---|---|
| HanLP 代码 | v2.1.1；分词/POS/句法等通用 NLP | Apache-2.0 | 代码层面允许 | Python >=3.6；torch>=1.6；transformers | 代码许可 ≠ 模型许可 | `PASS_STATIC` |
| HanLP 古汉语模型 | `KYOTO_EVAHAN_TOK_LEM_POS_UDEP_LZH`；分词、词形还原、POS、依存 | 默认 **CC BY-NC-SA 4.0**（模型页未另注） | **不允许直接商业使用** | 需 torch；模型约 450 MB | 非商业许可；无 NER；需独立 Runtime | `PARTIAL` |
| Jiayan 代码 | v0.0.21（2019）；分词、POS、断句、标点 | MIT | 代码层面允许 | 需额外安装 KenLM 源码；Python 旧版本声明 | 维护停滞；模型不在官方 Release | `PARTIAL` |
| Jiayan 模型 | 词库/CRF/HMM 模型经百度网盘或 Google Drive | **未明确** | **未确认** | 需手动下载/解压 | 无官方哈希/大小/许可；不可重复获取 | `NOT_RUN` |
| CTP | 古籍章节、正文、JSON API、Python 模块 | 订阅/站点条款；未确认开放再分发 | **未确认** | 订阅/API；禁止抓取 | 禁止 scraping；批量/缓存/再分发不明 | `PARTIAL` |
| CNKGraph | 诗文库/古籍库 API；诗文约 488 MB，古籍约 2 GB | 站点条款 | **仅限非商业** | HTTP API；研究/学习 | 不得进入商业发布链路 | `NOT_RUN`（商业） |
| Gujilab classical corpus | 1,970,924 行；约 823 MB；corpus/translate/punctuate | 结构化数据 CC0；代码 MIT | 数据集声明允许；上游需复核 | 下载 823 MB；本地解析 | 来源含 ctext.org 等；上游条款冲突风险 | `PARTIAL` |
| NiuTrans Classical-Modern | 古文-现代文平行语料；MIT 声明 | MIT（数据声明） | 需逐项复核原文版权 | 数据下载 | 数据来自互联网，原文版权归原来源 | `NOT_RUN` |
| SQLite FTS5 | 创建、写入、trigram 查询 | SQLite 公有领域 | 可用 | Python 内置 sqlite3 | 2 字中文查询不命中；需回退设计 | `PASS_VERIFIED` |
| 本地 LLM | 8080 OpenAI 兼容端点的配置/探测 | `Qwen3-30B-A3B-Instruct-2507` | 取决于模型 | 8080 在线（2026-11-03，CPU-only，64K）；客户端已实现 | 可能幻觉；不能当证据 | 质量证据 `NOT_RUN` |
| 向量数据库 / LangChain / Neo4j | 语义检索/编排/图数据库 | 不适用 | 不适用 | 未安装 | 本阶段明确不引入 | `NOT_RUN` |

## 逐项说明

### HanLP

- 官方 Release `v2.1.1`，2025-01-13；仓库代码 Apache-2.0。
- 古汉语模型 `KYOTO_EVAHAN_TOK_LEM_POS_UDEP_LZH` 支持分词、词形还原、POS、依存；不支持 NER。
- 模型包 `450,378,307` bytes；`hanlp==2.1.1` 的依赖包含 `torch>=1.6.0`、`transformers>=4.1.1`。
- 官方 README：除非另有说明，所有模型采用 **CC BY-NC-SA 4.0**；古汉语模型页没有单独的宽松许可。
- 结论：技术可研究，模型许可阻塞商业生产；不得安装到根 `.venv`。

### Jiayan

- 代码 MIT，PyPI `0.0.21`（2019），仓库最后 push 2021-11-02。
- README 的功能包括词库构建、分词、POS、断句、标点；模型文件通过百度网盘/Google Drive 分发。
- 模型大小、哈希、许可证、训练数据均未明确；运行还依赖 KenLM 源码。
- 结论：不作为生产候选；如研究，必须先锁定模型来源和许可。

### Chinese Text Project

- 官方 API 页面说明 JSON API/Python 模块通过订阅提供。
- 官方页面明确反对 scraping，并会返回 corrupted data 干扰抓取。
- 没有看到明确的商业使用、缓存、再分发许可。
- 结论：不能爬取；如使用必须取得订阅/API 授权并逐项记录条款。

### CNKGraph

- 官方开放资源页明确“仅限非商业用途”，提供诗文库/古籍库 API。
- 没有可替代的商业许可说明。
- 结论：不得作为商业发布链路的数据源。

### Gujilab / chinese-classical-corpus

- 数据卡声明 `cc0-1.0`，约 823 MB、1,970,924 行；代码 MIT。
- 来源包括殆知阁、Wikisource、ctext.org、NiuTrans 等；上游需分别核验。
- ctext.org 的抓取限制与数据集的 CC0 声明之间存在来源风险。
- 结论：只能作为候选，下载前必须获得批准并做来源级审计。

### SQLite FTS5

- 本机 `sqlite3 3.49.1` 实际创建/写入/`trigram` 查询成功。
- `unicode61`/`trigram` 对 2 字中文查询不命中；L1 必须设计 `LIKE` 回退或 bigram 辅助表。
- 结论：可用，但不是“中文语义检索”。

### 本地 LLM

- 配置指向 `http://127.0.0.1:8080/v1`；2026-11-03 在线，模型 `Qwen3-30B-A3B-Instruct-2507`，CPU-only（`-ngl 0`），64K 上下文。
- 文学客户端：`literary_intelligence/harness/llm_client.py`（`OpenAICompatibleLLMClient`）+ 入口 `run_li15.py`。
- 结论：服务与客户端已就绪；真实五轮输出尚未落盘，质量结论仍为 `NOT_RUN`。

## 矩阵结论

```text
可以继续研究：SQLite FTS5、结构化证据模型、来源登记
需要人工批准：HanLP 独立 Runtime（非商业）、Gujilab 数据下载
不得进入商业链路：HanLP 默认模型、CNKGraph、CTP 未授权抓取
暂不接入：Jiayan、向量数据库、LangChain、Neo4j
未执行：L1、真实 LLM 测试、模型推理、任何大型语料下载
```
