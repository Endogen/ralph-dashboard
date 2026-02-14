"""Project stats aggregation service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.iterations.models import IterationSummary
from app.iterations.service import list_project_iterations
from app.plan.service import get_project_plan
from app.stats.models import HealthBreakdown, PhaseTokenUsage, ProjectStats, VelocityStats

DEFAULT_COST_PER_1K_TOKENS = 0.006


def _cost_from_tokens(tokens: float, cost_per_1k_tokens: float) -> float:
    return (tokens / 1000.0) * cost_per_1k_tokens


def _build_task_phase_map(plan) -> dict[str, str]:
    task_phase_map: dict[str, str] = {}
    for phase in plan.phases:
        for task in phase.tasks:
            if task.id:
                task_phase_map[task.id] = phase.name
    return task_phase_map


def _phase_token_usage(
    iterations: list[IterationSummary], task_phase_map: dict[str, str]
) -> list[PhaseTokenUsage]:
    buckets: dict[str, float] = {}
    for iteration in iterations:
        if not iteration.tasks_completed or iteration.tokens_used is None:
            continue
        share = iteration.tokens_used / len(iteration.tasks_completed)
        for task_id in iteration.tasks_completed:
            phase_name = task_phase_map.get(task_id, "Unmapped")
            buckets[phase_name] = buckets.get(phase_name, 0.0) + share

    return [
        PhaseTokenUsage(phase=phase, tokens=round(tokens, 3))
        for phase, tokens in sorted(buckets.items(), key=lambda item: item[0])
    ]


def _health_breakdown(iterations: list[IterationSummary]) -> HealthBreakdown:
    productive = 0
    partial = 0
    failed = 0
    for iteration in iterations:
        if iteration.has_errors or iteration.status == "error":
            failed += 1
        elif iteration.tasks_completed:
            productive += 1
        else:
            partial += 1
    return HealthBreakdown(productive=productive, partial=partial, failed=failed)


async def aggregate_project_stats(project_id: str) -> ProjectStats:
    """Aggregate project stats from iteration and plan data."""
    iterations = await list_project_iterations(project_id)
    plan = await get_project_plan(project_id)

    total_iterations = len(iterations)
    total_tokens = float(sum(item.tokens_used or 0.0 for item in iterations))
    total_duration_seconds = float(sum(item.duration_seconds or 0.0 for item in iterations))
    total_cost_usd = _cost_from_tokens(total_tokens, DEFAULT_COST_PER_1K_TOKENS)

    avg_duration = total_duration_seconds / total_iterations if total_iterations else 0.0
    avg_tokens = total_tokens / total_iterations if total_iterations else 0.0

    tasks_done = plan.tasks_done
    tasks_total = plan.tasks_total
    tasks_remaining = max(tasks_total - tasks_done, 0)

    total_hours = total_duration_seconds / 3600 if total_duration_seconds > 0 else 0.0
    tasks_per_hour = (tasks_done / total_hours) if total_hours > 0 and tasks_done > 0 else 0.0
    hours_remaining = (tasks_remaining / tasks_per_hour) if tasks_per_hour > 0 else 0.0

    projected_completion = None
    if hours_remaining > 0:
        projected_completion = (datetime.now(tz=UTC) + timedelta(hours=hours_remaining)).isoformat()
    elif tasks_remaining == 0:
        projected_completion = datetime.now(tz=UTC).isoformat()

    remaining_tokens_projection = (
        (total_tokens / tasks_done) * tasks_remaining
        if tasks_done > 0 and tasks_remaining > 0
        else 0.0
    )
    projected_total_cost_usd = total_cost_usd + _cost_from_tokens(
        remaining_tokens_projection, DEFAULT_COST_PER_1K_TOKENS
    )

    task_phase_map = _build_task_phase_map(plan)
    return ProjectStats(
        total_iterations=total_iterations,
        total_tokens=round(total_tokens, 3),
        total_cost_usd=round(total_cost_usd, 4),
        total_duration_seconds=round(total_duration_seconds, 3),
        avg_iteration_duration_seconds=round(avg_duration, 3),
        avg_tokens_per_iteration=round(avg_tokens, 3),
        tasks_done=tasks_done,
        tasks_total=tasks_total,
        errors_count=sum(1 for item in iterations if item.has_errors or item.status == "error"),
        projected_completion=projected_completion,
        projected_total_cost_usd=round(projected_total_cost_usd, 4),
        velocity=VelocityStats(
            tasks_per_hour=round(tasks_per_hour, 3),
            tasks_remaining=tasks_remaining,
            hours_remaining=round(hours_remaining, 3),
        ),
        health_breakdown=_health_breakdown(iterations),
        tokens_by_phase=_phase_token_usage(iterations, task_phase_map),
    )
