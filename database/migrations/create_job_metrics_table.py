from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.Models.BaseModel import BaseModel


class JobMetric(BaseModel):
    """
    JobMetric model for tracking job execution metrics and performance.
    """
    __tablename__ = "job_metrics"
    
    # Job identification
    job_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_class: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    queue: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Execution metrics
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Duration in milliseconds
    
    # Resource usage
    memory_peak_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status and attempts
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # running, completed, failed, cancelled
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    
    # Worker information
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    worker_hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    worker_pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Additional metadata
    payload_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Size in bytes
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # JSON array
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON object
    
    # Batch information
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    
    def __repr__(self) -> str:
        return f"<JobMetric(job_uuid='{self.job_uuid}', status='{self.status}', duration={self.duration_ms}ms)>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary representation."""
        base_dict = super().to_dict()
        return {
            **base_dict,
            "duration_seconds": self.get_duration_seconds(),
            "memory_efficiency": self.get_memory_efficiency(),
            "is_long_running": self.is_long_running(),
            "performance_score": self.get_performance_score()
        }
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.duration_ms is None:
            return None
        return self.duration_ms / 1000.0
    
    def get_memory_efficiency(self) -> Optional[float]:
        """Calculate memory efficiency score (0-100)."""
        if not self.memory_usage_mb or not self.memory_peak_mb:
            return None
        
        if self.memory_peak_mb == 0:
            return 100.0
        
        # Lower peak-to-average ratio = better efficiency
        ratio = self.memory_usage_mb / self.memory_peak_mb
        return min(100.0, ratio * 100.0)
    
    def is_long_running(self, threshold_seconds: int = 300) -> bool:
        """Check if job is considered long-running (>5 minutes default)."""
        duration = self.get_duration_seconds()
        return duration is not None and duration > threshold_seconds
    
    def get_performance_score(self) -> float:
        """
        Calculate overall performance score (0-100).
        Factors in duration, memory usage, and success rate.
        """
        score = 100.0
        
        # Penalize long duration (assume 60s is baseline)
        if self.duration_ms:
            duration_penalty = min(50.0, (self.duration_ms / 1000.0) / 60.0 * 20)
            score -= duration_penalty
        
        # Penalize high memory usage (assume 50MB is baseline)
        if self.memory_peak_mb:
            memory_penalty = min(25.0, max(0, (self.memory_peak_mb - 50) / 100 * 25))
            score -= memory_penalty
        
        # Penalize failures and retries
        if self.status == "failed":
            score -= 30.0
        elif self.attempts > 1:
            score -= min(20.0, (self.attempts - 1) * 5)
        
        return max(0.0, score)
    
    def mark_completed(self, duration_ms: int, memory_peak_mb: Optional[float] = None) -> None:
        """Mark job as completed with metrics."""
        self.status = "completed"
        self.finished_at = datetime.now(timezone.utc)
        self.duration_ms = duration_ms
        self.memory_peak_mb = memory_peak_mb
    
    def mark_failed(self, error: Exception, duration_ms: int) -> None:
        """Mark job as failed with error details."""
        self.status = "failed"
        self.finished_at = datetime.now(timezone.utc)
        self.duration_ms = duration_ms
        self.error_message = str(error)
        self.error_type = error.__class__.__name__
        
        # Capture stack trace
        import traceback
        self.stack_trace = traceback.format_exc()
    
    def mark_cancelled(self) -> None:
        """Mark job as cancelled."""
        self.status = "cancelled"
        self.finished_at = datetime.now(timezone.utc)
        if not self.duration_ms and self.started_at:
            duration = datetime.now(timezone.utc) - self.started_at
            self.duration_ms = int(duration.total_seconds() * 1000)