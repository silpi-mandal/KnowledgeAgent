from unittest.mock import patch

from app.core.config import Settings
from app.services import embedding_service
from app.services.embedding_service import (
    LocalEmbeddingModel,
    OpenAIEmbeddingModel,
    create_embedding_model,
)


def test_create_embedding_model_defaults_to_openai_compatible():
    with patch.object(
        embedding_service,
        "get_settings",
        return_value=Settings(embedding_provider="openai", embedding_model="m", llm_api_key="test-key"),
    ):
        assert isinstance(create_embedding_model(), OpenAIEmbeddingModel)


def test_create_embedding_model_local_provider():
    with patch.object(
        embedding_service,
        "get_settings",
        return_value=Settings(embedding_provider="local"),
    ), patch.object(LocalEmbeddingModel, "__init__", lambda self: None):
        assert isinstance(create_embedding_model(), LocalEmbeddingModel)
