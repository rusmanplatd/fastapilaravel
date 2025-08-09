from __future__ import annotations

from typing import Optional, Dict, TYPE_CHECKING
from app.Types.JsonTypes import JsonObject, ModelAttributes, JsonValue
from datetime import datetime
from sqlalchemy import ForeignKey, String
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from app.Models.User import User


class ActivityLog(BaseModel):
    """Activity Log model for tracking user activities - Spatie Laravel Activitylog style."""
    
    __tablename__ = "activity_log"
    
    # Core activity information
    log_name: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)
    description: Mapped[str] = mapped_column(nullable=False)
    
    # Subject (the model being acted upon)
    subject_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    subject_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Causer (who performed the action) - always a User in this implementation
    causer_type: Mapped[Optional[str]] = mapped_column(nullable=True, default="User")
    causer_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)  # type: ignore[arg-type]
    
    # Properties and changes
    properties: Mapped[Optional[ModelAttributes]] = mapped_column(JSON, nullable=True)
    batch_uuid: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)
    
    # Event information
    event: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Relationships
    causer: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[causer_id], post_update=True
    )
    
    def __str__(self) -> str:
        """String representation of the activity log."""
        return f"ActivityLog(id={self.id}, description={self.description})"
    
    def __repr__(self) -> str:
        """Developer representation of the activity log."""
        return (
            f"<ActivityLog(id={self.id}, log_name='{self.log_name}', "
            f"description='{self.description}', event='{self.event}')>"
        )
    
    def get_changes(self) -> ModelAttributes:
        """Get the changes from properties if available."""
        if self.properties and "attributes" in self.properties and "old" in self.properties:
            return {
                "old": self.properties.get("old", {}),
                "attributes": self.properties.get("attributes", {})
            }
        return {}
    
    def get_extra_properties(self) -> ModelAttributes:
        """Get extra properties excluding standard changes."""
        if not self.properties:
            return {}
        
        extra = self.properties.copy()
        extra.pop("old", None)
        extra.pop("attributes", None)
        return extra
    
    def to_dict_safe(self) -> ModelAttributes:
        """Safe dictionary representation for API responses."""
        return {
            "id": self.id,
            "log_name": self.log_name,
            "description": self.description,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "causer_type": self.causer_type,
            "causer_id": self.causer_id,
            "properties": self.properties,
            "batch_uuid": self.batch_uuid,
            "event": self.event,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


__all__ = ["ActivityLog"]