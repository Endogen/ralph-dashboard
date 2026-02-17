"""LLM integration for generating project specs and plans."""

from __future__ import annotations

import json
import logging
import os

from app.wizard.schemas import GeneratedFile, GenerateRequest

LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert software architect and project planner. You create detailed, \
well-structured project specifications and implementation plans for AI coding agents.

You will receive a project description and tech stack preferences. Generate the \
following files as a JSON array of objects with "path" and "content" keys:

1. `specs/overview.md` — High-level project overview, goals, architecture, and key decisions.
2. `specs/features.md` — Detailed feature specifications with acceptance criteria.
3. `IMPLEMENTATION_PLAN.md` — A phased implementation plan with numbered tasks. \
   Use markdown checkboxes (- [ ] Task description) for each task. Group tasks into \
   phases (## Phase 1: ..., ## Phase 2: ..., etc). Start with foundational work and \
   build up to features.
4. `AGENTS.md` — Context file for the AI coding agent. Include: project description, \
   tech stack, build/test/lint commands, coding conventions, and important notes.
5. `PROMPT.md` — The prompt that will be fed to the AI coding agent each iteration \
   of the building loop. It should instruct the agent to read IMPLEMENTATION_PLAN.md, \
   pick the next unchecked task, implement it, run tests, and mark it done.

Important:
- Be thorough and specific in the implementation plan
- Break work into small, testable tasks (aim for 15-40 tasks total)
- Each task should be completable in one iteration by an AI agent
- Include setup tasks (project init, dependencies, config)
- Include testing tasks throughout, not just at the end
- The PROMPT.md should be a complete, self-contained instruction for one loop iteration
- Output ONLY valid JSON — no markdown fences, no commentary

Output format:
[
  {"path": "specs/overview.md", "content": "..."},
  {"path": "specs/features.md", "content": "..."},
  {"path": "IMPLEMENTATION_PLAN.md", "content": "..."},
  {"path": "AGENTS.md", "content": "..."},
  {"path": "PROMPT.md", "content": "..."}
]"""


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
    """Raised when ANTHROPIC_API_KEY is not set."""


async def generate_project_files(request: GenerateRequest) -> list[GeneratedFile]:
    """Call the Anthropic API to generate project specification files."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ApiKeyNotConfiguredError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Please configure it to use the project generation feature."
        )

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)
    user_prompt = _build_user_prompt(request)

    LOGGER.info("Generating project files for: %s", request.project_name)

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.AuthenticationError as exc:
        raise GenerationError("Invalid ANTHROPIC_API_KEY — authentication failed.") from exc
    except anthropic.APIError as exc:
        raise GenerationError(f"Anthropic API error: {exc}") from exc

    raw_text = ""
    for block in message.content:
        if block.type == "text":
            raw_text += block.text

    raw_text = raw_text.strip()

    # Strip markdown JSON fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line if it's closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_text = "\n".join(lines)

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

    LOGGER.info("Generated %d files for project: %s", len(files), request.project_name)
    return files
