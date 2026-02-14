"""Tests for project registration/discovery service layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.projects.service import (
    ProjectRegistrationError,
    discover_all_project_paths,
    get_project_detail,
    get_registered_project_paths,
    list_projects,
    register_project_path,
    unregister_project_by_id,
)


def _prepare_settings_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()


@pytest.mark.anyio
async def test_register_project_path_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _prepare_settings_env(monkeypatch, tmp_path)
    project = tmp_path / "project-a"
    (project / ".ralph").mkdir(parents=True)

    registered = await register_project_path(project)
    all_paths = await get_registered_project_paths()

    assert registered == project.resolve()
    assert all_paths == [project.resolve()]


@pytest.mark.anyio
async def test_register_project_rejects_path_without_ralph(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _prepare_settings_env(monkeypatch, tmp_path)
    invalid_project = tmp_path / "no-ralph"
    invalid_project.mkdir(parents=True)

    with pytest.raises(ProjectRegistrationError):
        await register_project_path(invalid_project)


@pytest.mark.anyio
async def test_unregister_project_by_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _prepare_settings_env(monkeypatch, tmp_path)
    project = tmp_path / "project-a"
    (project / ".ralph").mkdir(parents=True)
    await register_project_path(project)

    removed = await unregister_project_by_id(project_id_from_path(project.resolve()))
    remaining = await get_registered_project_paths()

    assert removed
    assert remaining == []


@pytest.mark.anyio
async def test_discover_all_project_paths_unions_discovered_and_registered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    discovered_root = tmp_path / "workspace"
    discovered_project = discovered_root / "from-discovery"
    manual_project = tmp_path / "manual-project"

    (discovered_project / ".ralph").mkdir(parents=True)
    (manual_project / ".ralph").mkdir(parents=True)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(discovered_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    await register_project_path(manual_project)
    all_paths = await discover_all_project_paths()

    assert all_paths == sorted([discovered_project.resolve(), manual_project.resolve()])


@pytest.mark.anyio
async def test_list_projects_returns_project_summaries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    discovered_root = tmp_path / "workspace"
    discovered_project = discovered_root / "from-discovery"
    (discovered_project / ".ralph").mkdir(parents=True)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(discovered_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    projects = await list_projects()

    assert len(projects) == 1
    assert projects[0].id == "from-discovery"
    assert projects[0].name == "from-discovery"


@pytest.mark.anyio
async def test_get_project_detail_by_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    discovered_root = tmp_path / "workspace"
    project = discovered_root / "from-discovery"
    ralph_dir = project / ".ralph"

    ralph_dir.mkdir(parents=True)
    (project / "IMPLEMENTATION_PLAN.md").write_text("STATUS: READY\n", encoding="utf-8")
    (ralph_dir / "ralph.log").write_text("start\n", encoding="utf-8")

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(discovered_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    detail = await get_project_detail("from-discovery")
    missing = await get_project_detail("missing")

    assert detail is not None
    assert detail.ralph_dir == ralph_dir.resolve()
    assert detail.plan_file == (project / "IMPLEMENTATION_PLAN.md").resolve()
    assert detail.log_file == (ralph_dir / "ralph.log").resolve()
    assert missing is None
