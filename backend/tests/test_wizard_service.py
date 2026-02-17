"""Tests for wizard service business logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.wizard.schemas import CreateRequest, GeneratedFile
from app.wizard.service import (
    ProjectDirectoryExistsError,
    create_project,
    get_default_templates,
)


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
        cli="claude-code",
        max_iterations=10,
        files=[
            GeneratedFile(path="README.md", content="# Test Project\n"),
            GeneratedFile(path="specs/overview.md", content="# Overview\nTest overview"),
            GeneratedFile(path="IMPLEMENTATION_PLAN.md", content="# Plan\n- [ ] Task 1"),
        ],
    )

    response = await create_project(request)

    assert response.project_id == "test-wizard-project"
    assert response.started is False

    project_dir = projects_root / "test-wizard-project"
    assert project_dir.is_dir()
    assert (project_dir / ".ralph").is_dir()
    assert (project_dir / ".ralph" / "config.json").is_file()
    assert (project_dir / "README.md").is_file()
    assert (project_dir / "specs" / "overview.md").is_file()
    assert (project_dir / "IMPLEMENTATION_PLAN.md").is_file()

    # Check config.json content
    config = json.loads((project_dir / ".ralph" / "config.json").read_text())
    assert config["cli"] == "claude-code"
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
async def test_create_project_full_auto_sets_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    projects_root.mkdir()

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(projects_root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    request = CreateRequest(
        project_name="auto-project",
        auto_approval="full-auto",
        files=[GeneratedFile(path="README.md", content="# Test")],
    )

    await create_project(request)

    config = json.loads(
        (projects_root / "auto-project" / ".ralph" / "config.json").read_text()
    )
    assert config["flags"] == "--full-auto"
