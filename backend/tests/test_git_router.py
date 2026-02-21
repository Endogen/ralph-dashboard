"""Tests for git route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from git import Actor, Repo

from app.config import get_settings
from app.git_service.router import get_commit_diff, get_commit_log
from app.projects.models import project_id_from_path


def _seed_git_project(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    project = workspace / "git-project"
    (project / ".ralph").mkdir(parents=True)

    repo = Repo.init(project)
    actor = Actor("Tester", "tester@example.com")
    file_path = project / "README.md"
    file_path.write_text("line one\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit", author=actor, committer=actor)
    return workspace, project


@pytest.mark.anyio
async def test_get_commit_log_handler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace, project = _seed_git_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    commits = await get_commit_log(project_id, limit=10, offset=0)
    assert len(commits) == 1
    assert commits[0].message == "initial commit"


@pytest.mark.anyio
async def test_get_commit_diff_handler_missing_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_git_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_commit_diff(project_id, "deadbeef")

    assert exc_info.value.status_code == 404
