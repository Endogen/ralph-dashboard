"""Process identity, locking and whole-group termination."""
from __future__ import annotations

import fcntl
import json
import os
import signal
import time
from contextlib import contextmanager
from pathlib import Path

import psutil

from app.utils.files import atomic_write


def read_pid(pid_file: Path) -> int | None:
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        return pid if pid > 1 else None
    except (OSError, ValueError):
        return None


def is_zombie_pid(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def is_process_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        return psutil.Process(pid).is_running() and not is_zombie_pid(pid)
    except psutil.NoSuchProcess:
        return False


def write_process_identity(directory: Path, pid: int) -> None:
    atomic_write(directory / "process.json", json.dumps({
        "pid": pid, "created": psutil.Process(pid).create_time(), "pgid": os.getpgid(pid),
    }))
    atomic_write(directory / "ralph.pid", str(pid))


def owns_process(directory: Path, pid: int) -> bool:
    """Check recorded birth time to avoid signalling a recycled PID."""
    try:
        identity = json.loads((directory / "process.json").read_text())
        return identity["pid"] == pid and identity["created"] == psutil.Process(pid).create_time()
    except FileNotFoundError:
        # Legacy shell runners have no identity record. Only their own session
        # leaders may be stopped; never signal the dashboard's process group.
        try:
            return os.getpgid(pid) == pid
        except ProcessLookupError:
            return False
    except (OSError, ValueError, KeyError, psutil.NoSuchProcess):
        return False


def prune_stale_locks(directory: Path, max_age_seconds: float = 7 * 24 * 3600) -> None:
    """Remove old, unlocked files while holding their inode lock."""
    cutoff = time.time() - max_age_seconds
    for entry in directory.glob("*.lock"):
        try:
            with entry.open("r+") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                stats = os.fstat(handle.fileno())
                current = entry.stat()
                if (stats.st_dev, stats.st_ino) == (current.st_dev, current.st_ino) and stats.st_mtime < cutoff:
                    entry.unlink()
        except OSError:
            continue


@contextmanager
def process_lock(directory: Path, name: str = "start.lock"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    while True:
        with path.open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                # A pruner may have unlinked this inode after we opened it.
                # Retry on the current name before entering the critical section.
                stats = os.fstat(handle.fileno())
                try:
                    current = path.stat()
                except FileNotFoundError:
                    continue
                if (stats.st_dev, stats.st_ino) != (current.st_dev, current.st_ino):
                    continue
                os.utime(handle.fileno())
                yield handle
                return
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def terminate_group(pgid: int, grace: float = 3.0) -> None:
    """Capture group before TERM; the leader can exit before its children."""
    if pgid <= 1 or pgid == os.getpgrp():
        raise ValueError("Refusing to terminate our own or an invalid process group")
    def members_alive() -> bool:
        # killpg(pgid, 0) is not a portable liveness test: on macOS a
        # group containing only zombies can report EPERM rather than ESRCH.
        for process in psutil.process_iter(["pid", "status"]):
            if process.info["status"] == psutil.STATUS_ZOMBIE:
                continue
            try:
                if os.getpgid(process.pid) == pgid:
                    return True
            except (ProcessLookupError, PermissionError):
                continue
        return False

    def signal_group(sig):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            if members_alive():
                raise
    signal_group(signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if not members_alive():
            return
        time.sleep(0.05)
    signal_group(signal.SIGKILL)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if not members_alive():
            return
        time.sleep(0.05)
    raise RuntimeError("Process group did not exit after SIGKILL")
