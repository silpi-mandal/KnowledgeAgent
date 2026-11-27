import pytest

from app.core.config import get_settings
from app.services import login_throttle


@pytest.fixture(autouse=True)
def _fake_llm_credentials(monkeypatch, tmp_path):
    """Tests never call a real provider; give clients a dummy key."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    # Most tests exercise features, not login; auth tests switch this on.
    monkeypatch.setenv("AUTH_ENABLED", "false")
    # Keep tests from ever writing into the real storage folder.
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "default-storage"))
    get_settings.cache_clear()
    login_throttle.reset_all()
    yield
    get_settings.cache_clear()
    login_throttle.reset_all()
