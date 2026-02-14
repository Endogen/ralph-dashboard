"""Tests for backend settings loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RALPH_PROJECT_DIRS", raising=False)
    monkeypatch.delenv("RALPH_PORT", raising=False)
    monkeypatch.delenv("RALPH_SECRET_KEY", raising=False)
    monkeypatch.delenv("RALPH_CREDENTIALS_FILE", raising=False)
    _clear_settings_cache()

    settings = get_settings()

    assert settings.project_dirs == [(Path.home() / "projects").resolve()]
    assert settings.port == 8420
    assert settings.secret_key == "replace-this-secret-key"
    assert (
        settings.credentials_file
        == (Path.home() / ".config" / "ralph-dashboard" / "credentials.yaml").resolve()
    )


def test_settings_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"
    credentials_file = tmp_path / "credentials.yaml"

    monkeypatch.setenv("RALPH_PROJECT_DIRS", f"{first}{os.pathsep}{second}")
    monkeypatch.setenv("RALPH_PORT", "9021")
    monkeypatch.setenv("RALPH_SECRET_KEY", "super-secret-key")
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials_file))
    _clear_settings_cache()

    settings = get_settings()

    assert settings.project_dirs == [first.resolve(), second.resolve()]
    assert settings.port == 9021
    assert settings.secret_key == "super-secret-key"
    assert settings.credentials_file == credentials_file.resolve()


def test_settings_project_dirs_comma_separated_and_deduped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"

    monkeypatch.setenv("RALPH_PROJECT_DIRS", f"{first},{first},{second}")
    _clear_settings_cache()

    settings = get_settings()

    assert settings.project_dirs == [first.resolve(), second.resolve()]
