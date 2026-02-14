"""Project registration endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.projects.models import ProjectSummary
from app.projects.service import (
    ProjectRegistrationError,
    register_project_path,
    unregister_project_by_id,
)
from app.projects.status import build_project_summary

router = APIRouter(prefix="/api/projects", tags=["projects"])


class RegisterProjectRequest(BaseModel):
    path: str


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
async def register_project(payload: RegisterProjectRequest) -> ProjectSummary:
    try:
        project_path = await register_project_path(Path(payload.path))
    except ProjectRegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return build_project_summary(project_path)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_project(project_id: str) -> None:
    removed = await unregister_project_by_id(project_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
