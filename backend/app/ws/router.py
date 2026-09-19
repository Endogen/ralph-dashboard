"""WebSocket endpoint and subscription protocol handlers."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.service import InvalidTokenError, validate_access_token
from app.ws.hub import hub

router = APIRouter(tags=["ws"])


def _normalize_projects(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    for value in raw:
        if isinstance(value, str):
            project_id = value.strip()
            if project_id:
                normalized.append(project_id)
    return sorted(set(normalized))


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        authentication = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        if not isinstance(authentication, dict):
            raise ValueError("Expected an authentication object")
        validate_access_token(authentication.get("token", ""))
    except (InvalidTokenError, ValueError, asyncio.TimeoutError, WebSocketDisconnect):
        await websocket.close(code=1008, reason="Invalid access token")
        return
    await websocket.send_json({"type": "authenticated"})
    hub.register(websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                await websocket.send_json({"type": "error", "message": "Expected an action object"})
                continue
            action = payload.get("action")

            if action == "subscribe":
                projects = _normalize_projects(payload.get("projects"))
                await hub.subscribe(websocket, projects)
                continue

            if action == "unsubscribe":
                projects = _normalize_projects(payload.get("projects"))
                await hub.unsubscribe(websocket, projects)
                continue

            if action == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            await websocket.send_json({"type": "error", "message": "Unknown action"})
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(websocket)
