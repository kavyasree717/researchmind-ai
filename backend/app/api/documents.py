
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    Form,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import Query
from sqlalchemy import select

from app.services.embeddings import embed_texts
from app.database import get_db
from app.models.document import Document, DocumentChunk
from app.models.research import ResearchSession
from app.models.user import User
from app.core.security import get_current_user
from app.services.pdf_processor import (
    extract_text_from_pdf,
    create_chunks,
)


router = APIRouter(prefix="/documents", tags=["Documents"])

# Store uploaded PDFs inside the backend folder
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    session_id: uuid.UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate filename
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed",
        )

    # If a research session is supplied, verify ownership
    if session_id is not None:
        research_session = db.scalar(
            select(ResearchSession).where(
                ResearchSession.id == session_id,
                ResearchSession.user_id == current_user.id,
            )
        )

        if research_session is None:
            raise HTTPException(
                status_code=404,
                detail="Research session not found",
            )

    # Read the uploaded file
    file_bytes = await file.read(MAX_FILE_SIZE + 1)

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty PDF file")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF must be 20 MB or smaller",
        )

    # Check PDF signature; do not trust only the extension or MIME type
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file",
        )

    # Extract text and create chunks
    try:
       pages = extract_text_from_pdf(file_bytes)
       chunks = create_chunks(pages)

# Generate one embedding for each chunk
       vectors = embed_texts([
              chunk["content"] for chunk in chunks
])

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not process PDF: {str(exc)}",
        )

    # Create a unique storage filename
    document_id = uuid.uuid4()
    safe_original_name = Path(file.filename).name
    stored_filename = f"{document_id}.pdf"
    storage_path = UPLOAD_DIR / stored_filename

    # Save the PDF locally
    storage_path.write_bytes(file_bytes)

    try:
        document = Document(
            id=document_id,
            user_id=current_user.id,
            session_id=session_id,
            filename=safe_original_name,
            storage_path=str(storage_path),
            mime_type="application/pdf",
            file_size=len(file_bytes),
            status="processed",
        )

        db.add(document)

        # Save extracted chunks
        for chunk, vector in zip(chunks, vectors):
           db.add(
             DocumentChunk(
               document_id=document_id,
               chunk_index=chunk["chunk_index"],
               content=chunk["content"],
               chunk_metadata={
                "page_number": chunk["page_number"]
            },
            embedding=vector,
        )
    )

        db.commit()

    except Exception:
        db.rollback()

        if storage_path.exists():
            storage_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Could not save document to database",
        )

    return {
        "message": "PDF uploaded and processed successfully",
        "document_id": str(document_id),
        "filename": safe_original_name,
        "pages_extracted": len(pages),
        "chunks_created": len(chunks),
        "status": "processed",
    }



@router.get("/search")
def search_documents(
    q: str = Query(min_length=2, max_length=1000),
    session_id: uuid.UUID | None = None,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Convert the question into an embedding
    query_vector = embed_texts([q])[0]

    # Calculate cosine distance between query and document chunks
    distance = DocumentChunk.embedding.cosine_distance(
        query_vector
    ).label("distance")

    statement = (
        select(DocumentChunk, Document.filename, distance)
        .join(
            Document,
            Document.id == DocumentChunk.document_id
        )
        .where(
            Document.user_id == current_user.id,
            DocumentChunk.embedding.is_not(None),
        )
    )

    # Optionally search only within one research session
    if session_id is not None:
        statement = statement.where(
            Document.session_id == session_id
        )

    results = db.execute(
        statement.order_by(distance).limit(limit)
    ).all()

    matches = []

    for chunk, filename, chunk_distance in results:
        matches.append({
            "filename": filename,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.chunk_metadata.get("page_number"),
            "content": chunk.content,
            "similarity": round(
                1 - float(chunk_distance), 4
            ),
        })

    return {
        "query": q,
        "results_count": len(matches),
        "results": matches,
    }
