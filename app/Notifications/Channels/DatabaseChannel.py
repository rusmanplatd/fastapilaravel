from __future__ import annotations

from typing import Any, TYPE_CHECKING, Type
from sqlalchemy.orm import Session
import importlib

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_120300_create_notifications_table")
DatabaseNotification: Type[Any] = _migration_module.DatabaseNotification

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification


class DatabaseChannel:
    """Database notification channel."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def send(self, notifiable: Any, notification: Notification) -> Any:
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