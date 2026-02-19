"""LLM integration for generating project specs and plans."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from asyncio.subprocess import PIPE

from app.wizard.schemas import GeneratedFile, GenerateRequest

LOGGER = logging.getLogger(__name__)
_ACTIVE_GENERATIONS: dict[str, asyncio.subprocess.Process] = {}
_ACTIVE_GENERATIONS_LOCK = asyncio.Lock()

SYSTEM_PROMPT = """\
You are an expert software architect and project planner. You create detailed, \
well-structured project specifications and implementation plans for AI coding agents.

You will receive a project description and tech stack preferences. Generate the \
following files as a JSON array of objects with "path" and "content" keys:

1. `specs/overview.md` — High-level project overview, goals, tech stack, architecture, \
   success criteria, and non-goals.
2. `specs/features.md` — Detailed feature specifications with acceptance criteria.
3. `IMPLEMENTATION_PLAN.md` — A phased implementation plan with numbered tasks. \
   Use markdown checkboxes with numbered task IDs in this exact format: \
   `- [ ] 1.1 — Task description` (phase.task number, space, em-dash, space, description). \
   Group tasks into phases (## Phase 1: ..., ## Phase 2: ..., etc). \
   Start with foundational work and build up to features. \
   Do NOT include any STATUS markers — the loop manages those.
4. `AGENTS.md` — Context file for the AI coding agent. Include: project description, \
   tech stack, build/test/lint commands, project structure, coding conventions. \
   Include a Backpressure section with lint and test commands to run after each task.

Do NOT generate PROMPT.md — it is a fixed template provided separately.

Important:
- Be thorough and specific in the implementation plan
- Break work into small, testable tasks (aim for 15-40 tasks total)
- Each task should be completable in one iteration by an AI agent
- Include setup tasks (project init, dependencies, config)
- Include testing tasks throughout, not just at the end
- Output ONLY valid JSON — no markdown fences, no commentary

Output format:
[
  {"path": "specs/overview.md", "content": "..."},
  {"path": "specs/features.md", "content": "..."},
  {"path": "IMPLEMENTATION_PLAN.md", "content": "..."},
  {"path": "AGENTS.md", "content": "..."}
]"""

# Fixed PROMPT.md template — never AI-generated, always the same.
# Enforces single-task-per-iteration so ralph.sh can track each task.
BUILDING_PROMPT_TEMPLATE = """\
# Ralph BUILDING Loop

## Goal
{goal}

## Context
- Read: specs/*.md (requirements and design)
- Read: IMPLEMENTATION_PLAN.md (your task list)
- Read: AGENTS.md (test commands, project conventions, learnings, human decisions)

## Rules
1. Pick the **single** highest priority incomplete task from IMPLEMENTATION_PLAN.md
2. Investigate the relevant code BEFORE making changes
3. Implement **only that one task** — do NOT continue to the next task
4. Run the backpressure commands from AGENTS.md (lint, test)
5. If tests pass:
   - Commit with a clear, conventional message (feat:, fix:, refactor:, etc.)
   - Mark the task as done in IMPLEMENTATION_PLAN.md: `- [x] Task`
6. If tests fail:
   - Attempt to fix (max 3 tries per task)
   - If still failing after 3 attempts, notify for help
7. Update AGENTS.md with any operational learnings
8. **Stop.** The outer loop will invoke you again for the next task.

## Error Handling
If you encounter issues:
- Missing dependency: Try to add it, if unsure notify
- Unclear requirement: Check specs/ and AGENTS.md (Human Decisions section), \
if still unclear notify
- Repeated test failures: Notify after 3 attempts
- Blocked by external factor: Notify immediately

## Notifications
The outer loop (ralph.sh) handles most notifications automatically (errors, progress, completion).
You only need to write a notification when YOU are blocked and need human input:

```bash
mkdir -p .ralph
cat > .ralph/pending-notification.txt << 'NOTIF'
{{"timestamp":"$(date -Iseconds)","prefix":"DECISION","message":"Brief description of what you need","details":"Full context","status":"pending"}}
NOTIF
```

Use prefix `DECISION` for design choices, `BLOCKED` for missing deps/credentials.

## Completion
When ALL tasks in IMPLEMENTATION_PLAN.md are marked done:
1. Run final test suite to verify everything works
2. Add this line to IMPLEMENTATION_PLAN.md: `STATUS: COMPLETE`
"""


def _build_user_prompt(request: GenerateRequest) -> str:
    """Build the user prompt from the generation request."""
    parts = [
        f"## Project Name\n{request.project_name}",
        f"\n## Project Description\n{request.project_description}",
    ]
    if request.tech_stack:
        parts.append(f"\n## Tech Stack Preferences\n{', '.join(request.tech_stack)}")
    if request.cli:
        parts.append(f"\n## AI Coding Agent\n{request.cli}")
    if request.test_command:
        parts.append(f"\n## Test Command\n{request.test_command}")
    return "\n".join(parts)


class GenerationError(Exception):
    """Raised when LLM generation fails."""


class ApiKeyNotConfiguredError(GenerationError):
    """Raised when generation tooling is unavailable."""


async def _register_generation_process(
    request_id: str,
    process: asyncio.subprocess.Process,
) -> None:
    """Register an in-flight generation process for cancellation by request id."""
    async with _ACTIVE_GENERATIONS_LOCK:
        _ACTIVE_GENERATIONS[request_id] = process


async def _unregister_generation_process(
    request_id: str,
    process: asyncio.subprocess.Process,
) -> None:
    """Remove a generation process from the active process map."""
    async with _ACTIVE_GENERATIONS_LOCK:
        current = _ACTIVE_GENERATIONS.get(request_id)
        if current is process:
            _ACTIVE_GENERATIONS.pop(request_id, None)


async def cancel_generation_request(request_id: str) -> bool:
    """Cancel an in-flight generation process by request id."""
    normalized = request_id.strip()
    if not normalized:
        return False

    async with _ACTIVE_GENERATIONS_LOCK:
        process = _ACTIVE_GENERATIONS.pop(normalized, None)

    if process is None:
        return False

    if process.returncode is not None:
        return True

    try:
        process.kill()
    except ProcessLookupError:
        return True

    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        LOGGER.warning("Timed out while waiting for cancelled generation process to stop: %s", normalized)

    return True


def _build_generation_prompt(request: GenerateRequest) -> str:
    """Build the full prompt passed to the selected coding CLI."""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "Generate files for this project request:\n\n"
        f"{_build_user_prompt(request)}"
    )


def _resolve_cli_command(request: GenerateRequest) -> tuple[list[str], str]:
    """Return subprocess command argv and normalized CLI id."""
    cli = request.cli.strip().lower()
    model_override = request.model_override.strip()

    if cli in ("claude", "claude-code"):
        command = ["claude", "--print", "--output-format", "json"]
        if model_override:
            command.extend(["--model", model_override])
        return command, "claude"
    if cli == "codex":
        command = ["codex", "exec"]
        if model_override:
            command.extend(["--model", model_override])
        return command, "codex"

    raise GenerationError(
        f"Unsupported CLI '{request.cli}' for wizard generation. "
        "Use 'claude' or 'codex'."
    )


def _extract_claude_result(raw_output: str) -> str:
    """Extract textual result from Claude JSON output when available."""
    text = raw_output.strip()
    if not text:
        return ""

    candidates = [text]
    lines = text.splitlines()
    if lines:
        candidates.append(lines[-1].strip())

    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            result = payload.get("result")
            if isinstance(result, str):
                return result.strip()

    # Fall back to raw output if we cannot parse the structured wrapper.
    return text


def _extract_model_text(cli_id: str, raw_output: str) -> str:
    """Extract model-generated text from CLI stdout."""
    if cli_id == "claude":
        return _extract_claude_result(raw_output)
    return raw_output.strip()


def _strip_json_fence(raw_text: str) -> str:
    """Strip a leading/trailing markdown JSON fence if present."""
    stripped = raw_text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.split("\n")
    # Remove first line (```json or ```)
    lines = lines[1:]
    # Remove last line if it's closing fence
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


async def generate_project_files(request: GenerateRequest) -> list[GeneratedFile]:
    """Generate project files by invoking the selected coding CLI."""
    command, cli_id = _resolve_cli_command(request)
    prompt = _build_generation_prompt(request)

    LOGGER.info(
        "Generating project files for: %s (cli=%s, model_override=%s)",
        request.project_name,
        request.cli,
        bool(request.model_override.strip()),
    )

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            prompt,
            stdout=PIPE,
            stderr=PIPE,
        )
    except FileNotFoundError as exc:
        raise ApiKeyNotConfiguredError(
            f"'{command[0]}' CLI was not found on PATH. Install/configure it to use project generation."
        ) from exc
    except Exception as exc:
        raise GenerationError(f"Failed to start {command[0]} CLI: {exc}") from exc

    request_id = request.request_id.strip()
    if request_id:
        await _register_generation_process(request_id, process)

    timeout_seconds = int(os.getenv("RALPH_WIZARD_GENERATION_TIMEOUT_SECONDS", "600"))
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise GenerationError(
            f"{command[0]} CLI generation timed out after {timeout_seconds} seconds."
        ) from exc
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        LOGGER.info("Wizard generation cancelled by client for project: %s", request.project_name)
        raise
    finally:
        if request_id:
            await _unregister_generation_process(request_id, process)

    output = stdout.decode("utf-8", errors="replace")
    error_output = stderr.decode("utf-8", errors="replace").strip()
    if process.returncode != 0:
        detail = error_output or output.strip() or "no error output"
        raise GenerationError(
            f"{command[0]} CLI generation failed (exit {process.returncode}): {detail}"
        )

    raw_text = _extract_model_text(cli_id, output)
    if not raw_text:
        raise GenerationError(f"{command[0]} CLI returned empty output.")

    raw_text = _strip_json_fence(raw_text)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        LOGGER.error("Failed to parse LLM response as JSON: %s", raw_text[:500])
        raise GenerationError("LLM returned invalid JSON — please try regenerating.") from exc

    if not isinstance(parsed, list):
        raise GenerationError("LLM response was not a JSON array — please try regenerating.")

    files: list[GeneratedFile] = []
    for item in parsed:
        if isinstance(item, dict) and "path" in item and "content" in item:
            files.append(GeneratedFile(path=str(item["path"]), content=str(item["content"])))

    if not files:
        raise GenerationError("LLM returned no valid files — please try regenerating.")

    # Append the fixed PROMPT.md template (never AI-generated)
    goal = request.project_description.strip().split("\n")[0]  # First line as goal
    prompt_content = BUILDING_PROMPT_TEMPLATE.format(goal=goal)
    files.append(GeneratedFile(path="PROMPT.md", content=prompt_content))

    LOGGER.info("Generated %d files for project: %s", len(files), request.project_name)
    return files
