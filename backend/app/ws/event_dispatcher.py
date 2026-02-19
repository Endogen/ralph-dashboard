"""Translate file-watcher changes into websocket events."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from pathlib import Path

from app.notifications.service import parse_notification_file
from app.plan.parser import parse_implementation_plan_file
from app.projects.status import detect_project_status
from app.ws.file_watcher import FileChangeEvent
from app.ws.hub import hub

LOGGER = logging.getLogger(__name__)

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
        # FileWatcherService already consumes file events sequentially, but keep
        # a lock here so direct callers/tests also get deterministic ordering.
        self._dispatch_lock = asyncio.Lock()

    async def handle_change(self, change: FileChangeEvent) -> None:
        """Dispatch a change event sequentially."""
        async with self._dispatch_lock:
            try:
                await self._dispatch(change)
            except Exception:
                LOGGER.exception(
                    "Error dispatching event for %s (%s)",
                    change.project_id,
                    change.path.name,
                )

    async def reconcile_project_status(self, project_id: str, project_path: Path) -> None:
        """Reconcile and emit status_changed for a project if status drifted."""
        async with self._dispatch_lock:
            await self._emit_status_if_changed(project_id, project_path)

    async def _dispatch(self, change: FileChangeEvent) -> None:
        if change.path.name == "IMPLEMENTATION_PLAN.md":
            await self._handle_plan_change(change)
            await self._emit_status_if_changed(change.project_id, change.project_path)
            return

        if change.path.name == "pending-notification.txt" and change.path.parent.name == ".ralph":
            await self._handle_notification_change(change)
            return

        if change.path.parent.name == ".ralph" and change.path.name in {"ralph.pid", "pause"}:
            await self._emit_status_if_changed(change.project_id, change.project_path)
            return

        if change.path.name == "iterations.jsonl" and change.path.parent.name == ".ralph":
            await self._handle_iterations_change(change)
            return

        if change.path.name != "ralph.log":
            await self._emit_file_changed(change)
            return
        if change.path.parent.name == ".ralph":
            await self._handle_log_change(change)
            return

        await self._emit_file_changed(change)

    @staticmethod
    def _read_last_jsonl_record(path) -> dict | None:
        """Read just the last JSON line from iterations.jsonl (sync I/O)."""
        try:
            with path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                if size == 0:
                    return None
                read_size = min(4096, size)
                f.seek(size - read_size)
                chunk = f.read().decode("utf-8", errors="replace")
                lines = chunk.strip().splitlines()
                if not lines:
                    return None
                return json.loads(lines[-1])
        except (OSError, json.JSONDecodeError, KeyError):
            return None

    async def _handle_iterations_change(self, change: FileChangeEvent) -> None:
        """Read the last line of iterations.jsonl to detect new iterations."""
        record = self._read_last_jsonl_record(change.path)
        if record is None:
            return

        iteration_num = record.get("iteration")
        if iteration_num is None:
            return

        started = self._started_iterations[change.project_id]
        completed = self._completed_iterations[change.project_id]

        if iteration_num not in started:
            started.add(iteration_num)
            await hub.emit(
                "iteration_started",
                change.project_id,
                {"iteration": iteration_num, "max": record.get("max", 0)},
            )

        if iteration_num not in completed:
            completed.add(iteration_num)
            await hub.emit(
                "iteration_completed",
                change.project_id,
                {
                    "iteration": iteration_num,
                    "max": record.get("max", 0),
                    "start": record.get("start"),
                    "end": record.get("end"),
                    "duration_seconds": record.get("duration_seconds"),
                    "tokens": record.get("tokens"),
                    "status": record.get("status", "success"),
                    "tasks_completed": record.get("tasks_completed", []),
                    "commit": record.get("commit"),
                    "test_passed": record.get("test_passed"),
                    "errors": record.get("errors", []),
                },
            )

    async def _handle_log_change(self, change: FileChangeEvent) -> None:
        lines = self._read_log_append_lines(change)
        if lines:
            await hub.emit("log_append", change.project_id, {"lines": lines})

    # Maximum bytes to read in one append chunk.  Prevents reading 200MB+
    # when the watcher fires for the first time on an existing large log.
    _MAX_APPEND_BYTES = 512 * 1024  # 512 KB

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

                # On first event after restart, skip to near the end of the
                # file instead of reading everything from offset 0.
                if previous_offset == 0 and size > self._MAX_APPEND_BYTES:
                    previous_offset = size - self._MAX_APPEND_BYTES
                    self._log_remainders.pop(change.project_id, None)

                handle.seek(previous_offset)
                chunk = handle.read(self._MAX_APPEND_BYTES)
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

    async def _emit_status_if_changed(self, project_id: str, project_path: Path) -> None:
        current = detect_project_status(project_path).value
        previous = self._statuses.get(project_id)
        if previous == current:
            return
        self._statuses[project_id] = current

        data: dict[str, str] = {"status": current}
        if previous is not None:
            data["previous"] = previous
        await hub.emit("status_changed", project_id, data)

    async def _emit_file_changed(self, change: FileChangeEvent) -> None:
        try:
            relative = change.path.relative_to(change.project_path).as_posix()
        except ValueError:
            relative = change.path.name
        await hub.emit("file_changed", change.project_id, {"file": relative})


watcher_event_dispatcher = WatcherEventDispatcher()
