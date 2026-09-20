"""Ralph's noninteractive loop. A single owner for lifecycle, logs and records."""
from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil

from app.control.models import LoopConfig
from app.utils.files import atomic_write, read_last_jsonl_record
from app.utils.process import process_lock, write_process_identity


def now() -> str:
    return datetime.now(UTC).isoformat()


def load_config(project: Path, max_iterations: int | None = None) -> LoopConfig:
    path = project / ".ralph/config.json"
    values = json.loads(path.read_text()) if path.exists() else {}
    for env, key in {"RALPH_CLI": "cli", "RALPH_FLAGS": "flags", "RALPH_TEST": "test_command",
                     "RALPH_MODEL": "model", "RALPH_APPROVAL_MODE": "approval_mode"}.items():
        if env in os.environ:
            values[key] = os.environ[env]
    if max_iterations is not None:
        values["max_iterations"] = max_iterations
    return LoopConfig.model_validate(values)


def preflight(project: Path, config: LoopConfig) -> None:
    if not (project / "PROMPT.md").is_file():
        raise ValueError("PROMPT.md is missing. Create a project prompt before starting.")
    if subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=project,
                      capture_output=True).returncode:
        raise ValueError("Project must be a Git repository.")
    executable = config.agent_command()[0]
    if not shutil.which(executable):
        raise ValueError(f"CLI '{executable}' is not available on the dashboard service PATH.")


