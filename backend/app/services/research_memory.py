
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.research import (
    ResearchSession,
    ResearchRun,
    Source,
)
from app.models.evidence import Evidence
from app.models.user import User

from app.services.embeddings import embed_texts
from app.services.source_freshness import (
    assess_source_freshness,
    decide_research_memory_action,
)


def normalize_domain(domain: str) -> str:
    """Normalize supported domain aliases."""

    if domain == "scientific":
        return "scientific_research"

    return domain


def _analysis_to_dict(analysis):
    """Convert an analysis result into a JSON-compatible dictionary."""

    if analysis is None:
        return {}

    if hasattr(analysis, "model_dump"):
        return analysis.model_dump(mode="json")

    if isinstance(analysis, dict):
        return analysis

    return {}


def generate_query_embedding(query: str) -> list[float]:
    """Generate and validate a query embedding."""

    vectors = embed_texts([query])

    if not vectors or len(vectors) != 1:
        raise ValueError(
            "Could not generate an embedding for the research query."
        )

    return vectors[0]


def create_or_get_research_session(
    db: Session,
    user: User,
    query: str,
    domain: str,
    session_id=None,
):
    """Create a new research session or retrieve an existing user session."""

    domain = normalize_domain(domain)

    if session_id:
        session = (
            db.query(ResearchSession)
            .filter(
                ResearchSession.id == session_id,
                ResearchSession.user_id == user.id,
            )
            .first()
        )

        if session is None:
            raise ValueError("Research session not found")

        session.query = query
        session.domain = domain

        if not session.title:
            session.title = query[:255]

        db.flush()

        return session

    session = ResearchSession(
        user_id=user.id,
        title=query[:255],
        query=query,
        domain=domain,
        status="active",
    )

    db.add(session)
    db.flush()

    return session


def start_research_run(
    db: Session,
    session: ResearchSession,
    query: str,
    domain: str,
    analysis=None,
):
    """Create a new research execution record."""

    query_embedding = generate_query_embedding(query)

    run = ResearchRun(
        session_id=session.id,
        query_text=query,
        domain=normalize_domain(domain),
        query_embedding=query_embedding,
        execution_plan=_analysis_to_dict(analysis),
        status="running",
        started_at=datetime.now(timezone.utc),
    )

    db.add(run)
    db.flush()

    return run


def search_similar_research(
    db: Session,
    user: User,
    query: str,
    domain: str,
    limit: int = 5,
):
    """
    Search completed research runs belonging to the current user.

    Results are restricted to the same research domain.
    """

    domain = normalize_domain(domain)
    query_embedding = generate_query_embedding(query)

    distance = ResearchRun.query_embedding.cosine_distance(
        query_embedding
    ).label("distance")

    results = (
        db.query(ResearchRun, distance)
        .join(
            ResearchSession,
            ResearchRun.session_id == ResearchSession.id,
        )
        .filter(ResearchSession.user_id == user.id)
        .filter(ResearchRun.query_embedding.isnot(None))
        .filter(ResearchRun.domain == domain)
        .filter(ResearchRun.status == "completed")
        .order_by(distance)
        .limit(max(1, min(limit, 10)))
        .all()
    )

    memories = []

    for run, distance_value in results:
        if distance_value is None:
            continue

        similarity = 1 - float(distance_value)

        memories.append({
            "run_id": str(run.id),
            "query": run.query_text,
            "domain": run.domain,
            "status": run.status,
            "similarity": round(similarity, 4),
            "created_at": (
                run.created_at.isoformat()
                if run.created_at
                else None
            ),
        })

    return memories


def decide_memory_action(memories: list[dict]):
    """Make a basic similarity-based memory decision."""

    if not memories:
        return {
            "action": "RESEARCH",
            "reason": "No relevant previous research was found.",
            "matched_memory": None,
        }

    best_memory = memories[0]
    similarity = best_memory["similarity"]

    if similarity >= 0.82:
        return {
            "action": "REVALIDATE",
            "reason": (
                "Similar previous research was found. "
                "Check its evidence before reuse."
            ),
            "matched_memory": best_memory,
        }

    return {
        "action": "RESEARCH",
        "reason": (
            "Previous research was not sufficiently similar."
        ),
        "matched_memory": best_memory,
    }


