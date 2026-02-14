"""Tests for auth dependency and public-path helpers."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import require_access_token
from app.auth.service import create_access_token
from app.config import get_settings
from app.main import is_public_api_path


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_require_access_token_missing_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_access_token(None)

    assert exc_info.value.status_code == 401


def test_require_access_token_invalid_token() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

    with pytest.raises(HTTPException) as exc_info:
        require_access_token(credentials)

    assert exc_info.value.status_code == 401


def test_require_access_token_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_SECRET_KEY", "dependency-test-secret")
    _clear_settings_cache()

    token = create_access_token("demo")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    payload = require_access_token(credentials)

    assert payload.sub == "demo"
    assert payload.type == "access"


def test_is_public_api_path() -> None:
    assert is_public_api_path("/api/health")
    assert is_public_api_path("/api/auth/login")
    assert is_public_api_path("/api/auth/refresh/")
    assert is_public_api_path("/project/anything")
    assert not is_public_api_path("/api/projects")
