"""WebSocket connection hub with project subscription support."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket


def _utc_timestamp() -> str:
    return datetime.now(tz=UTC).isoformat()


class WebSocketHub:
    """Manages websocket connections and per-project subscriptions."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._subscriptions: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
            self._subscriptions[websocket] = set()

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
            self._subscriptions.pop(websocket, None)

    async def subscribe(self, websocket: WebSocket, projects: list[str]) -> None:
        async with self._lock:
            if websocket not in self._connections:
                return
            targets = self._subscriptions.setdefault(websocket, set())
            targets.update(projects)

    async def unsubscribe(self, websocket: WebSocket, projects: list[str]) -> None:
        async with self._lock:
            if websocket not in self._connections:
                return
            targets = self._subscriptions.setdefault(websocket, set())
            targets.difference_update(projects)

    async def emit(self, event_type: str, project: str, data: dict[str, Any]) -> None:
        """Build and send a standard event envelope for a project."""
        await self.broadcast(
            {
                "type": event_type,
                "project": project,
                "timestamp": _utc_timestamp(),
                "data": data,
            },
            project=project,
        )

    async def broadcast(self, payload: dict[str, Any], project: str | None = None) -> None:
        """Send payload to all connections or only subscribers of a project."""
        async with self._lock:
            if project is None:
                targets = list(self._connections)
            else:
                targets = [
                    websocket
                    for websocket in self._connections
                    if project in self._subscriptions.get(websocket, set())
                ]

        failed: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:  # pragma: no cover - network/runtime dependent
                failed.append(websocket)

        for websocket in failed:
            await self.disconnect(websocket)


hub = WebSocketHub()
