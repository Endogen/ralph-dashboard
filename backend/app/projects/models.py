"""Project domain models."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9-]+")


class ProjectStatus(StrEnum):
    running = "running"
    paused = "paused"
    stopped = "stopped"
    complete = "complete"


class ProjectSummary(BaseModel):
    id: str
    name: str
    path: Path
    status: ProjectStatus


def project_id_from_path(project_path: Path) -> str:
    """Build a stable slug-like project identifier from directory name."""
    slug = project_path.name.lower().replace("_", "-").strip()
    slug = _NON_SLUG_CHARS.sub("-", slug).strip("-")
    return slug or "project"
