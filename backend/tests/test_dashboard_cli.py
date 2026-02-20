"""Tests for unified Ralph Dashboard CLI helpers."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import pytest

from app.cli import dashboard as dashboard_cli
from app.cli.dashboard import (
    build_doctor_checks,
    parse_env_file,
    parse_project_dirs,
    render_systemd_service_unit,
    run_build_frontend,
    write_env_file,
)


def test_parse_project_dirs_supports_pathsep_and_comma(tmp_path: Path) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"
    first.mkdir()
    second.mkdir()

    parsed_pathsep = parse_project_dirs(f"{first}{os.pathsep}{second}")
    parsed_comma = parse_project_dirs(f"{first},{second}")

    assert parsed_pathsep == [first.resolve(), second.resolve()]
    assert parsed_comma == [first.resolve(), second.resolve()]


def test_write_env_file_round_trip(tmp_path: Path) -> None:
    env_file = tmp_path / "ralph.env"
    values = {
        "RALPH_SECRET_KEY": "secret-value-123",
        "RALPH_PROJECT_DIRS": "/tmp/projects one:/tmp/projects-two",
        "RALPH_PORT": "8420",
        "RALPH_CREDENTIALS_FILE": "/tmp/credentials.yaml",
    }

    write_env_file(env_file, values)
    parsed = parse_env_file(env_file)

    assert parsed["RALPH_SECRET_KEY"] == values["RALPH_SECRET_KEY"]
    assert parsed["RALPH_PROJECT_DIRS"] == values["RALPH_PROJECT_DIRS"]
    assert parsed["RALPH_PORT"] == values["RALPH_PORT"]
    assert parsed["RALPH_CREDENTIALS_FILE"] == values["RALPH_CREDENTIALS_FILE"]


def test_render_systemd_service_unit_contains_expected_paths(tmp_path: Path) -> None:
    backend_path = tmp_path / "backend"
    env_file = tmp_path / "env"
    service_content = render_systemd_service_unit(
        service_name="ralph-dashboard",
        backend_path=backend_path,
        env_file=env_file,
        port=9123,
    )

    assert f"WorkingDirectory={backend_path}" in service_content
    assert f"EnvironmentFile={env_file}" in service_content
    assert "--port 9123" in service_content
    assert "WantedBy=default.target" in service_content


def test_build_doctor_checks_reports_missing_env_file(tmp_path: Path) -> None:
    checks = build_doctor_checks(tmp_path / "missing.env")
    env_check = next(check for check in checks if check.name == "Env file")

    assert env_check.ok is False
    assert env_check.fix is not None


def test_run_build_frontend_runs_npm_build_then_package(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    frontend = tmp_path / "frontend"
    scripts = tmp_path / "scripts"
    frontend.mkdir()
    scripts.mkdir()
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    (scripts / "package_frontend.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(dashboard_cli, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(dashboard_cli, "check_binary", lambda name: "/usr/bin/npm" if name == "npm" else None)

    calls: list[tuple[list[str], Path, bool]] = []

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd, check))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(dashboard_cli.subprocess, "run", fake_run)

    result = run_build_frontend(argparse.Namespace())

    assert result == 0
    assert calls == [
        (["/usr/bin/npm", "run", "build"], frontend, False),
        (["bash", str(scripts / "package_frontend.sh")], tmp_path, False),
    ]


def test_run_build_frontend_requires_npm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    frontend = tmp_path / "frontend"
    scripts = tmp_path / "scripts"
    frontend.mkdir()
    scripts.mkdir()
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    (scripts / "package_frontend.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(dashboard_cli, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(dashboard_cli, "check_binary", lambda _name: None)

    result = run_build_frontend(argparse.Namespace())
    output = capsys.readouterr().out

    assert result == 1
    assert "npm not found on PATH" in output
