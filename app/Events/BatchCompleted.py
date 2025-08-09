"""
Batch Completed Event
"""
from __future__ import annotations

from typing import Dict, Any
from app.Events.Event import Event


class BatchCompleted(Event):
    """Event fired when a job batch completes successfully."""
    
    def __init__(self, batch_id: str, batch_name: str, total_jobs: int) -> None:
        super().__init__()
        self.batch_id = batch_id
        self.batch_name = batch_name
        self.total_jobs = total_jobs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'batch_id': self.batch_id,
            'batch_name': self.batch_name,
            'total_jobs': self.total_jobs,
            'event': 'batch.completed'
        }