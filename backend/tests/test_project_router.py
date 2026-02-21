"""Tests for project router handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.projects.models import ProjectStatus, ProjectSummary, project_id_from_path
from app.projects import router as project_router
from app.projects.router import (
    RegisterProjectRequest,
    get_project,
    get_projects,
    register_project,
    unregister_project,
)


class _CapturingWatcherService:
    def __init__(self) -> None:
        self.refresh_calls = 0

    async def refresh_projects(self) -> None:
        self.refresh_calls += 1


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
    assert response[0].id == project_id_from_path(project)


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


@pytest.mark.anyio
async def test_register_project_refreshes_watcher(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    watcher = _CapturingWatcherService()
    project_path = (tmp_path / "registered").resolve()
    summary = ProjectSummary(
        id="registered",
        name="registered",
        path=project_path,
        status=ProjectStatus.stopped,
    )

    async def _register(_: Path) -> Path:
        return project_path

    monkeypatch.setattr(project_router, "file_watcher_service", watcher)
    monkeypatch.setattr(project_router, "register_project_path", _register)
    monkeypatch.setattr(project_router, "build_project_summary", lambda _: summary)

    response = await register_project(RegisterProjectRequest(path=str(project_path)))

    assert response == summary
    assert watcher.refresh_calls == 1


@pytest.mark.anyio
async def test_unregister_project_refreshes_watcher(monkeypatch: pytest.MonkeyPatch) -> None:
    watcher = _CapturingWatcherService()

    async def _unregister(_: str) -> bool:
        return True

    monkeypatch.setattr(project_router, "file_watcher_service", watcher)
    monkeypatch.setattr(project_router, "unregister_project_by_id", _unregister)

    await unregister_project("registered")

    assert watcher.refresh_calls == 1


@pytest.mark.anyio
async def test_unregister_project_missing_does_not_refresh_watcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watcher = _CapturingWatcherService()

    async def _unregister(_: str) -> bool:
        return False

    monkeypatch.setattr(project_router, "file_watcher_service", watcher)
    monkeypatch.setattr(project_router, "unregister_project_by_id", _unregister)

    with pytest.raises(HTTPException) as exc_info:
        await unregister_project("missing")

    assert exc_info.value.status_code == 404
    assert watcher.refresh_calls == 0
