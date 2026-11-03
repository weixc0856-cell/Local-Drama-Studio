---
name: literary-analysis
description: Analyze a fixed classical Chinese passage as text observations and explicitly provisional interpretations; never present interpretation as historical fact.
---

# Literary Analysis Skill

## 输入

- 已登记的原文来源与 locator；
- 原文和上下文；
- 允许的 claim 类型：`original_text` / `historical_fact` / `interpretation` / `creative`。

## 输出

只输出候选 claim。每条必须包含：

- `claim_id`
- `source_refs`
- `locator`
- `quote` / `source_quote`
- `claim_type`
- `statement`
- `confidence`
- `review_status: unreviewed`

## 规则

1. 先观察，后解释。
2. 字词、句式、对偶、意象候选属于文本观察；可以标 `interpretation`，不要标 `historical_fact`。
3. 每个解释至少说明支持理由和不确定性。
4. 不用现代审美判断冒充古人原意。
5. 没有来源的历史说法必须留空或降级为待核验，不得编造 `source_refs`。
6. 不修改原文，不补写不存在的句子。
7. 不自行把任何 claim 标为 `approved`。

## 检查

- 引文是否来自固定原文？
- locator 是否有效？
- 是否把解释写成了唯一正确结论？
- 是否混入了没有来源的历史事实？
