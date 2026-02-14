"""Unit tests for authentication service primitives."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.auth.service import (
    CredentialsNotConfiguredError,
    InvalidCredentialsError,
    InvalidTokenError,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    hash_password,
    load_credentials,
    validate_access_token,
    validate_refresh_token,
    verify_password,
)
from app.config import get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_hash_and_verify_password() -> None:
    hashed = hash_password("s3cr3t")
    assert verify_password("s3cr3t", hashed)
    assert not verify_password("wrong", hashed)


def test_load_credentials_and_authenticate(tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.yaml"
    password_hash = hash_password("s3cr3t")
    credentials_file.write_text(
        f"username: demo\npassword_hash: {password_hash}\n",
        encoding="utf-8",
    )

    credentials = load_credentials(credentials_file)

    assert credentials is not None
    assert credentials.username == "demo"
    assert authenticate_user("demo", "s3cr3t", credentials_file).username == "demo"


def test_authenticate_raises_for_missing_credentials(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.yaml"
    with pytest.raises(CredentialsNotConfiguredError):
        authenticate_user("demo", "s3cr3t", missing_file)


def test_authenticate_raises_for_invalid_password(tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.yaml"
    password_hash = hash_password("s3cr3t")
    credentials_file.write_text(
        f"username: demo\npassword_hash: {password_hash}\n",
        encoding="utf-8",
    )

    with pytest.raises(InvalidCredentialsError):
        authenticate_user("demo", "wrong", credentials_file)


def test_access_token_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_SECRET_KEY", "test-secret-a")
    _clear_settings_cache()

    token = create_access_token("demo")
    payload = validate_access_token(token)

    assert payload.sub == "demo"
    assert payload.type == "access"

    with pytest.raises(InvalidTokenError):
        validate_refresh_token(token)


def test_refresh_token_invalid_after_secret_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RALPH_SECRET_KEY", "test-secret-a")
    _clear_settings_cache()
    token = create_refresh_token("demo")

    monkeypatch.setenv("RALPH_SECRET_KEY", "test-secret-b")
    _clear_settings_cache()

    with pytest.raises(InvalidTokenError):
        validate_refresh_token(token)
