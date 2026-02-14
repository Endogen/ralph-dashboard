"""Iteration endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.iterations.models import IterationDetail, IterationListResponse
from app.iterations.service import (
    ProjectNotFoundError,
    get_project_iteration_detail,
    list_project_iterations,
)

router = APIRouter(prefix="/api/projects/{project_id}/iterations", tags=["iterations"])


@router.get("", response_model=IterationListResponse)
async def get_iterations(
    project_id: str,
    status_filter: Literal["all", "success", "error"] = Query(default="all", alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> IterationListResponse:
    try:
        iterations = await list_project_iterations(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if status_filter == "success":
        iterations = [item for item in iterations if item.status == "success"]
    elif status_filter == "error":
        iterations = [item for item in iterations if item.has_errors or item.status == "error"]

    total = len(iterations)
    paginated = iterations[offset : offset + limit]
    return IterationListResponse(iterations=paginated, total=total)


@router.get("/{iteration_number}", response_model=IterationDetail)
async def get_iteration_detail(project_id: str, iteration_number: int) -> IterationDetail:
    try:
        detail = await get_project_iteration_detail(project_id, iteration_number)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Iteration not found: {iteration_number}",
        )
    return detail
