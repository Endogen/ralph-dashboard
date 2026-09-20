"""Subprocess manager for Ralph loop lifecycle."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import time
import sys
from pathlib import Path

import psutil
from pydantic import ValidationError

from app.control.models import LoopConfig, ProcessStartResult
from app.projects.service import get_project_detail
from app.utils.process import (
    is_process_alive, read_pid, owns_process, process_lock, write_process_identity, terminate_group,
)
from app.utils.files import atomic_write


# Strong references to in-flight child reapers (see start_project_process).
_REAPERS: set[asyncio.Task] = set()


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


def _resolve_default_command() -> list[str]:
    # Use the installed runner, including in wheels and containers. A project
    # cannot silently replace the dashboard's lifecycle implementation.
    return [sys.executable, "-m", "app.runner"]


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

    try:
        with process_lock(ralph_dir):
            pid_file = ralph_dir / "ralph.pid"
            existing_pid = _read_pid(pid_file)
            if existing_pid and _is_pid_running(existing_pid) and owns_process(ralph_dir, existing_pid):
                raise ProcessAlreadyRunningError(f"Process already running with pid {existing_pid}")
            resolved_command = command or _resolve_default_command()
            launch_env = os.environ.copy()
            launch_env.update(env_overrides or {})
            launch_env["RALPH_MANAGED"] = "1"
            # Preserve importability in a source checkout as well as an installed wheel.
            launch_env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2]) + os.pathsep + launch_env.get("PYTHONPATH", "")
            with (ralph_dir / "launcher.log").open("a") as log_handle:
                process = subprocess.Popen(
                    resolved_command, cwd=project_path, stdout=log_handle, stderr=log_handle,
                    start_new_session=True, env=launch_env,
                )
            # Reap children without blocking the event loop, including failed starts.
            # asyncio keeps only weak references, so hold one until the task ends.
            reaper = asyncio.create_task(asyncio.to_thread(process.wait))
            _REAPERS.add(reaper)
            reaper.add_done_callback(_REAPERS.discard)
            try:
                write_process_identity(ralph_dir, process.pid)
            except psutil.NoSuchProcess:
                raise ProcessCommandNotFoundError("Runner exited during startup; see launcher.log") from None
            return ProcessStartResult(project_id=project_id, pid=process.pid, command=resolved_command)
    except BlockingIOError as exc:
        raise ProcessAlreadyRunningError("A start is already in progress") from exc


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

    atomic_write(inject_file, payload)
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
    atomic_write(config_file, json.dumps(config.model_dump(mode="json"), indent=2) + "\n")
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
    from app.runner import preflight
    try:
        await asyncio.to_thread(preflight, project_path, merged_config)
    except (ValueError, OSError) as exc:
        from app.runner import Runner
        failed = Runner(project_path, merged_config)
        failed.notify("ERROR", "Start failed", str(exc))
        failed.state("error", error=str(exc))
        raise ProcessCommandNotFoundError(str(exc)) from exc
    command = [*_resolve_default_command(), str(merged_config.max_iterations)]
    env_overrides = {
        "RALPH_CLI": merged_config.cli,
        "RALPH_FLAGS": merged_config.flags,
        "RALPH_TEST": merged_config.test_command,
        "RALPH_MODEL": merged_config.model,
        "RALPH_APPROVAL_MODE": merged_config.approval_mode,
    }
    state_file = project_path / ".ralph" / "state.json"
    previous = state_file.stat().st_mtime_ns if state_file.exists() else None
    result = await start_project_process(project_id, command=command, env_overrides=env_overrides)
    for _ in range(100):
        if state_file.exists() and state_file.stat().st_mtime_ns != previous:
            state = json.loads(state_file.read_text())
            if state.get("status") == "error":
                raise ProcessCommandNotFoundError(state.get("error", "Runner startup failed"))
            return result
        if not _is_pid_running(result.pid):
            raise ProcessCommandNotFoundError("Runner exited during startup; see launcher.log")
        await asyncio.sleep(0.05)
    await stop_project_process(project_id)
    raise ProcessCommandNotFoundError("Runner did not become ready within five seconds")


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

    if not owns_process(pid_file.parent, pid):
        raise ProcessManagerError("PID identity does not match this project's runner")
    try:
        pgid = os.getpgid(pid)
        await asyncio.to_thread(terminate_group, pgid, grace_period_seconds)
    except ProcessLookupError:
        pass
    pid_file.unlink(missing_ok=True)
    (pid_file.parent / "process.json").unlink(missing_ok=True)
    from datetime import UTC, datetime
    atomic_write(pid_file.parent / "state.json", json.dumps({
        "status": "stopped", "timestamp": datetime.now(UTC).isoformat(),
    }))
    (pid_file.parent / "pending-notification.txt").unlink(missing_ok=True)
    return True
