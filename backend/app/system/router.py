"""System metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.iterations.service import ProjectNotFoundError
from app.system.models import ProjectSystemInfo
from app.system.service import get_project_system_info

router = APIRouter(prefix="/api/projects/{project_id}/system", tags=["system"])


@router.get("", response_model=ProjectSystemInfo)
async def get_system_info(project_id: str) -> ProjectSystemInfo:
    try:
        return await get_project_system_info(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
