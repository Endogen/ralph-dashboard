"""Smoke tests for the FastAPI application skeleton."""

from pathlib import Path

import pytest

from app import main as main_module
from app.main import app, create_app


def test_app_metadata() -> None:
    assert app.title == "Ralph Dashboard API"
    assert app.version == "0.1.0"


def test_health_route_registered() -> None:
    registered_paths = {route.path for route in app.routes}
    assert "/api/health" in registered_paths


def test_static_routes_not_registered_without_dist(tmp_path: Path) -> None:
    empty_dist = tmp_path / "dist"
    test_app = create_app(frontend_dist=empty_dist)

    registered_paths = {route.path for route in test_app.routes}
    assert "/assets" not in registered_paths
    assert "/{full_path:path}" not in registered_paths


def test_static_routes_registered_with_dist(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<!doctype html><html></html>", encoding="utf-8")

    test_app = create_app(frontend_dist=dist_dir)
    registered_paths = {route.path for route in test_app.routes}

    assert "/assets" in registered_paths
    assert "/{full_path:path}" in registered_paths


@pytest.mark.anyio
async def test_reconcile_project_statuses_reconciles_each_discovered_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_one = tmp_path / "project-one"
    project_two = tmp_path / "project-two"
    project_one.mkdir()
    project_two.mkdir()

    async def _mock_discover_all_project_paths() -> list[Path]:
        return [project_one, project_two]

    reconciled: list[tuple[str, Path]] = []

    async def _mock_reconcile_project_status(project_id: str, project_path: Path) -> None:
        reconciled.append((project_id, project_path))

    monkeypatch.setattr(
        main_module,
        "discover_all_project_paths",
        _mock_discover_all_project_paths,
    )
    monkeypatch.setattr(
        main_module.watcher_event_dispatcher,
        "reconcile_project_status",
        _mock_reconcile_project_status,
    )

    await main_module._reconcile_project_statuses()

    assert {project_id for project_id, _ in reconciled} == {
        main_module.project_id_from_path(project_one),
        main_module.project_id_from_path(project_two),
    }
    assert {project_path for _, project_path in reconciled} == {
        project_one,
        project_two,
    }
