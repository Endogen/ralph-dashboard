"""System metrics domain models."""

from __future__ import annotations

from pydantic import BaseModel


class ProcessMetrics(BaseModel):
    pid: int | None = None
    rss_mb: float = 0.0  # Resident Set Size in MB
    children_rss_mb: float = 0.0  # RSS of child processes in MB
    total_rss_mb: float = 0.0  # pid + children combined
    cpu_percent: float = 0.0  # CPU % of process tree
    child_count: int = 0


class SystemMetrics(BaseModel):
    # RAM
    ram_total_mb: float
    ram_used_mb: float
    ram_available_mb: float
    ram_percent: float
    # CPU
    cpu_load_1m: float
    cpu_load_5m: float
    cpu_load_15m: float
    cpu_core_count: int
    # Disk (project mount point)
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_percent: float
    # Uptime
    uptime_seconds: float


class ProjectSystemInfo(BaseModel):
    process: ProcessMetrics
    system: SystemMetrics
