"""Application configuration and environment loading."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

DEFAULT_PROJECT_DIR = Path.home() / "projects"
DEFAULT_CREDENTIALS_FILE = Path.home() / ".config" / "ralph-dashboard" / "credentials.yaml"


class Settings(BaseModel):
    """Runtime settings for Ralph Dashboard backend."""

    project_dirs: list[Path] = Field(default_factory=lambda: [DEFAULT_PROJECT_DIR])
    port: int = Field(default=8420, ge=1, le=65535)
    secret_key: str = Field(default="replace-this-secret-key")
    credentials_file: Path = Field(default=DEFAULT_CREDENTIALS_FILE)

    @field_validator("project_dirs", mode="before")
    @classmethod
    def _parse_project_dirs(cls, value: Any) -> Any:
        if isinstance(value, str):
            raw_parts = value.split(os.pathsep)
            if len(raw_parts) == 1 and "," in value:
                raw_parts = value.split(",")
            return [part.strip() for part in raw_parts if part.strip()]
        return value

    @field_validator("project_dirs")
    @classmethod
    def _normalize_project_dirs(cls, value: list[Path]) -> list[Path]:
        normalized: list[Path] = []
        seen: set[Path] = set()
        for directory in value:
            absolute = directory.expanduser().resolve()
            if absolute not in seen:
                normalized.append(absolute)
                seen.add(absolute)
        if not normalized:
            raise ValueError("project_dirs must include at least one path")
        return normalized

    @field_validator("credentials_file")
    @classmethod
    def _normalize_credentials_file(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("secret_key must not be empty")
        if value == "replace-this-secret-key":
            raise ValueError(
                "RALPH_SECRET_KEY must be set to a secure random value — "
                "do not use the default. Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from environment variables with sane defaults."""
    payload: dict[str, Any] = {}

    project_dirs = os.getenv("RALPH_PROJECT_DIRS")
    if project_dirs is not None:
        payload["project_dirs"] = project_dirs

    port = os.getenv("RALPH_PORT")
    if port is not None:
        payload["port"] = port

    secret_key = os.getenv("RALPH_SECRET_KEY")
    if secret_key is not None:
        payload["secret_key"] = secret_key

    credentials_file = os.getenv("RALPH_CREDENTIALS_FILE")
    if credentials_file is not None:
        payload["credentials_file"] = credentials_file

    return Settings.model_validate(payload)
