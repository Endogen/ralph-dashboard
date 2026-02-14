"""Services for project specs/*.md CRUD operations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.projects.service import get_project_detail


class SpecsServiceError(Exception):
    """Base specs service error."""


class SpecsProjectNotFoundError(SpecsServiceError):
    """Raised when project id cannot be resolved."""


class SpecNotFoundError(SpecsServiceError):
    """Raised when requested spec file does not exist."""


class SpecAlreadyExistsError(SpecsServiceError):
    """Raised when creating a spec that already exists."""


class SpecValidationError(SpecsServiceError):
    """Raised when spec filename is invalid."""


def _validate_spec_name(name: str) -> str:
    candidate = name.strip()
    if not candidate or "/" in candidate or "\\" in candidate:
        raise SpecValidationError("Spec name must be a single filename")
    if not candidate.endswith(".md"):
        raise SpecValidationError("Spec name must end with .md")
    if candidate in {".", ".."}:
        raise SpecValidationError("Invalid spec filename")
    return candidate


async def _resolve_specs_dir(project_id: str) -> Path:
    project = await get_project_detail(project_id)
    if project is None:
        raise SpecsProjectNotFoundError(f"Project not found: {project_id}")
    return project.path / "specs"


def _isoformat_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=UTC).isoformat()


async def list_specs(project_id: str) -> list[dict[str, str | int]]:
    """List markdown spec files for a project."""
    specs_dir = await _resolve_specs_dir(project_id)
    if not specs_dir.exists() or not specs_dir.is_dir():
        return []

    items: list[dict[str, str | int]] = []
    for file_path in sorted(specs_dir.glob("*.md")):
        stat = file_path.stat()
        items.append(
            {
                "name": file_path.name,
                "size": stat.st_size,
                "modified": _isoformat_timestamp(stat.st_mtime),
            }
        )
    return items


async def read_spec(project_id: str, name: str) -> tuple[str, str]:
    """Read spec file content."""
    specs_dir = await _resolve_specs_dir(project_id)
    valid_name = _validate_spec_name(name)
    target = specs_dir / valid_name
    if not target.exists() or not target.is_file():
        raise SpecNotFoundError(f"Spec not found: {valid_name}")
    return valid_name, target.read_text(encoding="utf-8")


async def create_spec(project_id: str, name: str, content: str) -> tuple[str, str]:
    """Create a new spec file."""
    specs_dir = await _resolve_specs_dir(project_id)
    valid_name = _validate_spec_name(name)
    specs_dir.mkdir(parents=True, exist_ok=True)
    target = specs_dir / valid_name
    if target.exists():
        raise SpecAlreadyExistsError(f"Spec already exists: {valid_name}")
    target.write_text(content, encoding="utf-8")
    return valid_name, content


async def update_spec(project_id: str, name: str, content: str) -> tuple[str, str]:
    """Update an existing spec file."""
    specs_dir = await _resolve_specs_dir(project_id)
    valid_name = _validate_spec_name(name)
    target = specs_dir / valid_name
    if not target.exists() or not target.is_file():
        raise SpecNotFoundError(f"Spec not found: {valid_name}")
    target.write_text(content, encoding="utf-8")
    return valid_name, content


async def delete_spec(project_id: str, name: str) -> None:
    """Delete an existing spec file."""
    specs_dir = await _resolve_specs_dir(project_id)
    valid_name = _validate_spec_name(name)
    target = specs_dir / valid_name
    if not target.exists() or not target.is_file():
        raise SpecNotFoundError(f"Spec not found: {valid_name}")
    target.unlink()
