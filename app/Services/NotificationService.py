from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.migrations.create_notifications_table import DatabaseNotification
from app.Notifications.Channels.DatabaseChannel import DatabaseChannel
from app.Notifications.Channels.MailChannel import MailChannel
from app.Notifications.Channels.SMSChannel import SMSChannel
from app.Notifications.Channels.PushChannel import PushChannel
from app.Notifications.Channels.SlackChannel import SlackChannel
from app.Notifications.Channels.DiscordChannel import DiscordChannel
from app.Notifications.Channels.WebhookChannel import WebhookChannel

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification


class NotificationService:
    """Service for managing notifications."""
    
    def __init__(self, db: Session, channel_configs: Optional[Dict[str, Dict[str, Any]]] = None):
        self.db = db
        configs = channel_configs or {}
        
        self.channels = {
            'database': DatabaseChannel(db),
            'mail': MailChannel(configs.get('mail', {})),
            'sms': SMSChannel(configs.get('sms', {})),
            'push': PushChannel(configs.get('push', {})),
            'slack': SlackChannel(configs.get('slack', {})),
            'discord': DiscordChannel(configs.get('discord', {})),
            'webhook': WebhookChannel(configs.get('webhook', {}))
        }
    
    def send(self, notifiable: Any, notification: Notification) -> Dict[str, Any]:
        """Send a notification via configured channels."""
        results = {}
        channels = notification.via(notifiable)
        
        for channel_name in channels:
            if channel_name in self.channels:
                try:
                    channel = self.channels[channel_name]
                    result = channel.send(notifiable, notification)  # type: ignore[attr-defined]
                    results[channel_name] = {'success': True, 'result': result}
                except Exception as e:
                    results[channel_name] = {'success': False, 'error': str(e)}
            else:
                results[channel_name] = {'success': False, 'error': f'Unknown channel: {channel_name}'}
        
        return results
    
    def send_now(self, notifiable: Any, notification: Notification) -> Dict[str, Any]:
        """Send a notification immediately (ignoring delays)."""
        # For now, same as send. In future, could bypass queue
        return self.send(notifiable, notification)
    
    def get_notifications_for(self, notifiable: Any, limit: Optional[int] = None) -> List[DatabaseNotification]:
        """Get notifications for a notifiable entity."""
        query = self.db.query(DatabaseNotification).filter(
            DatabaseNotification.notifiable_type == notifiable.__class__.__name__
        ).filter(
            DatabaseNotification.notifiable_id == str(notifiable.id)
        ).order_by(DatabaseNotification.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_unread_notifications_for(self, notifiable: Any, limit: Optional[int] = None) -> List[DatabaseNotification]:
        """Get unread notifications for a notifiable entity."""
        query = self.db.query(DatabaseNotification).filter(
            DatabaseNotification.notifiable_type == notifiable.__class__.__name__
        ).filter(
            DatabaseNotification.notifiable_id == str(notifiable.id)
        ).filter(
            DatabaseNotification.read_at.is_(None)
        ).order_by(DatabaseNotification.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notification = self.db.query(DatabaseNotification).filter(
            DatabaseNotification.id == notification_id
        ).first()
        
        if notification:
            notification.mark_as_read()
            self.db.commit()
            return True
        
        return False
    
    def mark_all_as_read_for(self, notifiable: Any) -> int:
        """Mark all notifications as read for a notifiable entity."""
        from datetime import datetime, timezone
        
        count = self.db.query(DatabaseNotification).filter(
            DatabaseNotification.notifiable_type == notifiable.__class__.__name__
        ).filter(
            DatabaseNotification.notifiable_id == str(notifiable.id)
        ).filter(
            DatabaseNotification.read_at.is_(None)
        ).update(
            {'read_at': datetime.now(timezone.utc)},
            synchronize_session=False
        )
        
        self.db.commit()
        return count
    
    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification."""
        notification = self.db.query(DatabaseNotification).filter(
            DatabaseNotification.id == notification_id
        ).first()
        
        if notification:
            self.db.delete(notification)
            self.db.commit()
            return True
        
        return False
    
    def delete_all_notifications_for(self, notifiable: Any) -> int:
        """Delete all notifications for a notifiable entity."""
        count = self.db.query(DatabaseNotification).filter(
            DatabaseNotification.notifiable_type == notifiable.__class__.__name__
        ).filter(
            DatabaseNotification.notifiable_id == str(notifiable.id)
        ).count()
        
        self.db.query(DatabaseNotification).filter(
            DatabaseNotification.notifiable_type == notifiable.__class__.__name__
        ).filter(
            DatabaseNotification.notifiable_id == str(notifiable.id)
        ).delete(synchronize_session=False)
        
        self.db.commit()
        return count
    
    def get_notification_counts_for(self, notifiable: Any) -> Dict[str, int]:
        """Get notification counts for a notifiable entity."""
        total_count = self.db.query(DatabaseNotification).filter(
            DatabaseNotification.notifiable_type == notifiable.__class__.__name__
        ).filter(
            DatabaseNotification.notifiable_id == str(notifiable.id)
        ).count()
        
        unread_count = self.db.query(DatabaseNotification).filter(
            DatabaseNotification.notifiable_type == notifiable.__class__.__name__
        ).filter(
            DatabaseNotification.notifiable_id == str(notifiable.id)
        ).filter(
            DatabaseNotification.read_at.is_(None)
        ).count()
        
        return {
            'total': total_count,
            'unread': unread_count,
            'read': total_count - unread_count
        }