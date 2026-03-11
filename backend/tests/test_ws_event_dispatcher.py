"""Tests for websocket watcher event dispatching behavior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.ws import event_dispatcher
from app.ws.file_watcher import FileChangeEvent


class CapturingHub:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def emit(self, event_type: str, project: str, data: dict[str, Any]) -> None:
        self.events.append({"type": event_type, "project": project, "data": data})


def make_log_change(tmp_path: Path) -> tuple[Path, FileChangeEvent]:
    project_path = tmp_path / "demo-project"
    log_path = project_path / ".ralph" / "ralph.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    return project_path, FileChangeEvent(
        project_id="demo-project",
        project_path=project_path,
        path=log_path,
        event_type="modified",
    )


@pytest.mark.anyio
async def test_log_append_emits_only_new_complete_lines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, change = make_log_change(tmp_path)
    change.path.write_text("alpha\nbeta", encoding="utf-8")

    fake_hub = CapturingHub()
    monkeypatch.setattr(event_dispatcher, "hub", fake_hub)
    dispatcher = event_dispatcher.WatcherEventDispatcher()

    await dispatcher.handle_change(change)

    log_events = [event for event in fake_hub.events if event["type"] == "log_append"]
    assert log_events == [
        {
            "type": "log_append",
            "project": "demo-project",
            "data": {"lines": "alpha\n"},
        }
    ]

    with change.path.open("a", encoding="utf-8") as handle:
        handle.write("\ncharlie\n")
    await dispatcher.handle_change(change)
    await dispatcher.handle_change(change)

    log_events = [event for event in fake_hub.events if event["type"] == "log_append"]
    assert len(log_events) == 2
    assert log_events[1]["data"]["lines"] == "beta\ncharlie\n"


@pytest.mark.anyio
async def test_log_append_resets_offset_after_log_truncate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, change = make_log_change(tmp_path)

    fake_hub = CapturingHub()
    monkeypatch.setattr(event_dispatcher, "hub", fake_hub)
    dispatcher = event_dispatcher.WatcherEventDispatcher()

    change.path.write_text("one\n", encoding="utf-8")
    await dispatcher.handle_change(change)

    change.path.write_text("two\n", encoding="utf-8")
    await dispatcher.handle_change(change)

    log_lines = [
        event["data"]["lines"] for event in fake_hub.events if event["type"] == "log_append"
    ]
    assert log_lines == ["one\n", "two\n"]


@pytest.mark.anyio
async def test_reconcile_project_status_emits_only_when_status_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "status-project"
    project_path.mkdir()

    fake_hub = CapturingHub()
    monkeypatch.setattr(event_dispatcher, "hub", fake_hub)

    current_status = "running"

    class _StatusValue:
        def __init__(self, value: str) -> None:
            self.value = value

    def _mock_detect_project_status(_: Path) -> _StatusValue:
        return _StatusValue(current_status)

    monkeypatch.setattr(event_dispatcher, "detect_project_status", _mock_detect_project_status)
    dispatcher = event_dispatcher.WatcherEventDispatcher()

    await dispatcher.reconcile_project_status("status-project", project_path)
    await dispatcher.reconcile_project_status("status-project", project_path)

    current_status = "stopped"
    await dispatcher.reconcile_project_status("status-project", project_path)

    status_events = [event for event in fake_hub.events if event["type"] == "status_changed"]
    assert status_events == [
        {
            "type": "status_changed",
            "project": "status-project",
            "data": {"status": "running"},
        },
        {
            "type": "status_changed",
            "project": "status-project",
            "data": {"status": "stopped", "previous": "running"},
        },
    ]


@pytest.mark.anyio
async def test_notification_change_emits_once_and_records_history(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "notify-project"
    ralph_dir = project_path / ".ralph"
    notify_path = ralph_dir / "pending-notification.txt"
    notify_path.parent.mkdir(parents=True, exist_ok=True)
    notify_path.write_text(
        '{"timestamp":"2026-03-12T10:00:00Z","prefix":"ERROR","message":"Tests failed","iteration":4,"details":"pytest -q failed"}\n',
        encoding="utf-8",
    )

    fake_hub = CapturingHub()
    monkeypatch.setattr(event_dispatcher, "hub", fake_hub)
    dispatcher = event_dispatcher.WatcherEventDispatcher()
    change = FileChangeEvent(
        project_id="notify-project",
        project_path=project_path,
        path=notify_path,
        event_type="modified",
    )

    await dispatcher.handle_change(change)
    await dispatcher.handle_change(change)

    notification_events = [event for event in fake_hub.events if event["type"] == "notification"]
    assert notification_events == [
        {
            "type": "notification",
            "project": "notify-project",
            "data": {
                "prefix": "ERROR",
                "message": "Tests failed",
                "iteration": 4,
                "details": "pytest -q failed",
                "status": None,
                "source": "pending-notification.txt",
            },
        }
    ]

    history_path = ralph_dir / "notifications" / "events.jsonl"
    lines = history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["prefix"] == "ERROR"
    assert payload["message"] == "Tests failed"
    assert payload["iteration"] == 4
