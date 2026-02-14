"""Translate file-watcher changes into websocket events."""

from __future__ import annotations

from collections import defaultdict

from app.iterations.log_parser import parse_ralph_log_file
from app.notifications.service import parse_notification_file
from app.plan.parser import parse_implementation_plan_file
from app.projects.status import detect_project_status
from app.ws.file_watcher import FileChangeEvent
from app.ws.hub import hub


class WatcherEventDispatcher:
    """Consumes watcher file changes and emits websocket events."""

    def __init__(self) -> None:
        self._started_iterations: dict[str, set[int]] = defaultdict(set)
        self._completed_iterations: dict[str, set[int]] = defaultdict(set)
        self._log_offsets: dict[str, int] = {}
        self._log_mtimes_ns: dict[str, int] = {}
        self._log_ctimes_ns: dict[str, int] = {}
        self._log_prefixes: dict[str, bytes] = {}
        self._log_remainders: dict[str, str] = {}
        self._plan_snapshots: dict[str, tuple[int, int, tuple[tuple[str, int, int, str], ...]]] = {}
        self._last_notification_keys: dict[str, tuple[str, str, str | None, int | None]] = {}
        self._statuses: dict[str, str] = {}

    async def handle_change(self, change: FileChangeEvent) -> None:
        if change.path.name == "IMPLEMENTATION_PLAN.md":
            await self._handle_plan_change(change)
            await self._emit_status_if_changed(change)
            return

        if change.path.name == "pending-notification.txt" and change.path.parent.name == ".ralph":
            await self._handle_notification_change(change)
            return

        if change.path.parent.name == ".ralph" and change.path.name in {"ralph.pid", "pause"}:
            await self._emit_status_if_changed(change)
            return

        if change.path.name != "ralph.log":
            await self._emit_file_changed(change)
            return
        if change.path.parent.name == ".ralph":
            await self._handle_log_change(change)
            return

        await self._emit_file_changed(change)

    async def _handle_log_change(self, change: FileChangeEvent) -> None:
        lines = self._read_log_append_lines(change)
        if lines:
            await hub.emit("log_append", change.project_id, {"lines": lines})

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

    def _read_log_append_lines(self, change: FileChangeEvent) -> str | None:
        previous_offset = self._log_offsets.get(change.project_id, 0)
        previous_mtime = self._log_mtimes_ns.get(change.project_id)
        previous_ctime = self._log_ctimes_ns.get(change.project_id)
        previous_prefix = self._log_prefixes.get(change.project_id)
        try:
            file_stats = change.path.stat()
            with change.path.open("rb") as handle:
                size = file_stats.st_size
                probe_size = min(1024, size)
                handle.seek(0)
                current_prefix = handle.read(probe_size)
                if size < previous_offset:
                    previous_offset = 0
                    self._log_remainders.pop(change.project_id, None)
                elif size == previous_offset:
                    rewritten_by_time = (
                        previous_mtime is not None and file_stats.st_mtime_ns != previous_mtime
                    ) or (previous_ctime is not None and file_stats.st_ctime_ns != previous_ctime)
                    rewritten_by_prefix = (
                        previous_prefix is not None and current_prefix != previous_prefix
                    )
                    if rewritten_by_time or rewritten_by_prefix:
                        previous_offset = 0
                        self._log_remainders.pop(change.project_id, None)
                handle.seek(previous_offset)
                chunk = handle.read()
        except OSError:
            self._log_offsets.pop(change.project_id, None)
            self._log_mtimes_ns.pop(change.project_id, None)
            self._log_ctimes_ns.pop(change.project_id, None)
            self._log_prefixes.pop(change.project_id, None)
            self._log_remainders.pop(change.project_id, None)
            return None

        self._log_offsets[change.project_id] = size
        self._log_mtimes_ns[change.project_id] = file_stats.st_mtime_ns
        self._log_ctimes_ns[change.project_id] = file_stats.st_ctime_ns
        self._log_prefixes[change.project_id] = current_prefix
        if not chunk:
            return None

        buffer = self._log_remainders.get(change.project_id, "") + chunk.decode(
            "utf-8",
            errors="replace",
        )
        lines = buffer.splitlines(keepends=True)

        remainder = ""
        if lines and not lines[-1].endswith(("\n", "\r")):
            remainder = lines.pop()

        if remainder:
            self._log_remainders[change.project_id] = remainder
        else:
            self._log_remainders.pop(change.project_id, None)

        if not lines:
            return None
        return "".join(lines)

    async def _handle_plan_change(self, change: FileChangeEvent) -> None:
        parsed = parse_implementation_plan_file(change.path)
        if parsed is None:
            return

        phases = [
            {
                "name": phase.name,
                "done": phase.done_count,
                "total": phase.total_count,
                "status": phase.status,
            }
            for phase in parsed.phases
        ]
        snapshot = (
            parsed.tasks_done,
            parsed.tasks_total,
            tuple(
                (phase["name"], phase["done"], phase["total"], phase["status"]) for phase in phases
            ),
        )
        if self._plan_snapshots.get(change.project_id) == snapshot:
            return
        self._plan_snapshots[change.project_id] = snapshot

        await hub.emit(
            "plan_updated",
            change.project_id,
            {
                "tasks_done": parsed.tasks_done,
                "tasks_total": parsed.tasks_total,
                "phases": phases,
                "status": parsed.status,
            },
        )

    async def _handle_notification_change(self, change: FileChangeEvent) -> None:
        entry = parse_notification_file(change.path)
        if entry is None:
            return

        key = (entry.timestamp, entry.message, entry.prefix, entry.iteration)
        if self._last_notification_keys.get(change.project_id) == key:
            return
        self._last_notification_keys[change.project_id] = key

        await hub.emit(
            "notification",
            change.project_id,
            {
                "prefix": entry.prefix,
                "message": entry.message,
                "iteration": entry.iteration,
                "details": entry.details,
                "status": entry.status,
                "source": entry.source,
            },
        )

    async def _emit_status_if_changed(self, change: FileChangeEvent) -> None:
        current = detect_project_status(change.project_path).value
        previous = self._statuses.get(change.project_id)
        if previous == current:
            return
        self._statuses[change.project_id] = current

        data: dict[str, str] = {"status": current}
        if previous is not None:
            data["previous"] = previous
        await hub.emit("status_changed", change.project_id, data)

    async def _emit_file_changed(self, change: FileChangeEvent) -> None:
        try:
            relative = change.path.relative_to(change.project_path).as_posix()
        except ValueError:
            relative = change.path.name
        await hub.emit("file_changed", change.project_id, {"file": relative})


watcher_event_dispatcher = WatcherEventDispatcher()
