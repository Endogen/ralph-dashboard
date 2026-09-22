"""Project archiving service.

Archives are stored as a JSON list of project IDs in app_settings.
Auto-archive settings are also stored in app_settings.
"""

from __future__ import annotations

import json
import logging
import time

from app.database import get_setting, update_setting

ARCHIVED_PROJECTS_KEY = "archived_project_ids"
ARCHIVE_SETTINGS_KEY = "archive_settings"

LOGGER = logging.getLogger(__name__)

# Default: auto-archive after 30 days of inactivity, disabled by default
DEFAULT_ARCHIVE_SETTINGS: dict = {
    "auto_archive_enabled": False,
    "auto_archive_after_days": 30,
}


def _parse_archived_project_ids(raw: str | None) -> set[str]:
    if raw is None:
        return set()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if not isinstance(parsed, list):
        return set()
    return {item for item in parsed if isinstance(item, str)}


async def get_archived_project_ids() -> set[str]:
    """Return the set of archived project IDs."""
    return _parse_archived_project_ids(await get_setting(ARCHIVED_PROJECTS_KEY))


async def archive_project(project_id: str) -> bool:
    """Archive a project by ID. Returns True if newly archived."""
    previous, _ = await update_setting(
        ARCHIVED_PROJECTS_KEY,
        lambda raw: json.dumps(sorted(_parse_archived_project_ids(raw) | {project_id})),
    )
    changed = project_id not in _parse_archived_project_ids(previous)
    if changed:
        LOGGER.info("Archived project: %s", project_id)
    return changed


async def unarchive_project(project_id: str) -> bool:
    """Unarchive a project by ID. Returns True if was archived."""
    previous, _ = await update_setting(
        ARCHIVED_PROJECTS_KEY,
        lambda raw: json.dumps(sorted(_parse_archived_project_ids(raw) - {project_id})),
    )
    changed = project_id in _parse_archived_project_ids(previous)
    if changed:
        LOGGER.info("Unarchived project: %s", project_id)
    return changed


def _parse_archive_settings(raw: str | None) -> dict:
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


async def get_archive_settings() -> dict:
    """Return current archive settings."""
    return _parse_archive_settings(await get_setting(ARCHIVE_SETTINGS_KEY))


async def save_archive_settings(settings: dict) -> dict:
    """Atomically apply a settings patch. Returns the merged settings."""
    _, stored = await update_setting(
        ARCHIVE_SETTINGS_KEY,
        lambda raw: json.dumps({**_parse_archive_settings(raw), **settings}),
    )
    return _parse_archive_settings(stored)


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
        # Unknown activity is never evidence of inactivity.
        if last_ts is not None and last_ts < threshold:
            if not await archive_project(project_id):
                continue
            newly_archived.append(project_id)
            LOGGER.info(
                "Auto-archived project %s (last activity: %s, threshold: %s days)",
                project_id,
                last_ts,
                days,
            )

    return newly_archived
