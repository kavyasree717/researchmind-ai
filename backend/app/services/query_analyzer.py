
import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.llm import get_llm_client


Domain = Literal[
    "scientific_research",
    "agriculture",
    "government_policy",
    "education",
    "law",
]

AgentName = Literal[
    "research",
    "critic",
    "trend",
    "fact_verification",
    "judge",
    "report",
]


class QueryAnalysis(BaseModel):
    normalized_query: str

    domain: Domain

    intent: Literal[
        "research",
        "comparison",
        "explanation",
        "trend_analysis",
        "problem_solving",
    ]

    requires_web: bool
    requires_documents: bool
    needs_latest: bool

    complexity: Literal["simple", "moderate", "complex"]

    selected_agents: list[AgentName] = Field(default_factory=list)

    search_queries: list[str] = Field(default_factory=list)


def normalize_complexity(value) -> str:
    """Convert different LLM complexity formats into valid values."""

    if isinstance(value, str):
        value = value.strip().lower()

    complexity_mapping = {
        1: "simple",
        2: "moderate",
        3: "complex",
        "1": "simple",
        "2": "moderate",
        "3": "complex",
        "simple": "simple",
        "low": "simple",
        "easy": "simple",
        "moderate": "moderate",
        "medium": "moderate",
        "medium complexity": "moderate",
        "complex": "complex",
        "high": "complex",
        "difficult": "complex",
    }

    return complexity_mapping.get(value, "moderate")


def analyze_query(
    query: str,
    selected_domain: Domain | None = None,
) -> QueryAnalysis:

    client = get_llm_client()

    domain_instruction = (
        f"The user selected this domain: {selected_domain}. "
        "Use this domain."
        if selected_domain
        else "Identify the most appropriate domain."
    )

    prompt = f"""
You are the Query Analyzer for ResearchMind AI.

Analyze the user's research question and return valid JSON.

Available domains:
- scientific_research
- agriculture
- government_policy
- education
- law

Available intents:
- research
- comparison
- explanation
- trend_analysis
- problem_solving

Available agents:
- research
- critic
- trend
- fact_verification
- judge
- report

Complexity must be exactly one of:
- simple
- moderate
- complex

Rules:
1. Identify the user's intent.
2. Identify whether web search is required.
3. Identify whether uploaded document retrieval is required.
4. Identify whether latest information is required.
5. Estimate query complexity using the allowed string values.
6. Select relevant agents.
7. Always include research, fact_verification and report.
8. Include trend for latest information or trend analysis.
9. Include judge for comparisons or conflicting evidence.
10. Include critic for complex research.
11. Generate 2-4 useful web search queries when web search is required.
12. Do not invent information about uploaded documents.
13. Return complexity as a string, never as a number.

{domain_instruction}

Return only a JSON object with these fields:
normalized_query, domain, intent, requires_web,
requires_documents, needs_latest, complexity,
selected_agents, search_queries.

User question:
{query}
"""

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a structured research query analyzer. "
                    "Return valid JSON and follow the specified schema."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=1000,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("Query Analyzer returned an empty response")

    try:
        data = json.loads(content)

        if not isinstance(data, dict):
            raise ValueError(
                "Query Analyzer response must be a JSON object."
            )

        # Normalize numeric and alternative complexity values.
        data["complexity"] = normalize_complexity(
            data.get("complexity")
        )

        analysis = QueryAnalysis.model_validate(data)

    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise ValueError(
            "Query Analyzer returned invalid structured data"
        ) from exc

    # Backend validation: enforce mandatory agents and selection rules.
    agents = list(dict.fromkeys(analysis.selected_agents))

    for mandatory in ["research", "fact_verification", "report"]:
        if mandatory not in agents:
            agents.append(mandatory)

    if analysis.needs_latest or analysis.intent == "trend_analysis":
        if "trend" not in agents:
            agents.append("trend")

    if analysis.intent == "comparison":
        if "judge" not in agents:
            agents.append("judge")

    if analysis.complexity == "complex":
        if "critic" not in agents:
            agents.append("critic")

    analysis.selected_agents = agents

    return analysis
