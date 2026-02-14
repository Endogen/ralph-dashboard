"""Tests for IMPLEMENTATION_PLAN markdown parsing."""

from __future__ import annotations

from pathlib import Path

from app.plan.parser import parse_implementation_plan, parse_implementation_plan_file


def test_parse_implementation_plan_basic_structure() -> None:
    content = """STATUS: READY

# Implementation Plan

## Phase 1: Setup
- [x] 1.1: Initialize backend
- [ ] 1.2: Initialize frontend

## Phase 2: Auth
- [ ] 2.1: Add login endpoint
  - [x] 2.1.1: Add token model
"""
    parsed = parse_implementation_plan(content)

    assert parsed.status == "READY"
    assert parsed.tasks_done == 2
    assert parsed.tasks_total == 4
    assert len(parsed.phases) == 2
    assert parsed.phases[0].status == "in_progress"
    assert parsed.phases[1].tasks[1].id == "2.1.1"
    assert parsed.phases[1].tasks[1].indent == 2


def test_parse_implementation_plan_file_missing_returns_none(tmp_path: Path) -> None:
    parsed = parse_implementation_plan_file(tmp_path / "missing.md")
    assert parsed is None


def test_parse_implementation_plan_file_reads_existing(tmp_path: Path) -> None:
    plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
    plan_file.write_text(
        "STATUS: COMPLETE\n\n## Phase 1: Done\n- [x] 1.1: Task\n",
        encoding="utf-8",
    )

    parsed = parse_implementation_plan_file(plan_file)
    assert parsed is not None
    assert parsed.status == "COMPLETE"
    assert parsed.tasks_done == 1
    assert parsed.tasks_total == 1
