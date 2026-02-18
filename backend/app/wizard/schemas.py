"""Pydantic models for the project creation wizard."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


_SAFE_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def _validate_safe_project_name(value: str) -> str:
    """Validate project name is safe (no path traversal, no special chars)."""
    normalized = value.strip()
    if not normalized:
        raise ValueError("project_name cannot be empty")
    if ".." in normalized or "/" in normalized or "\\" in normalized:
        raise ValueError("project_name must not contain path separators or '..'")
    if not _SAFE_PROJECT_NAME_RE.match(normalized):
        raise ValueError(
            "project_name must start with alphanumeric and contain only "
            "alphanumeric, hyphens, underscores, or dots"
        )
    return normalized


class GenerateRequest(BaseModel):
    """Request body for LLM-powered spec/plan generation."""

    project_name: str = Field(min_length=1, max_length=100)
    project_description: str = Field(min_length=1, max_length=10000)
    tech_stack: list[str] = Field(default_factory=list)
    cli: str = "claude-code"
    auto_approval: str = "sandboxed"
    max_iterations: int = Field(default=20, ge=1, le=999)
    test_command: str = ""
    model_override: str = ""

    @field_validator("project_name")
    @classmethod
    def _validate_project_name(cls, value: str) -> str:
        return _validate_safe_project_name(value)

    @field_validator("project_description")
    @classmethod
    def _validate_project_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("project_description cannot be empty")
        return normalized

    @field_validator("cli")
    @classmethod
    def _validate_cli(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("cli cannot be empty")
        return normalized


class GeneratedFile(BaseModel):
    """A single generated file with path and content."""

    path: str
    content: str


class GenerateResponse(BaseModel):
    """Response from the generate endpoint containing all generated files."""

    files: list[GeneratedFile]


class CreateRequest(BaseModel):
    """Request body for creating the project on disk."""

    project_name: str = Field(min_length=1, max_length=100)
    cli: str = "claude-code"
    auto_approval: str = "sandboxed"
    max_iterations: int = Field(default=20, ge=1, le=999)
    test_command: str = ""
    model_override: str = ""
    files: list[GeneratedFile]
    start_loop: bool = False

    @field_validator("project_name")
    @classmethod
    def _validate_project_name(cls, value: str) -> str:
        return _validate_safe_project_name(value)


class CreateResponse(BaseModel):
    """Response from the create endpoint."""

    project_id: str
    project_path: str
    started: bool = False


class TemplatesResponse(BaseModel):
    """Response containing default templates."""

    agents_md: str
    prompt_md: str
