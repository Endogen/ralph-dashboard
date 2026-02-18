"""SQLite setup and persistence helpers for auth and settings data.

Uses a persistent connection pool (single long-lived connection) to avoid
opening/closing and running schema checks on every operation.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from app.config import get_settings

LOGGER = logging.getLogger(__name__)

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

# Persistent connection — initialized once at startup via init_database()
_persistent_connection: "AsyncSQLiteConnection" | None = None
_persistent_db_path: Path | None = None


class AsyncSQLiteCursor:
    """Async cursor wrapper around sqlite3 cursor methods."""

    def __init__(self, cursor: sqlite3.Cursor, lock: threading.Lock) -> None:
        self._cursor = cursor
        self._lock = lock

    def _call_locked(self, operation, *args):
        with self._lock:
            return operation(*args)

    async def fetchone(self) -> sqlite3.Row | None:
        return self._call_locked(self._cursor.fetchone)

    async def fetchall(self) -> list[sqlite3.Row]:
        return self._call_locked(self._cursor.fetchall)

    async def close(self) -> None:
        self._call_locked(self._cursor.close)


class AsyncSQLiteConnection:
    """Async connection wrapper over sqlite3 using thread offloading."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = threading.Lock()

    def _call_locked(self, operation, *args):
        with self._lock:
            return operation(*args)

    async def execute(
        self, sql: str, parameters: tuple[Any, ...] = ()
    ) -> AsyncSQLiteCursor:
        cursor = self._call_locked(self._connection.execute, sql, parameters)
        return AsyncSQLiteCursor(cursor, self._lock)

    async def executescript(self, script: str) -> None:
        self._call_locked(self._connection.executescript, script)

    async def commit(self) -> None:
        self._call_locked(self._connection.commit)

    async def close(self) -> None:
        self._call_locked(self._connection.close)


def _open_sqlite_connection(path: Path) -> AsyncSQLiteConnection:
    """Create a sqlite3 connection configured like the prior aiosqlite setup."""
    raw = sqlite3.connect(path, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return AsyncSQLiteConnection(raw)


def resolve_database_path(database_path: Path | None = None) -> Path:
    """Resolve the SQLite database path from explicit path, env, or settings defaults."""
    if database_path is not None:
        return database_path.expanduser().resolve()

    env_path = os.getenv("RALPH_DATABASE_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    settings = get_settings()
    return settings.credentials_file.with_name(DEFAULT_DATABASE_NAME).expanduser().resolve()


@asynccontextmanager
async def open_database(database_path: Path | None = None) -> AsyncIterator[AsyncSQLiteConnection]:
    """Open an async SQLite connection with row mappings enabled.

    Prefers the persistent connection when available and no explicit path is
    given.  Falls back to a fresh connection for callers that provide a custom
    ``database_path`` (e.g. tests or one-off migrations).
    """
    global _persistent_connection, _persistent_db_path

    resolved_path = resolve_database_path(database_path)

    # If persistent matches the resolved path, reuse it
    if (
        _persistent_connection is not None
        and _persistent_db_path is not None
        and resolved_path == _persistent_db_path
    ):
        yield _persistent_connection
        return

    # Config/env can change between calls (especially in tests). If the
    # persistent connection points at a different DB file, close it so callers
    # don't accidentally read/write stale state.
    if _persistent_connection is not None and _persistent_db_path != resolved_path:
        try:
            await _persistent_connection.close()
        except Exception:
            pass
        _persistent_connection = None
        _persistent_db_path = None

    # Fallback: open a one-off connection
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    connection: AsyncSQLiteConnection | None = None
    try:
        connection = _open_sqlite_connection(resolved_path)
        await _ensure_schema(connection)
        await connection.commit()
        yield connection
    finally:
        if connection is not None:
            await connection.close()


async def _ensure_schema(connection: AsyncSQLiteConnection) -> None:
    await connection.executescript(SCHEMA_SQL)


async def init_database(database_path: Path | None = None) -> Path:
    """Create or migrate the SQLite schema and return resolved db path.

    Also initializes the persistent connection used by all subsequent
    operations.
    """
    global _persistent_connection, _persistent_db_path

    resolved_path = resolve_database_path(database_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    # Close any existing persistent connection
    if _persistent_connection is not None:
        try:
            await _persistent_connection.close()
        except Exception:
            pass
        _persistent_connection = None

    connection = _open_sqlite_connection(resolved_path)
    await _ensure_schema(connection)
    await connection.commit()

    _persistent_connection = connection
    _persistent_db_path = resolved_path
    LOGGER.info("Database initialized at %s (persistent connection)", resolved_path)
    return resolved_path


async def close_database() -> None:
    """Close the persistent database connection (call during shutdown)."""
    global _persistent_connection, _persistent_db_path
    if _persistent_connection is not None:
        try:
            await _persistent_connection.close()
        except Exception:
            pass
        _persistent_connection = None
        _persistent_db_path = None


async def get_user_by_username(
    username: str, database_path: Path | None = None
) -> dict[str, Any] | None:
    """Fetch a user record by username."""
    async with open_database(database_path) as connection:
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
        cursor = await connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return str(row["value"])


async def set_setting(key: str, value: str, database_path: Path | None = None) -> None:
    """Create or update a setting value."""
    async with open_database(database_path) as connection:
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
