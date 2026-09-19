"""Regression coverage for the complete loop and dashboard lifecycle."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.control.models import LoopConfig
from app.control.process_manager import start_project_process, stop_project_process
from app.projects.models import project_id_from_path
from app.projects.service import discover_all_project_paths, get_project_detail
from app.projects.status import detect_project_status
from app.utils.process import is_process_alive
from app.wizard.schemas import CreateRequest, GeneratedFile
from app.wizard.service import ProjectTargetValidationError, create_project
from app.ws.event_dispatcher import WatcherEventDispatcher
from app.ws.file_watcher import FileChangeEvent, FileWatcherService

REPO = Path(__file__).resolve().parents[2]


def seed_runner(tmp_path: Path, body: str, *, test_command: str = "") -> tuple[Path, dict]:
    project = tmp_path / "projects" / "sample"
    (project / ".ralph").mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    (project / "PROMPT.md").write_text("Complete the test project")
    (project / "IMPLEMENTATION_PLAN.md").write_text("- [ ] 1.1 Test\n")
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    agent = binary / "claude"
    agent.write_text(f"#!{sys.executable}\n" + body)
    agent.chmod(0o755)
    (project / ".ralph/config.json").write_text(LoopConfig(
        cli="claude", max_iterations=1, test_command=test_command, model="fixture-model"
    ).model_dump_json())
    env = {**os.environ, "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}"}
    return project, env


SUCCESS = '''import json, pathlib, sys
pathlib.Path('argv.json').write_text(json.dumps(sys.argv[1:]))
pathlib.Path('IMPLEMENTATION_PLAN.md').write_text('- [x] 1.1 Test\\nSTATUS: COMPLETE\\n')
print(json.dumps({'type':'assistant','message':{'model':'fixture-model','content':[{'type':'text','text':'Early output'}]}}), flush=True)
import time
time.sleep(0.8)
print(json.dumps({'type':'result','result':'Early output','usage':{'input_tokens':42,'output_tokens':12},'total_cost_usd':0.001}), flush=True)
'''


def test_real_shell_streams_once_and_records_raw_usage(tmp_path):
    project, env = seed_runner(tmp_path, SUCCESS)
    with (tmp_path / "console").open("w") as console:
        process = subprocess.Popen([str(REPO / "scripts/ralph.sh")], cwd=project, env=env,
                                   stdout=console, stderr=console, start_new_session=True)
        try:
            deadline = time.monotonic() + 5
            log = project / ".ralph/ralph.log"
            while time.monotonic() < deadline and (not log.exists() or "Early output" not in log.read_text()):
                time.sleep(0.02)
            assert process.poll() is None, "Output was buffered until process exit"
            assert "Early output" in log.read_text()
            assert process.wait(timeout=5) == 0
        finally:
            if process.poll() is None:
                os.killpg(process.pid, 9)
                process.wait()
    assert log.read_text().count("Early output") == 1
    record = json.loads((project / ".ralph/iterations.jsonl").read_text())
    assert record["tokens"] == 0.054
    assert record["usage"]["input_tokens"] == 42
    assert record["model"] == "fixture-model"
    assert record["cost_usd"] == 0.001
    assert detect_project_status(project).value == "complete"
    argv = json.loads((project / "argv.json").read_text())
    assert "acceptEdits" in argv
    assert "--dangerously-skip-permissions" not in argv
    assert not (project / ".ralph/ralph.pid").exists()


def test_failed_verification_cannot_complete(tmp_path):
    project, env = seed_runner(tmp_path, SUCCESS, test_command="exit 1")
    result = subprocess.run([str(REPO / "scripts/ralph.sh")], cwd=project, env=env,
                            capture_output=True, timeout=10)
    assert result.returncode == 1
    record = json.loads((project / ".ralph/iterations.jsonl").read_text())
    assert record["test_passed"] is False
    assert record["status"] == "error"
    assert detect_project_status(project).value == "error"
    assert json.loads((project / ".ralph/pending-notification.txt").read_text())["prefix"] != "DONE"


def test_rate_limit_is_recorded_and_stops_without_retry(tmp_path):
    project, env = seed_runner(tmp_path, "import sys\nprint('rate limit exceeded')\nsys.exit(1)\n")
    result = subprocess.run([str(REPO / "scripts/ralph.sh"), "20"], cwd=project, env=env,
                            capture_output=True, timeout=10)
    assert result.returncode == 1
    records = (project / ".ralph/iterations.jsonl").read_text().splitlines()
    assert len(records) == 1
    assert json.loads(records[0])["status"] == "blocked"


def test_permissions_are_explicit_and_model_is_preserved():
    config = LoopConfig(cli="claude", flags="--dangerously-skip-permissions", approval_mode="sandboxed", model="custom")
    assert "bypassPermissions" not in config.agent_command()
    assert "acceptEdits" in config.agent_command()
    assert config.agent_command()[-2:] == ["--model", "custom"]
    migrated = LoopConfig.model_validate({"cli": "claude", "flags": "--dangerously-skip-permissions"})
    assert migrated.approval_mode == "full-auto"
    assert "bypassPermissions" in migrated.agent_command()


def test_no_default_signing_key(monkeypatch):
    monkeypatch.delenv("RALPH_SECRET_KEY", raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        get_settings()


@pytest.mark.anyio
async def test_creation_is_transactional_and_immediately_discoverable(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials"))
    get_settings.cache_clear()
    assert await discover_all_project_paths() == []
    with pytest.raises(ProjectTargetValidationError):
        await create_project(CreateRequest(project_name="broken", files=[
            GeneratedFile(path="README.md", content="first"), GeneratedFile(path="../escape", content="bad")]))
    assert not (root / "broken").exists()
    response = await create_project(CreateRequest(project_name="working", model_override="retained", files=[
        GeneratedFile(path="PROMPT.md", content="Goal")]))
    assert await get_project_detail(response.project_id) is not None
    from app.control.process_manager import read_project_config, write_project_config
    config = await read_project_config(response.project_id)
    config.max_iterations = 9
    await write_project_config(response.project_id, config)
    assert (await read_project_config(response.project_id)).model == "retained"


@pytest.mark.anyio
async def test_stop_kills_child_even_when_leader_exits(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    project = root / "tree"
    (project / ".ralph").mkdir(parents=True)
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(root))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials"))
    get_settings.cache_clear()
    script = project / "parent.py"
    script.write_text('''import subprocess,sys,time,pathlib
child=subprocess.Popen([sys.executable,'-c','import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])
pathlib.Path('child.pid').write_text(str(child.pid))
time.sleep(60)
''')
    project_id = project_id_from_path(project)
    started = await start_project_process(project_id, [sys.executable, str(script)])
    child = None
    try:
        for _ in range(100):
            if (project / "child.pid").exists():
                child = int((project / "child.pid").read_text())
                break
            await asyncio.sleep(0.02)
        assert child
        await asyncio.sleep(0.1)
        assert await stop_project_process(project_id, grace_period_seconds=0.2)
        for _ in range(50):
            if not is_process_alive(child):
                break
            await asyncio.sleep(0.02)
        assert not is_process_alive(child)
    finally:
        try:
            os.killpg(started.pid, 9)
        except ProcessLookupError:
            pass


@pytest.mark.anyio
async def test_watcher_delivers_final_rapid_append(monkeypatch, tmp_path):
    from app.ws import file_watcher
    project = tmp_path / "project"
    (project / ".ralph").mkdir(parents=True)
    log = project / ".ralph/ralph.log"
    log.write_text("")
    async def discover():
        return [project]
    monkeypatch.setattr(file_watcher, "discover_all_project_paths", discover)
    received = asyncio.Event()
    async def changed(event):
        if event.path == log and "last" in log.read_text():
            received.set()
    watcher = FileWatcherService(changed)
    await watcher.start()
    try:
        log.write_text("first\n")
        await asyncio.sleep(0.15)
        with log.open("a") as handle:
            handle.write("last\n")
        await asyncio.wait_for(received.wait(), timeout=3)
    finally:
        await watcher.stop()


@pytest.mark.anyio
async def test_large_append_is_drained_and_plan_content_edits_emit(monkeypatch, tmp_path):
    from app.ws import event_dispatcher
    events = []
    class Hub:
        async def emit(self, kind, project, data):
            events.append((kind, data))
    monkeypatch.setattr(event_dispatcher, "hub", Hub())
    dispatcher = WatcherEventDispatcher()
    directory = tmp_path / ".ralph"
    directory.mkdir()
    log = directory / "ralph.log"
    log.write_text("seed\n")
    change = FileChangeEvent("fixture", tmp_path, log, "modified")
    await dispatcher.handle_change(change)
    events.clear()
    appended = "next line\n" * 100000
    with log.open("a") as handle:
        handle.write(appended)
    await dispatcher.handle_change(change)
    assert "".join(data["lines"] for kind, data in events if kind == "log_append") == appended
    plan = tmp_path / "IMPLEMENTATION_PLAN.md"
    plan.write_text("## Tasks\n- [ ] 1.1 Original\n")
    change = FileChangeEvent("fixture", tmp_path, plan, "modified")
    await dispatcher.handle_change(change)
    plan.write_text("## Tasks\n- [ ] 1.1 Revised\n")
    await dispatcher.handle_change(change)
    assert len([kind for kind, _ in events if kind == "plan_updated"]) == 2


@pytest.mark.anyio
async def test_unknown_activity_never_autoarchives(monkeypatch):
    from app.projects import archive
    async def settings():
        return {"auto_archive_enabled": True, "auto_archive_after_days": 30}
    async def ids():
        return set()
    monkeypatch.setattr(archive, "get_archive_settings", settings)
    monkeypatch.setattr(archive, "get_archived_project_ids", ids)
    assert await archive.auto_archive_check({"brand-new": None, "recent": time.time()}) == []


def test_distinct_claude_result_is_not_discarded():
    from app.runner import Runner
    usage = {}
    assert Runner.render_event({"type": "assistant", "message": {"content": [{"type": "text", "text": "Working"}]}}, usage) == "Working"
    assert Runner.render_event({"type": "result", "result": "Finished"}, usage) == "Finished"


@pytest.mark.anyio
async def test_existing_preview_rejects_concurrent_changes(monkeypatch, tmp_path):
    from app.wizard.service import preview_project
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("Original")
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path))
    get_settings.cache_clear()
    request = CreateRequest(project_name="project", project_mode="existing", existing_project_path=str(project), files=[GeneratedFile(path="README.md", content="Proposed")])
    preview = await preview_project(request)
    assert preview["files"][0]["previous"] == "Original"
    request.expected_versions = preview["versions"]
    (project / "README.md").write_text("Concurrent edit")
    with pytest.raises(ProjectTargetValidationError, match="changed since preview"):
        await create_project(request)
    assert (project / "README.md").read_text() == "Concurrent edit"


def test_stopped_iteration_is_not_reported_as_failure(tmp_path):
    from app.runner import Runner
    project, _ = seed_runner(tmp_path, SUCCESS)
    directory = project / '.ralph'
    (directory / 'iterations.jsonl').write_text(json.dumps({'iteration': 1, 'status': 'cancelled', 'errors': ['Agent exited with code 130'], 'end': '2020-01-01T00:00:00Z'}) + '\n')
    (project / 'IMPLEMENTATION_PLAN.md').write_text('STATUS: COMPLETE\n')
    Runner(project, LoopConfig()).state('stopped')
    assert detect_project_status(project).value == 'stopped'


@pytest.mark.anyio
async def test_partial_and_batched_iteration_writes_are_delivered(monkeypatch, tmp_path):
    from app.ws import event_dispatcher
    events = []
    class Hub:
        async def emit(self, kind, project, data):
            if kind == 'iteration_completed':
                events.append(data['iteration'])
    monkeypatch.setattr(event_dispatcher, 'hub', Hub())
    dispatcher = WatcherEventDispatcher()
    path = tmp_path / 'iterations.jsonl'
    path.write_text('{"iteration":1}\n{"iter')
    change = FileChangeEvent('fixture', tmp_path, path, 'modified')
    await dispatcher._handle_iterations_change(change)
    with path.open('a') as handle:
        handle.write('ation":2}\n{"iteration":3}\n')
    await dispatcher._handle_iterations_change(change)
    await dispatcher._handle_iterations_change(change)
    assert events == [1, 2, 3]


def test_password_rotation_invalidates_existing_tokens(tmp_path, monkeypatch):
    from app.auth.service import create_access_token, validate_access_token, InvalidTokenError
    path = tmp_path / 'credentials'
    monkeypatch.setenv('RALPH_CREDENTIALS_FILE', str(path))
    get_settings.cache_clear()
    path.write_text('username: reviewer\npassword_hash: previous-hash\n')
    token = create_access_token('reviewer')
    assert validate_access_token(token).sub == 'reviewer'
    path.write_text('username: reviewer\npassword_hash: rotated-hash\n')
    with pytest.raises(InvalidTokenError):
        validate_access_token(token)


@pytest.mark.anyio
async def test_real_runner_pause_inject_resume_and_stop(monkeypatch, tmp_path):
    from app.control.process_manager import start_project_loop, inject_project_message, resume_project_process
    project, env = seed_runner(tmp_path, "import pathlib,sys,time\npathlib.Path('received.txt').write_text(sys.stdin.read())\nprint('Working', flush=True)\ntime.sleep(30)\n")
    monkeypatch.setenv('PATH', env['PATH'])
    monkeypatch.setenv('RALPH_PROJECT_DIRS', str(project.parent))
    get_settings.cache_clear()
    (project / '.ralph/pause').touch()
    project_id = project_id_from_path(project)
    started = await start_project_loop(project_id)
    try:
        for _ in range(100):
            if detect_project_status(project).value == 'paused':
                break
            await asyncio.sleep(0.02)
        assert detect_project_status(project).value == 'paused'
        assert not (project / 'received.txt').exists()
        await inject_project_message(project_id, 'Preserve the public API')
        await resume_project_process(project_id)
        for _ in range(100):
            if (project / 'received.txt').exists():
                break
            await asyncio.sleep(0.02)
        assert 'Preserve the public API' in (project / 'received.txt').read_text()
        assert not (project / '.ralph/inject.md').exists()
        assert await stop_project_process(project_id)
        assert not is_process_alive(started.pid)
        assert detect_project_status(project).value == 'stopped'
        assert json.loads((project / '.ralph/iterations.jsonl').read_text())['status'] == 'cancelled'
        assert not (project / '.ralph/pending-notification.txt').exists()
    finally:
        if is_process_alive(started.pid):
            await stop_project_process(project_id)


def test_completion_reaps_children_after_the_agent_exits(tmp_path):
    project, env = seed_runner(tmp_path, '''import pathlib,subprocess,sys
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
pathlib.Path('child.pid').write_text(str(child.pid))
pathlib.Path('IMPLEMENTATION_PLAN.md').write_text('STATUS: COMPLETE\\n')
print('Finished', flush=True)
''')
    result = subprocess.run([str(REPO / 'scripts/ralph.sh')], cwd=project, env=env, capture_output=True, timeout=10)
    assert result.returncode == 0
    child = int((project / 'child.pid').read_text())
    try:
        assert not is_process_alive(child)
    finally:
        if is_process_alive(child):
            os.kill(child, 9)
