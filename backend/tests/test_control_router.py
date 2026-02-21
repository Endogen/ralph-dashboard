"""Tests for control route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.control.models import LoopConfig
from app.control.process_manager import read_project_pid, terminate_pid
from app.projects.models import project_id_from_path
from app.control.router import (
    InjectRequest,
    StartLoopRequest,
    get_config,
    post_inject,
    post_pause,
    post_resume,
    post_start,
    post_stop,
    put_config,
)


def _seed_project(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    project = workspace / "control-project"
    (project / ".ralph").mkdir(parents=True)
    script = project / "ralph.sh"
    script.write_text("#!/usr/bin/env bash\nsleep 30\n", encoding="utf-8")
    script.chmod(0o755)
    return workspace, project


async def _cleanup_process(project_id: str) -> None:
    pid = await read_project_pid(project_id)
    if pid is not None:
        terminate_pid(pid)


@pytest.mark.anyio
async def test_pause_resume_handlers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    paused = await post_pause(project_id)
    paused_again = await post_pause(project_id)
    resumed = await post_resume(project_id)
    resumed_again = await post_resume(project_id)

    assert paused.paused
    assert not paused_again.paused
    assert resumed.resumed
    assert not resumed_again.resumed
    assert not (project / ".ralph" / "pause").exists()


@pytest.mark.anyio
async def test_inject_handler_writes_inject_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    response = await post_inject(
        project_id,
        InjectRequest(message="Use a migration for schema changes."),
    )

    assert response.content == "Use a migration for schema changes.\n"
    assert (project / ".ralph" / "inject.md").read_text(encoding="utf-8") == response.content


@pytest.mark.anyio
async def test_config_handlers_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    payload = LoopConfig(
        cli="claude",
        flags="--dangerously-skip-permissions",
        max_iterations=33,
        test_command="pytest -q",
        model_pricing={"claude": 0.015},
    )
    written = await put_config(project_id, payload)
    loaded = await get_config(project_id)

    assert written == payload
    assert loaded == payload


@pytest.mark.anyio
async def test_start_handler_uses_persisted_config_and_supports_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    await put_config(
        project_id,
        LoopConfig(
            cli="codex",
            flags="-s workspace-write",
            max_iterations=7,
            test_command="",
            model_pricing={"codex": 0.006},
        ),
    )

    started = await post_start(project_id)
    try:
        assert started.command[-1] == "7"
    finally:
        await post_stop(project_id)
        await _cleanup_process(project_id)

    started_override = await post_start(project_id, StartLoopRequest(max_iterations=3))
    try:
        assert started_override.command[-1] == "3"
    finally:
        await post_stop(project_id)
        await _cleanup_process(project_id)

    started_unlimited = await post_start(project_id, StartLoopRequest(max_iterations=0))
    try:
        assert started_unlimited.command[-1] == "0"
    finally:
        await post_stop(project_id)
        await _cleanup_process(project_id)


@pytest.mark.anyio
async def test_get_config_missing_project_raises_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_config("missing-project")

    assert exc_info.value.status_code == 404
