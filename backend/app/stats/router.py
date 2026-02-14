"""Stats endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.iterations.service import ProjectNotFoundError
from app.stats.models import ProjectStats
from app.stats.service import aggregate_project_stats

router = APIRouter(prefix="/api/projects/{project_id}/stats", tags=["stats"])


@router.get("", response_model=ProjectStats)
async def get_project_stats(project_id: str) -> ProjectStats:
    try:
        return await aggregate_project_stats(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
