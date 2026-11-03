# Literary Intelligence — L1 最小原型设计

> 状态：`PARTIAL`；LI-1 原型与 LI-1.5 真实 30B 五轮已跑通，人工审核仍为 `NOT_RUN`
> 日期：2026-11-03
> 范围：《洛神赋》单段证据链；不进入正式视频生产、不接 HanLP/Jiayan 生产、不做三篇扩展

## 1. 前置条件

L1 开始前必须确认：

- L0_AUDIT/TOOL_MATRIX/RISKS 已人工审查；
- 原文来源和许可已固定；
- 不下载大型数据集、不安装 torch、不修改根 `.venv`；
- 不修改 R3/S3 生产链路；
- Git 未提交工作受到保护；
- 本地 LLM 服务是否可用已实际探测，不硬编码未确认端点。

L1 的第一条记录必须先写 `source_registry.json`，再写任何解释。

## 2. 原文版本与上下文

目标段落：

> 翩若惊鸿，婉若游龙。

要求：

- 固定作品、作者、底本/版本、整理者、出版信息、URL/书目、获取日期、许可状态。
- 保存目标段落的上下文，至少覆盖相邻的“荣曜秋菊，华茂春松。髣髴兮若轻云之蔽月，飘飖兮若流风之回雪。”等句；具体文本以最终固定版本为准。
- 保存原文 SHA-256。
- 记录 `locator`（篇/段/句），不得只写“洛神赋”。
- 版本未确认时标 `UNVERIFIED`，不得补造“标准版本”。

LI-1 已固定的原文来源：

- 页面：Wikisource `洛神賦`，`oldid=7908816`，2026-07-19；
- 底本标注：昭明文選（四部叢刊本）卷19 / 曹子建集（四部叢刊本）卷3；
- 古代原文属公有领域；Wikisource 页面转录为 CC BY-SA 4.0/GFDL；
- 现代整理、校勘、注释、今译未使用；发布时复核页面转录的署名/相同方式共享义务；
- 原始繁体、规范化简体、映射和 SHA-256 已保存到 `corpus/luoshen_fu/`。

CTP/CNKGraph 等外部来源未用于 LI-1。不得抓取 CTP；CNKGraph 仅非商业研究参考。

## 3. 数据结构

### 3.1 `source_registry.json`

```json
{
  "source_id": "src_luoshen_001",
  "work": "洛神赋",
  "source_name": "待填写",
  "edition": "待填写",
  "author_or_editor": "待填写",
  "url_or_bibliography": "待填写",
  "content_sha256": "待填写",
  "retrieved_at": "待填写",
  "license": "待填写",
  "commercial_use": "UNVERIFIED",
  "scope": "原文/注释/今译/赏析分别标注",
  "locator": "篇/段/句"
}
```

### 3.2 `evidence.json`

```json
{
  "claim_id": "luoshen_001",
  "work": "洛神赋",
  "author": "曹植",
  "edition": "待填写",
  "locator": "篇/段/句",
  "quote": "翩若惊鸿，婉若游龙。",
  "claim_type": "original_text",
  "statement": "待填写",
  "source_refs": ["src_luoshen_001:locator"],
  "confidence": "high",
  "review_status": "unreviewed"
}
```

允许的 `claim_type`：

- `original_text`
- `historical_fact`
- `interpretation`
- `creative`

允许的 `review_status`：

- `unreviewed`
- `approved`
- `rejected`

规则：

- `original_text` 必须能定位到固定版本；
- `historical_fact` 必须有来源；
- `interpretation` 必须明确是解释；
- `creative` 必须明确是创作；
- 没有来源的事实性内容不得进入讲解稿；
- `source_refs` 不得由模型新增；
- `confidence` 不能替代证据。

## 4. 单段六层记录

### 第一层：原文

- 原文和上下文；
- 版本、locator、SHA-256；
- 异文/标点差异（如存在）；
- 不把现代注释混入原文。

### 第二层：字词

至少记录：

- 翩
- 婉
- 惊鸿
- 游龙

每条词义必须有来源；NLP 分词结果不能直接当词义证据。

### 第三层：修辞

- 比喻；
- 对偶；
- 句式和节奏；
- 两个意象的关系。

