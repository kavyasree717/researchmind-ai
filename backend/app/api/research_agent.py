import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.research_agent import run_research


router = APIRouter(
    prefix="/research",
    tags=["Research Agent"],
)


Domain = Literal[
    "scientific_research",
    "agriculture",
    "government_policy",
    "education",
    "law",
]


class ResearchRequest(BaseModel):
    query: str = Field(min_length=5, max_length=2000)
    domain: Domain
    use_web: bool | None = None
    use_documents: bool = False
    session_id: uuid.UUID | None = None


@router.post("/run")
def research(
    request: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return run_research(
            query=request.query,
            domain=request.domain,
            user=current_user,
            db=db,
            use_web=request.use_web,
            use_documents=request.use_documents,
            session_id=request.session_id,
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Research execution failed. Check backend logs.",
        )