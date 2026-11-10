
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.query_analyzer import analyze_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyzer", tags=["Query Analyzer"])

Domain = Literal[
    "scientific",
    "agriculture",
    "government_policy",
    "education",
    "law",
]


class AnalyzeRequest(BaseModel):
    query: str
    domain: Domain | None = None


@router.post("/analyze")
def analyze(
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = analyze_query(
            request.query,
            selected_domain=request.domain,
        )
        return result.model_dump()

    except Exception:
        logger.exception("Query Analyzer failed")
        raise HTTPException(
            status_code=502,
            detail="Query analysis failed. Check backend logs.",
        )
