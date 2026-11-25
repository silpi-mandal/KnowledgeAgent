from unittest.mock import patch

from langchain_core.embeddings import Embeddings

from app.services.vector_store_service import (
    create_vector_store,
    search_vector_store,
)

KEYWORDS = ["python", "fastapi", "holiday"]


class KeywordEmbeddings(Embeddings):
    """Deterministic offline embeddings: one dimension per keyword."""

    def _vec(self, text: str) -> list[float]:
        lowered = text.lower()
        return [float(lowered.count(word)) + 0.01 for word in KEYWORDS]

    def embed_documents(self, texts):
        return [self._vec(text) for text in texts]

    def embed_query(self, text):
        return self._vec(text)


CHUNKS = [
    {"page_number": 1, "text": "Python is a programming language."},
    {"page_number": 2, "text": "FastAPI is a Python web framework."},
]


def _patched():
    return patch(
        "app.services.vector_store_service.create_embedding_model",
        return_value=KeywordEmbeddings(),
    )


def test_create_vector_store():
    with _patched():
        vector_store = create_vector_store(CHUNKS, "doc-1")

    assert vector_store is not None


def test_search_vector_store_returns_page_and_document():
    with _patched():
        vector_store = create_vector_store(CHUNKS, "doc-1")
        results = search_vector_store(vector_store, "python", k=1)

    assert len(results) == 1
    assert results[0]["document_id"] == "doc-1"
    assert results[0]["page_number"] in {1, 2}
    assert "Python" in results[0]["text"]
