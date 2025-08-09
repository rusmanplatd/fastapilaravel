"""
Batch Finished Event
"""
from __future__ import annotations

from typing import Dict, Any
from app.Events.Event import Event


class BatchFinished(Event):
    """Event fired when a job batch finishes processing (success or failure)."""
    
    def __init__(self, batch_id: str, batch_name: str, total_jobs: int, failed_jobs: int) -> None:
        super().__init__()
        self.batch_id = batch_id
        self.batch_name = batch_name
        self.total_jobs = total_jobs
        self.failed_jobs = failed_jobs
    
    @property
    def successful_jobs(self) -> int:
        """Get count of successful jobs."""
        return self.total_jobs - self.failed_jobs
    
    @property
    def is_successful(self) -> bool:
        """Check if batch completed successfully."""
        return self.failed_jobs == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'batch_id': self.batch_id,
            'batch_name': self.batch_name,
            'total_jobs': self.total_jobs,
            'failed_jobs': self.failed_jobs,
            'successful_jobs': self.successful_jobs,
            'is_successful': self.is_successful,
            'event': 'batch.finished'
        }