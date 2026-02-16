"""Project registration endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.projects.archive import (
    archive_project,
    get_archive_settings,
    get_archived_project_ids,
    save_archive_settings,
    unarchive_project,
)
from app.projects.models import ProjectDetail, ProjectSummary
from app.projects.service import (
    ProjectRegistrationError,
    get_project_detail,
    list_projects,
    register_project_path,
    unregister_project_by_id,
)
from app.projects.status import build_project_summary
from app.ws.file_watcher import file_watcher_service

router = APIRouter(prefix="/api/projects", tags=["projects"])
LOGGER = logging.getLogger(__name__)


class RegisterProjectRequest(BaseModel):
    path: str


class ArchiveSettingsRequest(BaseModel):
    auto_archive_enabled: bool | None = None
    auto_archive_after_days: int | None = None


async def _refresh_file_watcher() -> None:
    """Best-effort watcher refresh after project set changes."""
    try:
        await file_watcher_service.refresh_projects()
    except Exception:
        LOGGER.warning("Failed to refresh file watcher project subscriptions", exc_info=True)


@router.get("", response_model=list[ProjectSummary])
async def get_projects(include_archived: bool = False) -> list[ProjectSummary]:
    all_projects = await list_projects()
    if include_archived:
        return all_projects
    archived_ids = await get_archived_project_ids()
    return [p for p in all_projects if p.id not in archived_ids]


@router.get("/archived", response_model=list[ProjectSummary])
async def get_archived_projects() -> list[ProjectSummary]:
    all_projects = await list_projects()
    archived_ids = await get_archived_project_ids()
    return [p for p in all_projects if p.id in archived_ids]


@router.get("/archive/settings")
async def get_archive_settings_endpoint() -> dict:
    return await get_archive_settings()


@router.put("/archive/settings")
async def update_archive_settings(payload: ArchiveSettingsRequest) -> dict:
    updates = {}
    if payload.auto_archive_enabled is not None:
        updates["auto_archive_enabled"] = payload.auto_archive_enabled
    if payload.auto_archive_after_days is not None:
        if payload.auto_archive_after_days < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="auto_archive_after_days must be at least 1",
            )
        updates["auto_archive_after_days"] = payload.auto_archive_after_days
    return await save_archive_settings(updates)


@router.post("/{project_id}/archive", status_code=status.HTTP_200_OK)
async def archive_project_endpoint(project_id: str) -> dict:
    project = await get_project_detail(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
    newly_archived = await archive_project(project_id)
    return {"archived": True, "was_already_archived": not newly_archived}


@router.post("/{project_id}/unarchive", status_code=status.HTTP_200_OK)
async def unarchive_project_endpoint(project_id: str) -> dict:
    project = await get_project_detail(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
    was_archived = await unarchive_project(project_id)
    return {"archived": False, "was_archived": was_archived}


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str) -> ProjectDetail:
    project = await get_project_detail(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
    return project


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
async def register_project(payload: RegisterProjectRequest) -> ProjectSummary:
    try:
        project_path = await register_project_path(Path(payload.path))
    except ProjectRegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await _refresh_file_watcher()
    return build_project_summary(project_path)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_project(project_id: str) -> None:
    removed = await unregister_project_by_id(project_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
    await _refresh_file_watcher()
