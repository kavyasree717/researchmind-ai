
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.research import ResearchSession, ResearchRun, Source
from app.models.evidence import Evidence
from app.models.agent import AgentOutput
from app.models.report import Report

from app.services.embeddings import embed_texts


def to_dict(value):
    """Convert Pydantic models into dictionaries."""

    if value is None:
        return {}

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return value

    return {}


def parse_published_date(value):
    """Parse an ISO date without failing research execution."""

    if not value:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def parse_uuid(value):
    """Convert a UUID string into a UUID object safely."""

    if not value:
        return None

    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def prepare_evidence_items(evidence_items: list[dict]) -> list[dict]:
    """Keep only valid evidence records with non-empty content."""

    prepared = []

    for index, item in enumerate(evidence_items, start=1):
        if not isinstance(item, dict):
            continue

        content = item.get("content", "")

        if not isinstance(content, str) or not content.strip():
            continue

        evidence_id = (
            item.get("id")
            or item.get("evidence_id")
            or f"E{index}"
        )

        prepared.append({
            **item,
            "id": str(evidence_id),
            "evidence_id": str(evidence_id),
            "content": content.strip(),
        })

    return prepared


def generate_evidence_embeddings(
    evidence_items: list[dict],
) -> list:
    """Generate embeddings and verify their alignment with evidence."""

    if not evidence_items:
        return []

    texts = [
        item["content"]
        for item in evidence_items
    ]

    vectors = embed_texts(texts)

    if vectors is None:
        raise ValueError(
            "Embedding service returned no embeddings."
        )

    vectors = list(vectors)

    if len(vectors) != len(evidence_items):
        raise ValueError(
            "Embedding count does not match evidence count. "
            f"Expected {len(evidence_items)}, received {len(vectors)}."
        )

    return vectors


def save_or_update_source(
    db: Session,
    session: ResearchSession,
    item: dict,
    domain: str,
) -> Source | None:
    """Create or update a web source within the research session."""

    if item.get("source_type") != "web" or not item.get("url"):
        return None

    url = str(item["url"]).strip()

    if not url:
        return None

    # Evidence reused from memory should not reset the original
    # source's freshness status or retrieval timestamp.
    if item.get("from_memory"):
        return (
            db.query(Source)
            .filter(
                Source.session_id == session.id,
                Source.url == url,
            )
            .first()
        )

    content = item["content"]

    content_hash = sha256(
        content.encode("utf-8")
    ).hexdigest()

    source = (
        db.query(Source)
        .filter(
            Source.session_id == session.id,
            Source.url == url,
        )
        .first()
    )

    now = datetime.now(timezone.utc)

    published_date = parse_published_date(
        item.get("published_date")
        or item.get("published_at")
    )

    if source is None:
        source = Source(
            session_id=session.id,
            title=item.get("title") or "Untitled source",
            url=url,
            source_type="web",
            domain=domain,
            published_at=published_date,
            retrieved_at=now,
            freshness_status="unverified",
            content_hash=content_hash,
            source_metadata={
                "relevance_score": item.get("relevance_score"),
            },
        )

        db.add(source)
        db.flush()

    else:
        source.title = item.get("title") or source.title
        source.domain = domain
        source.retrieved_at = now
        source.content_hash = content_hash

        if published_date is not None:
            source.published_at = published_date

        source_metadata = dict(source.source_metadata or {})
        source_metadata["relevance_score"] = item.get(
            "relevance_score"
        )
        source.source_metadata = source_metadata

        # Newly retrieved content needs freshness assessment.
        source.freshness_status = "unverified"

        db.flush()

    return source


