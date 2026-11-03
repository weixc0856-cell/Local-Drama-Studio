---
name: evidence-audit
description: Audit literary claims for valid source IDs, quote/locator matches, claim-type separation, and prohibited self-approval; reject unsupported facts rather than rewriting them into confident prose.
---

# Evidence Audit Skill

## 输入

- `claims.json`
- `source_registry.json`
- 原文、规范化文本、segments
- 审核记录

## 检查顺序

1. `source_id` 是否存在。
2. `source_refs` 是否全部存在。
3. `locator` 是否存在于来源 segments。
4. `quote` 是否出现在规范化文本。
5. `source_quote` 是否出现在原始文本。
6. `original_text` / `historical_fact` 是否有来源。
7. `creative` 是否被错误标成 `historical_fact`。
8. 是否存在无来源的历史说法。
9. LLM 是否试图自行 `approved`。
10. 审核记录是否来自人工。

## 输出

- `ValidationResult`：`ok` / `issues`，每项含 `code`、`claim_id`、字段和可读原因。
- 不自动把“无法确认”变成“正确”。

## 规则

- 引用字符串匹配不等于历史事实正确；仍需人工判断来源质量。
- 同一模型多轮意见一致不等于独立验证。
- 审核通过必须同时满足证据校验和人工审核。
- `rejected` 不得直接转为 `approved`。
- 拒绝时保留原 claim 和失败原因，不要静默删除。

## 常见错误码

`UNKNOWN_SOURCE`、`MISSING_SOURCE`、`INVALID_LOCATOR`、`QUOTE_NOT_FOUND`、`SOURCE_QUOTE_NOT_FOUND`、`QUOTE_WITHOUT_SOURCE`。
