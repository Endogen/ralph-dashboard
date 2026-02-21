"""Tests for report route handler."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.stats.report_router import get_project_report


def _seed_project(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    project = workspace / "report-project"
    ralph_dir = project / ".ralph"
    ralph_dir.mkdir(parents=True)

    (ralph_dir / "iterations.jsonl").write_text(
        '{"iteration":1,"max":1,"start":"2026-01-01T00:00:00Z","duration_seconds":10,"tokens":5,"status":"success","errors":[]}\n',
        encoding="utf-8",
    )
    (project / "IMPLEMENTATION_PLAN.md").write_text(
        "STATUS: COMPLETE\n\n## Phase 1: Setup\n- [x] 1.1: Done\n",
        encoding="utf-8",
    )
    return workspace


@pytest.mark.anyio
async def test_get_project_report_handler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = _seed_project(tmp_path)
    project_id = project_id_from_path(workspace / "report-project")
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    response = await get_project_report(project_id)
    assert "# Project Report: report-project" in response.content


@pytest.mark.anyio
async def test_get_project_report_handler_missing_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_project_report("missing")

    assert exc_info.value.status_code == 404
