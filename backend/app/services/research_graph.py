
from typing import TypedDict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, START, END

from app.models.user import User

from app.services.query_analyzer import analyze_query
from app.services.research_agent import run_research
from app.services.critic_agent import run_critic
from app.services.trend_agent import run_trend_analysis
from app.services.fact_verification_agent import run_fact_verification
from app.services.judge_agent import run_judge
from app.services.report_agent import generate_research_report

from app.services.research_memory import inspect_research_memory


class ResearchState(TypedDict, total=False):
    query: str
    domain: str
    user: User
    db: Session
    use_web: bool | None
    use_documents: bool
    session_id: UUID | None

    analysis: Any
    memory: dict
    research: dict
    evidence: list

    critic_results: dict
    trend_results: dict
    verification_results: dict
    judge_results: dict
    report: dict


def to_dict(result):
    """Convert Pydantic models into dictionaries."""

    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")

    return result


def get_selected_agents(analysis) -> list[str]:
    """Support both Pydantic analysis objects and dictionaries."""

    if isinstance(analysis, dict):
        selected = analysis.get("selected_agents", [])
    else:
        selected = getattr(analysis, "selected_agents", [])

    if not isinstance(selected, list):
        return []

    return [
        str(agent).strip().lower()
        for agent in selected
        if isinstance(agent, str)
    ]


def get_analysis_value(analysis, key, default=None):
    """Read an analysis field without depending on its representation."""

    if isinstance(analysis, dict):
        return analysis.get(key, default)

    return getattr(analysis, key, default)


def normalize_evidence(evidence: list[dict]) -> list[dict]:
    """
    Standardize evidence IDs and fields before passing evidence
    to downstream agents.
    """

    normalized = []

    for index, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            continue

        evidence_id = (
            item.get("id")
            or item.get("evidence_id")
            or f"E{index}"
        )

        evidence_id = str(evidence_id)

        normalized_item = {
            **item,
            "id": evidence_id,
            "evidence_id": evidence_id,
            "source_type": item.get(
                "source_type",
                item.get("evidence_type", "unknown"),
            ),
            "title": item.get("title") or "Untitled source",
            "url": item.get("url"),
            "content": str(item.get("content", "")),
            "published_date": (
                item.get("published_date")
                or item.get("published_at")
            ),
        }

        normalized.append(normalized_item)

    return normalized


def analyzer_node(state):
    """Understand the user's query and select agents."""

    analysis = analyze_query(
        state["query"],
        selected_domain=state["domain"],
    )

    return {"analysis": analysis}


def memory_node(state):
    """Search previous research and assess its freshness."""

    memory = inspect_research_memory(
        db=state["db"],
        user=state["user"],
        query=state["query"],
        domain=state["domain"],
    )

    return {"memory": memory}


def route_after_memory(state):
    """Reuse evidence only when memory passes freshness checks."""

    action = state.get("memory", {}).get("action")

    if action == "REUSE":
        return "reuse"

    # REVALIDATE and RESEARCH both retrieve fresh evidence.
    return "research"


def reuse_memory_node(state):
    """Convert saved evidence into the common evidence format."""

    memory = state.get("memory", {})
    previous_evidence = memory.get("previous_evidence", [])

    evidence = []

    for index, item in enumerate(previous_evidence, start=1):
        evidence_id = f"M{index}"

        evidence.append({
            "id": evidence_id,
            "evidence_id": evidence_id,
            "source_type": item.get(
                "evidence_type",
                "previous_memory",
            ),
            "title": (
                item.get("source_title")
                or "Previous research evidence"
            ),
            "url": item.get("source_url"),
            "content": item.get("evidence_text", ""),
            "page_number": item.get("page_number"),
            "published_date": item.get("published_date"),
            "relevance_score": item.get("relevance_score"),
            "from_memory": True,
        })

    analysis = state["analysis"]

    research = {
        "query": state["query"],
        "domain": state["domain"],
        "intent": get_analysis_value(analysis, "intent"),
        "selected_agents": get_selected_agents(analysis),
        "evidence_count": len(evidence),
        "evidence": evidence,
        "memory_reused": True,
    }

    return {
        "research": research,
        "evidence": normalize_evidence(evidence),
    }


