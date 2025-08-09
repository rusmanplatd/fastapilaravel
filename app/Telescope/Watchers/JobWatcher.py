from __future__ import annotations

import uuid
from typing import Dict, Any, Optional

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class JobWatcher(TelescopeWatcher):
    """
    Watches job queue operations.
    
    Records job dispatch, processing, completion, and failure events.
    """
    
    def __init__(self, telescope_manager) -> None:
        super().__init__(telescope_manager)
    
    def record_job_dispatched(
        self,
        job_id: str,
        job_class: str,
        queue: str = 'default',
        payload: Optional[Dict[str, Any]] = None,
        delay: Optional[int] = None
    ) -> None:
        """Record a job being dispatched to the queue."""
        content = {
            'job_id': job_id,
            'name': job_class,
            'queue': queue,
            'payload': payload or {},
            'delay': delay,
            'status': 'dispatched',
        }
        
        tags = [
            f"queue:{queue}",
            f"job:{job_class}",
            'dispatched',
        ]
        
        if delay:
            tags.append('delayed')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=job_id,
            should_display_on_index=True,
            type='job',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_job_started(
        self,
        job_id: str,
        job_class: str,
        queue: str = 'default',
        worker_id: Optional[str] = None
    ) -> None:
        """Record a job starting processing."""
        content = {
            'job_id': job_id,
            'name': job_class,
            'queue': queue,
            'worker_id': worker_id,
            'status': 'processing',
        }
        
        tags = [
            f"queue:{queue}",
            f"job:{job_class}",
            'processing',
        ]
        
        if worker_id:
            tags.append(f"worker:{worker_id}")
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=job_id,
            should_display_on_index=False,  # Don't show processing events by default
            type='job',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_job_completed(
        self,
        job_id: str,
        job_class: str,
        queue: str = 'default',
        duration: Optional[float] = None,
        memory_peak: Optional[int] = None
    ) -> None:
        """Record a job completing successfully."""
        content = {
            'job_id': job_id,
            'name': job_class,
            'queue': queue,
            'status': 'completed',
            'duration': duration,
            'memory_peak': memory_peak,
        }
        
        tags = [
            f"queue:{queue}",
            f"job:{job_class}",
            'completed',
        ]
        
        # Add performance tags
        if duration and duration > 30:  # Jobs taking more than 30 seconds
            tags.append('slow')
        
        if memory_peak and memory_peak > 128 * 1024 * 1024:  # More than 128MB
            tags.append('memory-intensive')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=job_id,
            should_display_on_index=True,
            type='job',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_job_failed(
        self,
        job_id: str,
        job_class: str,
        queue: str = 'default',
        exception: Optional[str] = None,
        attempts: int = 1,
        will_retry: bool = False,
        duration: Optional[float] = None
    ) -> None:
        """Record a job failing."""
        content = {
            'job_id': job_id,
            'name': job_class,
            'queue': queue,
            'status': 'failed',
            'exception': exception,
            'attempts': attempts,
            'will_retry': will_retry,
            'duration': duration,
        }
        
        tags = [
            f"queue:{queue}",
            f"job:{job_class}",
            'failed',
        ]
        
        if will_retry:
            tags.append('retry')
        else:
            tags.append('abandoned')
        
        if attempts > 1:
            tags.append('multiple-attempts')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=job_id,
            should_display_on_index=True,
            type='job',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_job_retrying(
        self,
        job_id: str,
        job_class: str,
        queue: str = 'default',
        attempt: int = 1,
        delay: Optional[int] = None
    ) -> None:
        """Record a job being retried."""
        content = {
            'job_id': job_id,
            'name': job_class,
            'queue': queue,
            'status': 'retrying',
            'attempt': attempt,
            'delay': delay,
        }
        
        tags = [
            f"queue:{queue}",
            f"job:{job_class}",
            'retrying',
            f"attempt:{attempt}",
        ]
        
        if delay:
            tags.append('delayed')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=job_id,
            should_display_on_index=False,
            type='job',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_batch_started(
        self,
        batch_id: str,
        job_count: int,
        jobs: list[str]
    ) -> None:
        """Record a job batch starting."""
        content = {
            'batch_id': batch_id,
            'job_count': job_count,
            'jobs': jobs,
            'status': 'batch_started',
        }
        
        tags = [
            'batch',
            'started',
            f"job_count:{job_count}",
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=batch_id,
            family_hash=batch_id,
            should_display_on_index=True,
            type='job',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_batch_completed(
        self,
        batch_id: str,
        successful_jobs: int,
        failed_jobs: int,
        total_duration: Optional[float] = None
    ) -> None:
        """Record a job batch completing."""
        content = {
            'batch_id': batch_id,
            'successful_jobs': successful_jobs,
            'failed_jobs': failed_jobs,
            'total_jobs': successful_jobs + failed_jobs,
            'total_duration': total_duration,
            'status': 'batch_completed',
        }
        
        tags = [
            'batch',
            'completed',
            f"success_rate:{successful_jobs}/{successful_jobs + failed_jobs}",
        ]
        
        if failed_jobs == 0:
            tags.append('all_successful')
        elif successful_jobs == 0:
            tags.append('all_failed')
        else:
            tags.append('partial_success')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=batch_id,
            family_hash=batch_id,
            should_display_on_index=True,
            type='job',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)