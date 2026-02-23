"""Tests for wizard router endpoints."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.wizard.generator import (
    _GenerationJob,
)
from app.wizard.router import (
    get_generate_status,
    get_templates,
    post_create,
    post_generate_start,
)
from app.wizard.schemas import (
    CancelGenerateRequest,
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
async def test_post_generate_start_returns_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_start(_: GenerateRequest) -> str:
        return "test-req-id"

    monkeypatch.setattr(wizard_router_module, "start_generation", _mock_start)

    response = await post_generate_start(
        GenerateRequest(project_name="test", project_description="desc")
    )
    assert response.request_id == "test-req-id"


@pytest.mark.anyio
async def test_get_generate_status_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_get_status(_: str) -> None:
        return None

    monkeypatch.setattr(wizard_router_module, "get_generation_status", _mock_get_status)

    with pytest.raises(HTTPException) as exc_info:
        await get_generate_status("nonexistent")
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_get_generate_status_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_event_loop()
    future: asyncio.Future[list[GeneratedFile]] = loop.create_future()
    task = asyncio.ensure_future(future)
    job = _GenerationJob(task=task, created_at=0.0, done=False)

    async def _mock_get_status(_: str) -> _GenerationJob:
        return job

    monkeypatch.setattr(wizard_router_module, "get_generation_status", _mock_get_status)

    response = await get_generate_status("pending-id")
    assert response.status == "pending"
    assert response.files is None

    # Cleanup
    future.set_result([])
    await task


@pytest.mark.anyio
async def test_get_generate_status_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_event_loop()
    future: asyncio.Future[list[GeneratedFile]] = loop.create_future()
    future.set_result([])
    task = asyncio.ensure_future(future)
    await task

    files = [
        GeneratedFile(path="README.md", content="# Hello"),
        GeneratedFile(path="AGENTS.md", content="# Agents"),
    ]
    job = _GenerationJob(task=task, created_at=0.0, result=files, done=True)

    async def _mock_get_status(_: str) -> _GenerationJob:
        return job

    monkeypatch.setattr(wizard_router_module, "get_generation_status", _mock_get_status)

    response = await get_generate_status("complete-id")
    assert response.status == "complete"
    assert response.files is not None
    assert len(response.files) == 2


@pytest.mark.anyio
async def test_get_generate_status_error(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_event_loop()
    future: asyncio.Future[list[GeneratedFile]] = loop.create_future()
    future.set_result([])
    task = asyncio.ensure_future(future)
    await task

    job = _GenerationJob(task=task, created_at=0.0, error="LLM failed", done=True)

    async def _mock_get_status(_: str) -> _GenerationJob:
        return job

    monkeypatch.setattr(wizard_router_module, "get_generation_status", _mock_get_status)

    response = await get_generate_status("error-id")
    assert response.status == "error"
    assert response.error == "LLM failed"
    assert response.files is None


@pytest.mark.anyio
async def test_post_generate_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_cancel(_: str) -> bool:
        return True

    monkeypatch.setattr(wizard_router_module, "cancel_generation_request", _mock_cancel)

    response = await wizard_router_module.post_generate_cancel(
        CancelGenerateRequest(request_id="abc123")
    )
    assert response.cancelled is True


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
