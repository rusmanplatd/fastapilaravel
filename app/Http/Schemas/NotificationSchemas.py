from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationData(BaseModel):
    """Base notification data schema."""
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    action_url: Optional[str] = Field(None, description="URL for notification action")
    icon: Optional[str] = Field(None, description="Notification icon")
    type: Optional[str] = Field("info", description="Notification type (info, success, warning, error)")


class NotificationResponse(BaseModel):
    """Notification response schema."""
    id: str = Field(..., description="Notification ID")
    type: str = Field(..., description="Notification type/class name")
    notifiable_type: str = Field(..., description="Notifiable entity type")
    notifiable_id: str = Field(..., description="Notifiable entity ID")
    data: Dict[str, Any] = Field(..., description="Notification data")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""
    notifications: List[NotificationResponse] = Field(..., description="List of notifications")
    total: int = Field(..., description="Total notifications")
    unread: int = Field(..., description="Unread notifications count")
    read: int = Field(..., description="Read notifications count")


class NotificationCountsResponse(BaseModel):
    """Notification counts response."""
    total: int = Field(..., description="Total notifications")
    unread: int = Field(..., description="Unread notifications count")
    read: int = Field(..., description="Read notifications count")


class MarkAsReadRequest(BaseModel):
    """Mark notification as read request."""
    notification_id: str = Field(..., description="Notification ID to mark as read")


class MarkAllAsReadResponse(BaseModel):
    """Mark all as read response."""
    marked_count: int = Field(..., description="Number of notifications marked as read")


class SendNotificationRequest(BaseModel):
    """Send notification request schema."""
    notification_type: str = Field(..., description="Notification class name")
    recipients: List[str] = Field(..., description="List of recipient IDs")
    data: Dict[str, Any] = Field({}, description="Notification data")
    channels: Optional[List[str]] = Field(None, description="Channels to send through")


class SendNotificationResponse(BaseModel):
    """Send notification response schema."""
    success: bool = Field(..., description="Whether sending was successful")
    results: Dict[str, Any] = Field(..., description="Results per channel")
    message: str = Field(..., description="Response message")


class DeleteNotificationResponse(BaseModel):
    """Delete notification response."""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Response message")


class DeleteAllNotificationsResponse(BaseModel):
    """Delete all notifications response."""
    deleted_count: int = Field(..., description="Number of notifications deleted")
    message: str = Field(..., description="Response message")