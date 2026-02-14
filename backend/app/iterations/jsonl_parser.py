"""Parser for `.ralph/iterations.jsonl` structured iteration records."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class ParsedJsonlIteration(BaseModel):
    iteration: int
    max: int
    start: str
    end: str | None = None
    duration_seconds: float | None = None
    tokens: float | None = None
    status: str | None = None
    tasks_completed: list[str] = Field(default_factory=list)
    commit: str | None = None
    commit_message: str | None = None
    test_passed: bool | None = None
    test_output: str | None = None
    errors: list[str] = Field(default_factory=list)


def parse_iterations_jsonl(content: str) -> list[ParsedJsonlIteration]:
    """Parse raw iterations.jsonl content into typed iteration entries."""
    iterations: list[ParsedJsonlIteration] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        try:
            iterations.append(ParsedJsonlIteration.model_validate(payload))
        except ValidationError:
            continue
    return iterations


def parse_iterations_jsonl_file(jsonl_file: Path) -> list[ParsedJsonlIteration]:
    """Parse iterations.jsonl file into typed iteration entries."""
    resolved = jsonl_file.expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        return []
    return parse_iterations_jsonl(resolved.read_text(encoding="utf-8"))
