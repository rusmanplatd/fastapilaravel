from __future__ import annotations

import json
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TYPE_CHECKING
from datetime import datetime
from dataclasses import dataclass

if TYPE_CHECKING:
    from database.migrations.create_jobs_table import Job as JobModel


@dataclass
class JobOptions:
    """Configuration options for jobs."""
    queue: str = "default"
    connection: str = "default"
    delay: int = 0  # Seconds to delay execution
    priority: int = 0  # Higher numbers = higher priority
    max_attempts: int = 3
    timeout: int = 3600  # Seconds before job times out
    retry_delay: int = 60  # Base seconds before retry
    tags: Optional[List[str]] = None


class ShouldQueue(ABC):
    """
    Base class for queueable jobs similar to Laravel's ShouldQueue interface.
    All jobs that should be queued must inherit from this class.
    """
    
    def __init__(self) -> None:
        self.job_id: Optional[str] = None
        self.attempts: int = 0
        self.options: JobOptions = JobOptions()
    
    @abstractmethod
    def handle(self) -> None:
        """
        Handle the job execution.
        This method must be implemented by all job classes.
        """
        pass
    
    def failed(self, exception: Exception) -> None:
        """
        Handle job failure. Override this method for custom failure logic.
        
        Args:
            exception: The exception that caused the job to fail
        """
        pass
    
    def get_display_name(self) -> str:
        """Get display name for the job."""
        return f"{self.__class__.__module__}.{self.__class__.__name__}"
    
    def get_tags(self) -> List[str]:
        """Get tags for the job. Override for custom tagging."""
        return self.options.tags or []
    
    def serialize(self) -> Dict[str, Any]:
        """
        Serialize job data for storage.
        Override this method if your job has custom data to serialize.
        """
        return {
            "job_class": f"{self.__class__.__module__}.{self.__class__.__name__}",
            "job_method": "handle",
            "data": {},
            "options": {
                "queue": self.options.queue,
                "connection": self.options.connection,
                "delay": self.options.delay,
                "priority": self.options.priority,
                "max_attempts": self.options.max_attempts,
                "timeout": self.options.timeout,
                "retry_delay": self.options.retry_delay,
                "tags": self.get_tags()
            }
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ShouldQueue:
        """
        Deserialize job from stored data.
        Override this method if your job has custom data to deserialize.
        """
        job = cls()
        if "options" in data:
            options_data = data["options"]
            job.options = JobOptions(
                queue=options_data.get("queue", "default"),
                connection=options_data.get("connection", "default"),
                delay=options_data.get("delay", 0),
                priority=options_data.get("priority", 0),
                max_attempts=options_data.get("max_attempts", 3),
                timeout=options_data.get("timeout", 3600),
                retry_delay=options_data.get("retry_delay", 60),
                tags=options_data.get("tags")
            )
        return job
    
    def delay_until(self, delay_seconds: int) -> ShouldQueue:
        """Set delay before job execution."""
        self.options.delay = delay_seconds
        return self
    
    def on_queue(self, queue: str) -> ShouldQueue:
        """Set the queue for job execution."""
        self.options.queue = queue
        return self
    
    def on_connection(self, connection: str) -> ShouldQueue:
        """Set the connection for job execution."""
        self.options.connection = connection
        return self
    
    def with_priority(self, priority: int) -> ShouldQueue:
        """Set job priority."""
        self.options.priority = priority
        return self
    
    def with_tags(self, *tags: str) -> ShouldQueue:
        """Set tags for the job."""
        self.options.tags = list(tags)
        return self


class Dispatchable:
    """
    Mixin class that provides job dispatching capabilities.
    Similar to Laravel's Dispatchable trait.
    """
    
    @classmethod
    def dispatch(cls, *args: Any, **kwargs: Any) -> str:
        """
        Dispatch the job to the queue.
        Returns the job ID.
        """
        from app.Services.QueueService import QueueService
        
        # Create job instance
        job = cls(*args, **kwargs)
        if not isinstance(job, ShouldQueue):
            raise ValueError(f"Job {cls.__name__} must implement ShouldQueue interface")
        
        # Dispatch to queue
        from config.database import get_database
        db = next(get_database())
        queue_service = QueueService(db)
        return queue_service.push(job)
    
    @classmethod
    def dispatch_if(cls, condition: bool, *args: Any, **kwargs: Any) -> Optional[str]:
        """Dispatch job only if condition is true."""
        if condition:
            return cls.dispatch(*args, **kwargs)
        return None
    
    @classmethod
    def dispatch_unless(cls, condition: bool, *args: Any, **kwargs: Any) -> Optional[str]:
        """Dispatch job unless condition is true."""
        if not condition:
            return cls.dispatch(*args, **kwargs)
        return None
    
    @classmethod
    def dispatch_now(cls, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the job immediately without queueing.
        Returns the result of the handle method.
        """
        job = cls(*args, **kwargs)
        if not isinstance(job, ShouldQueue):
            raise ValueError(f"Job {cls.__name__} must implement ShouldQueue interface")
        
        return job.handle()


class Job(ShouldQueue, Dispatchable):
    """
    Base job class combining ShouldQueue interface and Dispatchable mixin.
    This is the main class that user jobs should inherit from.
    """
    pass


class JobException(Exception):
    """Base exception for job-related errors."""
    pass


class JobRetryException(JobException):
    """Exception to trigger job retry with custom delay."""
    
    def __init__(self, message: str = "", delay: int = 0) -> None:
        super().__init__(message)
        self.delay = delay


class JobFailedException(JobException):
    """Exception to mark job as permanently failed."""
    pass