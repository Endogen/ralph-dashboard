"""Project registration endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

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


async def _refresh_file_watcher() -> None:
    """Best-effort watcher refresh after project set changes."""
    try:
        await file_watcher_service.refresh_projects()
    except Exception:
        LOGGER.warning("Failed to refresh file watcher project subscriptions", exc_info=True)


@router.get("", response_model=list[ProjectSummary])
async def get_projects() -> list[ProjectSummary]:
    return await list_projects()


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
