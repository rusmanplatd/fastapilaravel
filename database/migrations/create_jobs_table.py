from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, Integer, DateTime, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.Models.BaseModel import BaseModel


class Job(BaseModel):
    """
    Job model representing queued jobs similar to Laravel's jobs table.
    Stores job information for background processing.
    """
    __tablename__ = "jobs"
    
    # Queue information
    queue: Mapped[str] = mapped_column(String(255), nullable=False, default="default", index=True)
    
    # Job payload and metadata
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded job data
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # Job status and processing info
    is_reserved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Job type and class information
    job_class: Mapped[str] = mapped_column(String(255), nullable=False)
    job_method: Mapped[str] = mapped_column(String(255), default="handle", nullable=False)
    
    # Priority and delay
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    delay: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Seconds to delay
    
    # Connection information
    connection: Mapped[str] = mapped_column(String(255), default="default", nullable=False)
    
    def __repr__(self) -> str:
        return f"<Job(id='{self.id}', queue='{self.queue}', job_class='{self.job_class}', attempts={self.attempts})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary representation."""
        base_dict = super().to_dict()
        return {
            **base_dict,
            "is_available": self.is_available(),
            "is_failed": self.attempts >= 3,  # Default max attempts
            "next_retry": self.get_next_retry_time()
        }
    
    def is_available(self) -> bool:
        """Check if job is available for processing."""
        if self.is_reserved:
            return False
        return datetime.now(timezone.utc) >= self.available_at
    
    def is_expired(self, timeout: int = 3600) -> bool:
        """Check if reserved job has expired (default 1 hour timeout)."""
        if not self.is_reserved or not self.reserved_at:
            return False
        return datetime.now(timezone.utc) > (self.reserved_at + timedelta(seconds=timeout))
    
    def reserve(self, worker_id: str) -> None:
        """Reserve job for processing by worker."""
        self.is_reserved = True
        self.reserved_at = datetime.now(timezone.utc)
        self.worker_id = worker_id
        self.attempts += 1
    
    def release(self, delay: int = 0) -> None:
        """Release job back to queue with optional delay."""
        self.is_reserved = False
        self.reserved_at = None
        self.worker_id = None
        if delay > 0:
            self.available_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
    
    def get_next_retry_time(self) -> Optional[datetime]:
        """Calculate next retry time based on attempts."""
        if self.attempts == 0:
            return None
        
        # Exponential backoff: 2^attempts minutes
        delay_minutes = 2 ** min(self.attempts, 8)  # Cap at ~4 hours
        return datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)