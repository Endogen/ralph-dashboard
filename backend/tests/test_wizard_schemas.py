"""Tests for wizard Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.wizard.schemas import (
    CreateRequest,
    GeneratedFile,
    GenerateRequest,
    GenerateResponse,
    TemplatesResponse,
)


def test_generate_request_minimal() -> None:
    req = GenerateRequest(
        project_name="test-project",
        project_description="A test project",
    )
    assert req.project_name == "test-project"
    assert req.cli == "claude-code"
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
    )
    assert req.tech_stack == ["python", "react"]
    assert req.cli == "codex"
    assert req.max_iterations == 50


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
