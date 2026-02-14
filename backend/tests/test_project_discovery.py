"""Tests for filesystem project discovery."""

from __future__ import annotations

import os
from pathlib import Path

from app.config import get_settings
from app.projects.discovery import discover_project_paths


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_discover_project_paths_from_explicit_roots(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    project_a = root / "alpha"
    project_b = root / "nested" / "beta"
    ignored = root / "node_modules" / "pkg"

    (project_a / ".ralph").mkdir(parents=True)
    (project_b / ".ralph").mkdir(parents=True)
    (ignored / ".ralph").mkdir(parents=True)

    discovered = discover_project_paths([root])

    assert discovered == sorted([project_a.resolve(), project_b.resolve()])


def test_discover_project_paths_from_settings(monkeypatch, tmp_path: Path) -> None:
    root_one = tmp_path / "one"
    root_two = tmp_path / "two"
    project_one = root_one / "demo"
    project_two = root_two / "demo-two"

    (project_one / ".ralph").mkdir(parents=True)
    (project_two / ".ralph").mkdir(parents=True)

    monkeypatch.setenv("RALPH_PROJECT_DIRS", f"{root_one}{os.pathsep}{root_two}")
    _clear_settings_cache()

    discovered = discover_project_paths()
    assert discovered == sorted([project_one.resolve(), project_two.resolve()])


def test_discover_project_paths_skips_missing_roots(tmp_path: Path) -> None:
    missing_root = tmp_path / "does-not-exist"
    existing_root = tmp_path / "existing"
    project = existing_root / "demo"

    (project / ".ralph").mkdir(parents=True)

    discovered = discover_project_paths([missing_root, existing_root])
    assert discovered == [project.resolve()]
