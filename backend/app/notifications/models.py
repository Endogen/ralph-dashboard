"""Notification API models."""

from __future__ import annotations

from pydantic import BaseModel


class NotificationEntry(BaseModel):
    timestamp: str
    prefix: str | None = None
    message: str
    status: str | None = None
    iteration: int | None = None
    details: str | None = None
    source: str | None = None
