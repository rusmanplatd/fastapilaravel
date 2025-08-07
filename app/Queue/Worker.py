from __future__ import annotations

import json
import time
import signal
import logging
import traceback
import importlib
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.Jobs.Job import ShouldQueue, JobRetryException, JobFailedException
from config.database import get_database

if TYPE_CHECKING:
    from database.migrations.create_jobs_table import Job as JobModel
    from database.migrations.create_failed_jobs_table import FailedJob


@dataclass
class WorkerOptions:
    """Configuration options for queue worker."""
    name: str = "default"
    connection: str = "default"
    queue: str = "default"
    delay: int = 0  # Seconds to sleep when no jobs available
    sleep: int = 3  # Default sleep duration
    max_jobs: int = 0  # 0 = unlimited
    max_time: int = 0  # 0 = unlimited (seconds)
    memory_limit: int = 128  # MB
    timeout: int = 60  # Job timeout in seconds
    rest: int = 0  # Microseconds to rest between jobs
    force: bool = False  # Force worker to run even in maintenance mode


class QueueWorker:
    """
    Queue worker that processes jobs from the queue.
    Similar to Laravel's queue worker.
    """
    
    def __init__(self, options: Optional[WorkerOptions] = None) -> None:
        self.options = options or WorkerOptions()
        self.should_quit = False
        self.paused = False
        self.jobs_processed = 0
        self.start_time = datetime.utcnow()
        self.logger = logging.getLogger(f"queue.worker.{self.options.name}")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        if hasattr(signal, 'SIGUSR2'):
            signal.signal(signal.SIGUSR2, self._handle_pause_signal)
    
    def work(self) -> None:
        """Start processing jobs from the queue."""
        self.logger.info(f"Worker {self.options.name} starting on queue: {self.options.queue}")
        
        while not self.should_quit:
            if self.paused:
                self._sleep(self.options.delay or self.options.sleep)
                continue
            
            # Check memory limit
            if self._memory_exceeded():
                self.logger.warning("Memory limit exceeded, stopping worker")
                break
            
            # Check max time limit
            if self._time_limit_exceeded():
                self.logger.info("Time limit exceeded, stopping worker")
                break
            
            # Check max jobs limit
            if self._job_limit_exceeded():
                self.logger.info("Job limit exceeded, stopping worker")
                break
            
            # Process next job
            job_processed = self._run_next_job()
            
            if not job_processed:
                # No jobs available, sleep
                self._sleep(self.options.delay or self.options.sleep)
            else:
                self.jobs_processed += 1
                
                # Rest between jobs if configured
                if self.options.rest > 0:
                    time.sleep(self.options.rest / 1000000)  # Convert microseconds
        
        self.logger.info(f"Worker {self.options.name} stopping after processing {self.jobs_processed} jobs")
    
    def _run_next_job(self) -> bool:
        """Process the next available job."""
        db = next(get_database())
        try:
            # Import here to avoid circular imports
            from database.migrations.create_jobs_table import Job as JobModel
            
            # Get next available job with priority ordering
            job_model = (
                db.query(JobModel)
                .filter(
                    JobModel.queue == self.options.queue,
                    JobModel.is_reserved == False,
                    JobModel.available_at <= datetime.utcnow()
                )
                .order_by(JobModel.priority.desc(), JobModel.available_at.asc())
                .first()
            )
            
            if not job_model:
                return False
            
            # Reserve the job
            worker_id = f"{self.options.name}_{datetime.utcnow().isoformat()}"
            job_model.reserve(worker_id)
            db.commit()
            
            try:
                # Process the job
                self._process_job(db, job_model)
                
                # Job succeeded, delete from queue
                db.delete(job_model)
                db.commit()
                
                self.logger.info(f"Job {job_model.id} completed successfully")
                return True
                
            except JobRetryException as e:
                # Job requested retry
                self._handle_job_retry(db, job_model, str(e), e.delay)
                return True
                
            except JobFailedException as e:
                # Job failed permanently
                self._handle_job_failure(db, job_model, str(e))
                return True
                
            except Exception as e:
                # Unexpected exception
                self._handle_job_exception(db, job_model, e)
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing job: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def _process_job(self, db: Session, job_model: JobModel) -> None:
        """Execute a job."""
        try:
            # Parse job payload
            payload = json.loads(job_model.payload)
            job_class_path = payload.get("job_class")
            job_method = payload.get("job_method", "handle")
            
            if not job_class_path:
                raise ValueError("Job class not specified in payload")
            
            # Import job class dynamically
            module_path, class_name = job_class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            job_class = getattr(module, class_name)
            
            # Deserialize job instance
            job_instance = job_class.deserialize(payload)
            job_instance.job_id = job_model.id
            job_instance.attempts = job_model.attempts
            
            # Execute job with timeout
            start_time = datetime.utcnow()
            self.logger.info(f"Processing job {job_model.id}: {job_class_path}")
            
            # Call the job method
            method = getattr(job_instance, job_method)
            result = method()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(f"Job {job_model.id} completed in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing job {job_model.id}: {str(e)}")
            raise
    
    def _handle_job_retry(self, db: Session, job_model: JobModel, error: str, delay: int = 0) -> None:
        """Handle job retry."""
        max_attempts = 3  # Default, should come from job options
        
        if job_model.attempts >= max_attempts:
            self._handle_job_failure(db, job_model, f"Max attempts exceeded. Last error: {error}")
            return
        
        # Calculate retry delay
        if delay == 0:
            delay = min(60 * (2 ** (job_model.attempts - 1)), 3600)  # Exponential backoff, max 1 hour
        
        # Release job back to queue with delay
        job_model.release(delay)
        db.commit()
        
        self.logger.warning(f"Job {job_model.id} will retry in {delay}s. Attempt {job_model.attempts}/{max_attempts}")
    
    def _handle_job_failure(self, db: Session, job_model: JobModel, error: str) -> None:
        """Move job to failed jobs table."""
        from database.migrations.create_failed_jobs_table import FailedJob
        
        # Create failed job record
        failed_job = FailedJob(
            uuid=job_model.id,
            connection=job_model.connection,
            queue=job_model.queue,
            payload=job_model.payload,
            exception=error,
            job_class=job_model.job_class,
            job_method=job_model.job_method,
            attempts=job_model.attempts,
            worker_id=job_model.worker_id,
            context=json.dumps({
                "worker": self.options.name,
                "failed_at": datetime.utcnow().isoformat(),
                "priority": job_model.priority
            })
        )
        
        db.add(failed_job)
        db.delete(job_model)
        db.commit()
        
        self.logger.error(f"Job {job_model.id} failed permanently: {error}")
    
    def _handle_job_exception(self, db: Session, job_model: JobModel, exception: Exception) -> None:
        """Handle unexpected job exception."""
        error_message = f"{exception.__class__.__name__}: {str(exception)}\n{traceback.format_exc()}"
        
        # Treat as retry unless it's a specific failure
        self._handle_job_retry(db, job_model, error_message)
    
    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.should_quit = True
    
    def _handle_pause_signal(self, signum: int, frame: Any) -> None:
        """Handle pause/resume signal."""
        self.paused = not self.paused
        status = "paused" if self.paused else "resumed"
        self.logger.info(f"Worker {status}")
    
    def _memory_exceeded(self) -> bool:
        """Check if memory limit is exceeded."""
        if self.options.memory_limit <= 0:
            return False
        
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb > self.options.memory_limit
        except ImportError:
            # psutil not available, skip memory check
            return False
    
    def _time_limit_exceeded(self) -> bool:
        """Check if time limit is exceeded."""
        if self.options.max_time <= 0:
            return False
        
        runtime = (datetime.utcnow() - self.start_time).total_seconds()
        return runtime > self.options.max_time
    
    def _job_limit_exceeded(self) -> bool:
        """Check if job limit is exceeded."""
        if self.options.max_jobs <= 0:
            return False
        
        return self.jobs_processed >= self.options.max_jobs
    
    def _sleep(self, seconds: int) -> None:
        """Sleep with signal handling."""
        for _ in range(seconds):
            if self.should_quit:
                break
            time.sleep(1)