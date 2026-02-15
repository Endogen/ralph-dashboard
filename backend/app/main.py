"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.auth.service import InvalidTokenError, validate_access_token
from app.control.router import router as control_router
from app.database import init_database
from app.files.router import router as files_router
from app.files.specs_router import router as specs_router
from app.git_service.router import router as git_router
from app.iterations.router import router as iterations_router
from app.notifications.router import router as notifications_router
from app.plan.router import router as plan_router
from app.projects.router import router as projects_router
from app.stats.report_router import router as report_router
from app.stats.router import router as stats_router
from app.system.router import router as system_router
from app.ws.event_dispatcher import watcher_event_dispatcher
from app.ws.file_watcher import file_watcher_service
from app.ws.router import router as ws_router

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
PUBLIC_API_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/refresh",
}


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    await init_database()
    file_watcher_service.set_on_change(watcher_event_dispatcher.handle_change)
    await file_watcher_service.start()
    try:
        yield
    finally:
        await file_watcher_service.stop()


def is_public_api_path(path: str) -> bool:
    """Return True when the request path should bypass API auth checks."""
    normalized_path = path[:-1] if path != "/" and path.endswith("/") else path
    if not normalized_path.startswith("/api"):
        return True
    return normalized_path in PUBLIC_API_PATHS


def create_app(frontend_dist: Path | None = None) -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(title="Ralph Dashboard API", version="0.1.0", lifespan=app_lifespan)
    app.include_router(auth_router)
    app.include_router(control_router)
    app.include_router(files_router)
    app.include_router(specs_router)
    app.include_router(git_router)
    app.include_router(iterations_router)
    app.include_router(notifications_router)
    app.include_router(plan_router)
    app.include_router(projects_router)
    app.include_router(report_router)
    app.include_router(stats_router)
    app.include_router(system_router)
    app.include_router(ws_router)

    @app.middleware("http")
    async def authenticate_api_requests(request: Request, call_next):
        if is_public_api_path(request.url.path):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        try:
            payload = validate_access_token(token)
        except InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid access token"})

        request.state.auth_subject = payload.sub
        return await call_next(request)

    @app.get("/api/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    _configure_frontend_static(app, frontend_dist or DEFAULT_FRONTEND_DIST)

    return app


def _configure_frontend_static(app: FastAPI, frontend_dist: Path) -> None:
    """Serve built frontend assets in production when dist files are available."""
    if not frontend_dist.exists() or not frontend_dist.is_dir():
        return

    assets_dir = frontend_dist / "assets"
    if assets_dir.exists() and assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")

        base = frontend_dist.resolve()
        candidate = (frontend_dist / full_path).resolve()

        # Prevent path traversal outside the built frontend directory.
        if not candidate.is_relative_to(base):
            raise HTTPException(status_code=404, detail="Not Found")

        if full_path and candidate.is_file():
            return FileResponse(candidate)

        index_file = frontend_dist / "index.html"
        if index_file.exists() and index_file.is_file():
            return FileResponse(index_file)

        raise HTTPException(status_code=404, detail="Frontend build not found")


app = create_app()
