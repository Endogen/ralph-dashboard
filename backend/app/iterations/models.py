"""Iteration API models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IterationSummary(BaseModel):
    number: int
    max_iterations: int | None = None
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    duration_seconds: float | None = None
    tokens_used: float | None = None
    status: str | None = None
    has_errors: bool = False
    errors: list[str] = Field(default_factory=list)
    tasks_completed: list[str] = Field(default_factory=list)
    commit: str | None = None
    test_passed: bool | None = None


class IterationDetail(IterationSummary):
    log_output: str = ""


class IterationListResponse(BaseModel):
    iterations: list[IterationSummary] = Field(default_factory=list)
    total: int = 0
