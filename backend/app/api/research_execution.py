
import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user

from app.services.research_graph import research_workflow
from app.services.research_memory import (
    create_or_get_research_session,
    start_research_run,
    inspect_research_memory,
)
from app.services.research_persistence import (
    persist_research_execution,
    mark_research_run_failed,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/research",
    tags=["Research Workflow"],
)


Domain = Literal[
    "scientific",
    "scientific_research",
    "agriculture",
    "government_policy",
    "education",
    "law",
]


class ResearchExecutionRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    domain: Domain
    use_web: bool | None = None
    use_documents: bool = False
    session_id: UUID | None = None

    @field_validator("domain", mode="before")
    @classmethod
    def normalize_domain(cls, value):
        if value == "scientific":
            return "scientific_research"
        return value


def get_selected_agents(analysis) -> list[str]:
    """Support both Pydantic models and dictionaries."""

    if isinstance(analysis, dict):
        selected = analysis.get("selected_agents", [])
    else:
        selected = getattr(analysis, "selected_agents", [])

    if not isinstance(selected, list):
        return []

    return selected


@router.post("/execute")
def execute_research(
    request: ResearchExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = None

    try:
        # 1. Create or retrieve the research session.
        try:
            session = create_or_get_research_session(
                db=db,
                user=current_user,
                query=request.query,
                domain=request.domain,
                session_id=request.session_id,
            )

        except ValueError:
            raise HTTPException(
                status_code=404,
                detail="Research session not found.",
            )

        # 2. Create a research run.
        run = start_research_run(
            db=db,
            session=session,
            query=request.query,
            domain=request.domain,
        )

        # 3. Prepare the initial graph state.
        initial_state = {
            "query": request.query,
            "domain": request.domain,
            "user": current_user,
            "db": db,
            "use_web": request.use_web,
            "use_documents": request.use_documents,
            "session_id": session.id,
        }

        # 4. Execute the complete LangGraph workflow.
        result = research_workflow.invoke(initial_state)

        # 5. Collect graph outputs.
        research = result.get("research", {})
        critic_results = result.get("critic_results", {})
        trend_results = result.get("trend_results", {})
        verification_results = result.get(
            "verification_results", {}
        )
        judge_results = result.get("judge_results", {})
        report = result.get("report", {})

        evidence = result.get("evidence", [])

        selected_agents = get_selected_agents(
            result.get("analysis")
        )

        # 6. Persist research results.
        persistence_result = persist_research_execution(
            db=db,
            session=session,
            run=run,
            query=request.query,
            domain=request.domain,
            research=research,
            critic_results=critic_results,
            trend_results=trend_results,
            verification_results=verification_results,
            judge_results=judge_results,
            report=report,
        )

        # 7. Return the completed research execution.
        return {
            "status": "completed",
            "session_id": str(session.id),
            "research_run_id": str(run.id),
            "query": request.query,
            "domain": request.domain,
            "selected_agents": selected_agents,
            "evidence_count": len(evidence),
            "evidence": evidence,
            "critic_results": critic_results,
            "trend_results": trend_results,
            "verification_results": verification_results,
            "judge_results": judge_results,
            "report": report,
            "persistence": persistence_result,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Research workflow execution failed"
        )

        if run is not None:
            try:
                mark_research_run_failed(db, run)

            except Exception:
                logger.exception(
                    "Could not mark research run as failed"
                )

        raise HTTPException(
            status_code=502,
            detail=(
                "Research workflow failed. "
                "Check backend logs."
            ),
        )


class MemoryCheckRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    domain: Domain

    @field_validator("domain", mode="before")
    @classmethod
    def normalize_domain(cls, value):
        if value == "scientific":
            return "scientific_research"
        return value


@router.post("/memory-check")
def check_research_memory(
    request: MemoryCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = inspect_research_memory(
            db=db,
            user=current_user,
            query=request.query,
            domain=request.domain,
        )

        action = result.get("action", "RESEARCH")

        return {
            "query": request.query,
            "domain": request.domain,
            "memory": result.get("memory", {}),
            "memory_reused": action == "REUSE",
            "memory_decision": action,
            "reason": result.get(
                "reason",
                "No memory decision explanation was provided.",
            ),
            "matched_memory": result.get("matched_memory"),
            "freshness_results": result.get(
                "freshness_results", []
            ),
            "previous_evidence": result.get(
                "previous_evidence", []
            ),
        }

    except Exception:
        logger.exception(
            "Research memory check failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Research memory check failed. "
                "Check backend logs."
            ),
        )
