"""Notification endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.notifications.models import NotificationEntry
from app.notifications.service import NotificationsProjectNotFoundError, get_notification_history

router = APIRouter(prefix="/api/projects/{project_id}/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationEntry])
async def get_notifications(project_id: str) -> list[NotificationEntry]:
    try:
        return await get_notification_history(project_id)
    except NotificationsProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
