"""Parser for `.ralph/ralph.log` iteration data."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

ITERATION_HEADER_RE = re.compile(
    r"^\[(?P<timestamp>\d{2}:\d{2}:\d{2})\]\s+=== Iteration (?P<number>\d+)/(?P<max>\d+) ===$"
)
TOKEN_NUMBER_RE = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?")
ERROR_LINE_RE = re.compile(
    r"(⚠️|❌|\berror\b|\bexception\b|\bfailed\b|\btraceback\b|\bcrash\b)", re.I
)


class ParsedLogIteration(BaseModel):
    number: int
    max_iterations: int
    start_timestamp: str
    end_timestamp: str | None
    tokens_used: float | None
    has_errors: bool
    error_lines: list[str]
    raw_output: str


def _parse_token_count(iteration_lines: list[str]) -> float | None:
    for index, line in enumerate(iteration_lines):
        if line.strip().lower() != "tokens used":
            continue
        if index + 1 >= len(iteration_lines):
            return None
        match = TOKEN_NUMBER_RE.search(iteration_lines[index + 1].replace(",", ""))
        if match is None:
            return None
        return float(match.group(0))
    return None


def _extract_error_lines(iteration_lines: list[str]) -> list[str]:
    errors: list[str] = []
    for line in iteration_lines:
        if ERROR_LINE_RE.search(line):
            errors.append(line)
    return errors


def parse_ralph_log(content: str) -> list[ParsedLogIteration]:
    """Parse raw ralph.log text into per-iteration structured records."""
    lines = content.splitlines()
    markers: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = ITERATION_HEADER_RE.match(line.strip())
        if match is not None:
            markers.append((index, match))

    iterations: list[ParsedLogIteration] = []
    for marker_index, (line_index, header) in enumerate(markers):
        next_line_index = (
            markers[marker_index + 1][0] if marker_index + 1 < len(markers) else len(lines)
        )
        chunk_lines = lines[line_index:next_line_index]
        error_lines = _extract_error_lines(chunk_lines)

        end_timestamp = None
        if marker_index + 1 < len(markers):
            end_timestamp = markers[marker_index + 1][1].group("timestamp")

        iterations.append(
            ParsedLogIteration(
                number=int(header.group("number")),
                max_iterations=int(header.group("max")),
                start_timestamp=header.group("timestamp"),
                end_timestamp=end_timestamp,
                tokens_used=_parse_token_count(chunk_lines),
                has_errors=bool(error_lines),
                error_lines=error_lines,
                raw_output="\n".join(chunk_lines),
            )
        )

    return iterations


def parse_ralph_log_file(log_file: Path) -> list[ParsedLogIteration]:
    """Parse a ralph.log file path into structured iteration records."""
    resolved = log_file.expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        return []
    return parse_ralph_log(resolved.read_text(encoding="utf-8"))
