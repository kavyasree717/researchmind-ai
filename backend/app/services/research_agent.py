
from app.services.query_analyzer import analyze_query
from app.services.web_search import search_web
from app.services.embeddings import embed_texts
from app.models.document import Document, DocumentChunk


# Keep evidence compact so downstream agents stay within token limits.
MAX_WEB_EVIDENCE = 5
MAX_DOCUMENT_EVIDENCE = 3
MAX_CONTENT_LENGTH = 900


def run_research(
    query: str,
    domain: str,
    user,
    db,
    use_web=None,
    use_documents=False,
    session_id=None,
    analysis_result=None
):
    """
    Research Agent:
    1. Uses existing query analysis or analyzes the query.
    2. Searches the web when required.
    3. Searches the user's uploaded documents when requested.
    4. Combines and returns compact, traceable evidence.

    Evidence IDs are assigned sequentially across web and document
    results so downstream agents can refer to the same evidence.
    """

    # STEP 1: Use existing analysis or analyze the query.
    analysis = analysis_result or analyze_query(
        query,
        selected_domain=domain
    )

    evidence = []
    seen_urls = set()

    # STEP 2: Decide whether web search is needed.
    should_use_web = (
        use_web if use_web is not None
        else analysis.requires_web
    )

    if should_use_web:
        search_queries = analysis.search_queries or [query]

        for search_query in search_queries[:3]:

            if len(evidence) >= MAX_WEB_EVIDENCE:
                break

            results = search_web(
                query=search_query,
                max_results=5
            )

            for item in results:

                if len(evidence) >= MAX_WEB_EVIDENCE:
                    break

                if not isinstance(item, dict):
                    continue

                url = item.get("url")
                content = str(item.get("content") or "").strip()

                # Skip results without URLs or useful content.
                if not url or not content:
                    continue

                url = str(url).strip()

                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)

                evidence.append({
                    "id": f"E{len(evidence) + 1}",
                    "evidence_id": f"E{len(evidence) + 1}",
                    "source_type": "web",
                    "title": str(
                        item.get("title") or "Untitled source"
                    )[:180],
                    "url": url[:250],
                    "content": content[:MAX_CONTENT_LENGTH],
                    "published_date": item.get("published_date"),
                    "relevance_score": item.get("score")
                })

    # STEP 3: Search uploaded documents.
    if use_documents:

        remaining_slots = (
            MAX_WEB_EVIDENCE + MAX_DOCUMENT_EVIDENCE
            - len(evidence)
        )

        if remaining_slots > 0:

            query_vectors = embed_texts([query])

            if not query_vectors or len(query_vectors) != 1:
                raise ValueError(
                    "Could not generate a valid query embedding "
                    "for document search."
                )

            query_vector = query_vectors[0]

            document_query = (
                db.query(DocumentChunk, Document)
                .join(
                    Document,
                    DocumentChunk.document_id == Document.id
                )
                .filter(Document.user_id == user.id)
                .filter(DocumentChunk.embedding.isnot(None))
            )

            # Restrict results to the selected research session
            # when a session ID is provided.
            if session_id:
                document_query = document_query.filter(
                    Document.session_id == session_id
                )

            results = (
                document_query
                .order_by(
                    DocumentChunk.embedding.cosine_distance(
                        query_vector
                    )
                )
                .limit(
                    min(MAX_DOCUMENT_EVIDENCE, remaining_slots)
                )
                .all()
            )

            for chunk, document in results:

                page_number = None

                if chunk.chunk_metadata:
                    page_number = chunk.chunk_metadata.get(
                        "page_number"
                    )

                content = str(chunk.content or "").strip()

                if not content:
                    continue

                chunk_id = str(chunk.id)

                evidence_id = f"E{len(evidence) + 1}"

                evidence.append({
                    "id": evidence_id,
                    "evidence_id": evidence_id,
                    "source_type": "document",
                    "document_chunk_id": chunk_id,
                    "document_id": str(document.id),
                    "title": str(
                        document.filename or "Uploaded document"
                    )[:180],
                    "content": content[:MAX_CONTENT_LENGTH],
                    "page_number": page_number,
                    "relevance_score": None
                })

    # STEP 4: Return research results.
    return {
        "query": query,
        "domain": domain,
        "intent": analysis.intent,
        "selected_agents": analysis.selected_agents,
        "evidence_count": len(evidence),
        "evidence": evidence
    }
