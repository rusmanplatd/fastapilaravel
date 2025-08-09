from __future__ import annotations

import json
import traceback
import uuid
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TYPE_CHECKING, Union, Callable, TypeVar, Protocol, runtime_checkable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import inspect

if TYPE_CHECKING:
    from app.Models.Job import Job as JobModel

T = TypeVar('T', bound='ShouldQueue')


# Laravel 12 Job States
class JobState(Enum):
    """Laravel 12 job states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# Laravel 12 Job Interfaces
@runtime_checkable
class ShouldBeUnique(Protocol):
    """Laravel 12 interface for unique jobs."""
    
    def uniqueId(self) -> str:
        """Return a unique identifier for this job."""
        ...
    
    def uniqueFor(self) -> timedelta:
        """Return how long the job should remain unique."""
        ...


@runtime_checkable
class ShouldBeEncrypted(Protocol):
    """Laravel 12 interface for encrypted jobs."""
    pass


@runtime_checkable  
class ShouldBeUniqueUntilProcessing(Protocol):
    """Laravel 12 interface for jobs unique until processing."""
    pass


@runtime_checkable
class Batchable(Protocol):
    """Laravel 12 interface for batchable jobs."""
    
    def batch(self) -> Optional['JobBatch']:
        """Get the batch this job belongs to."""
        ...
    
    def withBatch(self, batch: 'JobBatch') -> 'ShouldQueue':
        """Set the batch for this job."""
        ...


@runtime_checkable
class Chainable(Protocol):
    """Laravel 12 interface for chainable jobs."""
    
    def chain(self) -> Optional['JobChain']:
        """Get the chain this job belongs to."""
        ...
    
    def withChain(self, chain: 'JobChain') -> 'ShouldQueue':
        """Set the chain for this job."""
        ...


# Laravel 12 Enhanced Job Options
@dataclass
class JobOptions:
    """Laravel 12 enhanced configuration options for jobs."""
    queue: str = "default"
    connection: str = "default"
    delay: int = 0  # Seconds to delay execution
    priority: int = 0  # Higher numbers = higher priority
    max_attempts: int = 3
    timeout: int = 3600  # Seconds before job times out
    retry_delay: int = 60  # Base seconds before retry
    tags: Optional[List[str]] = None
    
    # Laravel 12 new options
    unique_id: Optional[str] = None
    unique_for: Optional[timedelta] = None
    unique_until_processing: bool = False
    encrypted: bool = False
    middleware: List[str] = field(default_factory=list)
    after_commit: bool = False
    
    # Batching and chaining
    batch_id: Optional[str] = None
    chain_id: Optional[str] = None
    chain_index: int = 0
    
    # Enhanced retry options
    retry_until: Optional[datetime] = None
    backoff: List[int] = field(default_factory=list)  # Custom backoff strategy
    max_exceptions: Optional[int] = None


class ShouldQueue(ABC):
    """
    Laravel 12 enhanced base class for queueable jobs.
    All jobs that should be queued must inherit from this class.
    """
    
    def __init__(self) -> None:
        self.job_id: Optional[str] = None
        self.attempts: int = 0
        self.options: JobOptions = JobOptions()
        
        # Laravel 12 enhanced properties
        self.state: JobState = JobState.PENDING
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.exception_count: int = 0
        self.last_exception: Optional[str] = None
        
        # Job relationships
        self._batch: Optional['JobBatch'] = None
        self._chain: Optional['JobChain'] = None
        
        # Middleware and callbacks
        self._middleware: List[Any] = []
        self._before_callbacks: List[Callable[[], None]] = []
        self._after_callbacks: List[Callable[[], None]] = []
        self._progress_callbacks: List[Callable[[int, int], None]] = []
    
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
    
    # Laravel 12 Enhanced Methods
    def markAsStarted(self) -> None:
        """Mark job as started (Laravel 12)."""
        self.state = JobState.PROCESSING
        self.started_at = datetime.now()
    
    def markAsCompleted(self) -> None:
        """Mark job as completed (Laravel 12)."""
        self.state = JobState.COMPLETED
        self.finished_at = datetime.now()
    
    def markAsFailed(self, exception: Exception) -> None:
        """Mark job as failed (Laravel 12)."""
        self.state = JobState.FAILED
        self.finished_at = datetime.now()
        self.exception_count += 1
        self.last_exception = str(exception)
    
    def markAsRetrying(self) -> None:
        """Mark job as retrying (Laravel 12)."""
        self.state = JobState.RETRYING
        self.attempts += 1
    
    def shouldRetry(self, exception: Exception) -> bool:
        """Determine if job should be retried (Laravel 12)."""
        # Check max attempts
        if self.attempts >= self.options.max_attempts:
            return False
        
        # Check retry until time
        if self.options.retry_until and datetime.now() > self.options.retry_until:
            return False
        
        # Check max exceptions
        if self.options.max_exceptions and self.exception_count >= self.options.max_exceptions:
            return False
        
        return True
    
    def getRetryDelay(self) -> int:
        """Get retry delay with backoff strategy (Laravel 12)."""
        if self.options.backoff:
            # Use custom backoff strategy
            index = min(self.attempts - 1, len(self.options.backoff) - 1)
            return self.options.backoff[index] if index >= 0 else self.options.retry_delay
        
        # Default exponential backoff
        return self.options.retry_delay * (2 ** (self.attempts - 1))
    
    def progress(self, current: int, total: int) -> None:
        """Update job progress (Laravel 12)."""
        for callback in self._progress_callbacks:
            try:
                callback(current, total)
            except Exception:
                pass  # Don't fail job for progress callback errors
    
    def setProgress(self, current: int, total: int) -> 'ShouldQueue':
        """Set job progress fluently (Laravel 12)."""
        self.progress(current, total)
        return self
    
    # Laravel 12 Unique Job Methods
    def getUniqueId(self) -> str:
        """Get unique ID for job."""
        if isinstance(self, ShouldBeUnique):
            return self.uniqueId()
        
        # Generate unique ID based on class and job data
        job_data = json.dumps(self.serialize(), sort_keys=True)
        return hashlib.md5(job_data.encode()).hexdigest()
    
    def getUniqueFor(self) -> timedelta:
        """Get unique duration."""
        if isinstance(self, ShouldBeUnique):
            return self.uniqueFor()
        
        return timedelta(minutes=5)  # Default 5 minutes
    
    def shouldBeUnique(self) -> bool:
        """Check if job should be unique."""
        return isinstance(self, (ShouldBeUnique, ShouldBeUniqueUntilProcessing))
    
    def shouldBeEncrypted(self) -> bool:
        """Check if job should be encrypted."""
        return isinstance(self, ShouldBeEncrypted) or self.options.encrypted
    
    # Laravel 12 Middleware Methods
    def through(self, *middleware: Any) -> 'ShouldQueue':
        """Add middleware to job (Laravel 12)."""
        self._middleware.extend(middleware)
        self.options.middleware.extend([str(m) for m in middleware])
        return self
    
    def withMiddleware(self, middleware: List[Any]) -> 'ShouldQueue':
        """Set job middleware (Laravel 12)."""
        self._middleware = middleware
        self.options.middleware = [str(m) for m in middleware]
        return self
    
    def middleware(self) -> List[Any]:
        """Get job middleware (Laravel 12)."""
        return self._middleware.copy()
    
    # Laravel 12 Callback Methods
    def before(self, callback: Callable[[], None]) -> 'ShouldQueue':
        """Add before callback (Laravel 12)."""
        self._before_callbacks.append(callback)
        return self
    
    def after(self, callback: Callable[[], None]) -> 'ShouldQueue':
        """Add after callback (Laravel 12)."""
        self._after_callbacks.append(callback)
        return self
    
    def onProgress(self, callback: Callable[[int, int], None]) -> 'ShouldQueue':
        """Add progress callback (Laravel 12)."""
        self._progress_callbacks.append(callback)
        return self
    
    def runBeforeCallbacks(self) -> None:
        """Run before callbacks."""
        for callback in self._before_callbacks:
            try:
                callback()
            except Exception:
                pass  # Don't fail job for callback errors
    
    def runAfterCallbacks(self) -> None:
        """Run after callbacks."""
        for callback in self._after_callbacks:
            try:
                callback()
            except Exception:
                pass  # Don't fail job for callback errors
    
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