"""System metrics collection service."""

from __future__ import annotations

import os
import time
from pathlib import Path

import psutil

from app.iterations.service import ProjectNotFoundError
from app.projects.service import get_project_detail
from app.system.models import ProcessMetrics, ProjectSystemInfo, SystemMetrics


def _read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists() or not pid_file.is_file():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (TypeError, ValueError):
        return None


def get_process_metrics(pid_file: Path) -> ProcessMetrics:
    """Read PID from .ralph/ralph.pid and gather process tree metrics."""
    pid = _read_pid(pid_file)
    if pid is None:
        return ProcessMetrics()

    try:
        proc = psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return ProcessMetrics(pid=pid)

    try:
        mem_info = proc.memory_info()
        rss_mb = mem_info.rss / (1024 * 1024)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        rss_mb = 0.0

    children_rss_mb = 0.0
    child_count = 0
    try:
        children = proc.children(recursive=True)
        child_count = len(children)
        for child in children:
            try:
                children_rss_mb += child.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    cpu_percent = 0.0
    try:
        cpu_percent = proc.cpu_percent(interval=0)
        for child in proc.children(recursive=True):
            try:
                cpu_percent += child.cpu_percent(interval=0)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return ProcessMetrics(
        pid=pid,
        rss_mb=round(rss_mb, 1),
        children_rss_mb=round(children_rss_mb, 1),
        total_rss_mb=round(rss_mb + children_rss_mb, 1),
        cpu_percent=round(cpu_percent, 1),
        child_count=child_count,
    )


def get_system_metrics(project_path: Path) -> SystemMetrics:
    """Gather system-wide metrics."""
    vm = psutil.virtual_memory()
    load_avg = os.getloadavg()
    cpu_count = psutil.cpu_count() or 1
    disk = psutil.disk_usage(str(project_path))
    uptime = time.time() - psutil.boot_time()

    return SystemMetrics(
        ram_total_mb=round(vm.total / (1024 * 1024), 1),
        ram_used_mb=round(vm.used / (1024 * 1024), 1),
        ram_available_mb=round(vm.available / (1024 * 1024), 1),
        ram_percent=round(vm.percent, 1),
        cpu_load_1m=round(load_avg[0], 2),
        cpu_load_5m=round(load_avg[1], 2),
        cpu_load_15m=round(load_avg[2], 2),
        cpu_core_count=cpu_count,
        disk_total_gb=round(disk.total / (1024 ** 3), 1),
        disk_used_gb=round(disk.used / (1024 ** 3), 1),
        disk_free_gb=round(disk.free / (1024 ** 3), 1),
        disk_percent=round(disk.percent, 1),
        uptime_seconds=round(uptime, 0),
    )


async def get_project_system_info(project_id: str) -> ProjectSystemInfo:
    """Resolve project path and gather process + system metrics."""
    import asyncio

    project = await get_project_detail(project_id)
    if project is None:
        raise ProjectNotFoundError(f"Project not found: {project_id}")

    project_path = project.path
    pid_file = project_path / ".ralph" / "ralph.pid"

    # psutil calls block on /proc reads — run in thread pool
    process, system = await asyncio.gather(
        asyncio.to_thread(get_process_metrics, pid_file),
        asyncio.to_thread(get_system_metrics, project_path),
    )

    return ProjectSystemInfo(process=process, system=system)
