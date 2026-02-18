"""Shared process and PID file utilities.

Consolidates PID reading, process liveness checks, and zombie detection
that were previously duplicated across control/process_manager.py,
projects/status.py, and system/service.py.
"""

from __future__ import annotations

import os
from pathlib import Path


def read_pid(pid_file: Path) -> int | None:
    """Read a PID from a file, returning None if missing or invalid."""
    if not pid_file.exists() or not pid_file.is_file():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (TypeError, ValueError):
        return None


def is_zombie_pid(pid: int) -> bool:
    """Check whether a PID corresponds to a zombie process via /proc."""
    stat_file = Path("/proc") / str(pid) / "stat"
    if not stat_file.exists() or not stat_file.is_file():
        return False
    try:
        state = stat_file.read_text(encoding="utf-8").split()[2]
    except (OSError, IndexError):
        return False
    return state == "Z"


def is_process_alive(pid: int) -> bool:
    """Check whether a process is alive (not zombie, not gone)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    if is_zombie_pid(pid):
        return False
    return True
