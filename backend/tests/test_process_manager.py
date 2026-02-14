"""Tests for loop process manager."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from app.config import get_settings
from app.control.process_manager import (
    ProcessAlreadyRunningError,
    is_project_running,
    pause_project_process,
    read_project_pid,
    resume_project_process,
    start_project_process,
    stop_project_process,
    terminate_pid,
)


def _seed_project(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    project = workspace / "control-project"
    (project / ".ralph").mkdir(parents=True)
    return workspace, project


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@pytest.mark.anyio
async def test_start_project_process_writes_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    started = await start_project_process("control-project", command=["sleep", "30"])
    try:
        pid_file = project / ".ralph" / "ralph.pid"
        assert pid_file.exists()
        assert int(pid_file.read_text(encoding="utf-8")) == started.pid
        assert await read_project_pid("control-project") == started.pid
        assert await is_project_running("control-project")
    finally:
        terminate_pid(started.pid)
        for _ in range(20):
            if not _pid_is_alive(started.pid):
                break
            time.sleep(0.05)


@pytest.mark.anyio
async def test_start_project_process_rejects_duplicate_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, _ = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    started = await start_project_process("control-project", command=["sleep", "30"])
    try:
        with pytest.raises(ProcessAlreadyRunningError):
            await start_project_process("control-project", command=["sleep", "30"])
    finally:
        terminate_pid(started.pid)
        for _ in range(20):
            if not _pid_is_alive(started.pid):
                break
            time.sleep(0.05)


@pytest.mark.anyio
async def test_stop_project_process_stops_and_cleans_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    await start_project_process("control-project", command=["sleep", "30"])
    stopped = await stop_project_process("control-project", grace_period_seconds=0.2)

    assert stopped
    assert not await is_project_running("control-project")
    assert not (project / ".ralph" / "ralph.pid").exists()


@pytest.mark.anyio
async def test_stop_project_process_returns_false_when_not_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    (project / ".ralph" / "ralph.pid").write_text("999999", encoding="utf-8")
    stopped = await stop_project_process("control-project")

    assert not stopped
    assert not (project / ".ralph" / "ralph.pid").exists()


@pytest.mark.anyio
async def test_pause_project_process_creates_pause_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    paused = await pause_project_process("control-project")
    pause_file = project / ".ralph" / "pause"
    paused_again = await pause_project_process("control-project")

    assert paused
    assert not paused_again
    assert pause_file.exists()
    assert pause_file.is_file()


@pytest.mark.anyio
async def test_resume_project_process_removes_pause_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    pause_file = project / ".ralph" / "pause"
    pause_file.write_text("", encoding="utf-8")

    resumed = await resume_project_process("control-project")
    resumed_again = await resume_project_process("control-project")

    assert resumed
    assert not resumed_again
    assert not pause_file.exists()
