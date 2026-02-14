"""Tests for auth route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.auth.router import login, refresh_token
from app.auth.schemas import LoginRequest, RefreshRequest
from app.auth.service import hash_password, validate_access_token, validate_refresh_token
from app.config import get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def _write_credentials(path: Path, username: str, password: str) -> None:
    password_hash = hash_password(password)
    path.write_text(
        f"username: {username}\npassword_hash: {password_hash}\n",
        encoding="utf-8",
    )


@pytest.mark.anyio
async def test_login_success_issues_tokens(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.yaml"
    _write_credentials(credentials_file, "demo", "s3cr3t")

    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials_file))
    monkeypatch.setenv("RALPH_SECRET_KEY", "router-test-secret")
    _clear_settings_cache()

    response = await login(LoginRequest(username="demo", password="s3cr3t"))

    access_payload = validate_access_token(response.access_token)
    refresh_payload = validate_refresh_token(response.refresh_token)
    assert access_payload.sub == "demo"
    assert refresh_payload.sub == "demo"


@pytest.mark.anyio
async def test_login_invalid_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.yaml"
    _write_credentials(credentials_file, "demo", "s3cr3t")

    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials_file))
    _clear_settings_cache()

    with pytest.raises(HTTPException) as exc_info:
        await login(LoginRequest(username="demo", password="wrong"))

    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_login_missing_credentials_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    credentials_file = tmp_path / "missing.yaml"
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials_file))
    _clear_settings_cache()

    with pytest.raises(HTTPException) as exc_info:
        await login(LoginRequest(username="demo", password="s3cr3t"))

    assert exc_info.value.status_code == 503


@pytest.mark.anyio
async def test_refresh_token_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.yaml"
    _write_credentials(credentials_file, "demo", "s3cr3t")

    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials_file))
    monkeypatch.setenv("RALPH_SECRET_KEY", "router-test-secret")
    _clear_settings_cache()

    login_response = await login(LoginRequest(username="demo", password="s3cr3t"))
    refresh_response = await refresh_token(
        RefreshRequest(refresh_token=login_response.refresh_token)
    )
    payload = validate_access_token(refresh_response.access_token)

    assert payload.sub == "demo"


@pytest.mark.anyio
async def test_refresh_token_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_SECRET_KEY", "router-test-secret")
    _clear_settings_cache()

    with pytest.raises(HTTPException) as exc_info:
        await refresh_token(RefreshRequest(refresh_token="invalid-token"))

    assert exc_info.value.status_code == 401