class Runner:
    def __init__(self, project: Path, config: LoopConfig):
        self.project = project
        self.directory = project / ".ralph"
        self.config = config
        self.stopped = False
        self.iteration = 0
        self.iteration_deadline: float | None = None
        self.child: subprocess.Popen | None = None
        # Held open across writes; flushed per write so watchers see output live.
        self._log_handle = None
        self.directory.mkdir(exist_ok=True)

    def log(self, text: str) -> None:
        path = self.directory / "ralph.log"
        if self._log_handle is not None:
            try:
                current = path.stat()
                opened = os.fstat(self._log_handle.fileno())
                if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
                    self.close_log()
            except FileNotFoundError:
                self.close_log()
        if self._log_handle is None:
            self._log_handle = path.open("a", encoding="utf-8")
        self._log_handle.write(text)
        self._log_handle.flush()
        if os.getenv("RALPH_MANAGED") != "1":
            print(text, end="", flush=True)

    def close_log(self) -> None:
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def state(self, status: str, **extra) -> None:
        atomic_write(self.directory / "state.json", json.dumps({
            "status": status, "iteration": self.iteration, "max": self.config.max_iterations,
            "timestamp": now(), **extra,
        }))

    def notify(self, prefix: str, message: str, details: str = "") -> None:
        atomic_write(self.directory / "pending-notification.txt", json.dumps({
            "timestamp": now(), "prefix": prefix, "message": message, "details": details,
            "iteration": self.iteration, "max_iterations": self.config.max_iterations,
            "project": str(self.project), "project_name": self.project.name,
        }))

    def signal_stop(self, _sig, _frame) -> None:
        self.stopped = True

    def cleanup_child(self) -> None:
        processes = {}
        if self.child is not None:
            try:
                parent = psutil.Process(self.child.pid)
                processes.update({process.pid: process for process in parent.children(recursive=True) + [parent]})
            except psutil.NoSuchProcess:
                pass
        # An agent can exit before a spawned server. Such children are no
        # longer in its process tree, but remain in this runner's owned group.
        if os.getpgrp() == os.getpid():
            for process in psutil.process_iter():
                try:
                    if process.pid > 1 and process.pid != os.getpid() and os.getpgid(process.pid) == os.getpid():
                        processes[process.pid] = process
                except (ProcessLookupError, PermissionError):
                    continue
        for process in processes.values():
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(list(processes.values()), timeout=0.5)
        for process in alive:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(alive, timeout=2)
        if self.child is not None:
            self.child.wait(timeout=3)
            if self.child.stdout is not None:
                self.child.stdout.close()
        self.child = None

    def execute(self, command: list[str], prompt: str | None = None,
                structured: bool = False) -> tuple[int, str, dict]:
        """Drain stdout while the process runs, retaining only a bounded error tail."""
        usage: dict = {}
        tail = ""
        buffer = b""
        # Retains a partial multi-byte character across chunk boundaries.
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        deadline = self.iteration_deadline or time.monotonic() + self.config.iteration_timeout_seconds
        # A temporary file avoids deadlocking on a large prompt written to a pipe
        # before stdout is drained, and keeps prompts out of process listings.
        with tempfile.TemporaryFile() as input_file:
            if prompt is not None:
                input_file.write(prompt.encode())
                input_file.seek(0)
            self.child = subprocess.Popen(command, cwd=self.project, stdin=input_file,
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert self.child.stdout is not None
        def consume(line: bytes) -> None:
            nonlocal tail
            text = line.decode("utf-8", errors="replace")
            if structured:
                try:
                    event = json.loads(text)
                except ValueError:
                    event = None
                if isinstance(event, dict):
                    text = self.render_event(event, usage)
            tail = (tail + text)[-65536:]
            if text:
                self.log(text if text.endswith("\n") else text + "\n")
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(self.child.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    if self.stopped or time.monotonic() >= deadline:
                        self.cleanup_child()
                        reason = "Stopped by user" if self.stopped else "Iteration timed out"
                        return 130 if self.stopped else 124, tail + reason, usage
                    for key, _ in selector.select(timeout=0.1):
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        if not structured:
                            # Plain output needn't wait for a line break to become
                            # visible, and one decoder owns the whole stream so a
                            # character split across reads is never mangled.
                            text = decoder.decode(chunk)
                            if text:
                                self.log(text)
                                tail = (tail + text)[-65536:]
                            continue
                        buffer += chunk
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            consume(line + b"\n")
                        if len(buffer) > 4 * 1024 * 1024:
                            consume(buffer)
                            buffer = b""
                if not structured:
                    text = decoder.decode(b"", final=True)
                    if text:
                        self.log(text)
                        tail = (tail + text)[-65536:]
                elif buffer:
                    consume(buffer)
            code = self.child.wait(timeout=5)
            if usage.pop("agent_error", False) and code == 0:
                code = 1
            return code, tail, usage
        finally:
            if self.child is not None:
                self.child.stdout.close()
                if self.child.poll() is None:
                    self.cleanup_child()
                self.child = None

    @staticmethod
    def render_event(event: dict, usage: dict) -> str:
        kind = event.get("type")
        if kind == "turn.completed":
            for key, value in event.get("usage", {}).items():
                if isinstance(value, (int, float)):
                    usage[key] = usage.get(key, 0) + value
        elif kind == "result":
            usage.update(event.get("usage") or {})
            if event.get("total_cost_usd") is not None:
                usage["cost_usd"] = event["total_cost_usd"]
            usage["agent_error"] = event.get("is_error", False)
            # Claude's result repeats the assistant message already streamed.
            result = str(event.get("result", ""))
            return "" if usage.pop("last_assistant_text", None) == result else result
        elif kind == "assistant":
            message = event.get("message", {})
            usage["model"] = message.get("model", usage.get("model", ""))
            text = "\n".join(block.get("text", "") for block in message.get("content", [])
                             if block.get("type") == "text")
            if text:
                usage["last_assistant_text"] = text
            return text
        elif kind == "item.completed":
            item = event.get("item", {})
            return str(item.get("text") or item.get("aggregated_output") or "")
        elif kind in {"error", "turn.failed"}:
            usage["agent_error"] = True
            return str(event.get("message") or event.get("error") or event)
        return ""

    def git(self, *args: str) -> str:
        result = subprocess.run(["git", *args], cwd=self.project, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else ""

    def completed_tasks(self) -> set[str]:
        path = self.project / "IMPLEMENTATION_PLAN.md"
        if not path.exists():
            return set()
        return set(re.findall(r"^\s*-\s*\[[xX]\]\s+\*{0,2}([\w.-]+)", path.read_text(), re.M))

    def marker(self, value: str) -> bool:
        path = self.project / "IMPLEMENTATION_PLAN.md"
        return path.exists() and any(line.strip().upper() == f"STATUS: {value}"
                                     for line in path.read_text().splitlines())

    def run_iteration(self) -> str:
        start, clock = now(), time.monotonic()
        self.iteration_deadline = clock + self.config.iteration_timeout_seconds
        before_tasks = self.completed_tasks()
        before_head = self.git("rev-parse", "--short=7", "HEAD")
        self.state("running", start=start)
        self.log(f"=== Iteration {self.iteration} (loop {self.iteration}/{self.config.max_iterations}) ===\n")
        prompt = (self.project / "PROMPT.md").read_text()
        injection = self.directory / "inject.md"
        if injection.exists():
            prompt += "\n\nUser instructions for this iteration:\n" + injection.read_text()
            injection.unlink()
        try:
            code, output, usage = self.execute(self.config.agent_command(), prompt, structured=True)
        except OSError as exc:
            code, output, usage = 127, str(exc), {}
        errors = [f"Agent exited with code {code}"] if code else []
        blocked = bool(code in {124, 127} or (code and re.search(
            r"usage limit|rate.?limit|quota exceeded|too many requests", output, re.I)))
        test_passed = None
        test_output = ""
        if self.config.test_command and not self.stopped and not blocked:
            self.log(f"Running tests: {self.config.test_command}\n")
            try:
                test_code, test_output, _ = self.execute(["bash", "-lc", self.config.test_command])
            except OSError as exc:
                test_code, test_output = 127, str(exc)
            test_passed = test_code == 0
            blocked = test_code in {124, 127}  # Timed out, or the command is missing.
            if not test_passed:
                errors.append("Tests failed")
        status = "cancelled" if self.stopped else "blocked" if blocked else "error" if errors else "success"
        usage.pop("last_assistant_text", None)
        # Canonical usage counts are raw tokens. `tokens` remains k-tokens for old clients.
        token_total = sum(usage.get(key, 0) for key in (
            "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        provider = "claude" if self.config.cli == "claude-code" else self.config.cli
        rate = self.config.model_pricing.get(provider, 0.006)
        head = self.git("rev-parse", "--short=7", "HEAD")
        record = {
            "schema_version": 2, "iteration": self.iteration, "max": self.config.max_iterations,
            "start": start, "end": now(), "duration_seconds": round(time.monotonic() - clock, 3),
            "tokens": token_total / 1000 if usage else None, "usage": usage,
            "provider": provider, "model": usage.get("model") or self.config.model,
            "cost_usd": usage.get("cost_usd", token_total / 1000 * rate) if usage else None,
            "cost_estimated": "cost_usd" not in usage, "cost_per_1k_tokens": rate,
            "status": status, "tasks_completed": sorted(self.completed_tasks() - before_tasks),
            "commit": head if head != before_head else None,
            "commit_message": self.git("log", "-1", "--pretty=%s") if head != before_head else None,
            "test_passed": test_passed, "test_output": test_output[-4000:], "errors": errors,
        }
        with (self.directory / "iterations.jsonl").open("a") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if status in {"success", "cancelled"}:
            (self.directory / "pending-notification.txt").unlink(missing_ok=True)
        else:
            self.notify("BLOCKED" if blocked else "ERROR", f"Iteration {self.iteration}: {status}",
                        "\n".join(errors) + "\n" + output[-2000:])
        return status

    def run(self) -> int:
        with process_lock(self.directory, "run.lock"):
            preflight(self.project, self.config)
            if os.getpgrp() != os.getpid():
                os.setsid()
            write_process_identity(self.directory, os.getpid())
            signal.signal(signal.SIGTERM, self.signal_stop)
            signal.signal(signal.SIGINT, self.signal_stop)
            last = read_last_jsonl_record(self.directory / "iterations.jsonl") or {}
            self.iteration = int(last.get("iteration", 0))
            (self.directory / "pending-notification.txt").unlink(missing_ok=True)
            self.state("ready")
            try:
                count = 0
                while not self.stopped and (self.config.max_iterations == 0 or count < self.config.max_iterations):
                    if (self.directory / "pause").exists():
                        self.state("paused")
                    while (self.directory / "pause").exists() and not self.stopped:
                        time.sleep(0.2)
                    if self.stopped:
                        break
                    count += 1
                    self.iteration += 1
                    status = self.run_iteration()
                    if status == "success" and (self.marker("COMPLETE") or self.marker("PLANNING_COMPLETE")):
                        complete = self.marker("COMPLETE")
                        self.notify("DONE" if complete else "PLANNING_COMPLETE",
                                    "All tasks complete" if complete else "Planning complete")
                        self.state("complete" if complete else "stopped")
                        return 0
                    if status == "cancelled":
                        self.state("stopped")
                        return 0
                    if status == "blocked":
                        self.state(status)
                        return 1
                if self.stopped:
                    self.state("stopped")
                    return 0
                self.notify("BLOCKED", "Max iterations reached", "Review the latest results before restarting.")
                self.state("blocked")
                return 1
            finally:
                self.cleanup_child()
                self.close_log()
                (self.directory / "ralph.pid").unlink(missing_ok=True)
                (self.directory / "process.json").unlink(missing_ok=True)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Run Ralph in the current project.")
    parser.add_argument("max_iterations", type=int, nargs="?")
    args = parser.parse_args()
    project = Path.cwd()
    runner = None
    try:
        runner = Runner(project, load_config(project, args.max_iterations))
        code = runner.run()
    except BlockingIOError:
        print("Ralph is already running in this project.", file=sys.stderr)
        code = 1
    except Exception as exc:
        if runner is not None:
            runner.notify("ERROR", "Loop failed", str(exc))
            runner.state("error", error=str(exc))
        print(f"Ralph: {exc}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    cli()
