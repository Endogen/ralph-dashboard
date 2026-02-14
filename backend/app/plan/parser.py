"""Parser for `IMPLEMENTATION_PLAN.md` content."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

PHASE_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$")
TASK_RE = re.compile(r"^(?P<indent>\s*)-\s+\[(?P<done>[xX ])\]\s+(?P<content>.+?)\s*$")
TASK_ID_RE = re.compile(r"^(?P<task_id>\d+(?:\.\d+)*):\s*(?P<description>.+)$")
STATUS_RE = re.compile(r"^STATUS:\s*(?P<status>.+?)\s*$", re.IGNORECASE)


class ParsedPlanTask(BaseModel):
    id: str | None = None
    description: str
    done: bool
    indent: int = 0


class ParsedPlanPhase(BaseModel):
    name: str
    tasks: list[ParsedPlanTask] = Field(default_factory=list)
    done_count: int = 0
    total_count: int = 0
    status: str = "pending"


class ParsedImplementationPlan(BaseModel):
    status: str | None = None
    phases: list[ParsedPlanPhase] = Field(default_factory=list)
    tasks_done: int = 0
    tasks_total: int = 0
    raw: str


def _phase_status(done_count: int, total_count: int) -> str:
    if total_count == 0:
        return "pending"
    if done_count == total_count:
        return "complete"
    if done_count > 0:
        return "in_progress"
    return "pending"


def parse_implementation_plan(content: str) -> ParsedImplementationPlan:
    """Parse implementation plan markdown into structured phase/task data."""
    status: str | None = None
    phases: list[ParsedPlanPhase] = []
    current_phase: ParsedPlanPhase | None = None

    for line in content.splitlines():
        if status is None:
            status_match = STATUS_RE.match(line.strip())
            if status_match:
                status = status_match.group("status").strip()
                continue

        phase_match = PHASE_RE.match(line)
        if phase_match:
            current_phase = ParsedPlanPhase(name=phase_match.group("name").strip())
            phases.append(current_phase)
            continue

        task_match = TASK_RE.match(line)
        if task_match and current_phase is not None:
            content_text = task_match.group("content").strip()
            task_id = None
            description = content_text
            id_match = TASK_ID_RE.match(content_text)
            if id_match:
                task_id = id_match.group("task_id")
                description = id_match.group("description").strip()

            task = ParsedPlanTask(
                id=task_id,
                description=description,
                done=task_match.group("done").lower() == "x",
                indent=len(task_match.group("indent")),
            )
            current_phase.tasks.append(task)

    tasks_total = 0
    tasks_done = 0
    for phase in phases:
        phase.total_count = len(phase.tasks)
        phase.done_count = sum(1 for task in phase.tasks if task.done)
        phase.status = _phase_status(phase.done_count, phase.total_count)
        tasks_total += phase.total_count
        tasks_done += phase.done_count

    return ParsedImplementationPlan(
        status=status,
        phases=phases,
        tasks_done=tasks_done,
        tasks_total=tasks_total,
        raw=content,
    )


def parse_implementation_plan_file(plan_file: Path) -> ParsedImplementationPlan | None:
    """Parse implementation plan file if present."""
    resolved = plan_file.expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        return None
    return parse_implementation_plan(resolved.read_text(encoding="utf-8"))
