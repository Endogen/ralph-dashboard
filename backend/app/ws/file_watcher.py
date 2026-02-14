"""Watchdog-based file watching service for tracked Ralph projects."""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from watchdog.events import (
    EVENT_TYPE_CREATED,
    EVENT_TYPE_DELETED,
    EVENT_TYPE_MODIFIED,
    EVENT_TYPE_MOVED,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from app.projects.models import project_id_from_path
from app.projects.service import discover_all_project_paths

WATCHED_ROOT_FILES = {"IMPLEMENTATION_PLAN.md", "AGENTS.md", "PROMPT.md"}
WATCHED_RALPH_FILES = {
    "ralph.log",
    "iterations.jsonl",
    "pending-notification.txt",
    "ralph.pid",
    "pause",
}
# Only react to real content changes, not access/attribute metadata events.
_RELEVANT_EVENT_TYPES = {EVENT_TYPE_CREATED, EVENT_TYPE_DELETED, EVENT_TYPE_MODIFIED, EVENT_TYPE_MOVED}
# Minimum seconds between queuing events for the same file.
_DEBOUNCE_SECONDS = 0.5
# Hard cap on pending events to prevent unbounded memory growth.
_MAX_QUEUE_SIZE = 200

OnFileChange = Callable[["FileChangeEvent"], Awaitable[None]]


@dataclass(slots=True, frozen=True)
class FileChangeEvent:
    project_id: str
    project_path: Path
    path: Path
    event_type: str


def _is_relevant_path(project_path: Path, file_path: Path) -> bool:
    # Use string operations instead of resolve() to avoid expensive syscalls
    # in the hot path (called from watchdog thread on every fs event).
    try:
        proj_str = str(project_path)
        file_str = str(file_path)
        if not file_str.startswith(proj_str):
            return False
        relative = file_str[len(proj_str):].lstrip("/")
    except (TypeError, ValueError):
        return False

    if not relative:
        return False

    parts = relative.split("/")

    if len(parts) == 1 and parts[0] in WATCHED_ROOT_FILES:
        return True
    if len(parts) == 2 and parts[0] == ".ralph" and parts[1] in WATCHED_RALPH_FILES:
        return True
    if len(parts) >= 2 and parts[0] == "specs" and relative.endswith(".md"):
        return True
    return False


class _ProjectEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        project_id: str,
        project_path: Path,
        queue: asyncio.Queue[FileChangeEvent],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._project_id = project_id
        self._project_path = project_path
        self._queue = queue
        self._loop = loop
        self._last_event_times: dict[str, float] = {}

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        # Only process real content-change events.
        if event.event_type not in _RELEVANT_EVENT_TYPES:
            return

        path_value = getattr(event, "dest_path", None) or event.src_path
        path_str = str(path_value)
        if not _is_relevant_path(self._project_path, Path(path_str)):
            return

        # Debounce: skip if the same file was queued recently.
        now = time.monotonic()
        last = self._last_event_times.get(path_str, 0.0)
        if now - last < _DEBOUNCE_SECONDS:
            return
        self._last_event_times[path_str] = now

        # Drop events when queue is full to prevent memory leak.
        if self._queue.qsize() >= _MAX_QUEUE_SIZE:
            return

        change = FileChangeEvent(
            project_id=self._project_id,
            project_path=self._project_path,
            path=Path(path_str),
            event_type=event.event_type,
        )
        self._loop.call_soon_threadsafe(self._queue.put_nowait, change)


class FileWatcherService:
    """Manages watchdog observers for all currently tracked projects."""

    def __init__(self, on_change: OnFileChange | None = None) -> None:
        self._on_change = on_change
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[FileChangeEvent] = asyncio.Queue()
        self._consumer_task: asyncio.Task[None] | None = None
        self._observers: dict[str, Observer] = {}
        self._project_paths: dict[str, Path] = {}
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def set_on_change(self, on_change: OnFileChange | None) -> None:
        self._on_change = on_change

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._consumer_task = asyncio.create_task(self._consume_events())
        await self.refresh_projects()

    async def stop(self) -> None:
        if not self._running:
            return

        for observer in self._observers.values():
            observer.stop()
        for observer in self._observers.values():
            observer.join(timeout=1.0)

        self._observers.clear()
        self._project_paths.clear()

        if self._consumer_task is not None:
            self._consumer_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._consumer_task
            self._consumer_task = None

        self._running = False
        self._loop = None

    async def refresh_projects(self) -> None:
        """Reconcile observer set with currently discovered/registered projects."""
        if not self._running or self._loop is None:
            return

        desired_paths = await discover_all_project_paths()
        desired: dict[str, Path] = {project_id_from_path(path): path for path in desired_paths}

        stale_ids = [project_id for project_id in self._observers if project_id not in desired]
        for project_id in stale_ids:
            self._stop_observer(project_id)

        for project_id, project_path in desired.items():
            if project_id not in self._observers:
                self._start_observer(project_id, project_path)

    async def _consume_events(self) -> None:
        last_handled: dict[str, float] = {}
        while True:
            change = await self._queue.get()
            try:
                if self._on_change is not None:
                    key = f"{change.project_id}:{change.path}"
                    now = asyncio.get_event_loop().time()
                    if now - last_handled.get(key, 0.0) < _DEBOUNCE_SECONDS:
                        continue
                    last_handled[key] = now
                    # Drain any duplicate events that piled up during handling.
                    drained = 0
                    while not self._queue.empty() and drained < 50:
                        try:
                            self._queue.get_nowait()
                            self._queue.task_done()
                            drained += 1
                        except asyncio.QueueEmpty:
                            break
                    await self._on_change(change)
            except Exception:
                pass  # Don't let a handler error kill the consumer loop.
            finally:
                self._queue.task_done()

    def _start_observer(self, project_id: str, project_path: Path) -> None:
        if self._loop is None:
            return
        if not project_path.exists() or not project_path.is_dir():
            return

        observer = Observer()
        handler = _ProjectEventHandler(
            project_id=project_id,
            project_path=project_path,
            queue=self._queue,
            loop=self._loop,
        )
        try:
            # Watch only specific directories instead of recursive=True
            # to avoid watching node_modules, .venv, .git, etc.
            observer.schedule(handler, str(project_path), recursive=False)

            ralph_dir = project_path / ".ralph"
            if ralph_dir.exists() and ralph_dir.is_dir():
                observer.schedule(handler, str(ralph_dir), recursive=False)

            specs_dir = project_path / "specs"
            if specs_dir.exists() and specs_dir.is_dir():
                observer.schedule(handler, str(specs_dir), recursive=False)

            observer.start()
        except OSError:
            observer.stop()
            return
        self._observers[project_id] = observer
        self._project_paths[project_id] = project_path

    def _stop_observer(self, project_id: str) -> None:
        observer = self._observers.pop(project_id, None)
        self._project_paths.pop(project_id, None)
        if observer is None:
            return
        observer.stop()
        observer.join(timeout=1.0)


file_watcher_service = FileWatcherService()
