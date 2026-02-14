"""Smoke tests for the FastAPI application skeleton."""

from pathlib import Path

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
