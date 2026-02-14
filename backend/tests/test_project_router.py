"""Tests for project router handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.projects.router import get_project, get_projects


@pytest.mark.anyio
async def test_get_projects_handler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    project = root / "handler-project"
    (project / ".ralph").mkdir(parents=True)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    response = await get_projects()
    assert len(response) == 1
    assert response[0].id == "handler-project"


@pytest.mark.anyio
async def test_get_project_handler_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_project("missing")

    assert exc_info.value.status_code == 404
