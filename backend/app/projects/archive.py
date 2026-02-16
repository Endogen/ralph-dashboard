"""Project archiving service.

Archives are stored as a JSON list of project IDs in app_settings.
Auto-archive settings are also stored in app_settings.
"""

from __future__ import annotations

import json
import logging
import time

from app.database import get_setting, set_setting

ARCHIVED_PROJECTS_KEY = "archived_project_ids"
ARCHIVE_SETTINGS_KEY = "archive_settings"

LOGGER = logging.getLogger(__name__)

# Default: auto-archive after 30 days of inactivity, disabled by default
DEFAULT_ARCHIVE_SETTINGS: dict = {
    "auto_archive_enabled": False,
    "auto_archive_after_days": 30,
}


async def get_archived_project_ids() -> set[str]:
    """Return the set of archived project IDs."""
    raw = await get_setting(ARCHIVED_PROJECTS_KEY)
    if raw is None:
        return set()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if not isinstance(parsed, list):
        return set()
    return {item for item in parsed if isinstance(item, str)}


async def _save_archived_project_ids(ids: set[str]) -> None:
    await set_setting(ARCHIVED_PROJECTS_KEY, json.dumps(sorted(ids)))


async def archive_project(project_id: str) -> bool:
    """Archive a project by ID. Returns True if newly archived."""
    ids = await get_archived_project_ids()
    if project_id in ids:
        return False
    ids.add(project_id)
    await _save_archived_project_ids(ids)
    LOGGER.info("Archived project: %s", project_id)
    return True


async def unarchive_project(project_id: str) -> bool:
    """Unarchive a project by ID. Returns True if was archived."""
    ids = await get_archived_project_ids()
    if project_id not in ids:
        return False
    ids.discard(project_id)
    await _save_archived_project_ids(ids)
    LOGGER.info("Unarchived project: %s", project_id)
    return True


async def get_archive_settings() -> dict:
    """Return current archive settings."""
    raw = await get_setting(ARCHIVE_SETTINGS_KEY)
    if raw is None:
        return dict(DEFAULT_ARCHIVE_SETTINGS)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return dict(DEFAULT_ARCHIVE_SETTINGS)
    if not isinstance(parsed, dict):
        return dict(DEFAULT_ARCHIVE_SETTINGS)
    # Merge with defaults so new keys are always present
    merged = dict(DEFAULT_ARCHIVE_SETTINGS)
    merged.update(parsed)
    return merged


async def save_archive_settings(settings: dict) -> dict:
    """Save archive settings. Returns the merged settings."""
    current = await get_archive_settings()
    current.update(settings)
    await set_setting(ARCHIVE_SETTINGS_KEY, json.dumps(current))
    return current


async def auto_archive_check(
    project_last_activity: dict[str, float | None],
) -> list[str]:
    """Check projects for auto-archiving based on last activity timestamps.

    Args:
        project_last_activity: mapping of project_id -> last activity unix timestamp (or None)

    Returns:
        List of project IDs that were newly auto-archived.
    """
    settings = await get_archive_settings()
    if not settings.get("auto_archive_enabled", False):
        return []

    days = settings.get("auto_archive_after_days", 30)
    threshold = time.time() - (days * 86400)
    already_archived = await get_archived_project_ids()

    newly_archived: list[str] = []
    for project_id, last_ts in project_last_activity.items():
        if project_id in already_archived:
            continue
        # No activity at all or activity older than threshold
        if last_ts is None or last_ts < threshold:
            await archive_project(project_id)
            newly_archived.append(project_id)
            LOGGER.info(
                "Auto-archived project %s (last activity: %s, threshold: %s days)",
                project_id,
                last_ts,
                days,
            )

    return newly_archived
