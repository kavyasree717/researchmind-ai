from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.web_search import search_web


router = APIRouter(
    prefix="/research",
    tags=["Web Research"]
)


class WebSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    max_results: int = Field(default=5, ge=1, le=10)


@router.post("/web-search")
def web_search(
    request: WebSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        results = search_web(
            query=request.query,
            max_results=request.max_results,
        )

        return {
            "query": request.query,
            "results_count": len(results),
            "results": results,
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Web search failed. Check the Tavily API configuration.",
        )