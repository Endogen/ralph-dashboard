"""Project discovery utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from app.config import get_settings

IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


def discover_project_paths(project_dirs: Iterable[Path] | None = None) -> list[Path]:
    """Discover projects by scanning for directories containing `.ralph/`."""
    roots = list(project_dirs) if project_dirs is not None else get_settings().project_dirs
    discovered: set[Path] = set()

    for root in roots:
        resolved_root = root.expanduser().resolve()
        if not resolved_root.exists() or not resolved_root.is_dir():
            continue

        for current_root, dirnames, _ in os.walk(resolved_root):
            dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRS]
            if ".ralph" in dirnames:
                discovered.add(Path(current_root).resolve())
                dirnames.remove(".ralph")

    return sorted(discovered)
