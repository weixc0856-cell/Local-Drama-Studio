---
name: literary-scriptwriting
description: Turn only approved literary claims into a short-video explanation or storyboard, preserving claim IDs and separating original text, historical fact, interpretation, and creative adaptation.
---

# Literary Scriptwriting Skill

## 输入

- 仅 `approved` 的 claims；
- 原文 locator；
- 目标时长、平台和视觉风格；
- 不得引入未审核 claim。

## 输出

- Markdown 讲解稿或 JSON 分镜；
- 每条事实/解释保留 `claim_id`；
- `creative` 单独标注为创作；
- 没有 approved 内容时输出“无可发布内容”。

## 规则

1. 原文句、史实、解释、创作四种图层不能混写。
2. 不把解释说成唯一正确结论。
3. 不补充未在 claims 中出现的历史事实、典故或作者生平。
4. 不为“更好听”而改动原文引文。
5. 视觉转译只能是 `creative`，不能冒充史料。
6. 输出中的事实性句子必须能回指 `claim_id` 或 `source_refs`。
7. 不生成视频，不接入 R3/S3 生产链路；LI-1 只输出 Markdown/JSON。

## 检查

- 是否只用了 approved？
- 是否保留 claim_id？
- 创作是否单独标注？
- 是否有无法回指来源的事实句？
