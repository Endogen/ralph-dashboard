"""Project creation wizard API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.wizard.generator import ApiKeyNotConfiguredError, GenerationError, generate_project_files
from app.wizard.schemas import (
    CreateRequest,
    CreateResponse,
    GenerateRequest,
    GenerateResponse,
    TemplatesResponse,
)
from app.wizard.service import (
    ProjectCreationError,
    ProjectDirectoryExistsError,
    create_project,
    get_default_templates,
)

router = APIRouter(prefix="/api/wizard", tags=["wizard"])


@router.get("/templates", response_model=TemplatesResponse)
async def get_templates() -> TemplatesResponse:
    """Return default AGENTS.md and PROMPT.md template content."""
    templates = get_default_templates()
    return TemplatesResponse.model_validate(templates)


@router.post("/generate", response_model=GenerateResponse)
async def post_generate(payload: GenerateRequest) -> GenerateResponse:
    """Generate project specs and implementation plan using LLM."""
    try:
        files = await generate_project_files(payload)
        return GenerateResponse(files=files)
    except ApiKeyNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/create", response_model=CreateResponse)
async def post_create(payload: CreateRequest) -> CreateResponse:
    """Create a new project on disk with the provided files."""
    try:
        return await create_project(payload)
    except ProjectDirectoryExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ProjectCreationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
