"""Business logic for the project creation wizard."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.wizard.schemas import CreateRequest, CreateResponse, GeneratedFile

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
    """Return default content templates for AGENTS.md and PROMPT.md."""
    agents_md = """\
# AGENTS.md

## Project Overview
[Project description goes here]

## Tech Stack
[Technologies used]

## Commands
- **Build:** [build command]
- **Test:** [test command]
- **Lint:** [lint command]
- **Run:** [run command]

## Coding Conventions
- Follow existing code style and patterns
- Write tests for new functionality
- Keep functions small and focused
- Use meaningful variable and function names

## Important Notes
- Read IMPLEMENTATION_PLAN.md before starting work
- Check off completed tasks in the plan
- Run tests after each change
- Commit after completing each task
"""

    prompt_md = """\
# Loop Iteration Prompt

You are an AI coding agent working on this project. Follow these steps each iteration:

1. **Read** `IMPLEMENTATION_PLAN.md` to understand the project plan
2. **Find** the next unchecked task (`- [ ]`) in the plan
3. **Implement** that task thoroughly:
   - Write clean, well-structured code
   - Follow patterns established in existing code
   - Add appropriate error handling
4. **Test** your changes:
   - Run the test suite
   - Fix any failures before proceeding
5. **Mark** the task as done in IMPLEMENTATION_PLAN.md (`- [x]`)
6. **Commit** your changes with a descriptive message

If all tasks are checked, report completion. If you encounter a blocker, \
document it clearly and move to the next task if possible.
"""
    return {"agents_md": agents_md, "prompt_md": prompt_md}


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
        config = {
            "cli": request.cli,
            "flags": "",
            "max_iterations": request.max_iterations,
            "test_command": request.test_command,
            "model_pricing": {"codex": 0.006, "claude": 0.015},
        }
        if request.auto_approval == "full-auto":
            config["flags"] = "--full-auto"
        config_file = ralph_dir / "config.json"
        config_file.write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )

        # Write all generated files
        for file_entry in request.files:
            file_path = project_dir / file_entry.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_entry.content, encoding="utf-8")

        # Initialize git repo
        _git_init(project_dir)

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
