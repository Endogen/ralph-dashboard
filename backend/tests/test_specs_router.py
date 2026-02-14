"""Tests for specs CRUD route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.files.specs_router import (
    SpecCreateRequest,
    SpecWriteRequest,
    get_spec,
    get_specs,
    post_spec,
    put_spec,
    remove_spec,
)


def _seed_project(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    project = workspace / "specs-project"
    (project / ".ralph").mkdir(parents=True)
    specs_dir = project / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "01-overview.md").write_text("# Overview\n", encoding="utf-8")
    return workspace, project


@pytest.mark.anyio
async def test_specs_crud_handlers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace, project = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    listed = await get_specs("specs-project")
    assert len(listed) == 1
    assert listed[0].name == "01-overview.md"

    read_response = await get_spec("specs-project", "01-overview.md")
    assert "# Overview" in read_response.content

    created = await post_spec(
        "specs-project",
        SpecCreateRequest(name="02-api.md", content="# API\n"),
    )
    assert created.name == "02-api.md"

    updated = await put_spec(
        "specs-project",
        "02-api.md",
        SpecWriteRequest(content="# API Updated\n"),
    )
    assert "Updated" in updated.content
    assert (project / "specs" / "02-api.md").read_text(encoding="utf-8") == "# API Updated\n"

    await remove_spec("specs-project", "02-api.md")
    assert not (project / "specs" / "02-api.md").exists()


@pytest.mark.anyio
async def test_specs_handler_rejects_invalid_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, _ = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_spec("specs-project", "../evil.md")

    assert exc_info.value.status_code == 400
