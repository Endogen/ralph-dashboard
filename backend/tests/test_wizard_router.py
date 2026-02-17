"""Tests for wizard router endpoints."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.wizard.generator import ApiKeyNotConfiguredError, GenerationError
from app.wizard.router import get_templates, post_create, post_generate
from app.wizard.schemas import (
    CreateRequest,
    CreateResponse,
    GeneratedFile,
    GenerateRequest,
)
from app.wizard.service import ProjectDirectoryExistsError
from app.wizard import router as wizard_router_module


@pytest.mark.anyio
async def test_get_templates_returns_content() -> None:
    response = await get_templates()
    assert len(response.agents_md) > 0
    assert len(response.prompt_md) > 0


@pytest.mark.anyio
async def test_post_generate_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_generate(_: GenerateRequest):
        raise ApiKeyNotConfiguredError("ANTHROPIC_API_KEY not set")

    monkeypatch.setattr(wizard_router_module, "generate_project_files", _mock_generate)

    with pytest.raises(HTTPException) as exc_info:
        await post_generate(
            GenerateRequest(project_name="test", project_description="desc")
        )
    assert exc_info.value.status_code == 503


@pytest.mark.anyio
async def test_post_generate_generation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_generate(_: GenerateRequest):
        raise GenerationError("API error")

    monkeypatch.setattr(wizard_router_module, "generate_project_files", _mock_generate)

    with pytest.raises(HTTPException) as exc_info:
        await post_generate(
            GenerateRequest(project_name="test", project_description="desc")
        )
    assert exc_info.value.status_code == 502


@pytest.mark.anyio
async def test_post_generate_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_generate(_: GenerateRequest):
        return [
            GeneratedFile(path="README.md", content="# Hello"),
            GeneratedFile(path="AGENTS.md", content="# Agents"),
        ]

    monkeypatch.setattr(wizard_router_module, "generate_project_files", _mock_generate)

    response = await post_generate(
        GenerateRequest(project_name="test", project_description="desc")
    )
    assert len(response.files) == 2


@pytest.mark.anyio
async def test_post_create_directory_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_create(_: CreateRequest):
        raise ProjectDirectoryExistsError("Already exists")

    monkeypatch.setattr(wizard_router_module, "create_project", _mock_create)

    with pytest.raises(HTTPException) as exc_info:
        await post_create(
            CreateRequest(
                project_name="test",
                files=[GeneratedFile(path="f.md", content="c")],
            )
        )
    assert exc_info.value.status_code == 409


@pytest.mark.anyio
async def test_post_create_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_create(_: CreateRequest):
        return CreateResponse(
            project_id="test",
            project_path="/tmp/test",
            started=False,
        )

    monkeypatch.setattr(wizard_router_module, "create_project", _mock_create)

    response = await post_create(
        CreateRequest(
            project_name="test",
            files=[GeneratedFile(path="f.md", content="c")],
        )
    )
    assert response.project_id == "test"
    assert response.started is False
