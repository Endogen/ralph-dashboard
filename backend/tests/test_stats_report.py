"""Tests for markdown report generation service."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.stats.report import generate_project_report


def _seed_project(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    project = workspace / "report-project"
    ralph_dir = project / ".ralph"
    ralph_dir.mkdir(parents=True)

    (ralph_dir / "iterations.jsonl").write_text(
        '{"iteration":1,"max":2,"start":"2026-01-01T00:00:00Z","duration_seconds":120,"tokens":50,"status":"success","tasks_completed":["1.1"],"errors":[]}\n'
        '{"iteration":2,"max":2,"start":"2026-01-01T00:02:00Z","duration_seconds":60,"tokens":25,"status":"error","errors":["failure"]}\n',
        encoding="utf-8",
    )
    (project / "IMPLEMENTATION_PLAN.md").write_text(
        "STATUS: READY\n\n## Phase 1: Setup\n- [x] 1.1: Done\n- [ ] 1.2: Pending\n",
        encoding="utf-8",
    )
    return workspace


@pytest.mark.anyio
async def test_generate_project_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = _seed_project(tmp_path)
    project_id = project_id_from_path(workspace / "report-project")
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    report = await generate_project_report(project_id)

    assert "# Project Report: report-project" in report
    assert "## Summary" in report
    assert "## Phase Breakdown" in report
    assert "## Iteration Log" in report
    assert "## Errors" in report
