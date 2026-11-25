import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _fake_llm_credentials(monkeypatch):
    """Tests never call a real provider; give clients a dummy key."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
