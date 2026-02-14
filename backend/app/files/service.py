"""Services for project text-file read/write operations."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.projects.service import get_project_detail

AllowedProjectFile = Literal["agents", "prompt"]
FILE_NAME_MAP: dict[AllowedProjectFile, str] = {
    "agents": "AGENTS.md",
    "prompt": "PROMPT.md",
}


class FilesServiceError(Exception):
    """Base file service error."""


class FilesProjectNotFoundError(FilesServiceError):
    """Raised when project id cannot be resolved."""


class FilesTargetNotFoundError(FilesServiceError):
    """Raised when requested project file does not exist."""


async def _resolve_project_path(project_id: str) -> Path:
    project = await get_project_detail(project_id)
    if project is None:
        raise FilesProjectNotFoundError(f"Project not found: {project_id}")
    return project.path


async def read_project_file(project_id: str, file_key: AllowedProjectFile) -> tuple[str, str]:
    """Read AGENTS.md or PROMPT.md content for a project."""
    project_path = await _resolve_project_path(project_id)
    filename = FILE_NAME_MAP[file_key]
    target = project_path / filename
    if not target.exists() or not target.is_file():
        raise FilesTargetNotFoundError(f"File not found: {filename}")
    return filename, target.read_text(encoding="utf-8")


async def write_project_file(
    project_id: str, file_key: AllowedProjectFile, content: str
) -> tuple[str, str]:
    """Write AGENTS.md or PROMPT.md content for a project."""
    project_path = await _resolve_project_path(project_id)
    filename = FILE_NAME_MAP[file_key]
    target = project_path / filename
    target.write_text(content, encoding="utf-8")
    return filename, content
