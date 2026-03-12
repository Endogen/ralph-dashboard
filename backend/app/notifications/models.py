"""Notification API models."""

from __future__ import annotations

from pydantic import BaseModel


class NotificationEntry(BaseModel):
    event_id: str
    timestamp: str
    prefix: str | None = None
    kind: str
    severity: str
    active: bool = False
    message: str
    status: str | None = None
    iteration: int | None = None
    details: str | None = None
    source: str | None = None