文本可观察特征与文学解释分开标注。

### 第四层：意象

- 鸿雁意象；
- 龙意象；
- 动态、姿态和视觉联想；
- 两个意象如何塑造洛神形象。

历史文化关联必须有证据；审美分析可以为 `interpretation`。

### 第五层：文化关联

只纳入可靠来源支持的内容；没有来源的联想不得写成历史事实。

### 第六层：现代转译

例如：

- 翩若惊鸿：轻盈、迅捷、灵动的动态视觉；
- 婉若游龙：柔韧、连续、流动的身体姿态。

此层可以 `creative`，但不得冒充原文或历史事实。

## 5. SQLite FTS5 原型

使用 Python 标准库 `sqlite3`。

L0 实测结果：

- FTS5 创建/写入/查询可用；
- `unicode61` 对 2 字中文查询不命中；
- `trigram` 对 3 字及以上中文子串有效；
- 2 字查询需要回退。

L1 设计：

- `documents` 表保存 `source_id`、`work`、`edition`、`locator`、`text`、`sha256`；
- `documents_fts` 使用 `tokenize='trigram'`；
- 3 字及以上短语走 FTS5；
- 2 字查询使用受控 `LIKE` 回退或辅助 bigram 表；
- 检索结果必须回传 `source_id` 和 `locator`；
- 不引入向量数据库。

验收测试至少包括：

- `若惊鸿` -> 命中；
- `春江潮` -> 命中（若语料包含）；
- `惊鸿` 2 字 -> 回退命中；
- 作品/版本过滤；
- 空结果和无来源查询。

## 6. LLM 证据约束测试

### 6.1 前置

- 读取项目 `config/settings.yaml` 的 LLM 配置；
- 实际探测 8080 是否监听；
- 若未监听，记录 `NOT_RUN`，不得猜测接口或启动其他模型；
- 不硬编码地址，不读取未知 8080 实例。

### 6.2 输入

只提供：

- 原文；
- 已结构化证据（含 claim_id/source_refs）；
- 内容组织要求；
- 禁止事项。

模型任务：把已有证据组织成可读讲解稿。

禁止：

- 补写历史事实；
- 编造典故或出处；
- 编造原文；
- 把解释写成唯一正确结论；
- 编造 source_refs/locator；
- 把 creative 混入原典事实。

### 6.3 反例

故意提供一个没有来源的历史说法，例如“某意象最早见于某书”，但不提供 source_ref。检查模型是否：

- 拒绝写入；
- 标注为待核验；
- 或错误地当成事实。

如果模型无法识别证据缺失，记录为失败；不得通过提示词包装成通过。

### 6.4 输出

讲解稿中的事实性陈述必须保留 claim_id 或 source_refs，便于反向追踪。

## 7. 人工审核记录

至少检查：

- 原文准确；
- 版本/上下文可靠；
- 字词解释有依据；
- 修辞分析合理；
- 文化关联有来源；
- 解释和事实分开；
- 现代转译不改变原意；
- LLM 未添加未经证实内容。

审核前全部保持 `unreviewed`；自动生成结果不得直接 `approved`。

## 8. 验收标准

| 项 | 标准 |
|---|---|
| 原文来源 | 版本、出处、locator 可追溯 |
| 文本完整性 | SHA-256 可复核 |
| 证据分类 | 四类 claim 正确区分 |
| 字词分析 | 事实性释义有来源 |
| 文学解释 | 明确标注 interpretation |
| FTS5 | 创建/写入/trigram/2 字回退通过 |
| LLM 组织 | 引用已有证据，不伪造 source_refs |
| 反例 | 发现无来源事实，或明确记录失败 |
| 人工审核 | 有完整审核记录 |
| 工程隔离 | 不影响生产链路 |
| 环境 | 不污染根 `.venv`，不安装 torch |
| Git | 不提交、不覆盖既有修改 |

## 9. 明确不做

- 三篇作品完整赏析；
- 自动批量选题；
- 自动生成完整视频；
- HanLP/Jiayan 正式接入；
- 大型语料下载；
- 向量检索/知识图谱；
- 前端/生产流水线整合。
