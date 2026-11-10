from app.services.embeddings import embed_texts

texts = [
    "Plants need water to grow.",
    "Water is essential for plant growth.",
    "Computers are used for programming."
]

vectors = embed_texts(texts)

print("Number of vectors:", len(vectors))
print("Dimensions:", len(vectors[0]))
print("First 5 values:", vectors[0][:5])

assert len(vectors) == 3
assert len(vectors[0]) == 384

print("Embedding test successful!")