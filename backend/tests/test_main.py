"""Smoke tests for the FastAPI application skeleton."""

from app.main import app


def test_app_metadata() -> None:
    assert app.title == "Ralph Dashboard API"
    assert app.version == "0.1.0"


def test_health_route_registered() -> None:
    registered_paths = {route.path for route in app.routes}
    assert "/api/health" in registered_paths
