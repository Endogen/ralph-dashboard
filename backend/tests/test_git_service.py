"""Tests for git service operations."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Actor, Repo

from app.config import get_settings
from app.git_service.service import GitRepositoryNotFoundError, get_git_diff, get_git_log
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

    file_path.write_text("line one\nline two\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("second commit", author=actor, committer=actor)

    return workspace, project


@pytest.mark.anyio
async def test_get_git_log_and_diff(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace, project = _seed_git_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    commits = await get_git_log(project_id, limit=10, offset=0)
    assert len(commits) == 2
    assert commits[0].message == "second commit"
    assert commits[0].files_changed >= 1

    diff = await get_git_diff(project_id, commits[0].hash)
    assert diff.hash == commits[0].hash
    assert "diff --git" in diff.diff


@pytest.mark.anyio
async def test_get_git_log_non_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "not-git"
    (project / ".ralph").mkdir(parents=True)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()
    project_id = project_id_from_path(project)

    with pytest.raises(GitRepositoryNotFoundError):
        await get_git_log(project_id)
