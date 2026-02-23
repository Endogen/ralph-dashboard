"""Project creation wizard API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.wizard.generator import (
    cancel_generation_request,
    get_generation_status,
    start_generation,
)
from app.wizard.schemas import (
    CancelGenerateRequest,
    CancelGenerateResponse,
    CreateRequest,
    CreateResponse,
    GenerateRequest,
    GenerationStatus,
    StartGenerateResponse,
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


@router.post("/generate/start", response_model=StartGenerateResponse)
async def post_generate_start(payload: GenerateRequest) -> StartGenerateResponse:
    """Start async generation. Returns request_id immediately."""
    request_id = await start_generation(payload)
    return StartGenerateResponse(request_id=request_id)


@router.get("/generate/status/{request_id}", response_model=GenerationStatus)
async def get_generate_status(request_id: str) -> GenerationStatus:
    """Poll generation status. Returns pending/complete/error."""
    job = await get_generation_status(request_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation request not found")
    if not job.done:
        return GenerationStatus(status="pending")
    if job.error:
        return GenerationStatus(status="error", error=job.error)
    return GenerationStatus(status="complete", files=job.result)


@router.post("/generate/cancel", response_model=CancelGenerateResponse)
async def post_generate_cancel(payload: CancelGenerateRequest) -> CancelGenerateResponse:
    """Cancel an in-flight wizard generation request."""
    cancelled = await cancel_generation_request(payload.request_id)
    return CancelGenerateResponse(cancelled=cancelled)


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
