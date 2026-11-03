---
name: classical-text-research
description: Research classical Chinese sources with explicit provenance, edition, locator, and license; do not invent citations or treat a dataset's CC0 label as clearance for all upstream content.
---

# Classical Text Research Skill

## 输入

- 需要核验的原文、词语、典故、作者背景或相关作品；
- 允许的已登记来源。

## 输出

- `source_registry.json` 候选记录；
- 每条事实对应的 locator；
- 找不到来源时明确返回 `UNVERIFIED`，不要补写。

## 规则

1. 先确认底本、版本、整理者、出版信息和 URL。
2. 原文、校勘、注释、今译、赏析分别记录，不能混为一类。
3. 代码许可证、模型许可证、数据集许可证、上游文本权利分别判断。
4. 不得抓取 CTP 或绕过其访问限制。
5. CNKGraph 仅作研究参考，不得进入商业链路。
6. 大型语料下载必须先报告来源、大小、许可证和运行要求。
7. 不编造 source_id、locator、引文或页码。
8. 找不到证据时写“没有找到可靠来源”，而不是猜测。

## 检查

- 来源是否可定位？
- 许可证是否覆盖该具体内容？
- 原文是否与登记版本一致？
- 是否存在只凭记忆的作者生平/典故？
