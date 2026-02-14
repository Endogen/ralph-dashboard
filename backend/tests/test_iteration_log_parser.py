"""Tests for ralph.log iteration parsing."""

from __future__ import annotations

from pathlib import Path

from app.iterations.log_parser import parse_ralph_log, parse_ralph_log_file


def test_parse_ralph_log_multiple_iterations() -> None:
    content = """[01:00:00] === Iteration 1/3 ===
Planning changes
tokens used
69.31
[01:05:00] === Iteration 2/3 ===
Running tests
⚠️ test failed on auth endpoint
tokens used
45
[01:09:30] === Iteration 3/3 ===
Applying fixes
"""

    iterations = parse_ralph_log(content)

    assert len(iterations) == 3
    assert iterations[0].number == 1
    assert iterations[0].start_timestamp == "01:00:00"
    assert iterations[0].end_timestamp == "01:05:00"
    assert iterations[0].tokens_used == 69.31
    assert not iterations[0].has_errors

    assert iterations[1].number == 2
    assert iterations[1].tokens_used == 45.0
    assert iterations[1].has_errors
    assert "test failed" in iterations[1].error_lines[0]

    assert iterations[2].number == 3
    assert iterations[2].end_timestamp is None
    assert iterations[2].tokens_used is None


def test_parse_ralph_log_ignores_non_iteration_content() -> None:
    content = """start log
other lines
[10:00:00] === Iteration 5/8 ===
tokens used
123
"""

    iterations = parse_ralph_log(content)

    assert len(iterations) == 1
    assert iterations[0].number == 5
    assert iterations[0].max_iterations == 8
    assert iterations[0].tokens_used == 123.0


def test_parse_ralph_log_file_handles_missing_file(tmp_path: Path) -> None:
    parsed = parse_ralph_log_file(tmp_path / "missing.log")
    assert parsed == []


def test_parse_ralph_log_file_reads_existing_file(tmp_path: Path) -> None:
    log_file = tmp_path / "ralph.log"
    log_file.write_text(
        "[12:00:00] === Iteration 1/2 ===\ntokens used\n1,250.5\n",
        encoding="utf-8",
    )

    parsed = parse_ralph_log_file(log_file)
    assert len(parsed) == 1
    assert parsed[0].tokens_used == 1250.5
