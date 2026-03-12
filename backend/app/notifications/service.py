"""Notification history service."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app.notifications.models import NotificationEntry
from app.projects.service import get_project_detail

MESSAGE_PREFIX_RE = re.compile(r"^(?P<prefix>[A-Z_]+):\s*(?P<body>.+)$")
PREFIX_KIND_MAP = {
    "ERROR": "error",
    "BLOCKED": "blocked",
    "DECISION": "decision",
    "PROGRESS": "progress",
    "DONE": "done",
    "PLANNING_COMPLETE": "planning_complete",
}
PREFIX_SEVERITY_MAP = {
    "ERROR": "error",
    "BLOCKED": "error",
    "DECISION": "info",
    "PROGRESS": "info",
    "DONE": "success",
    "PLANNING_COMPLETE": "info",
}


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


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _coerce_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def _normalize_prefix(value: object, fallback: str | None) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip().upper()
    return fallback


def _notification_kind(prefix: str | None) -> str:
    if prefix is None:
        return "notification"
    return PREFIX_KIND_MAP.get(prefix, prefix.lower())


def _notification_severity(prefix: str | None) -> str:
    if prefix is None:
        return "info"
    return PREFIX_SEVERITY_MAP.get(prefix, "info")


def _fallback_event_id(
    timestamp: str,
    prefix: str | None,
    message: str,
    iteration: int | None,
    details: str | None,
) -> str:
    fingerprint = json.dumps(
        {
            "timestamp": timestamp,
            "prefix": prefix,
            "message": message,
            "iteration": iteration,
            "details": details,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]
    return f"notif-{digest}"


def _entry_from_payload(
    payload: dict[str, object],
    source: str,
    fallback_timestamp: str,
    *,
    default_active: bool,
) -> NotificationEntry:
    raw_message = str(payload.get("message", "")).strip()
    parsed_prefix, message = _parse_message(raw_message)
    prefix = _normalize_prefix(payload.get("prefix"), parsed_prefix)
    timestamp = str(payload.get("timestamp") or fallback_timestamp)
    status = payload.get("status")
    iteration = payload.get("iteration")
    details = payload.get("details")
    event_id = payload.get("event_id")
    kind = payload.get("kind")
    severity = payload.get("severity")
    active = payload.get("active")
    resolved_iteration = _coerce_int(iteration)
    resolved_details = str(details) if details is not None else None
    resolved_event_id = (
        event_id.strip()
        if isinstance(event_id, str) and event_id.strip()
        else _fallback_event_id(timestamp, prefix, message, resolved_iteration, resolved_details)
    )
    resolved_kind = (
        kind.strip().lower()
        if isinstance(kind, str) and kind.strip()
        else _notification_kind(prefix)
    )
    resolved_severity = (
        severity.strip().lower()
        if isinstance(severity, str) and severity.strip()
        else _notification_severity(prefix)
    )
    resolved_active = _coerce_bool(active)
    if resolved_active is None:
        resolved_active = default_active

    return NotificationEntry(
        event_id=resolved_event_id,
        timestamp=timestamp,
        prefix=prefix,
        kind=resolved_kind,
        severity=resolved_severity,
        active=resolved_active,
        message=message,
        status=str(status) if status is not None else None,
        iteration=resolved_iteration,
        details=resolved_details,
        source=source,
    )


def notification_entry_key(entry: NotificationEntry) -> str:
    return entry.event_id


def _entry_to_payload(entry: NotificationEntry) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_id": entry.event_id,
        "timestamp": entry.timestamp,
        "kind": entry.kind,
        "severity": entry.severity,
        "active": entry.active,
        "message": entry.message,
    }
    if entry.prefix is not None:
        payload["prefix"] = entry.prefix
    if entry.status is not None:
        payload["status"] = entry.status
    if entry.iteration is not None:
        payload["iteration"] = entry.iteration
    if entry.details is not None:
        payload["details"] = entry.details
    if entry.source is not None:
        payload["source"] = entry.source
    return payload


def parse_notification_file(path: Path) -> NotificationEntry | None:
    if not path.exists() or not path.is_file():
        return None
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return None

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        prefix, message = _parse_message(content)
        timestamp = _fallback_timestamp(path)
        return NotificationEntry(
            event_id=_fallback_event_id(timestamp, prefix, message, None, None),
            timestamp=timestamp,
            prefix=prefix,
            kind=_notification_kind(prefix),
            severity=_notification_severity(prefix),
            active=path.name == "pending-notification.txt",
            message=message,
            status="unknown",
            source=path.name,
        )

    if not isinstance(payload, dict):
        return None
    return _entry_from_payload(
        payload,
        path.name,
        _fallback_timestamp(path),
        default_active=path.name == "pending-notification.txt",
    )


def parse_notification_jsonl(path: Path) -> list[NotificationEntry]:
    if not path.exists() or not path.is_file():
        return []

    entries: list[NotificationEntry] = []
    fallback_timestamp = _fallback_timestamp(path)
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        entries.append(
            _entry_from_payload(
                payload,
                path.name,
                fallback_timestamp,
                default_active=False,
            )
        )
    return entries


def _read_last_notification_jsonl_entry(path: Path) -> NotificationEntry | None:
    if not path.exists() or not path.is_file():
        return None

    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            if size == 0:
                return None
            read_size = min(4096, size)
            handle.seek(size - read_size)
            chunk = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return None

    fallback_timestamp = _fallback_timestamp(path)
    for raw_line in reversed(chunk.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        return _entry_from_payload(
            payload,
            path.name,
            fallback_timestamp,
            default_active=False,
        )
    return None


def append_notification_history_entry(ralph_dir: Path, entry: NotificationEntry) -> bool:
    history_file = ralph_dir / "notifications" / "events.jsonl"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_entry = entry.model_copy(update={"active": False})

    last_entry = _read_last_notification_jsonl_entry(history_file)
    if last_entry is not None and notification_entry_key(last_entry) == notification_entry_key(history_entry):
        return False

    payload = _entry_to_payload(history_entry)
    with history_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
    return True


def _iter_archive_candidates(ralph_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for archive_dir in (ralph_dir / "notifications", ralph_dir / "archive" / "notifications"):
        if not archive_dir.exists() or not archive_dir.is_dir():
            continue
        candidates.extend(sorted(archive_dir.glob("*.txt")))
        candidates.extend(sorted(archive_dir.glob("*.json")))
    return candidates


async def get_notification_history(project_id: str) -> list[NotificationEntry]:
    """Return notification history plus any active pending notification."""
    ralph_dir = await _resolve_ralph_dir(project_id)

    seen_keys: set[str] = set()
    entries: list[NotificationEntry] = []

    pending_file = ralph_dir / "pending-notification.txt"
    archive_files = _iter_archive_candidates(ralph_dir)
    history_files = [
        ralph_dir / "notifications" / "events.jsonl",
    ]

    def append_entry(entry: NotificationEntry) -> None:
        key = notification_entry_key(entry)
        if key in seen_keys:
            return
        seen_keys.add(key)
        entries.append(entry)

    pending_entry = parse_notification_file(pending_file)
    if pending_entry is not None:
        append_entry(pending_entry)

    for path in history_files:
        for entry in parse_notification_jsonl(path):
            append_entry(entry)

    for path in archive_files:
        entry = parse_notification_file(path)
        if entry is not None:
            append_entry(entry)

    entries.sort(key=lambda item: item.timestamp, reverse=True)
    return entries
