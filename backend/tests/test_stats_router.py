"""Tests for stats route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.stats.router import get_project_stats


def _seed_project(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    project = workspace / "stats-project"
    ralph_dir = project / ".ralph"
    ralph_dir.mkdir(parents=True)

    (ralph_dir / "iterations.jsonl").write_text(
        '{"iteration":1,"max":2,"start":"2026-01-01T00:00:00Z","duration_seconds":120,"tokens":50,"status":"success","tasks_completed":["1.1"],"errors":[]}\n'
        '{"iteration":2,"max":2,"start":"2026-01-01T00:02:00Z","duration_seconds":60,"tokens":20,"status":"error","errors":["failure"]}\n',
        encoding="utf-8",
    )
    (project / "IMPLEMENTATION_PLAN.md").write_text(
        "STATUS: READY\n\n## Phase 1: Setup\n- [x] 1.1: Done\n- [ ] 1.2: Pending\n",
        encoding="utf-8",
    )
    return workspace


@pytest.mark.anyio
async def test_get_project_stats_handler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = _seed_project(tmp_path)
    project_id = project_id_from_path(workspace / "stats-project")
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    stats = await get_project_stats(project_id)
    assert stats.total_iterations == 2
    assert stats.errors_count == 1
    assert stats.tasks_total == 2


@pytest.mark.anyio
async def test_get_project_stats_handler_missing_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_project_stats("missing")

    assert exc_info.value.status_code == 404
