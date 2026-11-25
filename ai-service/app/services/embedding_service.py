from typing import Sequence

from openai import OpenAI

from langchain_core.embeddings import Embeddings

from app.core.config import get_settings


EMBEDDING_BATCH_SIZE = 100


class OpenAIEmbeddingModel(Embeddings):

    def __init__(self):
        settings = get_settings()

        self.client = OpenAI(
            api_key=settings.llm_api_key.get_secret_value(),
            base_url=settings.llm_base_url,
        )

        self.model = settings.embedding_model

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        embeddings: list[list[float]] = []

        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = list(texts[start : start + EMBEDDING_BATCH_SIZE])

            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )

            batch_embeddings = [
                entry.embedding
                for entry in sorted(
                    response.data,
                    key=lambda entry: entry.index,
                )
            ]

            embeddings.extend(batch_embeddings)

        return embeddings

    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )

        return response.data[0].embedding


DEFAULT_LOCAL_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class LocalEmbeddingModel(Embeddings):
    """Free, offline embeddings using sentence-transformers."""

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=local needs sentence-transformers. "
                "Run: pip install -r requirements-local-embeddings.txt"
            ) from exc

        settings = get_settings()
        self.model = SentenceTransformer(
            settings.embedding_model or DEFAULT_LOCAL_EMBEDDING_MODEL
        )

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.model.encode(list(texts), convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(text, convert_to_numpy=True).tolist()


def create_embedding_model() -> Embeddings:

    if get_settings().embedding_provider.strip().lower() == "local":
        return LocalEmbeddingModel()

    return OpenAIEmbeddingModel()
