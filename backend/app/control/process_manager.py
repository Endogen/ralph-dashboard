"""Subprocess manager for Ralph loop lifecycle."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

from pydantic import ValidationError

from app.control.models import LoopConfig, ProcessStartResult
from app.projects.service import get_project_detail
from app.utils.process import is_process_alive, read_pid


class ProcessManagerError(Exception):
    """Base process manager error."""


class ProcessProjectNotFoundError(ProcessManagerError):
    """Raised when project cannot be resolved."""


class ProcessAlreadyRunningError(ProcessManagerError):
    """Raised when project already has a running process."""


class ProcessCommandNotFoundError(ProcessManagerError):
    """Raised when startup command/script cannot be located."""


class ProcessInjectionValidationError(ProcessManagerError):
    """Raised when injection text is invalid."""


class ProcessConfigParseError(ProcessManagerError):
    """Raised when persisted loop config is not valid JSON."""


class ProcessConfigValidationError(ProcessManagerError):
    """Raised when loop config payload fails validation."""


# Aliases for backward compatibility within this module
_read_pid = read_pid
_is_pid_running = is_process_alive


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
    env_overrides: dict[str, str] | None = None,
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
    launch_env = os.environ.copy()
    if env_overrides:
        launch_env.update(env_overrides)
    with log_file.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(  # noqa: S603
            resolved_command,
            cwd=project_path,
            stdout=log_handle,
            stderr=log_handle,
            start_new_session=True,
            env=launch_env,
        )

    # Let ralph.sh manage its own PID file to avoid PID conflicts.
    # The script writes $$ to ralph.pid on startup; if we also write the
    # Popen PID, the script finds a running PID and exits immediately.
    return ProcessStartResult(project_id=project_id, pid=process.pid, command=resolved_command)


async def pause_project_process(project_id: str) -> bool:
    """Create .ralph/pause sentinel file. Returns true when newly paused."""
    project_path = await _resolve_project_path(project_id)
    ralph_dir = project_path / ".ralph"
    ralph_dir.mkdir(parents=True, exist_ok=True)
    pause_file = ralph_dir / "pause"
    already_paused = pause_file.exists()
    pause_file.touch(exist_ok=True)
    return not already_paused


async def resume_project_process(project_id: str) -> bool:
    """Remove .ralph/pause sentinel file. Returns true when pause was cleared."""
    project_path = await _resolve_project_path(project_id)
    pause_file = project_path / ".ralph" / "pause"
    if not pause_file.exists() or not pause_file.is_file():
        return False
    pause_file.unlink()
    return True


async def inject_project_message(project_id: str, message: str) -> str:
    """Write instruction text to .ralph/inject.md for next iteration."""
    content = message.strip()
    if not content:
        raise ProcessInjectionValidationError("Injection message cannot be empty")

    project_path = await _resolve_project_path(project_id)
    ralph_dir = project_path / ".ralph"
    ralph_dir.mkdir(parents=True, exist_ok=True)
    inject_file = ralph_dir / "inject.md"
    payload = f"{content}\n"
    if inject_file.exists() and inject_file.is_file():
        existing = inject_file.read_text(encoding="utf-8").rstrip()
        if existing:
            payload = f"{existing}\n\n{content}\n"

    inject_file.write_text(payload, encoding="utf-8")
    return payload


async def read_project_config(project_id: str) -> LoopConfig:
    """Read .ralph/config.json or return default config if absent."""
    project_path = await _resolve_project_path(project_id)
    config_file = project_path / ".ralph" / "config.json"
    if not config_file.exists() or not config_file.is_file():
        return LoopConfig()

    try:
        parsed = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProcessConfigParseError(f"Invalid config.json: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ProcessConfigParseError("Invalid config.json: root must be an object")

    try:
        return LoopConfig.model_validate(parsed)
    except ValidationError as exc:
        raise ProcessConfigValidationError("Invalid config.json values") from exc


async def write_project_config(
    project_id: str, payload: LoopConfig | dict[str, object]
) -> LoopConfig:
    """Validate and persist .ralph/config.json."""
    try:
        config = payload if isinstance(payload, LoopConfig) else LoopConfig.model_validate(payload)
    except ValidationError as exc:
        raise ProcessConfigValidationError("Invalid config payload") from exc

    project_path = await _resolve_project_path(project_id)
    ralph_dir = project_path / ".ralph"
    ralph_dir.mkdir(parents=True, exist_ok=True)
    config_file = ralph_dir / "config.json"
    config_file.write_text(
        json.dumps(config.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return config


async def start_project_loop(
    project_id: str,
    *,
    max_iterations: int | None = None,
    cli: str | None = None,
    flags: str | None = None,
    test_command: str | None = None,
) -> ProcessStartResult:
    """Start project loop using stored config values with optional request overrides."""
    config = await read_project_config(project_id)
    merged_config = config.model_copy(
        update={
            key: value
            for key, value in {
                "max_iterations": max_iterations,
                "cli": cli,
                "flags": flags,
                "test_command": test_command,
            }.items()
            if value is not None
        }
    )

    project_path = await _resolve_project_path(project_id)
    command = [*_resolve_default_command(project_path), str(merged_config.max_iterations)]
    env_overrides = {
        "RALPH_CLI": merged_config.cli,
        "RALPH_FLAGS": merged_config.flags,
        "RALPH_TEST": merged_config.test_command,
    }
    return await start_project_process(project_id, command=command, env_overrides=env_overrides)


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


async def _async_wait_for_exit(pid: int, timeout_seconds: float) -> bool:
    """Non-blocking version of _wait_for_exit for async callers."""
    import asyncio

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _is_pid_running(pid):
            return True
        await asyncio.sleep(0.1)
    return not _is_pid_running(pid)


async def stop_project_process(project_id: str, grace_period_seconds: float = 3.0) -> bool:
    """Stop a running project process via SIGTERM then SIGKILL fallback.

    Sends signals to the entire process group (not just the PID) so that
    child processes spawned by ralph.sh (coding agents, test runners, etc.)
    are also terminated instead of being orphaned.
    """
    project_path = await _resolve_project_path(project_id)
    pid_file = project_path / ".ralph" / "ralph.pid"

    pid = _read_pid(pid_file)
    if pid is None:
        return False

    if not _is_pid_running(pid):
        pid_file.unlink(missing_ok=True)
        return False

    # Kill the entire process group — ralph.sh is started with
    # start_new_session=True, making it a session leader.
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        # Fallback to single-PID kill if group lookup fails
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pid_file.unlink(missing_ok=True)
            return True

    exited = await _async_wait_for_exit(pid, grace_period_seconds)
    if not exited:
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        await _async_wait_for_exit(pid, 1.0)

    pid_file.unlink(missing_ok=True)
    return True
