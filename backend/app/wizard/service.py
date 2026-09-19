"""Business logic for the project creation wizard."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import tempfile
import shutil
import os
import hashlib

from app.control.models import LoopConfig
from app.utils.files import atomic_write, contained_path
from app.utils.process import process_lock, read_pid, is_process_alive
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
    return LoopConfig(
        cli=request.cli, approval_mode=request.auto_approval,
        model=request.model_override, max_iterations=request.max_iterations,
        test_command=request.test_command,
    ).model_dump(mode="json")


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


def _prepare_project(request: CreateRequest, project_dir: Path, is_new: bool) -> None:
    # Validate every target before creating directories or replacing any file.
    payloads: dict[str, str] = {}
    for entry in request.files:
        relative = Path(entry.path)
        if relative.is_absolute() or any(part in {"..", ".git", ".ralph"} for part in relative.parts):
            raise ProjectTargetValidationError(f"Invalid generated file path: {entry.path}")
        try:
            contained_path(project_dir, entry.path)
        except ValueError as exc:
            raise ProjectTargetValidationError(str(exc)) from exc
        name = relative.as_posix()
        if name in payloads:
            raise ProjectTargetValidationError(f"Duplicate generated file: {name}")
        payloads[name] = entry.content
    payloads[".ralph/config.json"] = json.dumps(_build_loop_config(request), indent=2) + "\n"
    # Symlink containment applies to the managed config directory too.
    try:
        contained_path(project_dir, ".ralph/config.json")
    except ValueError as exc:
        raise ProjectTargetValidationError(str(exc)) from exc
    project_dir.parent.mkdir(parents=True, exist_ok=True)
    if is_new:
        staging = Path(tempfile.mkdtemp(prefix=".ralph-create-", dir=project_dir.parent))
        try:
            for name, content in payloads.items():
                atomic_write(staging / name, content)
            _git_init_new_project(staging)
            if project_dir.exists():
                raise ProjectDirectoryExistsError(f"Directory already exists: {project_dir}")
            os.rename(staging, project_dir)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    else:
        # Serialize dashboard writers and reject changes to active projects.
        with process_lock(get_settings().credentials_file.parent / "project-locks",
                          hashlib.sha256(str(project_dir).encode()).hexdigest() + ".lock"):
            pid = read_pid(project_dir / ".ralph/ralph.pid")
            if pid and is_process_alive(pid):
                raise ProjectTargetValidationError("Stop the loop before replacing project files")
            for name, expected in request.expected_versions.items():
                target = contained_path(project_dir, name)
                actual = hashlib.sha256(target.read_bytes() if target.exists() else b"").hexdigest()
                if actual != expected:
                    raise ProjectTargetValidationError(f"{name} changed since preview. Review the files again.")
            backups = {name: (project_dir / name).read_text() if (project_dir / name).exists() else None
                       for name in payloads}
            written = []
            created_directories = set()
            try:
                for name, content in payloads.items():
                    parent = (project_dir / name).parent
                    while parent != project_dir and not parent.exists():
                        created_directories.add(parent)
                        parent = parent.parent
                    atomic_write(contained_path(project_dir, name), content)
                    written.append(name)
                _ensure_git_repository(project_dir)
            except Exception:
                for name in reversed(written):
                    previous = backups[name]
                    if previous is None:
                        (project_dir / name).unlink(missing_ok=True)
                    else:
                        atomic_write(project_dir / name, previous)
                for directory in sorted(created_directories, key=lambda p: len(p.parts), reverse=True):
                    directory.rmdir()
                raise


async def create_project(request: CreateRequest) -> CreateResponse:
    """Validate and stage all files, publish, then reconcile discovery before start."""
    project_dir, is_new_project = _resolve_target_project_dir(request)
    try:
        await asyncio.to_thread(_prepare_project, request, project_dir, is_new_project)
    except (ProjectDirectoryExistsError, ProjectTargetValidationError):
        raise
    except Exception as exc:
        raise ProjectCreationError(f"Failed to create project: {exc}") from exc
    from app.projects.service import invalidate_discovery_cache
    from app.ws.file_watcher import file_watcher_service

    invalidate_discovery_cache()
    await file_watcher_service.refresh_projects()
    project_id = project_id_from_path(project_dir)
    started, start_error = await _start_project_loop(project_id) if request.start_loop else (False, None)
    return CreateResponse(project_id=project_id, project_path=str(project_dir),
                          started=started, start_error=start_error)


def _ensure_git_repository(project_dir: Path) -> None:
    """Initialize git repository if project does not already have one."""
    if (project_dir / ".git").exists():
        return
    subprocess.run(["git", "init"], cwd=project_dir, check=True,
                   capture_output=True, timeout=30)


def _git_init_new_project(project_dir: Path) -> None:
    """Initialize a git repository and make an initial commit."""
    _ensure_git_repository(project_dir)
    try:
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
        LOGGER.warning("Project created without an initial commit: %s", exc.stderr)
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


async def preview_project(request: CreateRequest) -> dict:
    project_dir, is_new = _resolve_target_project_dir(request)
    versions = {}
    files = []
    entries = [(entry.path, entry.content) for entry in request.files]
    entries.append((".ralph/config.json", json.dumps(_build_loop_config(request), indent=2) + "\n"))
    for name, content in entries:
        try:
            target = contained_path(project_dir, name)
        except ValueError as exc:
            raise ProjectTargetValidationError(str(exc)) from exc
        previous = target.read_text() if not is_new and target.is_file() else None
        versions[name] = hashlib.sha256((previous or "").encode()).hexdigest()
        files.append({"path": name, "previous": previous, "content": content,
                      "action": "update" if previous is not None else "create"})
    return {"files": files, "versions": versions}
