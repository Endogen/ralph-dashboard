"""Project domain models."""

from __future__ import annotations

import hashlib
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


class ProjectDetail(ProjectSummary):
    ralph_dir: Path
    plan_file: Path | None = None
    log_file: Path | None = None


def project_id_from_path(project_path: Path) -> str:
    """Build a stable, collision-resistant project identifier from the full path.

    Produces ``<slug>-<hash6>`` where the slug comes from the directory name
    and the hash is derived from the *full resolved path*.  This prevents
    collisions when identically-named directories exist under different
    project roots (e.g. ``/projects/my-app`` vs ``/other/my-app``).
    """
    resolved = str(project_path.resolve())
    slug = project_path.name.lower().replace("_", "-").strip()
    slug = _NON_SLUG_CHARS.sub("-", slug).strip("-") or "project"
    path_hash = hashlib.sha256(resolved.encode()).hexdigest()[:6]
    return f"{slug}-{path_hash}"
