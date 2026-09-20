"""Behavioral regressions for the September 20 review changes."""

import asyncio
import os
import signal
import sys
import time

import jwt
import pytest
from fastapi import HTTPException

from app.auth import router as auth_router
from app.auth.service import InvalidCredentialsError, InvalidTokenError, validate_access_token
from app.config import get_settings
from app.control.models import LoopConfig
from app.runner import Runner
from app.utils.process import is_process_alive, process_lock, prune_stale_locks, terminate_group
from app.ws.event_dispatcher import WatcherEventDispatcher
from app.ws.file_watcher import FileChangeEvent, FileWatcherService


def test_pruning_does_not_unlink_an_old_held_lock(tmp_path):
    with process_lock(tmp_path, "held.lock"):
        os.utime(tmp_path / "held.lock", (1, 1))
        prune_stale_locks(tmp_path)
        assert (tmp_path / "held.lock").exists()
        with pytest.raises(BlockingIOError):
            with process_lock(tmp_path, "held.lock"):
                pytest.fail("Two writers entered the same project lock")


def test_persistent_runner_log_follows_rotation(tmp_path):
    runner = Runner(tmp_path, LoopConfig())
    path = tmp_path / ".ralph/ralph.log"
    try:
        runner.log("before\n")
        path.rename(path.with_suffix(".old"))
        path.write_text("rotated\n")
        runner.log("after\n")
        assert path.read_text() == "rotated\nafter\n"
        assert path.with_suffix(".old").read_text() == "before\n"
    finally:
        runner.close_log()


@pytest.mark.parametrize("claims", [{}, {"credential_version": None}])
def test_tokens_without_a_credential_identity_are_rejected(claims):
    token = jwt.encode(
        {"sub": "demo", "type": "access", "exp": int(time.time()) + 300, **claims},
        get_settings().secret_key,
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        validate_access_token(token)


@pytest.mark.anyio
async def test_concurrent_failed_logins_cannot_bypass_the_budget(monkeypatch):
    gate = asyncio.Event()
    entered = 0

    async def authenticate(*args):
        nonlocal entered
        entered += 1
        await gate.wait()
        raise InvalidCredentialsError("wrong")

    monkeypatch.setattr(auth_router.asyncio, "to_thread", authenticate)
    auth_router._login_attempts.clear()
    request = auth_router.LoginRequest(username="demo", password="wrong")
    tasks = [asyncio.create_task(auth_router.login(request)) for _ in range(11)]
    await asyncio.sleep(0)
    gate.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    auth_router._login_attempts.clear()
    assert entered == 10
    assert (
        sum(isinstance(result, HTTPException) and result.status_code == 429 for result in results)
        == 1
    )


@pytest.mark.anyio
async def test_final_log_tail_is_requeued_without_starving_other_files(monkeypatch, tmp_path):
    from app.ws import event_dispatcher

    events = []
    finished = asyncio.Event()

    class Hub:
        async def emit(self, kind, project, data):
            events.append((kind, data))
            if kind == "log_append" and "LAST" in data["lines"]:
                finished.set()

    monkeypatch.setattr(event_dispatcher, "hub", Hub())
    dispatcher = WatcherEventDispatcher()
    dispatcher._MAX_DRAIN_PASSES = 2
    dispatcher._MAX_APPEND_BYTES = 16
    (tmp_path / ".ralph").mkdir()
    path = tmp_path / ".ralph/ralph.log"
    path.write_text("seed\n")
    change = FileChangeEvent("fixture", tmp_path, path, "modified")
    await dispatcher.handle_change(change)
    events.clear()
    appended = "line123\n" * 24 + "LAST\n"
    with path.open("a") as handle:
        handle.write(appended)
    plan = tmp_path / "IMPLEMENTATION_PLAN.md"
    plan.write_text("## Tasks\n- [ ] 1.1 Test\n")
    watcher = FileWatcherService(dispatcher.handle_change)
    watcher._queue.put_nowait(change)
    watcher._queue.put_nowait(FileChangeEvent("fixture", tmp_path, plan, "modified"))
    consumer = asyncio.create_task(watcher._consume_events())
    try:
        await asyncio.wait_for(finished.wait(), timeout=2)
        assert "".join(data["lines"] for kind, data in events if kind == "log_append") == appended
        assert (
            next(i for i, (kind, _) in enumerate(events) if kind == "plan_updated")
            < len(events) - 1
        )
    finally:
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)


@pytest.mark.anyio
async def test_generation_cleanup_works_after_its_leader_exits():
    from app.wizard.generator import _terminate_generation_process

    script = """import subprocess,sys,os
child=subprocess.Popen([sys.executable,'-c','import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print("ready",flush=True); time.sleep(30)'])
print(child.pid,flush=True)
os._exit(0)
"""
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-c", script, stdout=asyncio.subprocess.PIPE, start_new_session=True
    )
    child = None
    try:
        lines = [await process.stdout.readline(), await process.stdout.readline()]
        assert b"ready\n" in lines
        child = int(next(line for line in lines if line != b"ready\n"))
        for _ in range(100):
            if process.returncode is not None:
                break
            await asyncio.sleep(0.01)
        assert process.returncode == 0
        await _terminate_generation_process(process)
        assert not is_process_alive(child)
    finally:
        await asyncio.to_thread(terminate_group, process.pid, 0.1)
        await asyncio.wait_for(process.communicate(), timeout=3)
        if child and is_process_alive(child):
            os.kill(child, signal.SIGKILL)


def test_lock_acquisition_retries_an_inode_unlinked_by_the_pruner(monkeypatch, tmp_path):
    import fcntl
    from app.utils import process

    path = tmp_path / "racing.lock"
    path.touch()
    os.utime(path, (1, 1))
    real_flock = fcntl.flock
    prune_before_lock = True

    def race(handle, operation):
        nonlocal prune_before_lock
        if prune_before_lock and operation == fcntl.LOCK_EX | fcntl.LOCK_NB:
            prune_before_lock = False
            process.prune_stale_locks(tmp_path)
        return real_flock(handle, operation)

    monkeypatch.setattr(process.fcntl, "flock", race)
    with process_lock(tmp_path, path.name) as handle:
        assert os.fstat(handle.fileno()).st_ino == path.stat().st_ino
        with pytest.raises(BlockingIOError):
            with process_lock(tmp_path, path.name):
                pytest.fail("A competing writer acquired the same lock")
