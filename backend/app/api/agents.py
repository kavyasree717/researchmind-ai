from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.user import User

from app.services.trend_agent import run_trend_analysis
from app.services.fact_verification_agent import run_fact_verification
from app.services.judge_agent import run_judge
from app.services.report_agent import generate_research_report


router = APIRouter(
    prefix="/agents",
    tags=["Research Agents"],
)


Domain = Literal[
    "scientific_research",
    "agriculture",
    "government_policy",
    "education",
    "law",
]


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: str
    title: str | None = None
    url: str | None = None
    content: str = Field(min_length=1, max_length=5000)
    page_number: int | None = None
    published_date: str | None = None
    relevance_score: float | None = None


class AgentRequest(BaseModel):
    query: str = Field(min_length=5, max_length=2000)
    domain: Domain
    evidence: list[EvidenceItem] = Field(max_length=20)


class JudgeRequest(AgentRequest):
    verification_results: dict


class ReportRequest(AgentRequest):
    critic_results: dict
    trend_results: dict
    verification_results: dict
    judge_results: dict


@router.post("/trend")
def trend(
    request: AgentRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = run_trend_analysis(
            request.query,
            request.domain,
            [item.model_dump() for item in request.evidence],
        )
        return {"trend_analysis": result}

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Trend Agent failed. Check backend logs.",
        )


@router.post("/verify")
def verify(
    request: AgentRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = run_fact_verification(
            request.query,
            request.domain,
            [item.model_dump() for item in request.evidence],
        )
        return {"verification_results": result}

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Fact Verification Agent failed. Check backend logs.",
        )


@router.post("/judge")
def judge(
    request: JudgeRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = run_judge(
            request.query,
            request.domain,
            request.verification_results,
            [item.model_dump() for item in request.evidence],
        )
        return {"judge_results": result}

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Judge Agent failed. Check backend logs.",
        )


@router.post("/report")
def report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = generate_research_report(
            query=request.query,
            domain=request.domain,
            evidence=[
                item.model_dump() for item in request.evidence
            ],
            critic_results=request.critic_results,
            trend_results=request.trend_results,
            verification_results=request.verification_results,
            judge_results=request.judge_results,
        )

        return {"report": result}

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Report Agent failed. Check backend logs.",
        )