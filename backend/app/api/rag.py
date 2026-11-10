import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.services.embeddings import embed_texts
from app.services.llm import generate_answer


router = APIRouter(prefix="/rag", tags=["RAG"])


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    session_id: uuid.UUID | None = None


@router.post("/ask")
def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # 1. Convert question into an embedding
        query_vector = embed_texts([request.question])[0]

        # 2. Calculate similarity with stored document chunks
        distance = DocumentChunk.embedding.cosine_distance(
            query_vector
        ).label("distance")

        statement = (
            select(
                DocumentChunk,
                Document.filename,
                distance,
            )
            .join(
                Document,
                Document.id == DocumentChunk.document_id,
            )
            .where(
                Document.user_id == current_user.id,
                DocumentChunk.embedding.is_not(None),
            )
        )

        if request.session_id:
            statement = statement.where(
                Document.session_id == request.session_id
            )

        results = db.execute(
            statement.order_by(distance).limit(5)
        ).all()

        if not results:
            raise HTTPException(
                status_code=404,
                detail="No relevant document chunks found. Upload a PDF first.",
            )

        # 3. Build context for the LLM
        context_parts = []
        sources = []

        for index, (chunk, filename, chunk_distance) in enumerate(
            results, start=1
        ):
            page_number = chunk.chunk_metadata.get("page_number")

            context_parts.append(
                f"""
[Source {index}, Page {page_number}]
Filename: {filename}
Content:
{chunk.content}
"""
            )

            sources.append({
                "source": index,
                "filename": filename,
                "page_number": page_number,
                "similarity": round(
                    1 - float(chunk_distance), 4
                ),
            })

        context = "\n\n".join(context_parts)

        # 4. Generate an answer using the retrieved context
        answer = generate_answer(
            question=request.question,
            context=context,
        )

        # 5. Return answer and source information
        return {
            "question": request.question,
            "answer": answer,
            "sources": sources,
            "chunks_used": len(sources),
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(f"RAG error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate an answer. Check the backend logs.",
        )