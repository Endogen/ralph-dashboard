"""Project status detection utilities."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app.projects.models import ProjectDetail, ProjectStatus, ProjectSummary, project_id_from_path
from app.utils.process import is_process_alive, read_pid

_NOTIFICATION_PREFIX_RE = re.compile(r"^(?P<prefix>[A-Z_]+):")


def _is_running(ralph_dir: Path) -> bool:
    pid_file = ralph_dir / "ralph.pid"
    pid = read_pid(pid_file)
    if pid is None:
        if pid_file.exists() and pid_file.is_file():
            pid_file.unlink(missing_ok=True)
        return False
    if is_process_alive(pid):
        return True

    pid_file.unlink(missing_ok=True)
    return False


def _is_plan_complete(project_path: Path) -> bool:
    plan_file = project_path / "IMPLEMENTATION_PLAN.md"
    if not plan_file.exists() or not plan_file.is_file():
        return False

    # Scan the entire file for the STATUS marker — it may appear after
    # headings, comments, or other content.
    for line in plan_file.read_text(encoding="utf-8").splitlines():
        if line.strip().upper() == "STATUS: COMPLETE":
            return True
    return False


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _read_last_jsonl_payload(path: Path) -> dict[str, object] | None:
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

    for raw_line in reversed(chunk.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _latest_iteration_state(ralph_dir: Path) -> tuple[datetime | None, bool]:
    payload = _read_last_jsonl_payload(ralph_dir / "iterations.jsonl")
    if payload is None:
        return None, False

    status = str(payload.get("status") or "").strip().lower()
    end_timestamp = _parse_timestamp(payload.get("end")) or _parse_timestamp(payload.get("start"))
    errors = payload.get("errors")
    has_errors = isinstance(errors, list) and any(str(item).strip() for item in errors)
    test_failed = payload.get("test_passed") is False
    failed = status == "error" or has_errors or test_failed
    return end_timestamp, failed


def _pending_notification_state(ralph_dir: Path) -> tuple[datetime | None, str | None]:
    path = ralph_dir / "pending-notification.txt"
    if not path.exists() or not path.is_file():
        return None, None

    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None, None
    if not content:
        return None, None

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        match = _NOTIFICATION_PREFIX_RE.match(content)
        prefix = match.group("prefix") if match else None
        return _parse_timestamp(None), prefix

    if not isinstance(payload, dict):
        return None, None

    prefix_value = payload.get("prefix")
    prefix = prefix_value.strip().upper() if isinstance(prefix_value, str) and prefix_value.strip() else None
    return _parse_timestamp(payload.get("timestamp")), prefix


def detect_project_status(project_path: Path) -> ProjectStatus:
    """Determine project status from process, plan, alerts, and latest iteration state."""
    resolved_path = project_path.expanduser().resolve()
    ralph_dir = resolved_path / ".ralph"
    running = _is_running(ralph_dir)

    if running:
        pause_file = ralph_dir / "pause"
        if pause_file.exists():
            return ProjectStatus.paused
        return ProjectStatus.running

    if _is_plan_complete(resolved_path):
        return ProjectStatus.complete

    notification_timestamp, notification_prefix = _pending_notification_state(ralph_dir)
    latest_iteration_timestamp, latest_iteration_failed = _latest_iteration_state(ralph_dir)

    if notification_prefix in {"ERROR", "BLOCKED"}:
        if (
            latest_iteration_timestamp is None
            or notification_timestamp is None
            or latest_iteration_timestamp <= notification_timestamp
        ):
            return ProjectStatus.error

    if latest_iteration_failed:
        return ProjectStatus.error

    return ProjectStatus.stopped


def build_project_summary(project_path: Path) -> ProjectSummary:
    """Build a summary model for a discovered project path."""
    resolved_path = project_path.expanduser().resolve()
    return ProjectSummary(
        id=project_id_from_path(resolved_path),
        name=resolved_path.name,
        path=resolved_path,
        status=detect_project_status(resolved_path),
    )


def build_project_detail(project_path: Path) -> ProjectDetail:
    """Build a detail model for a discovered project path."""
    resolved_path = project_path.expanduser().resolve()
    ralph_dir = resolved_path / ".ralph"
    plan_file = resolved_path / "IMPLEMENTATION_PLAN.md"
    log_file = ralph_dir / "ralph.log"
    return ProjectDetail(
        id=project_id_from_path(resolved_path),
        name=resolved_path.name,
        path=resolved_path,
        status=detect_project_status(resolved_path),
        ralph_dir=ralph_dir,
        plan_file=plan_file if plan_file.exists() else None,
        log_file=log_file if log_file.exists() else None,
    )
