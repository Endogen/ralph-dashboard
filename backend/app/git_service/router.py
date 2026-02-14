"""Git endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.git_service.models import GitCommitDiff, GitCommitSummary
from app.git_service.service import (
    GitCommitNotFoundError,
    GitProjectNotFoundError,
    GitRepositoryNotFoundError,
    get_git_diff,
    get_git_log,
)

router = APIRouter(prefix="/api/projects/{project_id}/git", tags=["git"])


@router.get("/log", response_model=list[GitCommitSummary])
async def get_commit_log(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[GitCommitSummary]:
    try:
        return await get_git_log(project_id, limit=limit, offset=offset)
    except (GitProjectNotFoundError, GitRepositoryNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/diff/{commit_hash}", response_model=GitCommitDiff)
async def get_commit_diff(project_id: str, commit_hash: str) -> GitCommitDiff:
    try:
        return await get_git_diff(project_id, commit_hash)
    except (GitProjectNotFoundError, GitRepositoryNotFoundError, GitCommitNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
