"""End-to-end smoke coverage using the antique-catalogue fixture."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from app.config import get_settings
from app.control.router import get_config
from app.iterations.router import get_iteration_detail, get_iterations
from app.notifications.router import get_notifications
from app.plan.router import get_plan
from app.projects.router import get_project, get_projects
from app.stats.report_router import get_project_report
from app.stats.router import get_project_stats

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "antique-catalogue"


def _seed_antique_catalogue_project(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    project = workspace / "antique-catalogue"
    ralph_dir = project / ".ralph"
    ralph_dir.mkdir(parents=True)

    shutil.copy2(FIXTURE_DIR / "IMPLEMENTATION_PLAN.md", project / "IMPLEMENTATION_PLAN.md")
    shutil.copy2(FIXTURE_DIR / "ralph.log", ralph_dir / "ralph.log")
    shutil.copy2(FIXTURE_DIR / "iterations.jsonl", ralph_dir / "iterations.jsonl")

    (ralph_dir / "pending-notification.txt").write_text(
        '{"timestamp":"2026-02-08T04:48:33+01:00","message":"PROGRESS: Fixture notification","status":"pending"}\n',
        encoding="utf-8",
    )
    return workspace


@pytest.mark.anyio
async def test_antique_catalogue_fixture_end_to_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = _seed_antique_catalogue_project(tmp_path)
    expected_project_path = (workspace / "antique-catalogue").resolve()

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    projects = await get_projects()
    assert len(projects) == 1
    assert projects[0].id == "antique-catalogue"
    assert projects[0].status.value == "complete"

    detail = await get_project("antique-catalogue")
    assert detail.path == expected_project_path
    assert detail.ralph_dir == expected_project_path / ".ralph"

    iterations_response = await get_iterations(
        "antique-catalogue", status_filter="all", limit=50, offset=0
    )
    assert iterations_response.total == 2
    assert [item.number for item in iterations_response.iterations] == [1, 2]

    first_iteration = await get_iteration_detail("antique-catalogue", 1)
    assert first_iteration.tokens_used == pytest.approx(69.31)
    assert first_iteration.tasks_completed == ["1.1"]
    assert first_iteration.commit == "6e9b516"

    plan = await get_plan("antique-catalogue")
    assert plan.status == "COMPLETE"
    assert plan.tasks_done == plan.tasks_total
    assert plan.tasks_total > 0

    stats = await get_project_stats("antique-catalogue")
    assert stats.total_iterations == 2
    assert stats.total_tokens == pytest.approx(114.31)
    assert stats.errors_count >= 1

    config = await get_config("antique-catalogue")
    assert config.cli == "codex"
    assert config.max_iterations == 20

    notifications = await get_notifications("antique-catalogue")
    assert len(notifications) == 1
    assert notifications[0].prefix == "PROGRESS"
    assert notifications[0].message == "Fixture notification"

    report = await get_project_report("antique-catalogue")
    assert "# Project Report: antique-catalogue" in report.content
