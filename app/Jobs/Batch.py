from __future__ import annotations

import json
import uuid
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING
from datetime import datetime, timezone
from dataclasses import dataclass

from app.Jobs.Job import ShouldQueue
from config.database import get_database

if TYPE_CHECKING:
    from database.migrations.create_job_batches_table import JobBatch
    from database.migrations.create_jobs_table import Job as JobModel


@dataclass
class BatchOptions:
    """Configuration options for job batches."""
    name: Optional[str] = None
    allow_failures: bool = False
    failure_threshold: Optional[int] = None
    then_callback: Optional[Callable[[], None]] = None
    catch_callback: Optional[Callable[[Exception], None]] = None
    finally_callback: Optional[Callable[[], None]] = None


class JobBatcher:
    """
    Job batching system similar to Laravel's Bus::batch().
    Allows grouping jobs for bulk processing with progress tracking.
    """
    
    def __init__(self) -> None:
        self.jobs: List[ShouldQueue] = []
        self.options = BatchOptions()
    
    def add(self, job: ShouldQueue) -> JobBatcher:
        """Add a job to the batch."""
        self.jobs.append(job)
        return self
    
    def name(self, batch_name: str) -> JobBatcher:
        """Set the batch name."""
        self.options.name = batch_name
        return self
    
    def allow_failures(self, threshold: Optional[int] = None) -> JobBatcher:
        """Allow failures up to threshold (None = unlimited)."""
        self.options.allow_failures = True
        self.options.failure_threshold = threshold
        return self
    
    def then(self, callback: Callable[[], None]) -> JobBatcher:
        """Set success callback."""
        self.options.then_callback = callback
        return self
    
    def catch(self, callback: Callable[[Exception], None]) -> JobBatcher:
        """Set failure callback."""
        self.options.catch_callback = callback
        return self
    
    def finally_callback(self, callback: Callable[[], None]) -> JobBatcher:
        """Set finally callback."""
        self.options.finally_callback = callback
        return self
    
    def dispatch(self, queue: Optional[str] = None) -> str:
        """Dispatch the batch to the queue."""
        if not self.jobs:
            raise ValueError("Cannot dispatch empty batch")
        
        batch_id = self._create_batch()
        
        # Dispatch all jobs with batch ID
        from app.Services.QueueService import QueueService
        from config.database import get_database
        db = next(get_database())
        queue_service = QueueService(db)
        
        for job in self.jobs:
            # Add batch ID to job payload
            job._batch_id = batch_id  # type: ignore
            queue_service.push(job, queue)
        
        return batch_id
    
    def _create_batch(self) -> str:
        """Create batch record in database."""
        db = next(get_database())
        try:
            from database.migrations.create_job_batches_table import JobBatch
            
            batch_name = self.options.name or f"Batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            batch = JobBatch(
                name=batch_name,
                total_jobs=len(self.jobs),
                pending_jobs=len(self.jobs),
                failed_jobs=0,
                allow_failures=self.options.allow_failures,
                failure_threshold=self.options.failure_threshold,
                options=json.dumps({
                    "has_then_callback": self.options.then_callback is not None,
                    "has_catch_callback": self.options.catch_callback is not None,
                    "has_finally_callback": self.options.finally_callback is not None,
                })
            )
            
            db.add(batch)
            db.commit()
            
            return batch.id
            
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()


class Batchable:
    """
    Mixin for jobs that can be part of a batch.
    Provides batch-aware functionality.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._batch_id: Optional[str] = None
    
    def batch_id(self) -> Optional[str]:
        """Get the batch ID this job belongs to."""
        return getattr(self, '_batch_id', None)
    
    def is_batched(self) -> bool:
        """Check if this job is part of a batch."""
        return self.batch_id() is not None
    
    def get_batch(self) -> Optional[JobBatch]:
        """Get the batch this job belongs to."""
        if not self.is_batched():
            return None
        
        db = next(get_database())
        try:
            from database.migrations.create_job_batches_table import JobBatch
            return db.query(JobBatch).filter(JobBatch.id == self.batch_id()).first()
        finally:
            db.close()
    
    def notify_batch_job_completed(self, failed: bool = False) -> None:
        """Notify batch that this job completed."""
        if not self.is_batched():
            return
        
        db = next(get_database())
        try:
            from database.migrations.create_job_batches_table import JobBatch
            
            batch = db.query(JobBatch).filter(JobBatch.id == self.batch_id()).first()
            if batch:
                batch.job_completed(failed)
                
                # Check if batch should be cancelled due to failures
                if not batch.allow_failures and batch.should_cancel_on_failure():
                    batch.cancel()
                    self._cancel_remaining_batch_jobs(db, batch.id)
                
                db.commit()
                
                # Execute callbacks if batch is finished
                if batch.is_finished():
                    self._execute_batch_callbacks(batch)
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def _cancel_remaining_batch_jobs(self, db: Any, batch_id: str) -> None:
        """Cancel remaining jobs in the batch."""
        from database.migrations.create_jobs_table import Job as JobModel
        
        # Mark remaining jobs in batch as cancelled
        remaining_jobs = (
            db.query(JobModel)
            .filter(JobModel.payload.contains(f'"_batch_id": "{batch_id}"'))
            .filter(JobModel.is_reserved == False)
            .all()
        )
        
        for job in remaining_jobs:
            db.delete(job)
    
    def _execute_batch_callbacks(self, batch: JobBatch) -> None:
        """Execute batch completion callbacks."""
        try:
            options_data = json.loads(batch.options or "{}")
            
            if batch.failed_jobs > 0 and options_data.get("has_catch_callback"):
                # Would execute catch callback here
                pass
            elif batch.failed_jobs == 0 and options_data.get("has_then_callback"):
                # Would execute then callback here  
                pass
            
            if options_data.get("has_finally_callback"):
                # Would execute finally callback here
                pass
                
        except Exception as e:
            # Log callback execution error
            print(f"Error executing batch callbacks: {str(e)}")


class BatchableJob(ShouldQueue, Batchable):
    """
    Base class for jobs that support batching.
    Combines ShouldQueue and Batchable functionality.
    """
    
    def __init__(self) -> None:
        ShouldQueue.__init__(self)
        Batchable.__init__(self)
    
    def handle(self) -> None:
        """Handle the job with batch notification."""
        try:
            self._handle()
            self.notify_batch_job_completed(failed=False)
        except Exception as e:
            self.notify_batch_job_completed(failed=True)
            raise
    
    def _handle(self) -> None:
        """Override this method instead of handle() for batchable jobs."""
        raise NotImplementedError("Batchable jobs must implement _handle()")
    
    def failed(self, exception: Exception) -> None:
        """Handle job failure with batch notification."""
        super().failed(exception)
        self.notify_batch_job_completed(failed=True)


def batch(jobs: List[ShouldQueue]) -> JobBatcher:
    """
    Create a new job batch.
    
    Usage:
        batch([
            SendEmailJob("user1@example.com", "Subject", "Body"),
            SendEmailJob("user2@example.com", "Subject", "Body"),
        ]).name("Newsletter Batch").allow_failures(2).dispatch()
    """
    batcher = JobBatcher()
    for job in jobs:
        batcher.add(job)
    return batcher