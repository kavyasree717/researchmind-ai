
import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.services.llm import get_llm


class CriticResult(BaseModel):
    overall_assessment: str = "Evidence assessment could not be completed."
    evidence_strength: str = "insufficient"
    weaknesses: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    needs_more_research: bool = True


VALID_EVIDENCE_STRENGTHS = {
    "strong",
    "moderate",
    "weak",
    "insufficient",
}

MAX_EVIDENCE_ITEMS = 10
MAX_CONTENT_LENGTH = 900


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return []

    results = []

    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()

        elif isinstance(item, dict):
            cleaned = (
                item.get("description")
                or item.get("claim")
                or item.get("reason")
                or item.get("issue")
                or item.get("recommendation")
                or ""
            )
            cleaned = str(cleaned).strip()

        else:
            continue

        if cleaned:
            results.append(cleaned[:500])

    return results


def prepare_evidence(evidence: list[dict]) -> list[dict]:
    prepared = []

    for item in evidence[:MAX_EVIDENCE_ITEMS]:
        prepared.append({
            "evidence_id": str(
                item.get("id") or item.get("evidence_id") or ""
            ),
            "source_type": str(item.get("source_type", "unknown")),
            "title": str(item.get("title", ""))[:180],
            "url": str(item.get("url", ""))[:250],
            "page_number": item.get("page_number"),
            "content": str(item.get("content", ""))[
                :MAX_CONTENT_LENGTH
            ],
        })

    return prepared


def normalize_critic_result(data: dict) -> dict:
    if not isinstance(data, dict):
        data = {}

    overall_assessment = data.get("overall_assessment")

    if (
        not isinstance(overall_assessment, str)
        or not overall_assessment.strip()
    ):
        overall_assessment = (
            "The available evidence requires further assessment."
        )

    evidence_strength = str(
        data.get("evidence_strength", "insufficient")
    ).strip().lower()

    if evidence_strength not in VALID_EVIDENCE_STRENGTHS:
        evidence_strength = "insufficient"

    weaknesses = normalize_string_list(data.get("weaknesses"))
    missing_information = normalize_string_list(
        data.get("missing_information")
    )
    unsupported_claims = normalize_string_list(
        data.get("unsupported_claims")
    )
    recommendations = normalize_string_list(
        data.get("recommendations")
    )

    needs_more_research = data.get("needs_more_research")

    if not isinstance(needs_more_research, bool):
        needs_more_research = (
            evidence_strength in {"weak", "insufficient"}
            or bool(missing_information)
            or bool(unsupported_claims)
        )

    return {
        "overall_assessment": overall_assessment.strip(),
        "evidence_strength": evidence_strength,
        "weaknesses": weaknesses,
        "missing_information": missing_information,
        "unsupported_claims": unsupported_claims,
        "recommendations": recommendations,
        "needs_more_research": needs_more_research,
    }


def run_critic(
    query: str,
    domain: str,
    evidence: list[dict],
) -> dict:

    if not evidence:
        return CriticResult(
            overall_assessment=(
                "No evidence was available to evaluate the research query."
            ),
            evidence_strength="insufficient",
            weaknesses=["No supporting evidence was retrieved."],
            missing_information=[
                "Relevant and reliable sources are required."
            ],
            recommendations=[
                "Collect relevant sources before drawing conclusions."
            ],
            needs_more_research=True,
        ).model_dump()

    compact_evidence = prepare_evidence(evidence)

    domain_requirements = {
        "scientific_research": (
            "Check research methodology, sample size, experimental design, "
            "reproducibility, and stated limitations."
        ),
        "scientific": (
            "Check research methodology, sample size, experimental design, "
            "reproducibility, and stated limitations."
        ),
        "agriculture": (
            "Check crop type, geographical region, climate, soil conditions, "
            "growing season, and practical applicability."
        ),
        "government_policy": (
            "Check jurisdiction, policy authority, implementation status, "
            "effective dates, and affected population."
        ),
        "education": (
            "Check country, education level, learner population, teaching "
            "context, and whether findings apply to the stated setting."
        ),
        "law": (
            "Check jurisdiction, court authority, legal status, effective "
            "dates, and whether cited legal material is binding or persuasive."
        ),
    }

    domain_check = domain_requirements.get(
        domain,
        "Check the relevance, reliability, completeness, and limitations "
        "of the evidence for this domain.",
    )

    prompt = f"""
You are the Critic Agent in a multi-agent research system.

Your task is to critically evaluate the quality and completeness of
the supplied evidence.

RESEARCH QUESTION:
{query}

DOMAIN:
{domain}

DOMAIN-SPECIFIC CHECK:
{domain_check}

EVIDENCE:
{json.dumps(compact_evidence, ensure_ascii=False)}

Evaluate the evidence using these rules:

1. Check whether the evidence directly answers the research question.
2. Identify weak, incomplete, outdated, or potentially biased sources.
3. Identify information needed to answer the question properly.
4. Identify claims that are not adequately supported by the supplied evidence.
5. Do not invent facts or unsupported weaknesses.
6. Do not treat missing information as proof that a claim is false.
7. Distinguish source limitations from actual contradictions.
8. Give practical recommendations for improving the research.

Choose evidence_strength using these definitions:

- strong: Relevant, credible, sufficiently detailed evidence with no
  major identified weaknesses.
- moderate: Useful evidence exists, but some limitations remain.
- weak: Evidence is limited, indirect, or has significant weaknesses.
- insufficient: There is not enough usable evidence to assess the question.

Set needs_more_research to true when important evidence gaps,
weaknesses, or unsupported claims remain.

Return ONLY valid JSON with exactly these fields:

{{
  "overall_assessment": "Short assessment",
  "evidence_strength": "strong | moderate | weak | insufficient",
  "weaknesses": [],
  "missing_information": [],
  "unsupported_claims": [],
  "recommendations": [],
  "needs_more_research": true
}}
"""

    llm = get_llm()

    response = llm.invoke(
        prompt,
        max_tokens=1000,
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
        normalized_data = normalize_critic_result(data)
        result = CriticResult.model_validate(normalized_data)

    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise ValueError(
            "Critic Agent returned invalid structured data."
        ) from exc

    return result.model_dump()
