"""Focused tests for frontend static serving behavior in production mode."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute

from app import main as main_module
from app.main import create_app


def _frontend_route_handler(test_app) -> Callable[[str], object]:
    for route in test_app.routes:
        if isinstance(route, APIRoute) and route.path == "/{full_path:path}":
            return route.endpoint
    raise AssertionError("Frontend catch-all route is not registered")


@pytest.mark.anyio
async def test_frontend_catch_all_serves_matching_file_and_spa_index(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)

    index_file = dist_dir / "index.html"
    doc_file = dist_dir / "docs.html"
    index_file.write_text("<html><body>index</body></html>", encoding="utf-8")
    doc_file.write_text("<html><body>docs</body></html>", encoding="utf-8")

    test_app = create_app(frontend_dist=dist_dir)
    handler = _frontend_route_handler(test_app)

    docs_response = await handler("docs.html")
    assert isinstance(docs_response, FileResponse)
    assert Path(docs_response.path).resolve() == doc_file.resolve()

    spa_response = await handler("project/antique-catalogue")
    assert isinstance(spa_response, FileResponse)
    assert Path(spa_response.path).resolve() == index_file.resolve()


@pytest.mark.anyio
async def test_frontend_catch_all_rejects_api_and_path_traversal(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>index</body></html>", encoding="utf-8")

    test_app = create_app(frontend_dist=dist_dir)
    handler = _frontend_route_handler(test_app)

    with pytest.raises(HTTPException) as api_exc:
        await handler("api/projects")
    assert api_exc.value.status_code == 404

    with pytest.raises(HTTPException) as traversal_exc:
        await handler("../outside.txt")
    assert traversal_exc.value.status_code == 404


def test_resolve_default_frontend_dist_prefers_packaged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    packaged = tmp_path / "packaged-dist"
    dev = tmp_path / "dev-dist"
    packaged.mkdir(parents=True)
    dev.mkdir(parents=True)

    monkeypatch.setattr(main_module, "PACKAGED_FRONTEND_DIST", packaged)
    monkeypatch.setattr(main_module, "DEV_FRONTEND_DIST", dev)
    monkeypatch.delenv("RALPH_FRONTEND_DIST", raising=False)

    assert main_module._resolve_default_frontend_dist() == packaged


def test_resolve_default_frontend_dist_honors_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    override = tmp_path / "override-dist"
    packaged = tmp_path / "packaged-dist"
    dev = tmp_path / "dev-dist"
    override.mkdir(parents=True)
    packaged.mkdir(parents=True)
    dev.mkdir(parents=True)

    monkeypatch.setattr(main_module, "PACKAGED_FRONTEND_DIST", packaged)
    monkeypatch.setattr(main_module, "DEV_FRONTEND_DIST", dev)
    monkeypatch.setenv("RALPH_FRONTEND_DIST", str(override))

    assert main_module._resolve_default_frontend_dist() == override.resolve()
