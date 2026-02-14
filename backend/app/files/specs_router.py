"""Specs CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.files.specs_service import (
    SpecAlreadyExistsError,
    SpecNotFoundError,
    SpecValidationError,
    SpecsProjectNotFoundError,
    create_spec,
    delete_spec,
    list_specs,
    read_spec,
    update_spec,
)

router = APIRouter(prefix="/api/projects/{project_id}/specs", tags=["specs"])


class SpecFileInfo(BaseModel):
    name: str
    size: int
    modified: str


class SpecFileResponse(BaseModel):
    name: str
    content: str


class SpecWriteRequest(BaseModel):
    content: str


class SpecCreateRequest(BaseModel):
    name: str
    content: str


@router.get("", response_model=list[SpecFileInfo])
async def get_specs(project_id: str) -> list[SpecFileInfo]:
    try:
        files = await list_specs(project_id)
    except SpecsProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [SpecFileInfo.model_validate(item) for item in files]


@router.get("/{name}", response_model=SpecFileResponse)
async def get_spec(project_id: str, name: str) -> SpecFileResponse:
    try:
        resolved_name, content = await read_spec(project_id, name)
    except SpecsProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SpecValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SpecNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SpecFileResponse(name=resolved_name, content=content)


@router.post("", response_model=SpecFileResponse, status_code=status.HTTP_201_CREATED)
async def post_spec(project_id: str, payload: SpecCreateRequest) -> SpecFileResponse:
    try:
        resolved_name, content = await create_spec(project_id, payload.name, payload.content)
    except SpecsProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SpecValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SpecAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return SpecFileResponse(name=resolved_name, content=content)


@router.put("/{name}", response_model=SpecFileResponse)
async def put_spec(project_id: str, name: str, payload: SpecWriteRequest) -> SpecFileResponse:
    try:
        resolved_name, content = await update_spec(project_id, name, payload.content)
    except SpecsProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SpecValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SpecNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SpecFileResponse(name=resolved_name, content=content)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_spec(project_id: str, name: str) -> None:
    try:
        await delete_spec(project_id, name)
    except SpecsProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SpecValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SpecNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
