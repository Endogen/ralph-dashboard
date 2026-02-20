"""Tests for iteration aggregation service."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.iterations.service import (
    ProjectNotFoundError,
    get_project_iteration_detail,
    list_project_iterations,
)
from app.iterations import service as iteration_service_module


def _seed_project_iteration_files(project: Path) -> None:
    ralph_dir = project / ".ralph"
    ralph_dir.mkdir(parents=True, exist_ok=True)
    (ralph_dir / "ralph.log").write_text(
        "[01:00:00] === Iteration 1/2 ===\n"
        "Planning\n"
        "tokens used\n"
        "40\n"
        "[01:05:00] === Iteration 2/2 ===\n"
        "⚠️ test failed\n"
        "tokens used\n"
        "55\n",
        encoding="utf-8",
    )
    (ralph_dir / "iterations.jsonl").write_text(
        '{"iteration":1,"max":2,"start":"2026-01-01T01:00:00Z","end":"2026-01-01T01:05:00Z","tokens":42.5,"status":"success","tasks_completed":["1.1"],"commit":"abc123","errors":[]}\n'
        '{"iteration":2,"max":2,"start":"2026-01-01T01:05:00Z","tokens":55.0,"status":"error","errors":["test failed"]}\n',
        encoding="utf-8",
    )


@pytest.mark.anyio
async def test_list_project_iterations_merges_log_and_jsonl(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "demo-project"
    _seed_project_iteration_files(project)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    iterations = await list_project_iterations("demo-project")
    assert len(iterations) == 2
    assert iterations[0].number == 1
    assert iterations[0].status == "success"
    assert iterations[0].commit == "abc123"
    assert iterations[1].number == 2
    assert iterations[1].has_errors
    assert iterations[1].errors == ["test failed"]


@pytest.mark.anyio
async def test_get_project_iteration_detail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "demo-project"
    _seed_project_iteration_files(project)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    detail = await get_project_iteration_detail("demo-project", 1)
    assert detail is not None
    # Detail view always parses log to get raw_output for the log viewer
    assert isinstance(detail.log_output, str)
    assert len(detail.log_output) > 0
    assert detail.status == "success"


@pytest.mark.anyio
async def test_list_project_iterations_project_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(ProjectNotFoundError):
        await list_project_iterations("missing")


@pytest.mark.anyio
async def test_get_project_iteration_detail_uses_tail_parse_for_large_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "demo-project"
    ralph_dir = project / ".ralph"
    ralph_dir.mkdir(parents=True, exist_ok=True)

    (ralph_dir / "ralph.log").write_text(
        "[01:00:00] === Iteration 1/2 ===\n"
        + ("early filler\n" * 300)
        + "[01:05:00] === Iteration 2/2 ===\n"
        + "tail payload line\n",
        encoding="utf-8",
    )
    (ralph_dir / "iterations.jsonl").write_text(
        '{"iteration":1,"max":2,"start":"2026-01-01T01:00:00Z","status":"success","errors":[]}\n'
        '{"iteration":2,"max":2,"start":"2026-01-01T01:05:00Z","status":"success","errors":[]}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(iteration_service_module, "MAX_LOG_PARSE_BYTES", 1024)
    monkeypatch.setattr(iteration_service_module, "LARGE_LOG_TAIL_PARSE_BYTES", 4096)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    detail = await get_project_iteration_detail("demo-project", 2)
    assert detail is not None
    assert "tail payload line" in detail.log_output
