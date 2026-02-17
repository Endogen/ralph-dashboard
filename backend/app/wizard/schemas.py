"""Pydantic models for the project creation wizard."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


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
        normalized = value.strip()
        if not normalized:
            raise ValueError("project_name cannot be empty")
        return normalized

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
        normalized = value.strip()
        if not normalized:
            raise ValueError("project_name cannot be empty")
        return normalized


class CreateResponse(BaseModel):
    """Response from the create endpoint."""

    project_id: str
    project_path: str
    started: bool = False


class TemplatesResponse(BaseModel):
    """Response containing default templates."""

    agents_md: str
    prompt_md: str
