"""Project plan read/write services."""

from __future__ import annotations

from pathlib import Path

from app.plan.parser import (
    ParsedImplementationPlan,
    parse_implementation_plan,
    parse_implementation_plan_file,
)
from app.projects.service import get_project_detail


class PlanServiceError(Exception):
    """Base plan service error."""


class PlanProjectNotFoundError(PlanServiceError):
    """Raised when a requested project does not exist."""


async def _resolve_project_path(project_id: str) -> Path:
    project = await get_project_detail(project_id)
    if project is None:
        raise PlanProjectNotFoundError(f"Project not found: {project_id}")
    return project.path


async def get_project_plan(project_id: str) -> ParsedImplementationPlan:
    """Read and parse a project's implementation plan file."""
    project_path = await _resolve_project_path(project_id)
    plan_file = project_path / "IMPLEMENTATION_PLAN.md"
    parsed = parse_implementation_plan_file(plan_file)
    if parsed is None:
        return parse_implementation_plan("")
    return parsed


async def update_project_plan(project_id: str, content: str) -> ParsedImplementationPlan:
    """Write and parse a project's implementation plan file."""
    project_path = await _resolve_project_path(project_id)
    plan_file = project_path / "IMPLEMENTATION_PLAN.md"
    plan_file.write_text(content, encoding="utf-8")
    return parse_implementation_plan(content)
