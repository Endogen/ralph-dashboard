# Task: Convert wizard generation to async start + poll architecture

## Context
The wizard's `POST /api/wizard/generate` currently blocks until the LLM subprocess finishes (can take minutes). This causes browser/proxy timeouts to kill the connection mid-generation, especially on mobile. Convert to async start + poll pattern.

## Backend Changes (backend/app/wizard/)

### 1. New schemas in `schemas.py`
Add these models:

```python
class StartGenerateResponse(BaseModel):
    """Response from the async generation start endpoint."""
    request_id: str

class GenerationStatus(BaseModel):
    """Response from the generation status polling endpoint."""
    status: str  # "pending" | "complete" | "error"
    files: list[GeneratedFile] | None = None
    error: str | None = None
```

### 2. New async job store in `generator.py`

Add a module-level dict to store async generation results alongside the existing `_ACTIVE_GENERATIONS`:

```python
@dataclass
class _GenerationJob:
    task: asyncio.Task
    created_at: float
    result: list[GeneratedFile] | None = None
    error: str | None = None
    done: bool = False

_GENERATION_JOBS: dict[str, _GenerationJob] = {}
_GENERATION_JOBS_LOCK = asyncio.Lock()
_JOB_TTL_SECONDS = 1800  # 30 minutes
```

Add these functions:

- `async def start_generation(request: GenerateRequest) -> str`: 
  - Generates a request_id if not provided
  - Creates an asyncio.Task that calls `generate_project_files(request)` 
  - Stores the task in `_GENERATION_JOBS`
  - Returns the request_id immediately
  - The task's done callback stores result/error in the job

- `async def get_generation_status(request_id: str) -> _GenerationJob | None`:
  - Returns the job from `_GENERATION_JOBS` or None

- `async def cleanup_stale_jobs() -> None`:
  - Removes jobs older than `_JOB_TTL_SECONDS` (30 minutes)
  - Kill any still-running subprocess for stale jobs
  - Call this from a periodic background task or at the start of `start_generation`

### 3. Update `router.py`

**Remove** the old `POST /api/wizard/generate` endpoint entirely.

**Add** two new endpoints:

```python
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
```

**Keep** the existing `/generate/cancel` endpoint as-is (it already works with request_id).

### 4. Register cleanup in app lifespan

In `backend/app/main.py`, add a periodic cleanup task in the lifespan that runs `cleanup_stale_jobs()` every 5 minutes.

## Frontend Changes

### 5. Update `step-generate-review.tsx`

Replace the single blocking `apiFetch("/wizard/generate")` call with:

1. `POST /api/wizard/generate/start` with the same payload → get `request_id`
2. Poll `GET /api/wizard/generate/status/{request_id}` every 2 seconds
3. When status is "complete" → set files
4. When status is "error" → set error
5. Cancel still sends POST to `/wizard/generate/cancel`
6. On unmount/cancel, clear the polling interval

The `AbortController` is no longer needed for the generation request itself (since start returns immediately), but keep it for the cancel flow. Use `setInterval` for polling and clean it up properly.

### 6. Update type definitions

Update `GenerateApiResponse` to match the new response types:
```typescript
type StartGenerateApiResponse = {
  request_id: string
}

type GenerationStatusApiResponse = {
  status: "pending" | "complete" | "error"
  files: GeneratedFile[] | null
  error: string | null
}
```

## Important
- Do NOT keep the old `POST /wizard/generate` endpoint — remove it completely
- The cancel endpoint path stays the same: `POST /wizard/generate/cancel`  
- Keep all existing cancel logic (subprocess kill via _ACTIVE_GENERATIONS)
- TTL for stale job cleanup is 30 minutes
- Poll interval should be 2 seconds
- The `request_id` generation should happen server-side if not provided in the request
- Make sure the cleanup task is properly cancelled on app shutdown
- Run the existing tests after changes: `cd backend && .venv/bin/python -m pytest tests/ -v`
- After all code changes, rebuild frontend: `cd frontend && npm run build && cp -r dist ../backend/app/static/dist`

## Files to modify
- `backend/app/wizard/schemas.py` — add new response models
- `backend/app/wizard/generator.py` — add job store, start_generation, get_generation_status, cleanup
- `backend/app/wizard/router.py` — remove old endpoint, add start + status endpoints
- `backend/app/main.py` — add periodic cleanup task
- `frontend/src/components/wizard/step-generate-review.tsx` — switch to start + poll pattern
- `backend/tests/test_wizard_router.py` — update tests for new endpoints
- `backend/tests/test_wizard_schemas.py` — add tests for new schemas
