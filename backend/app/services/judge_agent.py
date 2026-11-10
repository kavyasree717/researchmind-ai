
import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.services.llm import get_llm


DOMAIN_POLICIES = {
    "scientific_research": """
Evaluate methodology, sample size, experimental design, reproducibility,
peer-review status, research limitations, and strength of measured results.
Do not prefer a study simply because it is newer or has a larger number
of citations.
""",
    "scientific": """
Evaluate methodology, sample size, experimental design, reproducibility,
peer-review status, research limitations, and strength of measured results.
Do not prefer a study simply because it is newer or has a larger number
of citations.
""",
    "agriculture": """
Consider crop type, geographical region, climate, soil conditions,
growing season, experimental conditions, and practical applicability.
A result from one region or crop should not automatically be generalized
to another.
""",
    "government_policy": """
Consider the issuing authority, jurisdiction, official policy documents,
implementation status, effective dates, amendments, and affected population.
Distinguish proposed policies from implemented policies.
""",
    "education": """
Consider the country, education system, learner population, education level,
research methodology, and learning context. Do not generalize findings
from one educational setting to every setting.
""",
    "law": """
Consider jurisdiction, court hierarchy, binding legal authority,
precedential value, effective dates, amendments, and current legal status.
Distinguish binding decisions from persuasive opinions and secondary
legal commentary.
""",
}


class JudgeResult(BaseModel):
    conflict_decisions: list[dict] = Field(default_factory=list)
    preferred_evidence: list[str] = Field(default_factory=list)
    unresolved_conflicts: list[str] = Field(default_factory=list)
    reasoning: str = (
        "The available evidence does not support a definitive conflict decision."
    )
    confidence: str = "insufficient"


VALID_CONFIDENCE = {
    "high",
    "moderate",
    "low",
    "insufficient",
}

MAX_EVIDENCE_ITEMS = 8
MAX_CONTENT_LENGTH = 900


def compact_value(value: Any) -> Any:
    if isinstance(value, str):
        return value[:900]

    if isinstance(value, dict):
        return {
            str(key): compact_value(item)
            for key, item in list(value.items())[:12]
        }

    if isinstance(value, list):
        return [compact_value(item) for item in value[:8]]

    return value


def prepare_evidence(evidence: list[dict]) -> list[dict]:
    prepared = []

    for item in evidence[:MAX_EVIDENCE_ITEMS]:
        prepared.append({
            "id": str(item.get("id") or item.get("evidence_id") or ""),
            "source_type": str(item.get("source_type", "unknown")),
            "title": str(item.get("title", ""))[:180],
            "url": str(item.get("url", ""))[:250],
            "published_date": item.get("published_date"),
            "content": str(item.get("content", ""))[
                :MAX_CONTENT_LENGTH
            ],
        })

    return prepared


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return []

    result = []

    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()

        elif isinstance(item, dict):
            cleaned = (
                item.get("description")
                or item.get("reason")
                or item.get("claim")
                or ""
            )
            cleaned = str(cleaned).strip()

        else:
            continue

        if cleaned:
            result.append(cleaned[:500])

    return result


def normalize_conflict_decisions(
    value: Any,
    valid_evidence_ids: set[str],
) -> list[dict]:

    if not isinstance(value, list):
        return []

    normalized = []

    for item in value[:10]:
        if not isinstance(item, dict):
            continue

        claim = str(item.get("claim", "")).strip()
        decision = str(item.get("decision", "")).strip()
        explanation = str(
            item.get("explanation", item.get("reasoning", ""))
        ).strip()

        if not claim:
            continue

        supporting_ids = normalize_string_list(
            item.get("supporting_evidence")
            or item.get("supporting_evidence_ids")
        )

        contradicting_ids = normalize_string_list(
            item.get("contradicting_evidence")
            or item.get("contradicting_evidence_ids")
        )

        supporting_ids = [
            evidence_id
            for evidence_id in supporting_ids
            if evidence_id in valid_evidence_ids
        ]

        contradicting_ids = [
            evidence_id
            for evidence_id in contradicting_ids
            if evidence_id in valid_evidence_ids
        ]

        normalized.append({
            "claim": claim[:700],
            "decision": decision[:300] or "Unresolved",
            "supporting_evidence": supporting_ids,
            "contradicting_evidence": contradicting_ids,
            "explanation": explanation[:900],
        })

    return normalized


