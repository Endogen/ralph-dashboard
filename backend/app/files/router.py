"""Project file endpoints (AGENTS.md / PROMPT.md)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.files.service import (
    FilesProjectNotFoundError,
    FilesTargetNotFoundError,
    read_project_file,
    write_project_file,
)

router = APIRouter(prefix="/api/projects/{project_id}/files", tags=["files"])


class ProjectFileResponse(BaseModel):
    name: str
    content: str


class ProjectFileUpdateRequest(BaseModel):
    content: str


@router.get("/{filename}", response_model=ProjectFileResponse)
async def get_project_file(
    project_id: str, filename: Literal["agents", "prompt"]
) -> ProjectFileResponse:
    try:
        resolved_name, content = await read_project_file(project_id, filename)
    except FilesProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FilesTargetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProjectFileResponse(name=resolved_name, content=content)


@router.put("/{filename}", response_model=ProjectFileResponse)
async def put_project_file(
    project_id: str,
    filename: Literal["agents", "prompt"],
    payload: ProjectFileUpdateRequest,
) -> ProjectFileResponse:
    try:
        resolved_name, content = await write_project_file(project_id, filename, payload.content)
    except FilesProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProjectFileResponse(name=resolved_name, content=content)
