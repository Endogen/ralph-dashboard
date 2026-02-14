"""Project report endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.stats.report import ReportProjectNotFoundError, generate_project_report

router = APIRouter(prefix="/api/projects/{project_id}/report", tags=["stats"])


class ProjectReportResponse(BaseModel):
    content: str


@router.get("", response_model=ProjectReportResponse)
async def get_project_report(project_id: str) -> ProjectReportResponse:
    try:
        content = await generate_project_report(project_id)
    except ReportProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProjectReportResponse(content=content)
