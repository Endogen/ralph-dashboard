"""Tests for wizard service business logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.wizard.schemas import CreateRequest, GeneratedFile
from app.wizard.service import (
    ProjectDirectoryExistsError,
    ProjectTargetValidationError,
    create_project,
    get_default_templates,
)
from app.wizard import service as wizard_service_module


def test_get_default_templates() -> None:
    templates = get_default_templates()
    assert "AGENTS.md" in templates["agents_md"] or "agents" in templates["agents_md"].lower()
    assert "prompt" in templates["prompt_md"].lower()


@pytest.mark.anyio
async def test_create_project_basic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    projects_root.mkdir()

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    request = CreateRequest(
        project_name="test-wizard-project",
        cli="claude",
        max_iterations=10,
        files=[
            GeneratedFile(path="README.md", content="# Test Project\n"),
            GeneratedFile(path="specs/overview.md", content="# Overview\nTest overview"),
            GeneratedFile(path="IMPLEMENTATION_PLAN.md", content="# Plan\n- [ ] Task 1"),
        ],
    )

    response = await create_project(request)

    assert response.project_id == project_id_from_path(projects_root / "test-wizard-project")
    assert response.started is False
    assert response.start_error is None

    project_dir = projects_root / "test-wizard-project"
    assert project_dir.is_dir()
    assert (project_dir / ".ralph").is_dir()
    assert (project_dir / ".ralph" / "config.json").is_file()
    assert (project_dir / "README.md").is_file()
    assert (project_dir / "specs" / "overview.md").is_file()
    assert (project_dir / "IMPLEMENTATION_PLAN.md").is_file()

    # Check config.json content
    config = json.loads((project_dir / ".ralph" / "config.json").read_text())
    assert config["cli"] == "claude"
    assert config["max_iterations"] == 10

    # Check git was initialized
    assert (project_dir / ".git").is_dir()


@pytest.mark.anyio
async def test_create_project_directory_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    existing = projects_root / "existing-project"
    existing.mkdir(parents=True)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    request = CreateRequest(
        project_name="existing-project",
        files=[GeneratedFile(path="README.md", content="# Test")],
    )

    with pytest.raises(ProjectDirectoryExistsError):
        await create_project(request)


@pytest.mark.anyio
async def test_create_existing_project_with_existing_ralph_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    existing_project = projects_root / "existing-ralph-project"
    (existing_project / ".ralph").mkdir(parents=True)
    (existing_project / "README.md").write_text("old readme\n", encoding="utf-8")

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    request = CreateRequest(
        project_name="existing-ralph-project",
        project_mode="existing",
        existing_project_path=str(existing_project),
        files=[
            GeneratedFile(path="README.md", content="# Updated\n"),
            GeneratedFile(path="AGENTS.md", content="# Agents\n"),
        ],
    )

    response = await create_project(request)

    assert response.project_id == project_id_from_path(existing_project)
    assert response.project_path == str(existing_project.resolve())
    assert (existing_project / ".ralph" / "config.json").is_file()
    assert (existing_project / "README.md").read_text(encoding="utf-8") == "# Updated\n"
    assert (existing_project / "AGENTS.md").is_file()


@pytest.mark.anyio
async def test_create_existing_non_ralph_project_bootstraps_ralph_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    existing_project = projects_root / "existing-non-ralph-project"
    existing_project.mkdir(parents=True)
    (existing_project / "src").mkdir()
    (existing_project / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    request = CreateRequest(
        project_name="existing-non-ralph-project",
        project_mode="existing",
        existing_project_path=str(existing_project),
        files=[GeneratedFile(path="PROMPT.md", content="# Prompt\n")],
    )

    response = await create_project(request)

    assert response.project_id == project_id_from_path(existing_project)
    assert (existing_project / ".ralph").is_dir()
    assert (existing_project / ".ralph" / "config.json").is_file()
    assert (existing_project / ".git").exists()
    assert (existing_project / "PROMPT.md").is_file()


@pytest.mark.anyio
async def test_create_existing_project_rejects_path_outside_project_roots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    outside_project = tmp_path / "outside-project"
    projects_root.mkdir()
    outside_project.mkdir()

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    request = CreateRequest(
        project_name="outside-project",
        project_mode="existing",
        existing_project_path=str(outside_project),
        files=[GeneratedFile(path="PROMPT.md", content="# Prompt\n")],
    )

    with pytest.raises(ProjectTargetValidationError, match="must be inside one of RALPH_PROJECT_DIRS"):
        await create_project(request)


@pytest.mark.anyio
async def test_create_project_full_auto_sets_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    projects_root.mkdir()

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    # Test with codex CLI
    request = CreateRequest(
        project_name="auto-project",
        cli="codex",
        auto_approval="full-auto",
        files=[GeneratedFile(path="README.md", content="# Test")],
    )

    await create_project(request)

    config = json.loads(
        (projects_root / "auto-project" / ".ralph" / "config.json").read_text()
    )
    assert config["flags"] == "-s danger-full-access"

    # Test with claude CLI
    request_claude = CreateRequest(
        project_name="auto-project-claude",
        cli="claude",
        auto_approval="full-auto",
        files=[GeneratedFile(path="README.md", content="# Test")],
    )

    await create_project(request_claude)

    config_claude = json.loads(
        (projects_root / "auto-project-claude" / ".ralph" / "config.json").read_text()
    )
    assert config_claude["flags"] == "--dangerously-skip-permissions"


@pytest.mark.anyio
async def test_create_project_allows_unlimited_iterations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    projects_root.mkdir()

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    request = CreateRequest(
        project_name="unlimited-iterations-project",
        max_iterations=0,
        files=[GeneratedFile(path="README.md", content="# Test")],
    )

    await create_project(request)

    config = json.loads(
        (projects_root / "unlimited-iterations-project" / ".ralph" / "config.json").read_text()
    )
    assert config["max_iterations"] == 0


@pytest.mark.anyio
async def test_create_project_returns_start_error_when_autostart_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    projects_root.mkdir()

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    async def _mock_start(_: str) -> tuple[bool, str | None]:
        return False, "mocked start failure"

    monkeypatch.setattr(wizard_service_module, "_start_project_loop", _mock_start)

    request = CreateRequest(
        project_name="autostart-failure-project",
        start_loop=True,
        files=[GeneratedFile(path="README.md", content="# Test")],
    )

    response = await create_project(request)
    assert response.started is False
    assert response.start_error == "mocked start failure"
