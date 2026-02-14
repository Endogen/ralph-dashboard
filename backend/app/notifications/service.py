"""Notification history service."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app.notifications.models import NotificationEntry
from app.projects.service import get_project_detail

MESSAGE_PREFIX_RE = re.compile(r"^(?P<prefix>[A-Z_]+):\s*(?P<body>.+)$")


class NotificationsServiceError(Exception):
    """Base notification service error."""


class NotificationsProjectNotFoundError(NotificationsServiceError):
    """Raised when project id cannot be resolved."""


async def _resolve_ralph_dir(project_id: str) -> Path:
    project = await get_project_detail(project_id)
    if project is None:
        raise NotificationsProjectNotFoundError(f"Project not found: {project_id}")
    return project.path / ".ralph"


def _fallback_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _parse_message(raw_message: str) -> tuple[str | None, str]:
    message = raw_message.strip()
    match = MESSAGE_PREFIX_RE.match(message)
    if match:
        return match.group("prefix"), match.group("body")
    return None, message


def _parse_notification_file(path: Path) -> NotificationEntry | None:
    if not path.exists() or not path.is_file():
        return None
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return None

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        prefix, message = _parse_message(content)
        return NotificationEntry(
            timestamp=_fallback_timestamp(path),
            prefix=prefix,
            message=message,
            status="unknown",
            source=path.name,
        )

    raw_message = str(payload.get("message", "")).strip()
    prefix, message = _parse_message(raw_message)
    timestamp = str(payload.get("timestamp") or _fallback_timestamp(path))
    status = payload.get("status")
    iteration = payload.get("iteration")
    details = payload.get("details")

    return NotificationEntry(
        timestamp=timestamp,
        prefix=prefix,
        message=message,
        status=str(status) if status is not None else None,
        iteration=int(iteration) if isinstance(iteration, int) else None,
        details=str(details) if details is not None else None,
        source=path.name,
    )


def _iter_archive_candidates(ralph_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for archive_dir in (ralph_dir / "notifications", ralph_dir / "archive" / "notifications"):
        if not archive_dir.exists() or not archive_dir.is_dir():
            continue
        candidates.extend(sorted(archive_dir.glob("*.txt")))
        candidates.extend(sorted(archive_dir.glob("*.json")))
    return candidates


async def get_notification_history(project_id: str) -> list[NotificationEntry]:
    """Return pending + last + archived notifications for a project."""
    ralph_dir = await _resolve_ralph_dir(project_id)

    seen_keys: set[tuple[str, str, str | None]] = set()
    entries: list[NotificationEntry] = []

    primary_files = [
        ralph_dir / "pending-notification.txt",
        ralph_dir / "last-notification.txt",
    ]
    archive_files = _iter_archive_candidates(ralph_dir)

    for path in [*primary_files, *archive_files]:
        entry = _parse_notification_file(path)
        if entry is None:
            continue
        key = (entry.timestamp, entry.message, entry.source)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(entry)

    entries.sort(key=lambda item: item.timestamp, reverse=True)
    return entries
