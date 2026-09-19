"""Shared, versioned loop configuration for wizard, API and runner."""
from __future__ import annotations

import shlex
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProcessStartResult(BaseModel):
    project_id: str
    pid: int
    command: list[str]


class LoopConfig(BaseModel):
    # Preserve forward-compatible fields when an older dashboard saves config.
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    cli: str = "codex"
    flags: str = ""
    model: str = ""
    approval_mode: Literal["sandboxed", "full-auto"] = "sandboxed"
    max_iterations: int = Field(default=20, ge=0)
    test_command: str = ""
    iteration_timeout_seconds: int = Field(default=3600, ge=1)
    model_pricing: dict[str, float] = Field(
        default_factory=lambda: {"codex": 0.006, "claude": 0.015}
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_permissions(cls, value):
        if isinstance(value, dict) and "approval_mode" not in value:
            value = dict(value)
            flags = shlex.split(str(value.get("flags", "")))
            if "--dangerously-skip-permissions" in flags or "danger-full-access" in flags:
                value["approval_mode"] = "full-auto"
        return value

    @field_validator("cli")
    @classmethod
    def validate_cli(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("cli cannot be empty")
        return value

    @field_validator("flags", "test_command", "model")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("flags")
    @classmethod
    def validate_flags(cls, value: str) -> str:
        shlex.split(value)  # Report malformed quoting at save time.
        return value

    @field_validator("model_pricing")
    @classmethod
    def validate_pricing(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not key.strip() or price < 0 for key, price in value.items()):
            raise ValueError("model_pricing requires nonempty names and nonnegative prices")
        return {key.strip(): price for key, price in value.items()}

    def agent_command(self) -> list[str]:
        """One authoritative command builder; explicit permission mode wins."""
        flags = shlex.split(self.flags)
        # Permission/model/output switches have dedicated settings. Remove old
        # generated permission flags when migrating older config files.
        reserved = {"-s", "--sandbox", "--permission-mode", "--output-format", "--model", "-m"}
        clean: list[str] = []
        skip = False
        for flag in flags:
            if skip:
                skip = False
                continue
            key = flag.split("=", 1)[0]
            if key in reserved:
                skip = "=" not in flag
                continue
            if key in {"--dangerously-skip-permissions", "--dangerously-bypass-approvals-and-sandbox",
                       "--yolo", "--full-auto", "--json", "--allow-dangerously-skip-permissions"}:
                continue
            clean.append(flag)
        if self.cli == "codex":
            command = ["codex", "exec", "--json", "--sandbox",
                       "danger-full-access" if self.approval_mode == "full-auto" else "workspace-write"]
        elif self.cli in {"claude", "claude-code"}:
            command = ["claude", "--print", "--verbose", "--output-format", "stream-json",
                       "--permission-mode", "bypassPermissions" if self.approval_mode == "full-auto" else "acceptEdits"]
        elif self.cli in {"opencode", "goose"}:
            command = [self.cli, "run"]
        else:
            command = [self.cli]
        command.extend(clean)
        if self.model and self.cli in {"codex", "claude", "claude-code"}:
            command.extend(["--model", self.model])
        return command
