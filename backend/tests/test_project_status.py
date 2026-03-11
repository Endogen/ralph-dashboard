"""Tests for project status detection and project summary models."""

from __future__ import annotations

import os
from pathlib import Path

from app.projects.models import ProjectStatus, project_id_from_path
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


def test_detect_error_status_from_latest_failed_iteration(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    (project / ".ralph" / "iterations.jsonl").write_text(
        '{"iteration":1,"max":5,"start":"2026-03-12T10:00:00Z","end":"2026-03-12T10:05:00Z","status":"error","errors":["test failed"]}\n',
        encoding="utf-8",
    )

    status = detect_project_status(project)
    assert status == ProjectStatus.error


def test_detect_error_status_from_pending_error_notification_without_iterations(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    (project / ".ralph" / "pending-notification.txt").write_text(
        '{"timestamp":"2026-03-12T11:00:00Z","prefix":"ERROR","message":"Preflight failed"}\n',
        encoding="utf-8",
    )

    status = detect_project_status(project)
    assert status == ProjectStatus.error


def test_detect_error_status_from_blocked_notification_after_successful_iteration(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    (project / ".ralph" / "iterations.jsonl").write_text(
        '{"iteration":1,"max":1,"start":"2026-03-12T10:00:00Z","end":"2026-03-12T10:05:00Z","status":"success","errors":[]}\n',
        encoding="utf-8",
    )
    (project / ".ralph" / "pending-notification.txt").write_text(
        '{"timestamp":"2026-03-12T10:06:00Z","prefix":"BLOCKED","message":"Max iterations reached"}\n',
        encoding="utf-8",
    )

    status = detect_project_status(project)
    assert status == ProjectStatus.error


def test_stale_pending_error_is_ignored_after_later_successful_iteration(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    (project / ".ralph" / "pending-notification.txt").write_text(
        '{"timestamp":"2026-03-12T10:00:00Z","prefix":"ERROR","message":"Tests failed"}\n',
        encoding="utf-8",
    )
    (project / ".ralph" / "iterations.jsonl").write_text(
        '{"iteration":1,"max":5,"start":"2026-03-12T10:00:00Z","end":"2026-03-12T10:20:00Z","status":"success","errors":[]}\n',
        encoding="utf-8",
    )

    status = detect_project_status(project)
    assert status == ProjectStatus.stopped


def test_detect_stopped_status_with_stale_pid(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    pid_file = project / ".ralph" / "ralph.pid"
    pid_file.write_text("999999", encoding="utf-8")

    status = detect_project_status(project)
    assert status == ProjectStatus.stopped
    assert not pid_file.exists()


def test_detect_stopped_status_with_invalid_pid_content(tmp_path: Path) -> None:
    project = _create_project(tmp_path)
    pid_file = project / ".ralph" / "ralph.pid"
    pid_file.write_text("not-a-pid", encoding="utf-8")

    status = detect_project_status(project)
    assert status == ProjectStatus.stopped
    assert not pid_file.exists()


def test_build_project_summary(tmp_path: Path) -> None:
    project = _create_project(tmp_path, "My Demo_Project")
    summary = build_project_summary(project)

    assert summary.name == "My Demo_Project"
    assert summary.path == project.resolve()
    assert summary.id == project_id_from_path(project)
