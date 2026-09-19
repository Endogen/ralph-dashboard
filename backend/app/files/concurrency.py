"""Optimistic concurrency for browser-edited project text files."""
import asyncio
import hashlib
from weakref import WeakValueDictionary

from fastapi.responses import JSONResponse

from app.projects.service import get_project_detail
from app.utils.files import contained_path

_locks: WeakValueDictionary = WeakValueDictionary()


def revision(path):
    return '"' + hashlib.sha256(path.read_bytes() if path.exists() else b"").hexdigest() + '"'


async def protect_file_edit(request, call_next):
    parts = request.url.path.strip("/").split("/")
    relative = None
    if len(parts) >= 4 and parts[:2] == ["api", "projects"]:
        if parts[3:] == ["plan"]:
            relative = "IMPLEMENTATION_PLAN.md"
        elif len(parts) == 5 and parts[3] == "files":
            relative = {"agents": "AGENTS.md", "prompt": "PROMPT.md"}.get(parts[4])
        elif len(parts) == 5 and parts[3] == "specs":
            relative = "specs/" + parts[4]
    if not relative or request.method not in {"GET", "PUT", "DELETE"}:
        return await call_next(request)
    project = await get_project_detail(parts[2])
    if project is None:
        return await call_next(request)
    try:
        path = contained_path(project.path, relative)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    key = str(path)
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        before = await asyncio.to_thread(revision, path)
        if request.method in {"PUT", "DELETE"}:
            expected = request.headers.get("if-match")
            if expected is None:
                return JSONResponse(status_code=428, content={"detail": "Read the file before editing it."})
            if expected != before:
                return JSONResponse(status_code=412, content={"detail": "This file changed on disk. Reload and review your changes before saving."})
        response = await call_next(request)
        if response.status_code < 300:
            response.headers["ETag"] = before if request.method == "GET" else await asyncio.to_thread(revision, path)
        return response
