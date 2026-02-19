"""Tests for wizard LLM generator."""

from __future__ import annotations

import asyncio

import pytest

from app.wizard.generator import (
    ApiKeyNotConfiguredError,
    GenerationError,
    cancel_generation_request,
    generate_project_files,
)
from app.wizard import generator as wizard_generator_module
from app.wizard.schemas import GenerateRequest


class FakeProcess:
    def __init__(
        self,
        stdout: str,
        stderr: str = "",
        returncode: int | None = 0,
    ) -> None:
        self._stdout = stdout.encode("utf-8")
        self._stderr = stderr.encode("utf-8")
        self.returncode = returncode
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return self.returncode


@pytest.mark.anyio
async def test_generate_codex_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[tuple[object, ...], object, object]] = []

    async def _mock_subprocess_exec(*argv, stdout=None, stderr=None):
        captured.append((argv, stdout, stderr))
        output = """[
  {"path":"specs/overview.md","content":"# Overview"},
  {"path":"specs/features.md","content":"# Features"},
  {"path":"IMPLEMENTATION_PLAN.md","content":"# Plan"},
  {"path":"AGENTS.md","content":"# Agents"}
]"""
        return FakeProcess(stdout=output)

    monkeypatch.setattr(
        "app.wizard.generator.asyncio.create_subprocess_exec",
        _mock_subprocess_exec,
    )

    request = GenerateRequest(
        project_name="test-project",
        project_description="A simple test project",
        cli="codex",
        model_override="codex-5.3",
        request_id="req-1",
    )

    files = await generate_project_files(request)

    assert len(files) == 5
    assert files[-1].path == "PROMPT.md"
    assert captured
    argv = captured[0][0]
    assert argv[0:3] == ("codex", "exec", "--model")
    assert argv[3] == "codex-5.3"
    assert isinstance(argv[-1], str)
    assert "Project Description" in argv[-1]


@pytest.mark.anyio
async def test_generate_claude_json_wrapper_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_subprocess_exec(*_argv, **_kwargs):
        output = """{
  "result": "[{\\"path\\":\\"specs/overview.md\\",\\"content\\":\\"# Overview\\"},{\\"path\\":\\"specs/features.md\\",\\"content\\":\\"# Features\\"},{\\"path\\":\\"IMPLEMENTATION_PLAN.md\\",\\"content\\":\\"# Plan\\"},{\\"path\\":\\"AGENTS.md\\",\\"content\\":\\"# Agents\\"}]"
}"""
        return FakeProcess(stdout=output)

    monkeypatch.setattr(
        "app.wizard.generator.asyncio.create_subprocess_exec",
        _mock_subprocess_exec,
    )

    request = GenerateRequest(
        project_name="test-project",
        project_description="A simple test project",
        cli="claude",
    )

    files = await generate_project_files(request)

    assert any(file.path == "PROMPT.md" for file in files)
    assert any(file.path == "AGENTS.md" for file in files)


@pytest.mark.anyio
async def test_generate_raises_when_cli_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _mock_subprocess_exec(*_argv, **_kwargs):
        raise FileNotFoundError("codex not found")

    monkeypatch.setattr(
        "app.wizard.generator.asyncio.create_subprocess_exec",
        _mock_subprocess_exec,
    )

    request = GenerateRequest(
        project_name="test-project",
        project_description="A simple test project",
        cli="codex",
    )

    with pytest.raises(ApiKeyNotConfiguredError, match="CLI was not found"):
        await generate_project_files(request)


@pytest.mark.anyio
async def test_generate_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _mock_subprocess_exec(*_argv, **_kwargs):
        return FakeProcess(
            stdout="",
            stderr="invalid model",
            returncode=2,
        )

    monkeypatch.setattr(
        "app.wizard.generator.asyncio.create_subprocess_exec",
        _mock_subprocess_exec,
    )

    request = GenerateRequest(
        project_name="test-project",
        project_description="A simple test project",
        cli="codex",
    )

    with pytest.raises(GenerationError, match="exit 2"):
        await generate_project_files(request)


@pytest.mark.anyio
async def test_generate_kills_process_when_request_is_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess(stdout="")

    async def _mock_subprocess_exec(*_argv, **_kwargs):
        return process

    async def _mock_wait_for(_awaitable, timeout):
        _awaitable.close()
        raise asyncio.CancelledError()

    monkeypatch.setattr(
        "app.wizard.generator.asyncio.create_subprocess_exec",
        _mock_subprocess_exec,
    )
    monkeypatch.setattr(
        "app.wizard.generator.asyncio.wait_for",
        _mock_wait_for,
    )

    request = GenerateRequest(
        project_name="test-project",
        project_description="A simple test project",
        cli="codex",
        request_id="cancel-me",
    )

    with pytest.raises(asyncio.CancelledError):
        await generate_project_files(request)

    assert process.killed is True


@pytest.mark.anyio
async def test_cancel_generation_request_kills_registered_process() -> None:
    process = FakeProcess(stdout="", returncode=None)
    request_id = "req-cancel-1"
    wizard_generator_module._ACTIVE_GENERATIONS.clear()
    wizard_generator_module._ACTIVE_GENERATIONS[request_id] = process

    cancelled = await cancel_generation_request(request_id)

    assert cancelled is True
    assert process.killed is True
    assert request_id not in wizard_generator_module._ACTIVE_GENERATIONS


@pytest.mark.anyio
async def test_cancel_generation_request_returns_false_when_missing() -> None:
    wizard_generator_module._ACTIVE_GENERATIONS.clear()

    cancelled = await cancel_generation_request("missing-id")

    assert cancelled is False


@pytest.mark.anyio
async def test_generate_rejects_unsupported_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    request = GenerateRequest(
        project_name="test-project",
        project_description="A simple test project",
        cli="unknown-cli",
    )

    with pytest.raises(GenerationError, match="Unsupported CLI"):
        await generate_project_files(request)
