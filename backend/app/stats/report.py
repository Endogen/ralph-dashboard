"""Markdown report generation for project runs."""

from __future__ import annotations

from datetime import UTC, datetime

from app.control.process_manager import read_project_config
from app.iterations.service import list_project_iterations
from app.plan.service import get_project_plan
from app.projects.service import get_project_detail
from app.stats.service import aggregate_project_stats


class ReportServiceError(Exception):
    """Base report service error."""


class ReportProjectNotFoundError(ReportServiceError):
    """Raised when project id cannot be resolved."""


async def generate_project_report(project_id: str) -> str:
    """Generate a markdown report for a project."""
    project = await get_project_detail(project_id)
    if project is None:
        raise ReportProjectNotFoundError(f"Project not found: {project_id}")

    stats = await aggregate_project_stats(project_id)
    plan = await get_project_plan(project_id)
    iterations = await list_project_iterations(project_id)
    config = await read_project_config(project_id)

    now = datetime.now(tz=UTC).isoformat()
    duration_display = f"{int(stats.total_duration_seconds)}s"

    lines: list[str] = [
        f"# Project Report: {project.name}",
        "",
        f"**Generated:** {now}",
        f"**Status:** {project.status}",
        f"**Duration:** {duration_display}",
        "",
        "## Summary",
        f"- **Iterations:** {stats.total_iterations}",
        f"- **Tasks:** {stats.tasks_done} / {stats.tasks_total}",
        f"- **Total Tokens:** {stats.total_tokens}",
        f"- **Estimated Cost:** ${stats.total_cost_usd}",
        f"- **Velocity:** {stats.velocity.tasks_per_hour} tasks/hour",
        "",
        "## Phase Breakdown",
        "| Phase | Tasks Done | Tasks Total | Status |",
        "|---|---:|---:|---|",
    ]

    for phase in plan.phases:
        lines.append(
            f"| {phase.name} | {phase.done_count} | {phase.total_count} | {phase.status} |"
        )

    lines.extend(
        [
            "",
            "## Iteration Log",
            "| # | Duration (s) | Tokens | Status | Tasks Completed |",
            "|---:|---:|---:|---|---|",
        ]
    )
    for iteration in iterations:
        tasks = ", ".join(iteration.tasks_completed) if iteration.tasks_completed else "-"
        duration = (
            f"{iteration.duration_seconds:.0f}" if iteration.duration_seconds is not None else "-"
        )
        tokens = f"{iteration.tokens_used:.3f}" if iteration.tokens_used is not None else "-"
        lines.append(
            f"| {iteration.number} | {duration} | {tokens} | {iteration.status or '-'} | {tasks} |"
        )

    lines.extend(["", "## Errors"])
    errors_found = False
    for iteration in iterations:
        if iteration.has_errors and iteration.errors:
            errors_found = True
            lines.append(f"- Iteration {iteration.number}: {', '.join(iteration.errors)}")
    if not errors_found:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Configuration",
            f"- CLI: {config.cli}",
            f"- Flags: {config.flags or 'N/A'}",
            f"- Test Command: {config.test_command or 'N/A'}",
        ]
    )

    return "\n".join(lines) + "\n"
