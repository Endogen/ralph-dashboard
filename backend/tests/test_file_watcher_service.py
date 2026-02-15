"""Tests for file watcher service queue/consumer behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.ws import file_watcher
from app.ws.file_watcher import FileChangeEvent, FileWatcherService


@pytest.mark.anyio
async def test_consumer_processes_distinct_queued_events_without_dropping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def _discover_no_projects() -> list[Path]:
        return []

    monkeypatch.setattr(file_watcher, "discover_all_project_paths", _discover_no_projects)

    project_path = tmp_path / "project-a"
    project_path.mkdir(parents=True, exist_ok=True)

    handled_paths: list[str] = []
    processed = asyncio.Event()

    async def _on_change(change: FileChangeEvent) -> None:
        handled_paths.append(change.path.name)
        if len(handled_paths) >= 2:
            processed.set()

    service = FileWatcherService(on_change=_on_change)
    await service.start()
    try:
        await service._queue.put(
            FileChangeEvent(
                project_id="project-a",
                project_path=project_path,
                path=project_path / "AGENTS.md",
                event_type="modified",
            )
        )
        await service._queue.put(
            FileChangeEvent(
                project_id="project-a",
                project_path=project_path,
                path=project_path / "PROMPT.md",
                event_type="modified",
            )
        )

        await asyncio.wait_for(processed.wait(), timeout=1.0)
    finally:
        await service.stop()

    assert handled_paths == ["AGENTS.md", "PROMPT.md"]


class _CapturingHub:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    async def broadcast(self, payload: dict[str, Any], project: str | None = None) -> None:
        self.payloads.append(payload)


class _FakeObserver:
    def stop(self) -> None:
        return

    def join(self, timeout: float | None = None) -> None:
        return


@pytest.mark.anyio
async def test_refresh_projects_emits_watcher_projects_refreshed_on_set_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_alpha = tmp_path / "alpha"
    project_beta = tmp_path / "beta"
    project_alpha.mkdir(parents=True, exist_ok=True)
    project_beta.mkdir(parents=True, exist_ok=True)

    snapshots = iter(
        [
            [project_alpha],  # start() refresh
            [project_alpha],  # unchanged, no event
            [project_alpha, project_beta],  # add beta
            [project_beta],  # remove alpha
        ]
    )

    async def _discover_paths() -> list[Path]:
        return next(snapshots)

    hub = _CapturingHub()
    monkeypatch.setattr(file_watcher, "discover_all_project_paths", _discover_paths)
    monkeypatch.setattr(file_watcher, "hub", hub)

    service = FileWatcherService(on_change=None)

    def _start_observer(project_id: str, project_path: Path) -> None:
        service._observers[project_id] = _FakeObserver()  # type: ignore[assignment]
        service._project_paths[project_id] = project_path

    def _stop_observer(project_id: str) -> None:
        service._observers.pop(project_id, None)
        service._project_paths.pop(project_id, None)

    monkeypatch.setattr(service, "_start_observer", _start_observer)
    monkeypatch.setattr(service, "_stop_observer", _stop_observer)

    await service.start()
    try:
        assert len(hub.payloads) == 1
        first = hub.payloads[0]
        assert first["type"] == "watcher_projects_refreshed"
        assert first["data"]["added"] == ["alpha"]
        assert first["data"]["removed"] == []
        assert first["data"]["observed"] == ["alpha"]
        assert first["data"]["count"] == 1

        await service.refresh_projects()
        assert len(hub.payloads) == 1

        await service.refresh_projects()
        second = hub.payloads[1]
        assert second["data"]["added"] == ["beta"]
        assert second["data"]["removed"] == []
        assert second["data"]["observed"] == ["alpha", "beta"]
        assert second["data"]["count"] == 2

        await service.refresh_projects()
        third = hub.payloads[2]
        assert third["data"]["added"] == []
        assert third["data"]["removed"] == ["alpha"]
        assert third["data"]["observed"] == ["beta"]
        assert third["data"]["count"] == 1
    finally:
        await service.stop()
