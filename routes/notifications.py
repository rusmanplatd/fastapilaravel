from __future__ import annotations

from typing import Optional, Dict, Any
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from config.database import get_database
from app.Http.Controllers.NotificationController import NotificationController
from app.Http.Controllers.AuthController import get_current_user
from app.Http.Schemas.NotificationSchemas import (
    NotificationListResponse,
    NotificationCountsResponse,
    MarkAsReadRequest,
    MarkAllAsReadResponse,
    SendNotificationRequest,
    SendNotificationResponse,
    DeleteNotificationResponse,
    DeleteAllNotificationsResponse
)
from database.migrations.create_users_table import User

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)],
    limit: Annotated[Optional[int], Query(None, description="Limit number of notifications")] = None,
    unread_only: Annotated[bool, Query(False, description="Get only unread notifications")] = False
) -> NotificationListResponse:
    """Get notifications for the authenticated user."""
    controller = NotificationController(db)
    return controller.get_notifications(current_user, limit, unread_only)


@router.get("/counts", response_model=NotificationCountsResponse)
async def get_notification_counts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> NotificationCountsResponse:
    """Get notification counts for the authenticated user."""
    controller = NotificationController(db)
    return controller.get_notification_counts(current_user)


@router.get("/unread", response_model=NotificationListResponse)
async def get_unread_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)],
    limit: Annotated[Optional[int], Query(None, description="Limit number of notifications")] = None
) -> NotificationListResponse:
    """Get unread notifications for the authenticated user."""
    controller = NotificationController(db)
    return controller.get_notifications(current_user, limit, unread_only=True)


@router.post("/mark-as-read")
async def mark_as_read(
    request: MarkAsReadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, Any]:
    """Mark a notification as read."""
    controller = NotificationController(db)
    return controller.mark_as_read(request)


@router.post("/mark-all-as-read", response_model=MarkAllAsReadResponse)
async def mark_all_as_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> MarkAllAsReadResponse:
    """Mark all notifications as read for the authenticated user."""
    controller = NotificationController(db)
    return controller.mark_all_as_read(current_user)


@router.delete("/{notification_id}", response_model=DeleteNotificationResponse)
async def delete_notification(
    notification_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> DeleteNotificationResponse:
    """Delete a notification."""
    controller = NotificationController(db)
    return controller.delete_notification(notification_id)


@router.delete("/", response_model=DeleteAllNotificationsResponse)
async def delete_all_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> DeleteAllNotificationsResponse:
    """Delete all notifications for the authenticated user."""
    controller = NotificationController(db)
    return controller.delete_all_notifications(current_user)


@router.post("/send", response_model=SendNotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> SendNotificationResponse:
    """Send a notification to specified recipients (admin only)."""
    # In a real implementation, you'd check if the user has admin permissions
    controller = NotificationController(db)
    return controller.send_notification(request)