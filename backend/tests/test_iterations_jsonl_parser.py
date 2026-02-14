"""Tests for iterations.jsonl parsing."""

from __future__ import annotations

from pathlib import Path

from app.iterations.jsonl_parser import parse_iterations_jsonl, parse_iterations_jsonl_file


def test_parse_iterations_jsonl_valid_and_invalid_lines() -> None:
    content = """
{"iteration":1,"max":5,"start":"2026-02-08T01:00:00+01:00","end":"2026-02-08T01:05:00+01:00","tokens":42.5,"status":"success","tasks_completed":["1.1"],"errors":[]}
not-json
{"iteration":2,"max":5,"start":"2026-02-08T01:05:00+01:00","tokens":"55.2","status":"partial","errors":["test failed"]}
{"max":5}
"""
    parsed = parse_iterations_jsonl(content)

    assert len(parsed) == 2
    assert parsed[0].iteration == 1
    assert parsed[0].tokens == 42.5
    assert parsed[1].iteration == 2
    assert parsed[1].tokens == 55.2
    assert parsed[1].errors == ["test failed"]


def test_parse_iterations_jsonl_file_handles_missing_file(tmp_path: Path) -> None:
    parsed = parse_iterations_jsonl_file(tmp_path / "missing.jsonl")
    assert parsed == []


def test_parse_iterations_jsonl_file_reads_existing_file(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "iterations.jsonl"
    jsonl_file.write_text(
        '{"iteration":1,"max":2,"start":"2026-01-01T00:00:00Z","end":"2026-01-01T00:02:00Z","tokens":10.0}\n',
        encoding="utf-8",
    )

    parsed = parse_iterations_jsonl_file(jsonl_file)
    assert len(parsed) == 1
    assert parsed[0].iteration == 1
    assert parsed[0].max == 2
