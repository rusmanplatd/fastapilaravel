from __future__ import annotations

from typing import Any, TYPE_CHECKING
from sqlalchemy.orm import Session
from database.migrations.create_notifications_table import DatabaseNotification

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification


class DatabaseChannel:
    """Database notification channel."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def send(self, notifiable: Any, notification: Notification) -> DatabaseNotification:
        """Send notification via database channel."""
        notification_data = notification.to_database(notifiable)
        
        db_notification = DatabaseNotification(
            notifiable_type=notifiable.__class__.__name__,
            notifiable_id=str(notifiable.id),
            type=notification.__class__.__name__,
            data=notification_data
        )
        
        self.db.add(db_notification)
        self.db.commit()
        self.db.refresh(db_notification)
        
        return db_notification