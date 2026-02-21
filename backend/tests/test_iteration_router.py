"""Tests for iteration route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.iterations.router import get_iteration_detail, get_iterations
from app.projects.models import project_id_from_path


def _seed_iteration_files(project: Path) -> None:
    ralph_dir = project / ".ralph"
    ralph_dir.mkdir(parents=True, exist_ok=True)
    (ralph_dir / "ralph.log").write_text(
        "[01:00:00] === Iteration 1/2 ===\n"
        "tokens used\n"
        "10\n"
        "[01:01:00] === Iteration 2/2 ===\n"
        "❌ failed tests\n",
        encoding="utf-8",
    )
    (ralph_dir / "iterations.jsonl").write_text(
        '{"iteration":1,"max":2,"start":"2026-01-01T00:00:00Z","status":"success","errors":[]}\n'
        '{"iteration":2,"max":2,"start":"2026-01-01T00:01:00Z","status":"error","errors":["failed tests"]}\n',
        encoding="utf-8",
    )


@pytest.mark.anyio
async def test_get_iterations_handler_filters_and_paginates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "iter-project"
    project_id = project_id_from_path(project)
    _seed_iteration_files(project)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    response = await get_iterations(project_id, status_filter="error", limit=10, offset=0)
    assert response.total == 1
    assert len(response.iterations) == 1
    assert response.iterations[0].number == 2


@pytest.mark.anyio
async def test_get_iteration_detail_missing_iteration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "iter-project"
    project_id = project_id_from_path(project)
    _seed_iteration_files(project)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_iteration_detail(project_id, 999)

    assert exc_info.value.status_code == 404
