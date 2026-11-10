from app.services.pdf_processor import create_chunks

pages = [
    {
        "page_number": 1,
        "text": "ResearchMind AI is a multi-agent research platform. " * 100
    }
]

chunks = create_chunks(pages)

print("Total chunks:", len(chunks))
print("First chunk:")
print(chunks[0]["content"])
print("Page number:", chunks[0]["page_number"])