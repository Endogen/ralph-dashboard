"""Subprocess manager for Ralph loop lifecycle."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from app.control.models import ProcessStartResult
from app.projects.service import get_project_detail


class ProcessManagerError(Exception):
    """Base process manager error."""


class ProcessProjectNotFoundError(ProcessManagerError):
    """Raised when project cannot be resolved."""


class ProcessAlreadyRunningError(ProcessManagerError):
    """Raised when project already has a running process."""


class ProcessCommandNotFoundError(ProcessManagerError):
    """Raised when startup command/script cannot be located."""


def _is_zombie_pid(pid: int) -> bool:
    stat_file = Path("/proc") / str(pid) / "stat"
    if not stat_file.exists() or not stat_file.is_file():
        return False
    try:
        state = stat_file.read_text(encoding="utf-8").split()[2]
    except (OSError, IndexError):
        return False
    return state == "Z"


def _read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists() or not pid_file.is_file():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    if _is_zombie_pid(pid):
        return False
    return True


def _repo_script_path() -> Path:
    return Path(__file__).resolve().parents[3] / "scripts" / "ralph.sh"


def _resolve_default_command(project_path: Path) -> list[str]:
    local_script = project_path / "ralph.sh"
    if local_script.exists() and local_script.is_file():
        return [str(local_script)]

    fallback_script = _repo_script_path()
    if fallback_script.exists() and fallback_script.is_file():
        return [str(fallback_script)]

    raise ProcessCommandNotFoundError("No ralph.sh found for project start")


async def _resolve_project_path(project_id: str) -> Path:
    project = await get_project_detail(project_id)
    if project is None:
        raise ProcessProjectNotFoundError(f"Project not found: {project_id}")
    return project.path


async def read_project_pid(project_id: str) -> int | None:
    """Read project PID file if present."""
    project_path = await _resolve_project_path(project_id)
    return _read_pid(project_path / ".ralph" / "ralph.pid")


async def is_project_running(project_id: str) -> bool:
    """Check running state from project PID file."""
    pid = await read_project_pid(project_id)
    if pid is None:
        return False
    return _is_pid_running(pid)


async def start_project_process(
    project_id: str,
    command: list[str] | None = None,
) -> ProcessStartResult:
    """Start Ralph loop subprocess and write .ralph/ralph.pid."""
    project_path = await _resolve_project_path(project_id)
    ralph_dir = project_path / ".ralph"
    ralph_dir.mkdir(parents=True, exist_ok=True)

    pid_file = ralph_dir / "ralph.pid"
    existing_pid = _read_pid(pid_file)
    if existing_pid is not None and _is_pid_running(existing_pid):
        raise ProcessAlreadyRunningError(f"Process already running with pid {existing_pid}")
    if existing_pid is not None and not _is_pid_running(existing_pid):
        pid_file.unlink(missing_ok=True)

    resolved_command = command or _resolve_default_command(project_path)
    log_file = ralph_dir / "ralph.log"
    with log_file.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(  # noqa: S603
            resolved_command,
            cwd=project_path,
            stdout=log_handle,
            stderr=log_handle,
            start_new_session=True,
        )

    pid_file.write_text(str(process.pid), encoding="utf-8")
    return ProcessStartResult(project_id=project_id, pid=process.pid, command=resolved_command)


def terminate_pid(pid: int) -> None:
    """Best-effort terminate helper for tests/callers."""
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def _wait_for_exit(pid: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _is_pid_running(pid):
            return True
        time.sleep(0.05)
    return not _is_pid_running(pid)


async def stop_project_process(project_id: str, grace_period_seconds: float = 3.0) -> bool:
    """Stop a running project process via SIGTERM then SIGKILL fallback."""
    project_path = await _resolve_project_path(project_id)
    pid_file = project_path / ".ralph" / "ralph.pid"

    pid = _read_pid(pid_file)
    if pid is None:
        return False

    if not _is_pid_running(pid):
        pid_file.unlink(missing_ok=True)
        return False

    os.kill(pid, signal.SIGTERM)
    exited = _wait_for_exit(pid, grace_period_seconds)
    if not exited:
        os.kill(pid, signal.SIGKILL)
        _wait_for_exit(pid, 1.0)

    pid_file.unlink(missing_ok=True)
    return True
