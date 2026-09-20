"""Tests for SQLite setup and storage helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database import (
    open_database,
    get_setting,
    init_database,
    resolve_database_path,
    set_setting,
)


@pytest.mark.anyio
async def test_init_database_creates_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "dashboard.db"

    created_path = await init_database(database_path)

    assert created_path == database_path.resolve()
    assert created_path.exists()

    async with open_database(database_path) as connection:
        cursor = await connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'app_settings'"
        )
        rows = await cursor.fetchall()
        await cursor.close()

    assert {row["name"] for row in rows} == {"app_settings"}


@pytest.mark.anyio
async def test_settings_roundtrip(tmp_path: Path) -> None:
    database_path = tmp_path / "settings.db"
    await init_database(database_path)

    await set_setting("theme", "dark", database_path=database_path)

    value = await get_setting("theme", database_path=database_path)
    missing = await get_setting("does-not-exist", database_path=database_path)

    assert value == "dark"
    assert missing is None


def test_database_path_uses_credentials_dir_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    credentials_file = tmp_path / "credentials.yaml"

    monkeypatch.setenv("RALPH_CREDENTIALS_FILE", str(credentials_file))
    monkeypatch.delenv("RALPH_DATABASE_PATH", raising=False)

    from app.config import get_settings

    get_settings.cache_clear()

    resolved = resolve_database_path()

    assert resolved == (tmp_path / "dashboard.db").resolve()
