from __future__ import annotations

import json

from literary_intelligence.schemas.llm_pass import PassName


PASS_INSTRUCTIONS: dict[PassName, str] = {
    "text_analyst": (
        "只做文本观察：结构、字词候选、句式、对偶、意象候选。"
        "必须优先分析 context.target 指定的目标句；只有确有需要才分析邻近上下文。"
        "目标句 claim 的 locator 必须等于 target.locator，scope 必须为 target；"
        "邻近句 claim 必须 scope=contextual，不能冒充目标句。"
        "不要原样重复 registered_claims；只输出新增观察，没有新增就 claims=[]。"
        "不得输出 historical_fact 或 creative，不得批准任何 claim。claims 最多 1 条。"
        "如果目标句无法分析，必须返回 coverage=not_analyzable、coverage_reason 说明原因，且 claims=[]。"
    ),
    "literary_analyst": (
        "提出修辞、意象、情感和审美解释候选；允许不确定，必须标记 interpretation。"
        "不要原样重复 registered_claims；只输出新增候选，claims 最多 2 条。不要把解释写成唯一正确结论。"
        "非目标句的候选必须 scope=contextual。"
    ),
    "researcher": (
        "只查找可验证的历史背景、典故、版本信息或外部来源；当前只有已登记 source，不能假装外部检索。"
        "不得输出 original_text，不得回显已有 claim，不得把已有 claim 当新成果。"
        "没有来源就写 UNVERIFIED 或返回空结果，不要编造 source_id 或典故出处。claims 最多 1 条。"
    ),
    "skeptic": (
        "专门找问题：现代观点冒充古意、伪造引用、无来源历史事实、过度解读、"
        "把争议解释说成定论。claims 必须为空列表，不要生成可批准的事实。"
        "必须设置 skeptic_verdict=findings 或 no_material_risk；每项 finding 必须包含 "
        "target_claim_id、risk_category、severity、finding、evidence_or_reason、"
        "suggested_revision、verdict。没有实质风险时列出 reviewed_dimensions。"
    ),
    "editor": (
        "只使用 review_status=approved 的 claim 组织讲解。当前通常没有 approved claim；"
        "没有就输出空 draft_text，claims 必须为空列表，不要用未审核内容补写。"
    ),
}

OUTPUT_CONTRACT = """只输出一个 JSON 对象，不要 Markdown code fence，不要思考过程：
{
  "pass_name": "<当前任务名>",
  "claims": [
    {
      "claim_id": "unique_id",
      "work": "洛神賦",
      "author": "曹植",
      "edition": "来源登记中的 edition",
      "source_refs": ["source_id"],
      "locator": "来源登记中的 locator",
      "quote": "规范化引文",
      "source_quote": "原始繁体引文，没有就空字符串",
      "display_quote": "展示句，可为空",
      "claim_type": "original_text|historical_fact|interpretation|creative",
      "statement": "陈述",
      "confidence": "high|medium|low",
      "review_status": "unreviewed",
      "scope": "target|contextual",
      "notes": "可选"
    }
  ],
  "notes": "简短说明",
  "draft_text": "仅有 approved claim 时才可非空",
  "coverage": "target|not_analyzable|not_applicable",
  "coverage_reason": "text_analyst 使用",
  "skeptic_verdict": "findings|no_material_risk|not_reviewed",
  "reviewed_dimensions": ["skeptic 实际检查的维度"],
  "skeptic_findings": [
    {
      "target_claim_id": "被审查的 claim_id",
      "risk_category": "unsupported_interpretation|overinterpretation|semantic_error|rhetorical_error|context_mismatch|historical_claim_without_source|wording_overstates_certainty",
      "severity": "low|medium|high",
      "finding": "具体问题",
      "evidence_or_reason": "依据",
      "suggested_revision": "建议",
      "verdict": "risk|no_material_risk"
    }
  ]
}
禁止新增不存在的 source_id、locator 或 source_refs；禁止把 review_status 设为 approved。"""


def build_messages(pass_name: PassName, context: dict) -> list[dict]:
    source_payload = context.get("sources", [])
    claims_payload = context.get("claims", [])
    payload = {
        "task": pass_name,
        "instruction": PASS_INSTRUCTIONS[pass_name],
        "target": context.get("target", {}),
        "sources": source_payload,
        "registered_claims": claims_payload,
        "approved_claims": context.get("approved_claims", []),
    }
    system = (
        "你是 Local-Drama-Studio Literary Harness 的任务执行器。"
        " /no_think 不要输出思维链。严格遵守证据约束；只输出合法 JSON。"
    )
    user = (
        f"任务：{pass_name}\n{PASS_INSTRUCTIONS[pass_name]}\n\n"
        f"证据上下文：\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        f"输出合同：\n{OUTPUT_CONTRACT}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