def save_research_sources(
    db: Session,
    session: ResearchSession,
    run: ResearchRun,
    evidence_items: list[dict],
    domain: str,
):
    """
    Save sources and evidence.

    Duplicate web URLs within the same session reuse their Source record.
    Each research run receives its own Evidence record.
    """

    prepared_items = prepare_evidence_items(evidence_items)

    if not prepared_items:
        return []

    vectors = generate_evidence_embeddings(prepared_items)

    saved_evidence = []

    for item, vector in zip(prepared_items, vectors):
        source = save_or_update_source(
            db=db,
            session=session,
            item=item,
            domain=domain,
        )

        document_chunk_id = parse_uuid(
            item.get("document_chunk_id")
        )

        evidence_metadata = {
            "id": item["id"],
            "evidence_id": item["evidence_id"],
            "title": item.get("title"),
            "url": item.get("url"),
            "page_number": item.get("page_number"),
            "published_date": item.get(
                "published_date",
                item.get("published_at"),
            ),
            "relevance_score": item.get("relevance_score"),
            "from_memory": item.get("from_memory", False),
            "document_id": item.get("document_id"),
            "document_chunk_id": (
                str(document_chunk_id)
                if document_chunk_id else None
            ),
        }

        evidence = Evidence(
            session_id=session.id,
            research_run_id=run.id,
            source_id=source.id if source else None,
            document_chunk_id=document_chunk_id,
            evidence_text=item["content"],
            evidence_type=item.get("source_type", "unknown"),
            # Search relevance is not factual confidence.
            # Keep confidence unset until verification assigns it.
            confidence=None,
            embedding=vector,
            evidence_metadata=evidence_metadata,
        )

        db.add(evidence)
        saved_evidence.append(evidence)

    db.flush()

    return saved_evidence


def save_agent_output(
    db: Session,
    session: ResearchSession,
    run: ResearchRun,
    agent_name: str,
    output: dict,
    query: str,
):
    """Save one agent's result."""

    output = to_dict(output)

    if not output:
        return None

    record = AgentOutput(
        session_id=session.id,
        research_run_id=run.id,
        agent_name=agent_name,
        status="completed",
        input_summary=query[:1000],
        output=output,
        error_message=None,
        completed_at=datetime.now(timezone.utc),
    )

    db.add(record)

    return record


def save_research_report(
    db: Session,
    session: ResearchSession,
    run: ResearchRun,
    report_data: dict,
):
    """Save the final structured and Markdown report."""

    report_data = to_dict(report_data)

    if not report_data:
        return None

    report = Report(
        session_id=session.id,
        research_run_id=run.id,
        title=report_data.get("title") or "Research Report",
        content=report_data,
        markdown_content=report_data.get(
            "report_markdown", ""
        ),
        version=1,
    )

    db.add(report)

    return report


def persist_research_execution(
    db: Session,
    session: ResearchSession,
    run: ResearchRun,
    query: str,
    domain: str,
    research: dict,
    critic_results: dict,
    trend_results: dict,
    verification_results: dict,
    judge_results: dict,
    report: dict,
):
    """
    Persist all outputs from one completed research execution.

    The caller creates the session and run before invoking this function.
    All persistence operations are committed together.
    """

    try:
        research = to_dict(research)
        critic_results = to_dict(critic_results)
        trend_results = to_dict(trend_results)
        verification_results = to_dict(verification_results)
        judge_results = to_dict(judge_results)
        report = to_dict(report)

        evidence_items = research.get("evidence", [])

        if not isinstance(evidence_items, list):
            raise ValueError(
                "Research evidence must be a list."
            )

        saved_evidence = save_research_sources(
            db=db,
            session=session,
            run=run,
            evidence_items=evidence_items,
            domain=domain,
        )

        agent_outputs = {
            "research": research,
            "critic": critic_results,
            "trend": trend_results,
            "fact_verification": verification_results,
            "judge": judge_results,
        }

        saved_agent_outputs = 0

        for agent_name, output in agent_outputs.items():
            record = save_agent_output(
                db=db,
                session=session,
                run=run,
                agent_name=agent_name,
                output=output,
                query=query,
            )

            if record is not None:
                saved_agent_outputs += 1

        saved_report = save_research_report(
            db=db,
            session=session,
            run=run,
            report_data=report,
        )

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "status": "completed",
            "research_run_id": str(run.id),
            "evidence_saved": len(saved_evidence),
            "agent_outputs_saved": saved_agent_outputs,
            "report_saved": saved_report is not None,
        }

    except Exception:
        db.rollback()
        raise


def mark_research_run_failed(
    db: Session,
    run: ResearchRun,
):
    """Mark a failed run so it is not treated as completed memory."""

    try:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)

        db.commit()

    except Exception:
        db.rollback()
        raise