def research_node(state):
    """Retrieve new evidence from web and/or uploaded documents."""

    research = run_research(
        query=state["query"],
        domain=state["domain"],
        user=state["user"],
        db=state["db"],
        use_web=state.get("use_web"),
        use_documents=state.get("use_documents", False),
        session_id=state.get("session_id"),
        analysis_result=state["analysis"],
    )

    evidence = normalize_evidence(
        research.get("evidence", [])
    )

    research["evidence"] = evidence
    research["evidence_count"] = len(evidence)
    research["selected_agents"] = get_selected_agents(
        state["analysis"]
    )
    research["memory_reused"] = False

    return {
        "research": research,
        "evidence": evidence,
    }


def critic_node(state):
    """Evaluate evidence quality and research gaps."""

    selected = get_selected_agents(state["analysis"])

    if "critic" not in selected:
        return {"critic_results": {}}

    result = run_critic(
        query=state["query"],
        domain=state["domain"],
        evidence=state.get("evidence", []),
    )

    return {"critic_results": to_dict(result)}


def trend_node(state):
    """Identify trends and possible future directions."""

    selected = get_selected_agents(state["analysis"])

    if "trend" not in selected:
        return {"trend_results": {}}

    result = run_trend_analysis(
        query=state["query"],
        domain=state["domain"],
        evidence=state.get("evidence", []),
    )

    return {"trend_results": to_dict(result)}


def verification_node(state):
    """Verify claims against the available evidence."""

    result = run_fact_verification(
        query=state["query"],
        domain=state["domain"],
        evidence=state.get("evidence", []),
    )

    return {"verification_results": to_dict(result)}


def judge_node(state):
    """Resolve meaningful conflicts when required."""

    verification = state.get("verification_results", {})
    selected = get_selected_agents(state["analysis"])

    if not isinstance(verification, dict):
        verification = {}

    needs_judge = (
        verification.get("requires_judge", False)
        or "judge" in selected
    )

    if not needs_judge:
        return {"judge_results": {}}

    result = run_judge(
        query=state["query"],
        domain=state["domain"],
        verification_results=verification,
        evidence=state.get("evidence", []),
    )

    return {"judge_results": to_dict(result)}


def report_node(state):
    """Generate the final structured research report."""

    result = generate_research_report(
        query=state["query"],
        domain=state["domain"],
        evidence=state.get("evidence", []),
        critic_results=state.get("critic_results", {}),
        trend_results=state.get("trend_results", {}),
        verification_results=state.get("verification_results", {}),
        judge_results=state.get("judge_results", {}),
    )

    return {"report": to_dict(result)}


def build_research_graph():
    """Build and compile the complete research workflow."""

    graph = StateGraph(ResearchState)

    graph.add_node("analyzer", analyzer_node)
    graph.add_node("memory", memory_node)
    graph.add_node("reuse_memory", reuse_memory_node)
    graph.add_node("research", research_node)
    graph.add_node("critic", critic_node)
    graph.add_node("trend", trend_node)
    graph.add_node("verification", verification_node)
    graph.add_node("judge", judge_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "memory")

    graph.add_conditional_edges(
        "memory",
        route_after_memory,
        {
            "reuse": "reuse_memory",
            "research": "research",
        },
    )

    graph.add_edge("reuse_memory", "critic")
    graph.add_edge("research", "critic")

    graph.add_edge("critic", "trend")
    graph.add_edge("trend", "verification")
    graph.add_edge("verification", "judge")
    graph.add_edge("judge", "report")
    graph.add_edge("report", END)

    return graph.compile()


research_workflow = build_research_graph()
