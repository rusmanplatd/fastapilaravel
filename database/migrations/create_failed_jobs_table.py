from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.Models.BaseModel import BaseModel


class FailedJob(BaseModel):
    """
    FailedJob model representing failed jobs similar to Laravel's failed_jobs table.
    Stores information about jobs that failed and could not be retried.
    """
    __tablename__ = "failed_jobs"
    
    # Original job information
    uuid: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    connection: Mapped[str] = mapped_column(nullable=False)
    queue: Mapped[str] = mapped_column(nullable=False, index=True)
    
    # Job payload and metadata
    payload: Mapped[str] = mapped_column(nullable=False)  # JSON-encoded job data
    exception: Mapped[str] = mapped_column(nullable=False)  # Exception details
    
    # Job class and method information
    job_class: Mapped[str] = mapped_column(nullable=False, index=True)
    job_method: Mapped[str] = mapped_column(default="handle", nullable=False)
    
    # Failure metadata
    attempts: Mapped[int] = mapped_column(nullable=False)
    worker_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    failed_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)
    
    # Additional context
    context: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON-encoded context data
    tags: Mapped[Optional[str]] = mapped_column(nullable=True)  # Comma-separated tags
    
    def __repr__(self) -> str:
        return f"<FailedJob(id='{self.id}', uuid='{self.uuid}', job_class='{self.job_class}', failed_at='{self.failed_at}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert failed job to dictionary representation."""
        base_dict = super().to_dict()
        return {
            **base_dict,
            "age_in_hours": self.get_age_in_hours(),
            "tag_list": self.get_tag_list()
        }
    
    def get_age_in_hours(self) -> float:
        """Get age of failed job in hours."""
        delta = datetime.now(timezone.utc) - self.failed_at
        return delta.total_seconds() / 3600
    
    def get_tag_list(self) -> list[str]:
        """Get tags as a list."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the failed job."""
        current_tags = self.get_tag_list()
        if tag not in current_tags:
            current_tags.append(tag)
            self.tags = ', '.join(current_tags)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the failed job."""
        current_tags = self.get_tag_list()
        if tag in current_tags:
            current_tags.remove(tag)
            self.tags = ', '.join(current_tags) if current_tags else None