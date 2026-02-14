"""Plan endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.plan.parser import ParsedImplementationPlan
from app.plan.service import PlanProjectNotFoundError, get_project_plan, update_project_plan

router = APIRouter(prefix="/api/projects/{project_id}/plan", tags=["plan"])


class PlanUpdateRequest(BaseModel):
    content: str


@router.get("", response_model=ParsedImplementationPlan)
async def get_plan(project_id: str) -> ParsedImplementationPlan:
    try:
        return await get_project_plan(project_id)
    except PlanProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("", response_model=ParsedImplementationPlan)
async def put_plan(project_id: str, payload: PlanUpdateRequest) -> ParsedImplementationPlan:
    try:
        return await update_project_plan(project_id, payload.content)
    except PlanProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
