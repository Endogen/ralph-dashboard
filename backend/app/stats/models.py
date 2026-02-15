"""Stats domain models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VelocityStats(BaseModel):
    tasks_per_hour: float = 0.0
    tasks_remaining: int = 0
    hours_remaining: float = 0.0


class HealthBreakdown(BaseModel):
    productive: int = 0
    partial: int = 0
    failed: int = 0


class PhaseTokenUsage(BaseModel):
    phase: str
    tokens: float


class ProjectStats(BaseModel):
    total_iterations: int = 0
    total_tokens: float = 0.0
    total_cost_usd: float = 0.0
    total_duration_seconds: float = 0.0
    avg_iteration_duration_seconds: float = 0.0
    avg_tokens_per_iteration: float = 0.0
    tasks_done: int = 0
    tasks_total: int = 0
    errors_count: int = 0
    projected_completion: str | None = None
    projected_total_cost_usd: float = 0.0
    velocity: VelocityStats = Field(default_factory=VelocityStats)
    health_breakdown: HealthBreakdown = Field(default_factory=HealthBreakdown)
    tokens_by_phase: list[PhaseTokenUsage] = Field(default_factory=list)
    cost_per_1k_tokens: float = 0.006
