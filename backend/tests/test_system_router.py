"""Tests for system metrics router."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.iterations.service import ProjectNotFoundError
from app.system.models import ProcessMetrics, ProjectSystemInfo, SystemMetrics
from app.system.router import get_system_info


def _make_system_info() -> ProjectSystemInfo:
    return ProjectSystemInfo(
        process=ProcessMetrics(
            pid=12345,
            rss_mb=50.0,
            children_rss_mb=20.0,
            total_rss_mb=70.0,
            cpu_percent=3.5,
            child_count=2,
        ),
        system=SystemMetrics(
            ram_total_mb=16384.0,
            ram_used_mb=8192.0,
            ram_available_mb=8192.0,
            ram_percent=50.0,
            cpu_load_1m=1.5,
            cpu_load_5m=1.2,
            cpu_load_15m=0.9,
            cpu_core_count=4,
            disk_total_gb=500.0,
            disk_used_gb=200.0,
            disk_free_gb=300.0,
            disk_percent=40.0,
            uptime_seconds=86400.0,
        ),
    )


@pytest.mark.anyio
async def test_get_system_info_success() -> None:
    expected = _make_system_info()
    with patch(
        "app.system.router.get_project_system_info",
        new_callable=AsyncMock,
        return_value=expected,
    ):
        result = await get_system_info("test-project")
    assert result == expected
    assert result.process.pid == 12345
    assert result.system.ram_total_mb == 16384.0


@pytest.mark.anyio
async def test_get_system_info_project_not_found() -> None:
    with patch(
        "app.system.router.get_project_system_info",
        new_callable=AsyncMock,
        side_effect=ProjectNotFoundError("Project not found: missing"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_system_info("missing")
        assert exc_info.value.status_code == 404
