"""Business logic for the project creation wizard."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.wizard.generator import BUILDING_PROMPT_TEMPLATE
from app.wizard.schemas import CreateRequest, CreateResponse

LOGGER = logging.getLogger(__name__)


class WizardServiceError(Exception):
    """Base error for wizard service operations."""


class ProjectDirectoryExistsError(WizardServiceError):
    """Raised when the target project directory already exists."""


class ProjectCreationError(WizardServiceError):
    """Raised when project creation fails."""


def _get_projects_root() -> Path:
    """Return the first configured project directory as the root for new projects."""
    settings = get_settings()
    return settings.project_dirs[0]


def get_default_templates() -> dict[str, str]:
    """Return built-in AGENTS/PROMPT templates for the wizard preview endpoint."""
    agents_template = """# AGENTS.md

## Project
Describe your project goals, scope, and constraints.

## Commands
- Build: ...
- Test: ...
- Lint: ...

## Conventions
- Code style, architecture, and repository rules.

## Backpressure
Run lint/tests after each implementation step.
"""
    prompt_template = (
        "# Prompt.md\n\n" + BUILDING_PROMPT_TEMPLATE.format(goal="[Describe what you want to build]")
    )
    return {"agents_md": agents_template, "prompt_md": prompt_template}


async def create_project(request: CreateRequest) -> CreateResponse:
    """Create a new project on disk from wizard output."""
    projects_root = _get_projects_root()
    project_dir = projects_root / request.project_name

    if project_dir.exists():
        raise ProjectDirectoryExistsError(
            f"Directory already exists: {project_dir}"
        )

    try:
        # Create project directory
        project_dir.mkdir(parents=True, exist_ok=False)

        # Create .ralph directory
        ralph_dir = project_dir / ".ralph"
        ralph_dir.mkdir()

        # Write config.json
        # Map approval mode to correct CLI flags
        cli_flags = ""
        if request.auto_approval == "full-auto":
            if request.cli == "codex":
                cli_flags = "-s danger-full-access -a never"
            elif request.cli in ("claude", "claude-code"):
                cli_flags = "--dangerously-skip-permissions"
        config = {
            "cli": request.cli,
            "flags": cli_flags,
            "max_iterations": request.max_iterations,
            "test_command": request.test_command,
            "model_pricing": {"codex": 0.006, "claude": 0.015, "claude-code": 0.015},
        }
        if request.model_override:
            config["model"] = request.model_override
        config_file = ralph_dir / "config.json"
        config_file.write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )

        # Write all generated files (with path containment check)
        resolved_project_dir = project_dir.resolve()
        for file_entry in request.files:
            file_path = (project_dir / file_entry.path).resolve()
            if not file_path.is_relative_to(resolved_project_dir):
                raise ProjectCreationError(
                    f"File path escapes project directory: {file_entry.path}"
                )
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_entry.content, encoding="utf-8")

        # Initialize git repo (subprocess calls — run in thread pool)
        await asyncio.to_thread(_git_init, project_dir)

        project_id = project_id_from_path(project_dir)

        # Optionally start the loop
        started = False
        if request.start_loop:
            started = await _start_project_loop(project_id)

        LOGGER.info("Created project '%s' at %s", request.project_name, project_dir)
        return CreateResponse(
            project_id=project_id,
            project_path=str(project_dir),
            started=started,
        )

    except (ProjectDirectoryExistsError, ProjectCreationError):
        raise
    except Exception as exc:
        LOGGER.error("Failed to create project: %s", exc, exc_info=True)
        raise ProjectCreationError(f"Failed to create project: {exc}") from exc


def _git_init(project_dir: Path) -> None:
    """Initialize a git repository and make an initial commit."""
    try:
        subprocess.run(
            ["git", "init"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "add", "-A"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial project setup from wizard"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        LOGGER.warning("Git init failed: %s", exc.stderr)
    except FileNotFoundError:
        LOGGER.warning("git not found on PATH — skipping git init")


async def _start_project_loop(project_id: str) -> bool:
    """Attempt to start the ralph loop for the newly created project."""
    try:
        from app.control.process_manager import start_project_loop

        await start_project_loop(project_id)
        return True
    except Exception:
        LOGGER.warning("Failed to auto-start loop for %s", project_id, exc_info=True)
        return False
