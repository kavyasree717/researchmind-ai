
from tavily import TavilyClient

from app.config import settings


def search_web(query: str, max_results: int = 5) -> list[dict]:
    if not settings.tavily_api_key:
        raise ValueError("Tavily API key is missing")

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    max_results = max(1, min(max_results, 10))

    client = TavilyClient(api_key=settings.tavily_api_key)

    response = client.search(
        query=query.strip(),
        search_depth="advanced",
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )

    results = []
    seen_urls = set()

    for item in response.get("results", []):
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        content = (item.get("content") or "").strip()

        if not title or not url or not content:
            continue

        normalized_url = url.rstrip("/").lower()

        if normalized_url in seen_urls:
            continue

        seen_urls.add(normalized_url)

        results.append({
            "title": title,
            "url": url,
            "content": content,
            "score": item.get("score"),
            "published_date": item.get("published_date"),
        })

    return results
