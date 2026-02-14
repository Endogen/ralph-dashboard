"""Translate file-watcher changes into websocket events."""

from __future__ import annotations

from collections import defaultdict

from app.iterations.log_parser import parse_ralph_log_file
from app.ws.file_watcher import FileChangeEvent
from app.ws.hub import hub


class WatcherEventDispatcher:
    """Consumes watcher file changes and emits websocket events."""

    def __init__(self) -> None:
        self._started_iterations: dict[str, set[int]] = defaultdict(set)
        self._completed_iterations: dict[str, set[int]] = defaultdict(set)

    async def handle_change(self, change: FileChangeEvent) -> None:
        if change.path.name != "ralph.log":
            return
        if change.path.parent.name != ".ralph":
            return
        await self._handle_log_change(change)

    async def _handle_log_change(self, change: FileChangeEvent) -> None:
        iterations = parse_ralph_log_file(change.path)
        started = self._started_iterations[change.project_id]
        completed = self._completed_iterations[change.project_id]

        for iteration in iterations:
            if iteration.number not in started:
                started.add(iteration.number)
                await hub.emit(
                    "iteration_started",
                    change.project_id,
                    {"iteration": iteration.number, "max": iteration.max_iterations},
                )

            if iteration.end_timestamp is not None and iteration.number not in completed:
                completed.add(iteration.number)
                await hub.emit(
                    "iteration_completed",
                    change.project_id,
                    {
                        "iteration": iteration.number,
                        "max": iteration.max_iterations,
                        "start": iteration.start_timestamp,
                        "end": iteration.end_timestamp,
                        "tokens": iteration.tokens_used,
                        "status": "error" if iteration.has_errors else "success",
                        "errors": iteration.error_lines,
                    },
                )


watcher_event_dispatcher = WatcherEventDispatcher()
