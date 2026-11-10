from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.user import User
from app.services.critic_agent import run_critic


router = APIRouter(
    prefix="/agents",
    tags=["Research Agents"],
)


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: str
    title: str | None = None
    url: str | None = None
    content: str = Field(min_length=1, max_length=5000)
    page_number: int | None = None


class CriticRequest(BaseModel):
    query: str = Field(min_length=5, max_length=2000)
    domain: str
    evidence: list[EvidenceItem] = Field(min_length=1, max_length=20)


@router.post("/critic")
def evaluate_research(
    request: CriticRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = run_critic(
            query=request.query,
            domain=request.domain,
            evidence=[
                item.model_dump()
                for item in request.evidence
            ],
        )

        return {
            "query": request.query,
            "domain": request.domain,
            "critic_review": result,
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Critic Agent failed. Check backend logs.",
        )