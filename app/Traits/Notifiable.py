from __future__ import annotations

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification
    from database.migrations.create_notifications_table import DatabaseNotification


class NotifiableMixin:
    """Mixin to add notification functionality to models."""
    
    def notify(self, notification: Notification, db: Session) -> Dict[str, Any]:
        """Send a notification to this notifiable entity."""
        from app.Services.NotificationService import NotificationService
        service = NotificationService(db)
        return service.send(self, notification)
    
    def notify_now(self, notification: Notification, db: Session) -> Dict[str, Any]:
        """Send a notification immediately."""
        from app.Services.NotificationService import NotificationService
        service = NotificationService(db)
        return service.send_now(self, notification)
    
    def notifications(self, db: Session, limit: Optional[int] = None) -> List[DatabaseNotification]:
        """Get all notifications for this entity."""
        from app.Services.NotificationService import NotificationService
        service = NotificationService(db)
        return service.get_notifications_for(self, limit)
    
    def unread_notifications(self, db: Session, limit: Optional[int] = None) -> List[DatabaseNotification]:
        """Get unread notifications for this entity."""
        from app.Services.NotificationService import NotificationService
        service = NotificationService(db)
        return service.get_unread_notifications_for(self, limit)
    
    def mark_all_notifications_as_read(self, db: Session) -> int:
        """Mark all notifications as read."""
        from app.Services.NotificationService import NotificationService
        service = NotificationService(db)
        return service.mark_all_as_read_for(self)
    
    def delete_all_notifications(self, db: Session) -> int:
        """Delete all notifications."""
        from app.Services.NotificationService import NotificationService
        service = NotificationService(db)
        return service.delete_all_notifications_for(self)
    
    def notification_counts(self, db: Session) -> Dict[str, int]:
        """Get notification counts."""
        from app.Services.NotificationService import NotificationService
        service = NotificationService(db)
        return service.get_notification_counts_for(self)
    
    def route_notification_for_mail(self) -> Optional[str]:
        """Get email address for mail notifications."""
        if hasattr(self, 'email'):
            email = getattr(self, 'email')
            return str(email) if email is not None else None
        return None
    
    def route_notification_for_database(self) -> bool:
        """Check if entity should receive database notifications."""
        return True
    
    def route_notification_for_sms(self) -> Optional[str]:
        """Get phone number for SMS notifications."""
        if hasattr(self, 'phone'):
            phone = getattr(self, 'phone')
            return str(phone) if phone is not None else None
        return None
    
    def route_notification_for_push(self) -> Optional[List[str]]:
        """Get device tokens for push notifications."""
        if hasattr(self, 'device_tokens'):
            tokens = getattr(self, 'device_tokens')
            if isinstance(tokens, list):
                return [str(token) for token in tokens]
            elif tokens:
                return [str(tokens)]
        return None
    
    def route_notification_for_slack(self) -> Optional[str]:
        """Get Slack channel for notifications."""
        if hasattr(self, 'slack_channel'):
            channel = getattr(self, 'slack_channel')
            return str(channel) if channel is not None else None
        return None
    
    def route_notification_for_discord(self) -> Optional[str]:
        """Get Discord webhook URL for notifications."""
        if hasattr(self, 'discord_webhook'):
            webhook = getattr(self, 'discord_webhook')
            return str(webhook) if webhook is not None else None
        return None
    
    def route_notification_for_webhook(self) -> Optional[str]:
        """Get webhook URL for notifications."""
        if hasattr(self, 'webhook_url'):
            url = getattr(self, 'webhook_url')
            return str(url) if url is not None else None
        return None