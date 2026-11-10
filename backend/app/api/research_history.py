
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.research import ResearchSession, ResearchRun, Source
from app.models.evidence import Evidence, Claim
from app.models.agent import AgentOutput
from app.models.report import Report

import logging

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/research",
    tags=["Research History"],
)


def get_user_run(
    db: Session,
    user: User,
    run_id: UUID,
):
    """Retrieve a run only if it belongs to the logged-in user."""

    return (
        db.query(ResearchRun)
        .join(
            ResearchSession,
            ResearchRun.session_id == ResearchSession.id,
        )
        .filter(
            ResearchRun.id == run_id,
            ResearchSession.user_id == user.id,
        )
        .first()
    )


@router.get("/history")
def get_research_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's research runs."""

    runs = (
        db.query(ResearchRun)
        .join(
            ResearchSession,
            ResearchRun.session_id == ResearchSession.id,
        )
        .filter(ResearchSession.user_id == current_user.id)
        .order_by(ResearchRun.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    total = (
        db.query(ResearchRun)
        .join(
            ResearchSession,
            ResearchRun.session_id == ResearchSession.id,
        )
        .filter(ResearchSession.user_id == current_user.id)
        .count()
    )

    history = []

    for run in runs:
        report = (
            db.query(Report)
            .filter(Report.research_run_id == run.id)
            .order_by(Report.version.desc())
            .first()
        )

        history.append({
            "run_id": str(run.id),
            "session_id": str(run.session_id),
            "query": run.query_text,
            "domain": run.domain,
            "status": run.status,
            "started_at": (
                run.started_at.isoformat()
                if run.started_at else None
            ),
            "completed_at": (
                run.completed_at.isoformat()
                if run.completed_at else None
            ),
            "created_at": (
                run.created_at.isoformat()
                if run.created_at else None
            ),
            "report": {
                "title": report.title,
                "version": report.version,
            } if report else None,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "history": history,
    }


@router.get("/history/{run_id}")
def get_research_history_detail(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve one research run with its evidence and outputs."""

    run = get_user_run(db, current_user, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Research run not found.",
        )

    evidence_records = (
        db.query(Evidence)
        .filter(Evidence.research_run_id == run.id)
        .order_by(Evidence.created_at.asc())
        .all()
    )

    evidence = []

    for item in evidence_records:
        source = (
            db.get(Source, item.source_id)
            if item.source_id else None
        )

        metadata = item.evidence_metadata or {}

        evidence.append({
            "evidence_id": metadata.get("evidence_id"),
            "evidence_type": item.evidence_type,
            "evidence_text": item.evidence_text,
            "confidence": item.confidence,
            "source": {
                "title": source.title,
                "url": source.url,
                "published_at": (
                    source.published_at.isoformat()
                    if source.published_at else None
                ),
                "freshness_status": source.freshness_status,
            } if source else None,
            "metadata": metadata,
        })

    agent_records = (
        db.query(AgentOutput)
        .filter(AgentOutput.research_run_id == run.id)
        .order_by(AgentOutput.created_at.asc())
        .all()
    )

    agent_outputs = [
        {
            "agent_name": item.agent_name,
            "status": item.status,
            "output": item.output,
            "error_message": item.error_message,
            "started_at": (
                item.started_at.isoformat()
                if item.started_at else None
            ),
            "completed_at": (
                item.completed_at.isoformat()
                if item.completed_at else None
            ),
        }
        for item in agent_records
    ]

    report_records = (
        db.query(Report)
        .filter(Report.research_run_id == run.id)
        .order_by(Report.version.desc())
        .all()
    )

    reports = [
        {
            "title": report.title,
            "version": report.version,
            "content": report.content,
            "markdown_content": report.markdown_content,
            "created_at": (
                report.created_at.isoformat()
                if report.created_at else None
            ),
        }
        for report in report_records
    ]

    return {
        "run": {
            "run_id": str(run.id),
            "session_id": str(run.session_id),
            "query": run.query_text,
            "domain": run.domain,
            "status": run.status,
            "execution_plan": run.execution_plan,
            "started_at": (
                run.started_at.isoformat()
                if run.started_at else None
            ),
            "completed_at": (
                run.completed_at.isoformat()
                if run.completed_at else None
            ),
            "created_at": (
                run.created_at.isoformat()
                if run.created_at else None
            ),
        },
        "evidence": evidence,
        "agent_outputs": agent_outputs,
        "reports": reports,
    }


@router.delete("/history/{run_id}")
def delete_research_history(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a research run and its run-specific records."""

    run = get_user_run(db, current_user, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Research run not found.",
        )

    # Do not delete a run while its research is still executing.
    if (run.status or "").lower() in ("pending", "running"):
        raise HTTPException(
            status_code=409,
            detail="This research is still running. Try deleting it after it finishes.",
        )

    try:
        # Delete records associated with this specific run.
        db.query(Evidence).filter(
            Evidence.research_run_id == run.id
        ).delete(synchronize_session=False)

        db.query(Claim).filter(
            Claim.research_run_id == run.id
        ).delete(synchronize_session=False)

        db.query(AgentOutput).filter(
            AgentOutput.research_run_id == run.id
        ).delete(synchronize_session=False)

        db.query(Report).filter(
            Report.research_run_id == run.id
        ).delete(synchronize_session=False)

        # Finally delete the research run.
        db.delete(run)

        db.commit()

        return {
            "message": "Research history deleted successfully.",
            "run_id": str(run_id),
        }

    except Exception:
     db.rollback()

     logger.exception(
        "Failed to delete research run: %s",
        run_id,
    )

     raise HTTPException(
        status_code=500,
        detail="Unable to delete research history.",
    )