def normalize_judge_result(
    data: dict,
    valid_evidence_ids: set[str],
) -> dict:

    if not isinstance(data, dict):
        data = {}

    conflict_decisions = normalize_conflict_decisions(
        data.get("conflict_decisions"),
        valid_evidence_ids,
    )

    preferred_evidence = normalize_string_list(
        data.get("preferred_evidence")
    )

    preferred_evidence = [
        evidence_id
        for evidence_id in preferred_evidence
        if evidence_id in valid_evidence_ids
    ]

    unresolved_conflicts = normalize_string_list(
        data.get("unresolved_conflicts")
    )

    reasoning = data.get("reasoning")

    if not isinstance(reasoning, str) or not reasoning.strip():
        reasoning = (
            "The available evidence does not support a definitive decision."
        )

    confidence = str(
        data.get("confidence", "insufficient")
    ).strip().lower()

    if confidence not in VALID_CONFIDENCE:
        confidence = "insufficient"

    return {
        "conflict_decisions": conflict_decisions,
        "preferred_evidence": preferred_evidence,
        "unresolved_conflicts": unresolved_conflicts,
        "reasoning": reasoning.strip()[:1500],
        "confidence": confidence,
    }


def run_judge(
    query: str,
    domain: str,
    verification_results: dict,
    evidence: list[dict],
) -> dict:

    if not evidence:
        return JudgeResult(
            reasoning=(
                "No evidence was available for comparing conflicting claims."
            ),
            confidence="insufficient",
            unresolved_conflicts=[
                "Conflicts cannot be evaluated without supporting evidence."
            ],
        ).model_dump()

    if not isinstance(verification_results, dict):
        verification_results = {}

    verification_summary = compact_value(verification_results)
    compact_evidence = prepare_evidence(evidence)

    valid_evidence_ids = {
        str(item.get("id") or item.get("evidence_id"))
        for item in evidence
        if item.get("id") is not None or item.get("evidence_id") is not None
    }

    requires_judge = verification_results.get("requires_judge", False)

    contradicted_claims = verification_results.get(
        "contradicted_claims",
        [],
    )

    if not isinstance(contradicted_claims, list):
        contradicted_claims = []

    if not requires_judge and not contradicted_claims:
        return JudgeResult(
            reasoning=(
                "No meaningful evidence conflict requiring a Judge "
                "decision was identified by the Fact Verification Agent."
            ),
            confidence="moderate",
        ).model_dump()

    domain_policy = DOMAIN_POLICIES.get(
        domain,
        """
Evaluate source reliability, relevance, methodology, authority,
recency where relevant, and the context of each claim.
""",
    )

    prompt = f"""
You are the Judge Agent in a multi-agent research system.

Your task is to evaluate meaningful conflicts identified by the
Fact Verification Agent.

RESEARCH QUESTION:
{query}

DOMAIN:
{domain}

DOMAIN-SPECIFIC EVALUATION POLICY:
{domain_policy}

FACT VERIFICATION RESULTS:
{json.dumps(verification_summary, ensure_ascii=False)}

AVAILABLE EVIDENCE:
{json.dumps(compact_evidence, ensure_ascii=False)}

JUDGING RULES:

1. Evaluate the actual evidence supporting each conflicting claim.
2. Consider source authority, methodology, relevance, reliability,
   completeness, and context.
3. Do not automatically prefer newer sources.
4. Do not automatically prefer the claim supported by more sources.
5. Do not assume that a source is reliable merely because it is
   well-known or professionally presented.
6. In law, distinguish binding legal authority from persuasive
   opinions and secondary commentary.
7. In science, consider methodology and quality of results.
8. In agriculture, consider regional and crop-specific conditions.
9. In government policy, consider issuing authority and current
   implementation status.
10. In education, consider the population and learning context.
11. Never invent evidence IDs or facts.
12. If evidence is insufficient to resolve a conflict, preserve it
    as unresolved instead of guessing.
13. Only select preferred evidence when there is a clear,
    evidence-based reason.

Return ONLY valid JSON with exactly these fields:

{{
  "conflict_decisions": [
    {{
      "claim": "The disputed claim",
      "decision": "Which position is better supported, or Unresolved",
      "supporting_evidence": ["E1"],
      "contradicting_evidence": ["E2"],
      "explanation": "Why this decision was reached"
    }}
  ],
  "preferred_evidence": ["E1"],
  "unresolved_conflicts": [],
  "reasoning": "Overall explanation of the evaluation",
  "confidence": "high | moderate | low | insufficient"
}}

Use only evidence IDs that appear in the supplied evidence.
If no conflict can be resolved, use an empty preferred_evidence list.
"""

    llm = get_llm()

    response = llm.invoke(
        prompt,
        max_tokens=1200,
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.content

    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )

    try:
        data = json.loads(content)

        normalized_data = normalize_judge_result(
            data,
            valid_evidence_ids,
        )

        result = JudgeResult.model_validate(normalized_data)

    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise ValueError(
            "Judge Agent returned invalid structured data."
        ) from exc

    return result.model_dump()
