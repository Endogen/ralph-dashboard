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
    """Build iteration map from log and JSONL entries.

    JSONL is the canonical source — each line is one iteration in chronological
    order.  We use 1-based row order as the iteration number to avoid collisions
    from older loops that restarted the counter at 1.  If the JSONL iteration
    field is already unique and monotonically increasing (i.e. no duplicates),
    we honour it as-is so that the dashboard matches the log output.
    """
    merged: dict[int, IterationDetail] = {}

    for log_iteration in log_iterations:
        merged[log_iteration.number] = _from_log_iteration(log_iteration)

    if jsonl_iterations:
        # Detect whether the JSONL iteration numbers are unique
        seen_numbers: set[int] = set()
        has_duplicates = False
        for entry in jsonl_iterations:
            if entry.iteration in seen_numbers:
                has_duplicates = True
                break
            seen_numbers.add(entry.iteration)

        for row_index, jsonl_iteration in enumerate(jsonl_iterations, 1):
            # Use row order when there are duplicates, otherwise honour the field
            number = row_index if has_duplicates else jsonl_iteration.iteration
            detail = merged.get(number)
            if detail is None:
                detail = IterationDetail(number=number)
            merged[number] = _merge_jsonl(detail, jsonl_iteration)

    return merged


MAX_LOG_PARSE_BYTES = 20 * 1024 * 1024  # Only parse log files under 20 MB


def _safe_parse_log(log_file: Path) -> list[ParsedLogIteration]:
    """Parse log file only if it's small enough to avoid memory issues."""
    if not log_file.exists():
        return []
    try:
        if log_file.stat().st_size > MAX_LOG_PARSE_BYTES:
            return []
    except OSError:
        return []
    return parse_ralph_log_file(log_file)


async def list_project_iterations(project_id: str) -> list[IterationSummary]:
    """List merged iteration summaries for a project."""
    project_path = await _resolve_project_path(project_id)
    ralph_dir = project_path / ".ralph"
    jsonl_iterations = parse_iterations_jsonl_file(ralph_dir / "iterations.jsonl")

    # Prefer jsonl data; only parse log if jsonl is empty and log is small
    log_iterations = _safe_parse_log(ralph_dir / "ralph.log") if not jsonl_iterations else []

    merged = _build_iteration_map(log_iterations, jsonl_iterations)
    details = [merged[number] for number in sorted(merged)]
    return [IterationSummary.model_validate(detail.model_dump()) for detail in details]


async def get_project_iteration_detail(
    project_id: str, iteration_number: int
) -> IterationDetail | None:
    """Get merged iteration detail for a specific iteration number."""
    project_path = await _resolve_project_path(project_id)
    ralph_dir = project_path / ".ralph"
    jsonl_iterations = parse_iterations_jsonl_file(ralph_dir / "iterations.jsonl")

    # Always parse log for detail view to get raw_output
    log_iterations = _safe_parse_log(ralph_dir / "ralph.log")

    merged = _build_iteration_map(log_iterations, jsonl_iterations)
    return merged.get(iteration_number)
