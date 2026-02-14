"""Tests for project status detection and project summary models."""

from __future__ import annotations

import os
from pathlib import Path

from app.projects.models import ProjectStatus
from app.projects.status import build_project_summary, detect_project_status


def _create_project(tmp_path: Path, name: str = "demo_project") -> Path:
    project_path = tmp_path / name
    (project_path / ".ralph").mkdir(parents=True)
    return project_path


def test_detect_running_status(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    (project / ".ralph" / "ralph.pid").write_text(str(os.getpid()), encoding="utf-8")

    status = detect_project_status(project)
    assert status == ProjectStatus.running


def test_detect_paused_status(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    ralph_dir = project / ".ralph"
    (ralph_dir / "ralph.pid").write_text(str(os.getpid()), encoding="utf-8")
    (ralph_dir / "pause").write_text("", encoding="utf-8")

    status = detect_project_status(project)
    assert status == ProjectStatus.paused


def test_detect_complete_status(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    (project / "IMPLEMENTATION_PLAN.md").write_text("STATUS: COMPLETE\n", encoding="utf-8")

    status = detect_project_status(project)
    assert status == ProjectStatus.complete


def test_detect_stopped_status_with_stale_pid(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    (project / ".ralph" / "ralph.pid").write_text("999999", encoding="utf-8")

    status = detect_project_status(project)
    assert status == ProjectStatus.stopped


def test_build_project_summary(tmp_path: Path) -> None:
    project = _create_project(tmp_path, "My Demo_Project")
    summary = build_project_summary(project)

    assert summary.name == "My Demo_Project"
    assert summary.path == project.resolve()
    assert summary.id == "my-demo-project"
