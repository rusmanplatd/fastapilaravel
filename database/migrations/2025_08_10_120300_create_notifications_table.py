from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import JSON as SQLJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class DatabaseNotification(BaseModel):
    __tablename__ = "notifications"
    
    # Notifiable polymorphic relationship
    notifiable_type: Mapped[str] = mapped_column(nullable=False)
    notifiable_id: Mapped[str] = mapped_column(nullable=False)
    
    # Notification type (class name)
    type: Mapped[str] = mapped_column(nullable=False)
    
    # Notification data as JSON
    data: Mapped[Dict[str, Any]] = mapped_column(SQLJSON, nullable=False)
    
    # Read timestamp
    read_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_notifiable', 'notifiable_type', 'notifiable_id'),
        Index('idx_unread', 'read_at'),
        Index('idx_type', 'type'),
        Index('idx_created_at', 'created_at'),
    )
    
    def mark_as_read(self) -> None:
        """Mark the notification as read."""
        if self.read_at is None:
            from datetime import datetime, timezone
            self.read_at = datetime.now(timezone.utc)
    
    def mark_as_unread(self) -> None:
        """Mark the notification as unread."""
        self.read_at = None
    
    def is_read(self) -> bool:
        """Check if notification is read."""
        return self.read_at is not None
    
    def is_unread(self) -> bool:
        """Check if notification is unread."""
        return self.read_at is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "notifiable_type": self.notifiable_type,
            "notifiable_id": self.notifiable_id,
            "data": self.data,
            "read_at": self.read_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }