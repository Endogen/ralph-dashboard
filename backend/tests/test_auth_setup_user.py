"""Tests for auth setup-user CLI helper."""

from __future__ import annotations

from pathlib import Path

from app.auth.service import authenticate_user
from app.auth.setup_user import main, write_credentials_file
from app.config import get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_write_credentials_file(tmp_path: Path) -> None:
    output = write_credentials_file(tmp_path / "credentials.yaml", "demo", "hashed-value")
    content = output.read_text(encoding="utf-8")

    assert "username: demo" in content
    assert "password_hash: hashed-value" in content


def test_setup_user_main_non_interactive(monkeypatch, tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.yaml"
    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials_file))
    _clear_settings_cache()

    exit_code = main(
        [
            "--username",
            "demo",
            "--password",
            "s3cr3t",
            "--password-confirm",
            "s3cr3t",
        ]
    )

    assert exit_code == 0
    assert credentials_file.exists()
    assert authenticate_user("demo", "s3cr3t", credentials_file).username == "demo"


def test_setup_user_main_existing_file_requires_force(monkeypatch, tmp_path: Path) -> None:
    credentials_file = tmp_path / "credentials.yaml"
    credentials_file.write_text("username: demo\npassword_hash: old\n", encoding="utf-8")

    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials_file))
    _clear_settings_cache()

    exit_code = main(["--username", "demo", "--password", "new", "--password-confirm", "new"])
    assert exit_code == 1
