"""Loop process control models."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ProcessStartResult(BaseModel):
    project_id: str
    pid: int
    command: list[str]


class LoopConfig(BaseModel):
    cli: str = "codex"
    flags: str = ""
    # 0 means unlimited iterations.
    max_iterations: int = Field(default=20, ge=0)
    test_command: str = ""
    model_pricing: dict[str, float] = Field(
        default_factory=lambda: {"codex": 0.006, "claude": 0.015}
    )

    @field_validator("cli")
    @classmethod
    def _validate_cli(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("cli cannot be empty")
        return normalized

    @field_validator("flags", "test_command")
    @classmethod
    def _normalize_command_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("model_pricing")
    @classmethod
    def _validate_model_pricing(cls, value: dict[str, float]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for model, price in value.items():
            model_name = model.strip()
            if not model_name:
                raise ValueError("model_pricing keys cannot be empty")
            numeric_price = float(price)
            if numeric_price < 0:
                raise ValueError("model_pricing values must be non-negative")
            normalized[model_name] = numeric_price
        return normalized
