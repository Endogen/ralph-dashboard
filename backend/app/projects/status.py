"""Project status detection utilities."""

from __future__ import annotations

from pathlib import Path

from app.projects.models import ProjectDetail, ProjectStatus, ProjectSummary, project_id_from_path
from app.utils.process import is_process_alive, read_pid


def _is_running(ralph_dir: Path) -> bool:
    pid_file = ralph_dir / "ralph.pid"
    pid = read_pid(pid_file)
    if pid is None:
        if pid_file.exists() and pid_file.is_file():
            pid_file.unlink(missing_ok=True)
        return False
    if is_process_alive(pid):
        return True

    pid_file.unlink(missing_ok=True)
    return False


def _is_plan_complete(project_path: Path) -> bool:
    plan_file = project_path / "IMPLEMENTATION_PLAN.md"
    if not plan_file.exists() or not plan_file.is_file():
        return False

    # Scan the entire file for the STATUS marker — it may appear after
    # headings, comments, or other content.
    for line in plan_file.read_text(encoding="utf-8").splitlines():
        if line.strip().upper() == "STATUS: COMPLETE":
            return True
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


def build_project_detail(project_path: Path) -> ProjectDetail:
    """Build a detail model for a discovered project path."""
    resolved_path = project_path.expanduser().resolve()
    ralph_dir = resolved_path / ".ralph"
    plan_file = resolved_path / "IMPLEMENTATION_PLAN.md"
    log_file = ralph_dir / "ralph.log"
    return ProjectDetail(
        id=project_id_from_path(resolved_path),
        name=resolved_path.name,
        path=resolved_path,
        status=detect_project_status(resolved_path),
        ralph_dir=ralph_dir,
        plan_file=plan_file if plan_file.exists() else None,
        log_file=log_file if log_file.exists() else None,
    )
