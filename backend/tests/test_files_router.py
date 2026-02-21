"""Tests for project file route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.files.router import ProjectFileUpdateRequest, get_project_file, put_project_file
from app.projects.models import project_id_from_path


def _seed_project(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    project = workspace / "files-project"
    (project / ".ralph").mkdir(parents=True)
    (project / "AGENTS.md").write_text("agents content\n", encoding="utf-8")
    (project / "PROMPT.md").write_text("prompt content\n", encoding="utf-8")
    return workspace, project


@pytest.mark.anyio
async def test_get_project_file_handler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    response = await get_project_file(project_id, "agents")
    assert response.name == "AGENTS.md"
    assert "agents content" in response.content


@pytest.mark.anyio
async def test_put_project_file_handler_updates_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    payload = ProjectFileUpdateRequest(content="updated prompt\n")
    response = await put_project_file(project_id, "prompt", payload)

    assert response.name == "PROMPT.md"
    assert response.content == "updated prompt\n"
    assert (project / "PROMPT.md").read_text(encoding="utf-8") == "updated prompt\n"


@pytest.mark.anyio
async def test_get_project_file_handler_missing_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_project_file("missing", "agents")

    assert exc_info.value.status_code == 404
