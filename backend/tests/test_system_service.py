"""Tests for system metrics service."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import get_settings
from app.projects.models import project_id_from_path
from app.system.models import ProcessMetrics, SystemMetrics
from app.system.service import get_process_metrics, get_system_metrics, get_project_system_info


def test_get_process_metrics_missing_pid_file(tmp_path: Path) -> None:
    pid_file = tmp_path / ".ralph" / "ralph.pid"
    result = get_process_metrics(pid_file)
    assert result == ProcessMetrics()
    assert result.pid is None


def test_get_process_metrics_stale_pid(tmp_path: Path) -> None:
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    pid_file = ralph_dir / "ralph.pid"
    pid_file.write_text("999999999", encoding="utf-8")

    result = get_process_metrics(pid_file)
    assert result.pid == 999999999
    assert result.rss_mb == 0.0
    assert result.total_rss_mb == 0.0


def test_get_process_metrics_valid_pid(tmp_path: Path) -> None:
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    pid_file = ralph_dir / "ralph.pid"
    pid_file.write_text(str(os.getpid()), encoding="utf-8")

    result = get_process_metrics(pid_file)
    assert result.pid == os.getpid()
    assert result.rss_mb > 0.0
    assert result.total_rss_mb >= result.rss_mb


def test_get_process_metrics_invalid_pid_content(tmp_path: Path) -> None:
    ralph_dir = tmp_path / ".ralph"
    ralph_dir.mkdir()
    pid_file = ralph_dir / "ralph.pid"
    pid_file.write_text("not-a-number", encoding="utf-8")

    result = get_process_metrics(pid_file)
    assert result == ProcessMetrics()


def test_get_system_metrics_returns_sensible_values(tmp_path: Path) -> None:
    result = get_system_metrics(tmp_path)

    assert isinstance(result, SystemMetrics)
    assert result.ram_total_mb > 0
    assert result.ram_used_mb > 0
    assert result.ram_available_mb > 0
    assert 0 <= result.ram_percent <= 100

    assert result.cpu_load_1m >= 0
    assert result.cpu_load_5m >= 0
    assert result.cpu_load_15m >= 0
    assert result.cpu_core_count >= 1

    assert result.disk_total_gb > 0
    assert result.disk_used_gb >= 0
    assert result.disk_free_gb >= 0
    assert 0 <= result.disk_percent <= 100

    assert result.uptime_seconds > 0


@pytest.mark.anyio
async def test_get_project_system_info_known_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "sys-project"
    project_id = project_id_from_path(project)
    ralph_dir = project / ".ralph"
    ralph_dir.mkdir(parents=True)
    (ralph_dir / "ralph.pid").write_text(str(os.getpid()), encoding="utf-8")

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(workspace))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    result = await get_project_system_info(project_id)
    assert result.process.pid == os.getpid()
    assert result.process.rss_mb > 0
    assert result.system.ram_total_mb > 0
    assert result.system.cpu_core_count >= 1


@pytest.mark.anyio
async def test_get_project_system_info_unknown_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path / "workspace"))
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(tmp_path / "credentials.yaml"))
    get_settings.cache_clear()

    from app.iterations.service import ProjectNotFoundError

    with pytest.raises(ProjectNotFoundError):
        await get_project_system_info("nonexistent")
