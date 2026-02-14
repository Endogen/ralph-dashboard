"""Tests for SQLite setup and storage helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database import (
    open_database,
    get_setting,
    get_user_by_username,
    init_database,
    resolve_database_path,
    set_setting,
    upsert_user,
)


@pytest.mark.anyio
async def test_init_database_creates_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "dashboard.db"

    created_path = await init_database(database_path)

    assert created_path == database_path.resolve()
    assert created_path.exists()

    async with open_database(database_path) as connection:
        cursor = await connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('users', 'app_settings')"
        )
        rows = await cursor.fetchall()
        await cursor.close()

    assert {row["name"] for row in rows} == {"users", "app_settings"}


@pytest.mark.anyio
async def test_settings_roundtrip(tmp_path: Path) -> None:
    database_path = tmp_path / "settings.db"
    await init_database(database_path)

    await set_setting("theme", "dark", database_path=database_path)

    value = await get_setting("theme", database_path=database_path)
    missing = await get_setting("does-not-exist", database_path=database_path)

    assert value == "dark"
    assert missing is None


@pytest.mark.anyio
async def test_user_upsert_roundtrip(tmp_path: Path) -> None:
    database_path = tmp_path / "users.db"
    await init_database(database_path)

    await upsert_user("alice", "hash-v1", database_path=database_path)
    await upsert_user("alice", "hash-v2", database_path=database_path)

    user = await get_user_by_username("alice", database_path=database_path)
    missing = await get_user_by_username("nobody", database_path=database_path)

    assert user is not None
    assert user["username"] == "alice"
    assert user["password_hash"] == "hash-v2"
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
