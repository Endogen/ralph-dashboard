"""Loop process control models."""

from __future__ import annotations

from pydantic import BaseModel


class ProcessStartResult(BaseModel):
    project_id: str
    pid: int
    command: list[str]
