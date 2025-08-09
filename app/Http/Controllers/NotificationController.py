from __future__ import annotations

from typing import List, Dict, Any, Optional
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Http.Schemas.NotificationSchemas import (
    NotificationResponse, 
    NotificationListResponse,
    NotificationCountsResponse,
    MarkAsReadRequest,
    MarkAllAsReadResponse,
    SendNotificationRequest,
    SendNotificationResponse,
    DeleteNotificationResponse,
    DeleteAllNotificationsResponse
)
from app.Services.NotificationService import NotificationService
from app.Models.User import User
from app.Models.Notification import DatabaseNotification


class NotificationController(BaseController):
    """Controller for notification management."""
    
    def __init__(self, db: Session):
        super().__init__()
        self.notification_service = NotificationService(db)
    
    def get_notifications(
        self, 
        user: User, 
        limit: Optional[int] = None,
        unread_only: bool = False
    ) -> NotificationListResponse:
        """Get notifications for the authenticated user."""
        try:
            if unread_only:
                notifications = self.notification_service.get_unread_notifications_for(user, limit)
            else:
                notifications = self.notification_service.get_notifications_for(user, limit)
            
            counts = self.notification_service.get_notification_counts_for(user)
            
            return NotificationListResponse(
                notifications=[
                    NotificationResponse(
                        id=notification.id,
                        type=notification.type,
                        notifiable_type=notification.notifiable_type,
                        notifiable_id=notification.notifiable_id,
                        data=notification.data,
                        read_at=notification.read_at,
                        created_at=notification.created_at,
                        updated_at=notification.updated_at
                    ) for notification in notifications
                ],
                total=counts['total'],
                unread=counts['unread'],
                read=counts['read']
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")
    
    def get_notification_counts(self, user: User) -> NotificationCountsResponse:
        """Get notification counts for the authenticated user."""
        try:
            counts = self.notification_service.get_notification_counts_for(user)
            return NotificationCountsResponse(**counts)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get notification counts: {str(e)}")
    
    def mark_as_read(self, request: MarkAsReadRequest) -> Dict[str, Any]:
        """Mark a notification as read."""
        try:
            success = self.notification_service.mark_as_read(request.notification_id)
            if not success:
                raise HTTPException(status_code=404, detail="Notification not found")
            
            return {"success": True, "message": "Notification marked as read"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")
    
    def mark_all_as_read(self, user: User) -> MarkAllAsReadResponse:
        """Mark all notifications as read for the authenticated user."""
        try:
            marked_count = self.notification_service.mark_all_as_read_for(user)
            return MarkAllAsReadResponse(marked_count=marked_count)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to mark all notifications as read: {str(e)}")
    
    def delete_notification(self, notification_id: str) -> DeleteNotificationResponse:
        """Delete a notification."""
        try:
            success = self.notification_service.delete_notification(notification_id)
            if not success:
                raise HTTPException(status_code=404, detail="Notification not found")
            
            return DeleteNotificationResponse(
                success=True,
                message="Notification deleted successfully"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete notification: {str(e)}")
    
    def delete_all_notifications(self, user: User) -> DeleteAllNotificationsResponse:
        """Delete all notifications for the authenticated user."""
        try:
            deleted_count = self.notification_service.delete_all_notifications_for(user)
            return DeleteAllNotificationsResponse(
                deleted_count=deleted_count,
                message=f"Deleted {deleted_count} notifications"
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete all notifications: {str(e)}")
    
    def send_notification(self, request: SendNotificationRequest) -> SendNotificationResponse:
        """Send a notification to specified recipients."""
        try:
            # This would typically be restricted to admin users
            # Implementation would depend on having notification classes available
            return SendNotificationResponse(
                success=False,
                results={},
                message="Notification sending not implemented yet"
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")