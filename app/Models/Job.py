from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from app.Models.BaseModel import BaseModel


class Job(BaseModel):
    """Job model for queue system."""
    
    __tablename__ = "jobs"
    
    queue: Mapped[str] = mapped_column(nullable=False, default="default", index=True)
    payload: Mapped[str] = mapped_column(nullable=False)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    reserved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    available_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    is_reserved: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    worker_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    job_class: Mapped[str] = mapped_column(nullable=False)
    job_method: Mapped[str] = mapped_column(nullable=False, default="handle")
    priority: Mapped[int] = mapped_column(nullable=False, default=0, index=True)
    delay: Mapped[int] = mapped_column(nullable=False, default=0)
    connection: Mapped[str] = mapped_column(nullable=False, default="default")
    
    def __str__(self) -> str:
        return f"Job(id={self.id}, queue={self.queue}, job_class={self.job_class})"
    
    def __repr__(self) -> str:
        return f"<Job(id={self.id}, queue='{self.queue}', job_class='{self.job_class}', attempts={self.attempts})>"
    
    def reserve(self, worker_id: str) -> None:
        """Reserve this job for a worker."""
        self.is_reserved = True
        self.worker_id = worker_id
        self.reserved_at = datetime.now()
    
    def release(self, delay: int = 0) -> None:
        """Release this job back to the queue."""
        self.is_reserved = False
        self.worker_id = None
        self.reserved_at = None
        if delay > 0:
            self.available_at = datetime.now() + timedelta(seconds=delay)


__all__ = ["Job"]