
import fitz
import re


def extract_text_from_pdf(file_bytes: bytes) -> list[dict]:
    """
    Extract text from every page of a PDF.
    Returns page-wise text.
    """

    pages = []

    with fitz.open(stream=file_bytes, filetype="pdf") as pdf:

        for page_number, page in enumerate(pdf, start=1):

            text = page.get_text("text")

            # Clean unnecessary spaces and blank lines
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = text.strip()

            if text:
                pages.append({
                    "page_number": page_number,
                    "text": text
                })

    if not pages:
        raise ValueError(
            "No extractable text found. The PDF may be scanned or empty."
        )

    return pages


def create_chunks(
    pages: list[dict],
    chunk_size: int = 1000,
    overlap: int = 200
) -> list[dict]:
    """
    Split page text into overlapping character-based chunks.
    """

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk_size or overlap")

    chunks = []
    chunk_id = 0

    for page in pages:

        text = page["text"]
        start = 0

        while start < len(text):

            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_index": chunk_id,
                    "page_number": page["page_number"],
                    "content": chunk_text
                })
                chunk_id += 1

            if end == len(text):
                break

            start = end - overlap

    return chunks
