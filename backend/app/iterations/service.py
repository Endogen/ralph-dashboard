"""Iteration aggregation and lookup services."""

from __future__ import annotations

from pathlib import Path

from app.iterations.jsonl_parser import ParsedJsonlIteration, parse_iterations_jsonl_file
from app.iterations.log_parser import ParsedLogIteration, parse_ralph_log_file
from app.iterations.models import IterationDetail, IterationSummary
from app.projects.service import get_project_detail


class IterationServiceError(Exception):
    """Base error for iteration-service operations."""


class ProjectNotFoundError(IterationServiceError):
    """Raised when project id cannot be resolved to a project path."""


async def _resolve_project_path(project_id: str) -> Path:
    project = await get_project_detail(project_id)
    if project is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")
    return project.path


def _from_log_iteration(iteration: ParsedLogIteration) -> IterationDetail:
    return IterationDetail(
        number=iteration.number,
        max_iterations=iteration.max_iterations,
        start_timestamp=iteration.start_timestamp,
        end_timestamp=iteration.end_timestamp,
        tokens_used=iteration.tokens_used,
        has_errors=iteration.has_errors,
        errors=iteration.error_lines,
        log_output=iteration.raw_output,
    )


def _merge_jsonl(detail: IterationDetail, jsonl_iteration: ParsedJsonlIteration) -> IterationDetail:
    detail.max_iterations = jsonl_iteration.max
    detail.start_timestamp = jsonl_iteration.start
    detail.end_timestamp = jsonl_iteration.end
    detail.duration_seconds = jsonl_iteration.duration_seconds
    detail.tokens_used = jsonl_iteration.tokens
    detail.status = jsonl_iteration.status
    detail.tasks_completed = jsonl_iteration.tasks_completed
    detail.commit = jsonl_iteration.commit
    detail.test_passed = jsonl_iteration.test_passed
    detail.errors = jsonl_iteration.errors or detail.errors
    detail.has_errors = bool(detail.errors) or detail.has_errors
    return detail


def _build_iteration_map(
    log_iterations: list[ParsedLogIteration], jsonl_iterations: list[ParsedJsonlIteration]
) -> dict[int, IterationDetail]:
    merged: dict[int, IterationDetail] = {}

    for log_iteration in log_iterations:
        merged[log_iteration.number] = _from_log_iteration(log_iteration)

    for jsonl_iteration in jsonl_iterations:
        detail = merged.get(jsonl_iteration.iteration)
        if detail is None:
            detail = IterationDetail(number=jsonl_iteration.iteration)
        merged[jsonl_iteration.iteration] = _merge_jsonl(detail, jsonl_iteration)

    return merged


async def list_project_iterations(project_id: str) -> list[IterationSummary]:
    """List merged iteration summaries for a project."""
    project_path = await _resolve_project_path(project_id)
    ralph_dir = project_path / ".ralph"
    log_iterations = parse_ralph_log_file(ralph_dir / "ralph.log")
    jsonl_iterations = parse_iterations_jsonl_file(ralph_dir / "iterations.jsonl")

    merged = _build_iteration_map(log_iterations, jsonl_iterations)
    details = [merged[number] for number in sorted(merged)]
    return [IterationSummary.model_validate(detail.model_dump()) for detail in details]


async def get_project_iteration_detail(
    project_id: str, iteration_number: int
) -> IterationDetail | None:
    """Get merged iteration detail for a specific iteration number."""
    project_path = await _resolve_project_path(project_id)
    ralph_dir = project_path / ".ralph"
    log_iterations = parse_ralph_log_file(ralph_dir / "ralph.log")
    jsonl_iterations = parse_iterations_jsonl_file(ralph_dir / "iterations.jsonl")

    merged = _build_iteration_map(log_iterations, jsonl_iterations)
    return merged.get(iteration_number)
