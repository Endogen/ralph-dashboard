"""Tests for websocket hub and router behavior."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import WebSocketDisconnect

from app.auth.service import InvalidTokenError
from app.ws.hub import WebSocketHub
from app.ws import router as ws_router


class FakeWebSocket:
    def __init__(
        self,
        *,
        query_params: dict[str, str] | None = None,
        incoming: list[dict[str, Any]] | None = None,
    ) -> None:
        self.query_params = query_params or {}
        self._incoming = list(incoming or [])
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None
        self.close_reason: str | None = None
        self.sent: list[dict[str, Any]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.closed = True
        self.close_code = code
        self.close_reason = reason

    async def receive_json(self) -> dict[str, Any]:
        if not self._incoming:
            raise WebSocketDisconnect()
        return self._incoming.pop(0)

    async def send_json(self, payload: dict[str, Any]) -> None:
        self.sent.append(payload)


@pytest.mark.anyio
async def test_websocket_hub_broadcasts_to_project_subscribers_only() -> None:
    hub = WebSocketHub()
    ws_alpha = FakeWebSocket()
    ws_beta = FakeWebSocket()

    await hub.connect(ws_alpha)
    await hub.connect(ws_beta)
    await hub.subscribe(ws_alpha, ["alpha"])
    await hub.subscribe(ws_beta, ["beta"])

    await hub.broadcast({"type": "event"}, project="alpha")

    assert ws_alpha.sent == [{"type": "event"}]
    assert ws_beta.sent == []


@pytest.mark.anyio
async def test_websocket_hub_emit_builds_event_envelope() -> None:
    hub = WebSocketHub()
    ws_alpha = FakeWebSocket()
    await hub.connect(ws_alpha)
    await hub.subscribe(ws_alpha, ["alpha"])

    await hub.emit("file_changed", "alpha", {"file": "AGENTS.md"})

    assert len(ws_alpha.sent) == 1
    payload = ws_alpha.sent[0]
    assert payload["type"] == "file_changed"
    assert payload["project"] == "alpha"
    assert payload["data"]["file"] == "AGENTS.md"
    assert isinstance(payload["timestamp"], str)


@pytest.mark.anyio
async def test_websocket_endpoint_rejects_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    ws = FakeWebSocket()
    monkeypatch.setattr(ws_router, "hub", WebSocketHub())

    await ws_router.websocket_endpoint(ws)

    assert not ws.accepted
    assert ws.closed
    assert ws.close_code == 1008
    assert ws.close_reason == "Not authenticated"


@pytest.mark.anyio
async def test_websocket_endpoint_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    ws = FakeWebSocket(query_params={"token": "bad-token"})
    monkeypatch.setattr(ws_router, "hub", WebSocketHub())

    def _raise_invalid(_: str) -> None:
        raise InvalidTokenError("Invalid token")

    monkeypatch.setattr(ws_router, "validate_access_token", _raise_invalid)

    await ws_router.websocket_endpoint(ws)

    assert not ws.accepted
    assert ws.closed
    assert ws.close_code == 1008
    assert ws.close_reason == "Invalid access token"


@pytest.mark.anyio
async def test_websocket_endpoint_handles_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    ws = FakeWebSocket(
        query_params={"token": "ok"},
        incoming=[
            {"action": "subscribe", "projects": ["alpha", "alpha", "  "]},
            {"action": "ping"},
            {"action": "unsubscribe", "projects": ["alpha"]},
            {"action": "unknown"},
        ],
    )
    monkeypatch.setattr(ws_router, "hub", WebSocketHub())
    monkeypatch.setattr(ws_router, "validate_access_token", lambda _: None)

    await ws_router.websocket_endpoint(ws)

    assert ws.accepted
    assert {"type": "pong"} in ws.sent
    assert {"type": "error", "message": "Unknown action"} in ws.sent
