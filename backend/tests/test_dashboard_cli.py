"""Tests for unified Ralph Dashboard CLI helpers."""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
from pathlib import Path

import pytest

from app.cli import dashboard as dashboard_cli
from app.cli.dashboard import (
    build_doctor_checks,
    launchd_service_label,
    parse_env_file,
    parse_project_dirs,
    render_launchd_service_plist,
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


def test_build_doctor_checks_reports_missing_websocket_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        dashboard_cli,
        "detect_websocket_runtime",
        lambda: (False, "No supported websocket backend detected"),
    )

    checks = build_doctor_checks(tmp_path / "missing.env")
    websocket_check = next(check for check in checks if check.name == "WebSocket runtime")

    assert websocket_check.ok is False
    assert websocket_check.fix is not None
    assert "uvicorn[standard]" in websocket_check.fix


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


def test_render_launchd_service_plist_contains_expected_values(tmp_path: Path) -> None:
    label = launchd_service_label("ralph-dashboard")
    plist_text = render_launchd_service_plist(
        label=label,
        backend_path=tmp_path / "backend",
        program_arguments=["/tmp/backend/.venv/bin/uvicorn", "app.main:app", "--port", "8420"],
        environment_variables={
            "RALPH_SECRET_KEY": "abc",
            "RALPH_PROJECT_DIRS": "/tmp/projects",
            "RALPH_PORT": "8420",
            "RALPH_CREDENTIALS_FILE": "/tmp/credentials.yaml",
        },
        stdout_path=tmp_path / "logs" / "out.log",
        stderr_path=tmp_path / "logs" / "err.log",
    )
    payload = plistlib.loads(plist_text.encode("utf-8"))

    assert payload["Label"] == label
    assert payload["ProgramArguments"] == ["/tmp/backend/.venv/bin/uvicorn", "app.main:app", "--port", "8420"]
    assert payload["EnvironmentVariables"]["RALPH_SECRET_KEY"] == "abc"
    assert payload["WorkingDirectory"] == str(tmp_path / "backend")
    assert payload["RunAtLoad"] is True
    assert payload["KeepAlive"] is True
    assert payload["StandardOutPath"] == str(tmp_path / "logs" / "out.log")
    assert payload["StandardErrorPath"] == str(tmp_path / "logs" / "err.log")


def test_build_parser_accepts_launchd_install() -> None:
    parser = dashboard_cli.build_parser()
    args = parser.parse_args(["launchd", "install", "--no-start"])

    assert args.command == "launchd"
    assert args.launchd_command == "install"
    assert args.start is False
    assert "enable" not in vars(args)


def test_run_launchd_install_requires_macos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(dashboard_cli.sys, "platform", "linux")
    args = argparse.Namespace(
        env_file=str(tmp_path / "env"),
        service_name="ralph-dashboard",
        port=None,
        start=True,
    )

    result = dashboard_cli.run_launchd_install(args)
    output = capsys.readouterr().out

    assert result == 1
    assert "only supported on macOS" in output


def test_resolve_launchd_domain_target_falls_back_to_user_domain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dashboard_cli.os, "getuid", lambda: 501)

    def fake_run_command(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        target = command[-1]
        if target == "gui/501":
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="domain does not exist")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(dashboard_cli, "run_command", fake_run_command)

    assert dashboard_cli.resolve_launchd_domain_target() == "user/501"


@pytest.mark.parametrize(
    "details",
    [
        "launchctl bootout returned: no such process",
        "Could not find service",
        "service does not exist",
        "not loaded",
    ],
)
def test_launchd_not_loaded_error_detection(details: str) -> None:
    assert dashboard_cli._launchd_is_not_loaded(details)
