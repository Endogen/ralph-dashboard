"""Tests for notification route handlers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.notifications.router import get_notifications


def _seed_project(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    project = workspace / "notify-project"
    ralph_dir = project / ".ralph"
    archive_dir = ralph_dir / "notifications"

    archive_dir.mkdir(parents=True)
    (ralph_dir / "pending-notification.txt").write_text(
        '{"timestamp":"2026-01-01T01:00:00Z","message":"ERROR: Pending failure","status":"pending"}',
        encoding="utf-8",
    )
    (ralph_dir / "last-notification.txt").write_text(
        '{"timestamp":"2026-01-01T00:30:00Z","message":"PROGRESS: Last status","status":"delivered"}',
        encoding="utf-8",
    )
    (archive_dir / "2025-12-31.txt").write_text(
        '{"timestamp":"2025-12-31T23:00:00Z","message":"DONE: Archived message","status":"archived"}',
        encoding="utf-8",
    )
    return workspace


@pytest.mark.anyio
async def test_get_notifications_handler(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = _seed_project(tmp_path)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    notifications = await get_notifications("notify-project")
    assert len(notifications) == 3
    assert notifications[0].prefix == "ERROR"
    assert notifications[0].message == "Pending failure"
    assert notifications[1].prefix == "PROGRESS"
    assert notifications[2].prefix == "DONE"


@pytest.mark.anyio
async def test_get_notifications_handler_missing_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        await get_notifications("missing")

    assert exc_info.value.status_code == 404
