"""Loop control endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.control.models import LoopConfig, ProcessStartResult
from app.control.process_manager import (
    ProcessAlreadyRunningError,
    ProcessCommandNotFoundError,
    ProcessConfigParseError,
    ProcessConfigValidationError,
    ProcessInjectionValidationError,
    ProcessProjectNotFoundError,
    inject_project_message,
    pause_project_process,
    read_project_config,
    resume_project_process,
    start_project_loop,
    stop_project_process,
    write_project_config,
)

router = APIRouter(prefix="/api/projects/{project_id}", tags=["control"])


class StartLoopRequest(BaseModel):
    max_iterations: int | None = Field(default=None, ge=1, le=999)
    cli: str | None = None
    flags: str | None = None
    test_command: str | None = None

    @field_validator("cli")
    @classmethod
    def _normalize_cli(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("cli cannot be empty")
        return normalized

    @field_validator("flags", "test_command")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class StopResponse(BaseModel):
    stopped: bool


class PauseResponse(BaseModel):
    paused: bool


class ResumeResponse(BaseModel):
    resumed: bool


class InjectRequest(BaseModel):
    message: str


class InjectResponse(BaseModel):
    content: str


@router.post("/start", response_model=ProcessStartResult)
async def post_start(
    project_id: str, payload: StartLoopRequest | None = None
) -> ProcessStartResult:
    request_payload = payload or StartLoopRequest()
    try:
        return await start_project_loop(
            project_id,
            max_iterations=request_payload.max_iterations,
            cli=request_payload.cli,
            flags=request_payload.flags,
            test_command=request_payload.test_command,
        )
    except ProcessProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProcessAlreadyRunningError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProcessCommandNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProcessConfigValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/stop", response_model=StopResponse)
async def post_stop(project_id: str) -> StopResponse:
    try:
        stopped = await stop_project_process(project_id)
    except ProcessProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return StopResponse(stopped=stopped)


@router.post("/pause", response_model=PauseResponse)
async def post_pause(project_id: str) -> PauseResponse:
    try:
        paused = await pause_project_process(project_id)
    except ProcessProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PauseResponse(paused=paused)


@router.post("/resume", response_model=ResumeResponse)
async def post_resume(project_id: str) -> ResumeResponse:
    try:
        resumed = await resume_project_process(project_id)
    except ProcessProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResumeResponse(resumed=resumed)


@router.post("/inject", response_model=InjectResponse)
async def post_inject(project_id: str, payload: InjectRequest) -> InjectResponse:
    try:
        content = await inject_project_message(project_id, payload.message)
    except ProcessProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProcessInjectionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return InjectResponse(content=content)


@router.get("/config", response_model=LoopConfig)
async def get_config(project_id: str) -> LoopConfig:
    try:
        return await read_project_config(project_id)
    except ProcessProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ProcessConfigParseError, ProcessConfigValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/config", response_model=LoopConfig)
async def put_config(project_id: str, payload: LoopConfig) -> LoopConfig:
    try:
        return await write_project_config(project_id, payload)
    except ProcessProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProcessConfigValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
