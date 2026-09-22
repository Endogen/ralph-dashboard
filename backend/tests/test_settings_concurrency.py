"""Exercise real SQLite read/modify/write operations under concurrent requests."""
import asyncio

import pytest

from app.database import close_database, init_database
from app.projects.archive import (
    archive_project, get_archived_project_ids, get_archive_settings,
    save_archive_settings, unarchive_project,
)
from app.projects.models import project_id_from_path
from app.projects.service import get_registered_project_paths, register_project_path, unregister_project_by_id


@pytest.mark.anyio
async def test_concurrent_archive_updates_keep_every_project():
    await init_database()
    try:
        ids = {f"project-{i}" for i in range(8)}
        assert all(await asyncio.gather(*(archive_project(key) for key in ids)))
        assert await get_archived_project_ids() == ids
        await asyncio.gather(*(unarchive_project(key) for key in ids))
        assert await get_archived_project_ids() == set()
    finally:
        await close_database()


@pytest.mark.anyio
async def test_concurrent_duplicate_archive_reports_one_change():
    await init_database()
    try:
        results = await asyncio.gather(*(archive_project("same") for _ in range(8)))
        assert sum(results) == 1
    finally:
        await close_database()


@pytest.mark.anyio
async def test_concurrent_archive_setting_patches_are_preserved():
    await init_database()
    try:
        await asyncio.gather(
            save_archive_settings({"auto_archive_enabled": True}),
            save_archive_settings({"auto_archive_after_days": 7}),
        )
        assert await get_archive_settings() == {
            "auto_archive_enabled": True, "auto_archive_after_days": 7,
        }
    finally:
        await close_database()


@pytest.mark.anyio
async def test_concurrent_registration_and_removal_keep_every_change(tmp_path):
    await init_database()
    try:
        paths = [tmp_path / f"project-{i}" for i in range(8)]
        for path in paths:
            (path / ".ralph").mkdir(parents=True)
        await asyncio.gather(*(register_project_path(path) for path in paths))
        assert await get_registered_project_paths() == sorted(path.resolve() for path in paths)
        removed = await asyncio.gather(*(unregister_project_by_id(project_id_from_path(path)) for path in paths))
        assert all(removed)
        assert await get_registered_project_paths() == []
    finally:
        await close_database()


@pytest.mark.anyio
async def test_atomic_update_across_independent_database_connections(tmp_path):
    from app.database import get_setting, update_setting

    path = tmp_path / "independent.db"
    await init_database(path)
    await close_database()
    await asyncio.gather(*(
        update_setting("counter", lambda raw: str(int(raw or "0") + 1), path)
        for _ in range(12)
    ))
    assert await get_setting("counter", path) == "12"
