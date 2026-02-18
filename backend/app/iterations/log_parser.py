"""Parser for `.ralph/ralph.log` iteration data."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

# Match both old and new ralph.sh iteration header formats:
#   Old: [HH:MM:SS] === Iteration 5/50 ===
#   New: === Iteration 8 (loop 1/50) ===
ITERATION_HEADER_RE = re.compile(
    r"^"
    r"(?:\[(?P<timestamp>\d{2}:\d{2}:\d{2})\]\s+)?"  # optional [HH:MM:SS] prefix
    r"=== Iteration (?P<number>\d+)"
    r"(?:"
    r"/(?P<max_old>\d+)"                              # old format: /50
    r"|"
    r" \(loop \d+/(?P<max_new>\d+)\)"                 # new format: (loop 1/50)
    r")"
    r" ===$"
)
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
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


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def parse_ralph_log(content: str) -> list[ParsedLogIteration]:
    """Parse raw ralph.log text into per-iteration structured records."""
    lines = content.splitlines()
    markers: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        match = ITERATION_HEADER_RE.match(_strip_ansi(line).strip())
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

        # max_iterations from either old format (/50) or new format (loop 1/50)
        max_iter_str = header.group("max_old") or header.group("max_new") or "0"

        iterations.append(
            ParsedLogIteration(
                number=int(header.group("number")),
                max_iterations=int(max_iter_str),
                start_timestamp=header.group("timestamp") or "",
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
