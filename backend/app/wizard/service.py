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


class ProjectTargetValidationError(WizardServiceError):
    """Raised when wizard project target input is invalid."""


def _get_project_roots() -> list[Path]:
    """Return configured project roots as resolved absolute paths."""
    settings = get_settings()
    return [path.expanduser().resolve() for path in settings.project_dirs]


def _is_within_roots(path: Path, roots: list[Path]) -> bool:
    """Return whether path is equal to or nested under any configured root."""
    for root in roots:
        if path == root or path.is_relative_to(root):
            return True
    return False


def _resolve_target_project_dir(request: CreateRequest) -> tuple[Path, bool]:
    """Resolve target project path and whether it is a newly created directory."""
    roots = _get_project_roots()

    if request.project_mode == "existing":
        if not request.existing_project_path:
            raise ProjectTargetValidationError(
                "existing_project_path is required when project_mode is 'existing'"
            )
        project_dir = Path(request.existing_project_path).expanduser().resolve()
        if not project_dir.exists() or not project_dir.is_dir():
            raise ProjectTargetValidationError(
                f"Existing project path does not exist or is not a directory: {project_dir}"
            )
        if not _is_within_roots(project_dir, roots):
            roots_display = ", ".join(str(root) for root in roots)
            raise ProjectTargetValidationError(
                "Existing project path must be inside one of RALPH_PROJECT_DIRS: "
                f"{roots_display}"
            )
        return project_dir, False

    project_dir = roots[0] / request.project_name
    if project_dir.exists():
        raise ProjectDirectoryExistsError(f"Directory already exists: {project_dir}")
    return project_dir, True


def _build_loop_config(request: CreateRequest) -> dict[str, object]:
    """Build .ralph/config.json payload from wizard request."""
    cli_flags = ""
    if request.auto_approval == "full-auto":
        if request.cli == "codex":
            cli_flags = "-s danger-full-access"
        elif request.cli in ("claude", "claude-code"):
            cli_flags = "--dangerously-skip-permissions"

    config: dict[str, object] = {
        "cli": request.cli,
        "flags": cli_flags,
        "max_iterations": request.max_iterations,
        "test_command": request.test_command,
        "model_pricing": {"codex": 0.006, "claude": 0.015},
    }
    if request.model_override:
        config["model"] = request.model_override
    return config


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
    """Create or initialize a wizard target project on disk."""
    project_dir, is_new_project = _resolve_target_project_dir(request)

    try:
        if is_new_project:
            project_dir.mkdir(parents=True, exist_ok=False)

        ralph_dir = project_dir / ".ralph"
        ralph_dir.mkdir(parents=True, exist_ok=True)

        config = _build_loop_config(request)
        config_file = ralph_dir / "config.json"
        config_file.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

        # Write all generated files (with path containment check)
        resolved_project_dir = project_dir.resolve()
        for file_entry in request.files:
            file_path = (project_dir / file_entry.path).resolve()
            if not file_path.is_relative_to(resolved_project_dir):
                raise ProjectTargetValidationError(
                    f"File path escapes project directory: {file_entry.path}"
                )
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_entry.content, encoding="utf-8")

        if is_new_project:
            await asyncio.to_thread(_git_init_new_project, project_dir)
        else:
            await asyncio.to_thread(_ensure_git_repository, project_dir)

        project_id = project_id_from_path(project_dir)

        # Optionally start the loop
        started = False
        start_error: str | None = None
        if request.start_loop:
            started, start_error = await _start_project_loop(project_id)

        LOGGER.info(
            "%s project '%s' at %s",
            "Created" if is_new_project else "Prepared",
            request.project_name,
            project_dir,
        )
        return CreateResponse(
            project_id=project_id,
            project_path=str(project_dir),
            started=started,
            start_error=start_error,
        )

    except (ProjectDirectoryExistsError, ProjectCreationError, ProjectTargetValidationError):
        raise
    except Exception as exc:
        LOGGER.error("Failed to create project: %s", exc, exc_info=True)
        raise ProjectCreationError(f"Failed to create project: {exc}") from exc


def _ensure_git_repository(project_dir: Path) -> None:
    """Initialize git repository if project does not already have one."""
    if (project_dir / ".git").exists():
        return
    try:
        subprocess.run(
            ["git", "init"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        LOGGER.warning("Git init failed: %s", exc.stderr)
    except FileNotFoundError:
        LOGGER.warning("git not found on PATH — skipping git init")


def _git_init_new_project(project_dir: Path) -> None:
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


async def _start_project_loop(project_id: str) -> tuple[bool, str | None]:
    """Attempt to start the ralph loop for the newly created project."""
    try:
        from app.control.process_manager import start_project_loop

        await start_project_loop(project_id)
        return True, None
    except Exception as exc:
        LOGGER.warning("Failed to auto-start loop for %s", project_id, exc_info=True)
        reason = str(exc).strip() or exc.__class__.__name__
        return False, reason
