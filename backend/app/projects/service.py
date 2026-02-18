"""Project registration and discovery services."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from app.database import get_setting, set_setting
from app.projects.discovery import discover_project_paths
from app.projects.models import ProjectDetail, ProjectSummary, project_id_from_path
from app.projects.status import build_project_detail, build_project_summary

REGISTERED_PROJECTS_KEY = "registered_project_paths"

# TTL cache for discovered paths to avoid repeated os.walk on every request
_discovered_paths_cache: list[Path] | None = None
_discovered_paths_timestamp: float = 0.0
_DISCOVERY_CACHE_TTL_SECONDS = 10.0


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
    """Discover projects from configured roots and manual registrations.

    Results are cached for up to ``_DISCOVERY_CACHE_TTL_SECONDS`` to avoid
    repeated expensive ``os.walk`` calls on every request.
    """
    global _discovered_paths_cache, _discovered_paths_timestamp

    now = time.monotonic()
    if (
        _discovered_paths_cache is not None
        and (now - _discovered_paths_timestamp) < _DISCOVERY_CACHE_TTL_SECONDS
    ):
        return _discovered_paths_cache

    # os.walk is blocking — run in thread pool
    discovered = await asyncio.to_thread(discover_project_paths)
    registered = await get_registered_project_paths()
    result = _normalize_paths([*discovered, *registered])

    _discovered_paths_cache = result
    _discovered_paths_timestamp = now
    return result


def invalidate_discovery_cache() -> None:
    """Force the next ``discover_all_project_paths`` call to re-scan."""
    global _discovered_paths_cache, _discovered_paths_timestamp
    _discovered_paths_cache = None
    _discovered_paths_timestamp = 0.0


async def list_projects() -> list[ProjectSummary]:
    """Return project summaries across discovered and registered projects."""
    paths = await discover_all_project_paths()
    # build_project_summary reads PID files and plan files (blocking I/O)
    return await asyncio.to_thread(
        lambda: [build_project_summary(path) for path in paths]
    )


async def get_project_detail(project_id: str) -> ProjectDetail | None:
    """Return a single project detail model by project id."""
    paths = await discover_all_project_paths()

    def _find_detail() -> ProjectDetail | None:
        for path in paths:
            detail = build_project_detail(path)
            if detail.id == project_id:
                return detail
        return None

    return await asyncio.to_thread(_find_detail)
