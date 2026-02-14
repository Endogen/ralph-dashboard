"""Parser tests using antique-catalogue fixture samples."""

from __future__ import annotations

from pathlib import Path

from app.iterations.jsonl_parser import parse_iterations_jsonl_file
from app.iterations.log_parser import parse_ralph_log_file
from app.plan.parser import parse_implementation_plan_file

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "antique-catalogue"


def test_ralph_log_fixture_parses_ansi_iteration_headers() -> None:
    parsed = parse_ralph_log_file(FIXTURE_DIR / "ralph.log")

    assert len(parsed) == 2
    assert parsed[0].number == 1
    assert parsed[0].start_timestamp == "01:07:23"
    assert parsed[0].tokens_used == 69.31
    assert parsed[1].number == 2
    assert parsed[1].start_timestamp == "01:11:48"
    assert parsed[1].has_errors


def test_iterations_jsonl_fixture_parses_records() -> None:
    parsed = parse_iterations_jsonl_file(FIXTURE_DIR / "iterations.jsonl")
    assert len(parsed) == 2
    assert parsed[0].iteration == 1
    assert parsed[1].status == "error"


def test_plan_fixture_parses_structure() -> None:
    parsed = parse_implementation_plan_file(FIXTURE_DIR / "IMPLEMENTATION_PLAN.md")
    assert parsed is not None
    assert parsed.status is not None
    assert parsed.tasks_total > 0
    assert len(parsed.phases) > 0
