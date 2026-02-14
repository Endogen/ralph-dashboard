"""Project registration and discovery services."""

from __future__ import annotations

import json
from pathlib import Path

from app.database import get_setting, set_setting
from app.projects.discovery import discover_project_paths
from app.projects.models import project_id_from_path

REGISTERED_PROJECTS_KEY = "registered_project_paths"


class ProjectRegistrationError(Exception):
    """Raised when project registration or unregistration is invalid."""


def _normalize_paths(paths: list[Path]) -> list[Path]:
    unique: set[Path] = set()
    for path in paths:
        unique.add(path.expanduser().resolve())
    return sorted(unique)


def _validate_project_directory(project_path: Path) -> Path:
    resolved = project_path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ProjectRegistrationError("Project path does not exist or is not a directory")
    if not (resolved / ".ralph").is_dir():
        raise ProjectRegistrationError("Project path must contain a .ralph directory")
    return resolved


async def get_registered_project_paths() -> list[Path]:
    """Return manually registered project paths from persistent settings storage."""
    raw = await get_setting(REGISTERED_PROJECTS_KEY)
    if raw is None:
        return []

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    paths: list[Path] = []
    for item in parsed:
        if isinstance(item, str):
            paths.append(Path(item))
    return _normalize_paths(paths)


async def _save_registered_project_paths(paths: list[Path]) -> None:
    normalized = _normalize_paths(paths)
    serialized = json.dumps([str(path) for path in normalized])
    await set_setting(REGISTERED_PROJECTS_KEY, serialized)


async def register_project_path(project_path: Path) -> Path:
    """Persist a project path for explicit tracking."""
    resolved = _validate_project_directory(project_path)
    existing = await get_registered_project_paths()
    if resolved in existing:
        return resolved

    await _save_registered_project_paths([*existing, resolved])
    return resolved


async def unregister_project_by_id(project_id: str) -> bool:
    """Remove a registered project path by computed project id."""
    existing = await get_registered_project_paths()
    remaining = [path for path in existing if project_id_from_path(path) != project_id]
    removed = len(remaining) != len(existing)
    if removed:
        await _save_registered_project_paths(remaining)
    return removed


async def discover_all_project_paths() -> list[Path]:
    """Discover projects from configured roots and manual registrations."""
    discovered = discover_project_paths()
    registered = await get_registered_project_paths()
    return _normalize_paths([*discovered, *registered])
