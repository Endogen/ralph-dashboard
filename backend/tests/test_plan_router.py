"""Tests for project plan route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.plan.router import PlanUpdateRequest, get_plan, put_plan
from app.projects.models import project_id_from_path


def _seed_project(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    project = workspace / "plan-project"
    (project / ".ralph").mkdir(parents=True)
    (project / "IMPLEMENTATION_PLAN.md").write_text(
        "STATUS: READY\n\n## Phase 1: Setup\n- [ ] 1.1: Initial task\n",
        encoding="utf-8",
    )
    return workspace, project


@pytest.mark.anyio
async def test_get_plan_handler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    parsed = await get_plan(project_id)

    assert parsed.status == "READY"
    assert parsed.tasks_total == 1


@pytest.mark.anyio
async def test_put_plan_handler_updates_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, project = _seed_project(tmp_path)
    project_id = project_id_from_path(project)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    payload = PlanUpdateRequest(content="STATUS: COMPLETE\n\n## Phase 1: Setup\n- [x] 1.1: Done\n")
    parsed = await put_plan(project_id, payload)

    assert parsed.status == "COMPLETE"
    assert parsed.tasks_done == 1
    assert (project / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8") == payload.content


@pytest.mark.anyio
async def test_get_plan_handler_missing_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_plan("missing")

    assert exc_info.value.status_code == 404
