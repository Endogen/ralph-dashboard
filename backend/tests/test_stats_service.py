"""Tests for stats aggregation service."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.stats.service import aggregate_project_stats


def _seed_project(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    project = workspace / "stats-project"
    ralph_dir = project / ".ralph"

    ralph_dir.mkdir(parents=True)
    (ralph_dir / "iterations.jsonl").write_text(
        '{"iteration":1,"max":3,"start":"2026-01-01T00:00:00Z","duration_seconds":120,"tokens":50,"status":"success","tasks_completed":["1.1"],"errors":[]}\n'
        '{"iteration":2,"max":3,"start":"2026-01-01T00:03:00Z","duration_seconds":60,"tokens":30,"status":"error","errors":["failure"]}\n'
        '{"iteration":3,"max":3,"start":"2026-01-01T00:05:00Z","duration_seconds":60,"tokens":20,"status":"success","errors":[]}\n',
        encoding="utf-8",
    )
    (project / "IMPLEMENTATION_PLAN.md").write_text(
        "STATUS: READY\n\n## Phase 1: Setup\n- [x] 1.1: Done task\n- [ ] 1.2: Pending task\n",
        encoding="utf-8",
    )
    return workspace, project


@pytest.mark.anyio
async def test_aggregate_project_stats(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    stats = await aggregate_project_stats(project_id)

    assert stats.total_iterations == 3
    assert stats.total_tokens == 100.0
    assert stats.total_duration_seconds == 240.0
    assert stats.tasks_done == 1
    assert stats.tasks_total == 2
    assert stats.errors_count == 1
    assert stats.health_breakdown.productive == 1
    assert stats.health_breakdown.failed == 1
    assert stats.health_breakdown.partial == 1
    assert stats.velocity.tasks_remaining == 1
    assert stats.velocity.tasks_per_hour > 0
    assert stats.projected_completion is not None
    assert len(stats.tokens_by_phase) == 1
    assert stats.tokens_by_phase[0].phase == "Phase 1: Setup"
