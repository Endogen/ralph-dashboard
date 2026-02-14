"""SQLite setup and persistence helpers for auth and settings data."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from app.config import get_settings

DEFAULT_DATABASE_NAME = "dashboard.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def resolve_database_path(database_path: Path | None = None) -> Path:
    """Resolve the SQLite database path from explicit path, env, or settings defaults."""
    if database_path is not None:
        return database_path.expanduser().resolve()

    env_path = os.getenv("RALPH_DATABASE_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    settings = get_settings()
    return settings.credentials_file.with_name(DEFAULT_DATABASE_NAME).expanduser().resolve()


async def _event_loop_heartbeat(stop_event: asyncio.Event, interval_seconds: float = 0.01) -> None:
    """Periodically wake the loop while thread-backed sqlite calls are in flight."""
    while not stop_event.is_set():
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def open_database(database_path: Path | None = None) -> AsyncIterator[aiosqlite.Connection]:
    """Open an async SQLite connection with row mappings enabled."""
    stop_event = asyncio.Event()
    heartbeat_task = asyncio.create_task(_event_loop_heartbeat(stop_event))

    resolved_path = resolve_database_path(database_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    connection: aiosqlite.Connection | None = None
    try:
        connection = await aiosqlite.connect(resolved_path)
        connection.row_factory = aiosqlite.Row
        pragma_cursor = await connection.execute("PRAGMA foreign_keys = ON")
        await pragma_cursor.close()
        yield connection
    finally:
        if connection is not None:
            await connection.close()
        stop_event.set()
        await heartbeat_task


async def _ensure_schema(connection: aiosqlite.Connection) -> None:
    await connection.executescript(SCHEMA_SQL)


async def init_database(database_path: Path | None = None) -> Path:
    """Create or migrate the SQLite schema and return resolved db path."""
    resolved_path = resolve_database_path(database_path)
    async with open_database(resolved_path) as connection:
        await _ensure_schema(connection)
        await connection.commit()
    return resolved_path


async def get_user_by_username(
    username: str, database_path: Path | None = None
) -> dict[str, Any] | None:
    """Fetch a user record by username."""
    async with open_database(database_path) as connection:
        await _ensure_schema(connection)
        cursor = await connection.execute(
            "SELECT id, username, password_hash, created_at, updated_at FROM users WHERE username = ?",
            (username,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None


async def upsert_user(username: str, password_hash: str, database_path: Path | None = None) -> None:
    """Create or update a user password hash by username."""
    async with open_database(database_path) as connection:
        await _ensure_schema(connection)
        await connection.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                updated_at = CURRENT_TIMESTAMP
            """,
            (username, password_hash),
        )
        await connection.commit()


async def get_setting(key: str, database_path: Path | None = None) -> str | None:
    """Read a setting value by key."""
    async with open_database(database_path) as connection:
        await _ensure_schema(connection)
        cursor = await connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return str(row["value"])


async def set_setting(key: str, value: str, database_path: Path | None = None) -> None:
    """Create or update a setting value."""
    async with open_database(database_path) as connection:
        await _ensure_schema(connection)
        await connection.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        await connection.commit()
