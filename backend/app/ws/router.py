"""WebSocket endpoint and subscription protocol handlers."""

from __future__ import annotations

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
    # Accept the WebSocket first, then authenticate via the first message.
    # This avoids leaking the token in URL query parameters (logged by
    # proxies, browsers, etc.).  Legacy query-param auth is still supported
    # for backward compatibility but discouraged.
    token = websocket.query_params.get("token")
    authenticated = False

    if token:
        try:
            validate_access_token(token)
            authenticated = True
        except InvalidTokenError:
            await websocket.close(code=1008, reason="Invalid access token")
            return

    await websocket.accept()

    if not authenticated:
        # Expect the first message to be: {"action": "auth", "token": "..."}
        try:
            first_message = await websocket.receive_json()
        except WebSocketDisconnect:
            return

        if first_message.get("action") != "auth" or not isinstance(
            first_message.get("token"), str
        ):
            await websocket.send_json(
                {"type": "error", "message": "First message must be auth"}
            )
            await websocket.close(code=1008, reason="Not authenticated")
            return

        try:
            validate_access_token(first_message["token"])
        except InvalidTokenError:
            await websocket.send_json(
                {"type": "error", "message": "Invalid access token"}
            )
            await websocket.close(code=1008, reason="Invalid access token")
            return

        await websocket.send_json({"type": "auth_ok"})

    hub.register(websocket)
    try:
        while True:
            payload = await websocket.receive_json()
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
