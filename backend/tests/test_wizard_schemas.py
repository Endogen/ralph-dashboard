"""Tests for wizard Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.wizard.schemas import (
    CancelGenerateRequest,
    CancelGenerateResponse,
    CreateRequest,
    GeneratedFile,
    GenerateRequest,
    GenerateResponse,
    GenerationStatus,
    StartGenerateResponse,
    TemplatesResponse,
)


def test_generate_request_minimal() -> None:
    req = GenerateRequest(
        project_name="test-project",
        project_description="A test project",
    )
    assert req.project_name == "test-project"
    assert req.cli == "claude"
    assert req.max_iterations == 20
    assert req.tech_stack == []


def test_generate_request_full() -> None:
    req = GenerateRequest(
        project_name="full-project",
        project_description="A full project with all options",
        tech_stack=["python", "react"],
        cli="codex",
        auto_approval="full-auto",
        max_iterations=50,
        test_command="pytest",
        model_override="gpt-4o",
        request_id=" req-123 ",
    )
    assert req.tech_stack == ["python", "react"]
    assert req.cli == "codex"
    assert req.max_iterations == 50
    assert req.request_id == "req-123"


def test_generate_request_allows_unlimited_iterations() -> None:
    req = GenerateRequest(
        project_name="unlimited-project",
        project_description="A project without iteration cap",
        max_iterations=0,
    )
    assert req.max_iterations == 0


def test_generate_request_name_with_spaces_slugified() -> None:
    req = GenerateRequest(
        project_name="Chore Tracker",
        project_description="A chore tracking app",
    )
    assert req.project_name == "chore-tracker"


def test_generate_request_name_with_multiple_spaces_slugified() -> None:
    req = GenerateRequest(
        project_name="  My  Cool  Project  ",
        project_description="desc",
    )
    assert req.project_name == "my-cool-project"


def test_generate_request_empty_name_rejected() -> None:
    with pytest.raises(ValidationError):
        GenerateRequest(project_name="", project_description="desc")


def test_generate_request_empty_description_rejected() -> None:
    with pytest.raises(ValidationError):
        GenerateRequest(project_name="name", project_description="")


def test_generate_request_whitespace_name_rejected() -> None:
    with pytest.raises(ValidationError):
        GenerateRequest(project_name="   ", project_description="desc")


def test_generate_response() -> None:
    resp = GenerateResponse(files=[
        GeneratedFile(path="AGENTS.md", content="# Agents"),
        GeneratedFile(path="PROMPT.md", content="# Prompt"),
    ])
    assert len(resp.files) == 2
    assert resp.files[0].path == "AGENTS.md"


def test_create_request_minimal() -> None:
    req = CreateRequest(
        project_name="new-project",
        files=[GeneratedFile(path="README.md", content="# Hello")],
    )
    assert req.project_name == "new-project"
    assert req.start_loop is False
    assert len(req.files) == 1


def test_create_request_allows_unlimited_iterations() -> None:
    req = CreateRequest(
        project_name="unlimited-create",
        max_iterations=0,
        files=[GeneratedFile(path="README.md", content="# Hello")],
    )
    assert req.max_iterations == 0


def test_create_request_empty_name_rejected() -> None:
    with pytest.raises(ValidationError):
        CreateRequest(
            project_name="",
            files=[GeneratedFile(path="f.md", content="c")],
        )


def test_templates_response() -> None:
    resp = TemplatesResponse(agents_md="# agents", prompt_md="# prompt")
    assert "agents" in resp.agents_md
    assert "prompt" in resp.prompt_md


def test_cancel_generate_request_and_response() -> None:
    req = CancelGenerateRequest(request_id=" cancel-1 ")
    resp = CancelGenerateResponse(cancelled=True)
    assert req.request_id == "cancel-1"
    assert resp.cancelled is True


def test_start_generate_response() -> None:
    resp = StartGenerateResponse(request_id="abc-123")
    assert resp.request_id == "abc-123"


def test_generation_status_pending() -> None:
    status = GenerationStatus(status="pending")
    assert status.status == "pending"
    assert status.files is None
    assert status.error is None


def test_generation_status_complete() -> None:
    files = [
        GeneratedFile(path="AGENTS.md", content="# Agents"),
        GeneratedFile(path="PROMPT.md", content="# Prompt"),
    ]
    status = GenerationStatus(status="complete", files=files)
    assert status.status == "complete"
    assert status.files is not None
    assert len(status.files) == 2
    assert status.error is None


def test_generation_status_error() -> None:
    status = GenerationStatus(status="error", error="LLM failed")
    assert status.status == "error"
    assert status.error == "LLM failed"
    assert status.files is None
