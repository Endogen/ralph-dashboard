"""Isolate test configuration from the user's authentication settings."""
import pytest
from app.config import get_settings

@pytest.fixture(autouse=True)
def test_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("RALPH_SECRET_KEY", "test-only-signing-key-with-32-characters")
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "test-credentials.yaml"))
    monkeypatch.setenv("RALPH_DATABASE_PATH", str(tmp_path / "test-dashboard.db"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

@pytest.fixture
def anyio_backend():
    return "asyncio"
