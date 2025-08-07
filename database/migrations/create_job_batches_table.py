from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.Models.BaseModel import BaseModel


class JobBatch(BaseModel):
    """
    JobBatch model for tracking batch job operations.
    Similar to Laravel's job_batches table.
    """
    __tablename__ = "job_batches"
    
    # Batch identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    total_jobs: Mapped[int] = mapped_column(Integer, nullable=False)
    pending_jobs: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    
    # Batch options and metadata
    options: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Progress tracking
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # Percentage completed
    
    # Failure handling
    allow_failures: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    def __repr__(self) -> str:
        return f"<JobBatch(id='{self.id}', name='{self.name}', progress={self.progress}%)>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert batch to dictionary representation."""
        base_dict = super().to_dict()
        return {
            **base_dict,
            "completed_jobs": self.total_jobs - self.pending_jobs,
            "is_finished": self.is_finished(),
            "is_cancelled": self.is_cancelled(),
            "has_failures": self.failed_jobs > 0,
            "success_rate": self.get_success_rate()
        }
    
    def is_finished(self) -> bool:
        """Check if batch is completely finished."""
        return self.finished_at is not None
    
    def is_cancelled(self) -> bool:
        """Check if batch was cancelled."""
        return self.cancelled_at is not None
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_jobs == 0:
            return 100.0
        
        successful_jobs = self.total_jobs - self.failed_jobs
        return (successful_jobs / self.total_jobs) * 100.0
    
    def update_progress(self) -> None:
        """Update progress percentage based on completed jobs."""
        if self.total_jobs == 0:
            self.progress = 100.0
        else:
            completed = self.total_jobs - self.pending_jobs
            self.progress = (completed / self.total_jobs) * 100.0
    
    def job_completed(self, failed: bool = False) -> None:
        """Mark a job in this batch as completed."""
        if self.pending_jobs > 0:
            self.pending_jobs -= 1
        
        if failed:
            self.failed_jobs += 1
        
        self.update_progress()
        
        # Check if batch is finished
        if self.pending_jobs == 0:
            self.finished_at = datetime.now(timezone.utc)
    
    def should_cancel_on_failure(self) -> bool:
        """Check if batch should be cancelled due to failures."""
        if not self.failure_threshold:
            return False
        
        return self.failed_jobs >= self.failure_threshold
    
    def cancel(self) -> None:
        """Cancel the batch."""
        if not self.is_finished():
            self.cancelled_at = datetime.now(timezone.utc)
            self.finished_at = datetime.now(timezone.utc)