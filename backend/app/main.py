"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_database

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    await init_database()
    yield


def create_app(frontend_dist: Path | None = None) -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(title="Ralph Dashboard API", version="0.1.0", lifespan=app_lifespan)

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