def get_evidence_metadata(item: Evidence) -> dict:
    """Safely retrieve evidence metadata."""

    metadata = item.evidence_metadata

    if isinstance(metadata, dict):
        return metadata

    return {}


def inspect_research_memory(
    db: Session,
    user: User,
    query: str,
    domain: str,
):
    """
    Find similar research, inspect its evidence, assess freshness,
    and decide whether evidence can be reused.

    Old evidence is reused only when the freshness decision permits it.
    """

    domain = normalize_domain(domain)

    memories = search_similar_research(
        db=db,
        user=user,
        query=query,
        domain=domain,
    )

    if not memories:
        return {
            "action": "RESEARCH",
            "reason": "No previous research was found.",
            "matched_memory": None,
            "freshness_results": [],
            "previous_evidence": [],
        }

    best_memory = memories[0]

    if best_memory["similarity"] < 0.82:
        return {
            "action": "RESEARCH",
            "reason": (
                "The closest previous query is not sufficiently similar."
            ),
            "matched_memory": best_memory,
            "freshness_results": [],
            "previous_evidence": [],
        }

    run_id = UUID(best_memory["run_id"])

    previous_evidence = (
        db.query(Evidence)
        .filter(Evidence.research_run_id == run_id)
        .order_by(Evidence.created_at.asc())
        .all()
    )

    freshness_results = []
    evidence_results = []
    checked_source_ids = set()

    for index, item in enumerate(previous_evidence, start=1):
        source = None
        assessment = None

        if item.source_id:
            source = db.get(Source, item.source_id)

        metadata = get_evidence_metadata(item)

        # Assess each linked source only once.
        if source:
            source_key = str(source.id)

            if source_key not in checked_source_ids:
                assessment = assess_source_freshness(
                    source=source,
                    domain=domain,
                )

                freshness_results.append({
                    "source_id": source_key,
                    "title": source.title,
                    **assessment,
                })

                checked_source_ids.add(source_key)

        else:
            # Evidence without a linked source cannot be assumed fresh.
            freshness_results.append({
                "source_id": None,
                "title": (
                    metadata.get("title")
                    or "Document or unlinked evidence"
                ),
                "status": "UNVERIFIED",
                "reason": (
                    "No linked source record is available for "
                    "freshness assessment."
                ),
                "age_days": None,
            })

        # Support both the old and updated persistence formats.
        evidence_id = (
            metadata.get("id")
            or metadata.get("evidence_id")
            or f"M{index}"
        )

        evidence_results.append({
            "id": str(evidence_id),
            "evidence_id": str(evidence_id),
            "evidence_type": item.evidence_type,
            "source_type": item.evidence_type,
            "evidence_text": item.evidence_text,
            "content": item.evidence_text,
            "source_title": (
                source.title
                if source
                else metadata.get("title")
            ),
            "title": (
                source.title
                if source
                else metadata.get("title")
            ),
            "source_url": (
                source.url
                if source
                else metadata.get("url")
            ),
            "url": (
                source.url
                if source
                else metadata.get("url")
            ),
            "page_number": metadata.get("page_number"),
            "published_date": (
                metadata.get("published_date")
                or (
                    source.published_at.isoformat()
                    if source and source.published_at
                    else None
                )
            ),
            "relevance_score": metadata.get("relevance_score"),
            "from_memory": True,
        })

    decision = decide_research_memory_action(
        memories=[best_memory],
        freshness_results=freshness_results,
    )

    return {
        **decision,
        "matched_memory": best_memory,
        "freshness_results": freshness_results,
        "previous_evidence": evidence_results,
    }
