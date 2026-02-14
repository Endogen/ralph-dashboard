"""Project status detection utilities."""

from __future__ import annotations

import os
from pathlib import Path

from app.projects.models import ProjectStatus, ProjectSummary, project_id_from_path


def _read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists() or not pid_file.is_file():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (TypeError, ValueError):
        return None


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _is_running(ralph_dir: Path) -> bool:
    pid = _read_pid(ralph_dir / "ralph.pid")
    if pid is None:
        return False
    return _is_process_alive(pid)


def _is_plan_complete(project_path: Path) -> bool:
    plan_file = project_path / "IMPLEMENTATION_PLAN.md"
    if not plan_file.exists() or not plan_file.is_file():
        return False

    for line in plan_file.read_text(encoding="utf-8").splitlines():
        if line.strip().upper() == "STATUS: COMPLETE":
            return True
        if line.strip():
            break
    return False


def detect_project_status(project_path: Path) -> ProjectStatus:
    """Determine project status from process, pause, and plan markers."""
    resolved_path = project_path.expanduser().resolve()
    ralph_dir = resolved_path / ".ralph"
    running = _is_running(ralph_dir)

    if running:
        pause_file = ralph_dir / "pause"
        if pause_file.exists():
            return ProjectStatus.paused
        return ProjectStatus.running

    if _is_plan_complete(resolved_path):
        return ProjectStatus.complete

    return ProjectStatus.stopped


def build_project_summary(project_path: Path) -> ProjectSummary:
    """Build a summary model for a discovered project path."""
    resolved_path = project_path.expanduser().resolve()
    return ProjectSummary(
        id=project_id_from_path(resolved_path),
        name=resolved_path.name,
        path=resolved_path,
        status=detect_project_status(resolved_path),
    )
