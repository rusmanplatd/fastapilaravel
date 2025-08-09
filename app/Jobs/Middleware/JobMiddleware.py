from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, TYPE_CHECKING, List, Optional
from datetime import datetime, timezone

if TYPE_CHECKING:
    from app.Jobs.Job import ShouldQueue


class JobMiddleware(ABC):
    """
    Abstract base class for job middleware.
    Middleware can intercept job execution for logging, authentication, etc.
    """
    
    @abstractmethod
    def handle(self, job: ShouldQueue, next_handler: Callable[[], Any]) -> Any:
        """
        Handle the job middleware.
        
        Args:
            job: The job being processed
            next_handler: The next middleware or job handler
            
        Returns:
            The result of the next handler
        """
        pass


class LoggingMiddleware(JobMiddleware):
    """
    Middleware that logs job execution details.
    """
    
    def __init__(self, detailed: bool = False) -> None:
        self.detailed = detailed
    
    def handle(self, job: ShouldQueue, next_handler: Callable[[], Any]) -> Any:
        """Log job execution."""
        job_name = job.get_display_name()
        start_time = datetime.now(timezone.utc)
        
        print(f"[{start_time.isoformat()}] Starting job: {job_name}")
        
        if self.detailed:
            print(f"  - Job ID: {getattr(job, 'job_id', 'N/A')}")
            print(f"  - Attempts: {getattr(job, 'attempts', 0)}")
            print(f"  - Queue: {job.options.queue}")
            print(f"  - Priority: {job.options.priority}")
        
        try:
            result = next_handler()
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            print(f"[{end_time.isoformat()}] Completed job: {job_name} ({duration:.2f}s)")
            return result
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            print(f"[{end_time.isoformat()}] Failed job: {job_name} ({duration:.2f}s) - {str(e)}")
            raise


class ThrottleMiddleware(JobMiddleware):
    """
    Middleware that throttles job execution based on rate limits.
    """
    
    def __init__(self, max_attempts: int = 60, decay_seconds: int = 60) -> None:
        self.max_attempts = max_attempts
        self.decay_seconds = decay_seconds
        self._attempts: Dict[str, list[datetime]] = {}
    
    def handle(self, job: ShouldQueue, next_handler: Callable[[], Any]) -> Any:
        """Throttle job execution."""
        key = self._get_throttle_key(job)
        
        if self._should_throttle(key):
            from app.Jobs.Job import JobRetryException
            raise JobRetryException(
                f"Job throttled. Max {self.max_attempts} attempts per {self.decay_seconds}s",
                delay=self.decay_seconds
            )
        
        self._record_attempt(key)
        return next_handler()
    
    def _get_throttle_key(self, job: ShouldQueue) -> str:
        """Generate throttle key for the job."""
        return f"{job.__class__.__module__}.{job.__class__.__name__}"
    
    def _should_throttle(self, key: str) -> bool:
        """Check if job should be throttled."""
        if key not in self._attempts:
            return False
        
        # Clean old attempts
        cutoff = datetime.now(timezone.utc).timestamp() - self.decay_seconds
        self._attempts[key] = [
            attempt for attempt in self._attempts[key]
            if attempt.timestamp() > cutoff
        ]
        
        return len(self._attempts[key]) >= self.max_attempts
    
    def _record_attempt(self, key: str) -> None:
        """Record a job attempt."""
        if key not in self._attempts:
            self._attempts[key] = []
        
        self._attempts[key].append(datetime.now(timezone.utc))


class RetryMiddleware(JobMiddleware):
    """
    Middleware that handles job retry logic with backoff strategies.
    """
    
    def __init__(self, max_attempts: int = 3, backoff_strategy: str = "exponential") -> None:
        self.max_attempts = max_attempts
        self.backoff_strategy = backoff_strategy
    
    def handle(self, job: ShouldQueue, next_handler: Callable[[], Any]) -> Any:
        """Handle job with retry logic."""
        attempts = getattr(job, 'attempts', 0)
        
        try:
            return next_handler()
        except Exception as e:
            if attempts >= self.max_attempts:
                from app.Jobs.Job import JobFailedException
                raise JobFailedException(f"Job failed after {attempts} attempts: {str(e)}")
            
            # Calculate retry delay
            delay = self._calculate_delay(attempts)
            
            from app.Jobs.Job import JobRetryException
            raise JobRetryException(f"Job retry {attempts}/{self.max_attempts}: {str(e)}", delay)
    
    def _calculate_delay(self, attempt: int) -> int:
        """Calculate retry delay based on backoff strategy."""
        if self.backoff_strategy == "exponential":
            return int(min(2 ** attempt * 60, 3600))  # Cap at 1 hour
        elif self.backoff_strategy == "linear":
            return attempt * 60  # Linear increase
        elif self.backoff_strategy == "fixed":
            return 300  # 5 minutes
        else:
            return 60  # Default 1 minute


class AuthenticationMiddleware(JobMiddleware):
    """
    Middleware that validates job permissions and authentication.
    """
    
    def __init__(self, required_permissions: Optional[List[str]] = None) -> None:
        self.required_permissions = required_permissions or []
    
    def handle(self, job: ShouldQueue, next_handler: Callable[[], Any]) -> Any:
        """Validate job authentication."""
        # Check if job has required permissions
        job_permissions = getattr(job, 'permissions', [])
        
        for permission in self.required_permissions:
            if permission not in job_permissions:
                from app.Jobs.Job import JobFailedException
                raise JobFailedException(f"Job missing required permission: {permission}")
        
        return next_handler()


class MemoryLimitMiddleware(JobMiddleware):
    """
    Middleware that monitors memory usage during job execution.
    """
    
    def __init__(self, memory_limit_mb: int = 128) -> None:
        self.memory_limit_mb = memory_limit_mb
    
    def handle(self, job: ShouldQueue, next_handler: Callable[[], Any]) -> Any:
        """Monitor memory usage during job execution."""
        try:
            import psutil
        except ImportError:
            # If psutil not available, skip memory monitoring
            return next_handler()
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = next_handler()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = final_memory - initial_memory
            
            if final_memory > self.memory_limit_mb:
                print(f"Warning: Job {job.get_display_name()} exceeded memory limit: {final_memory:.1f}MB")
            
            return result
            
        except Exception as e:
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            if final_memory > self.memory_limit_mb:
                from app.Jobs.Job import JobFailedException
                raise JobFailedException(f"Job failed due to memory limit exceeded: {final_memory:.1f}MB")
            raise


class MiddlewareStack:
    """
    Manages a stack of middleware for job processing.
    """
    
    def __init__(self) -> None:
        self.middleware: list[JobMiddleware] = []
    
    def add(self, middleware: JobMiddleware) -> MiddlewareStack:
        """Add middleware to the stack."""
        self.middleware.append(middleware)
        return self
    
    def process(self, job: ShouldQueue, handler: Callable[[], Any]) -> Any:
        """Process job through middleware stack."""
        if not self.middleware:
            return handler()
        
        # Create nested middleware chain
        def create_handler(index: int) -> Callable[[], Any]:
            if index >= len(self.middleware):
                return handler
            
            middleware = self.middleware[index]
            next_handler = create_handler(index + 1)
            
            return lambda: middleware.handle(job, next_handler)
        
        return create_handler(0)()