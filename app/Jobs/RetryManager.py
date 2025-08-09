"""
Production-ready Job Retry Manager with Exponential Backoff
"""
from __future__ import annotations

import time
import asyncio
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import math


class RetryStrategy(Enum):
    """Available retry strategies."""
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"
    CUSTOM = "custom"


class BackoffConfig:
    """Configuration for backoff strategies."""
    
    def __init__(
        self,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
        jitter: bool = True,
        max_retries: int = 3
    ) -> None:
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.max_retries = max_retries
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        if self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.multiplier ** (attempt - 1))
        
        elif self.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            base_delay = self.base_delay * (self.multiplier ** (attempt - 1))
            jitter_range = base_delay * 0.1  # 10% jitter
            delay = base_delay + random.uniform(-jitter_range, jitter_range)
        
        else:
            delay = self.base_delay
        
        # Apply jitter if enabled
        if self.jitter and self.strategy != RetryStrategy.EXPONENTIAL_JITTER:
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)
        
        # Cap at max delay
        return min(delay, self.max_delay)


@dataclass
class RetryAttempt:
    """Record of a retry attempt."""
    attempt_number: int
    timestamp: datetime
    delay_seconds: float
    error_message: str
    error_type: str
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryInfo:
    """Information about retry configuration and history."""
    job_id: str
    max_retries: int
    current_attempt: int
    backoff_config: BackoffConfig
    attempts: List[RetryAttempt] = field(default_factory=list)
    last_error: Optional[Exception] = None
    next_retry_at: Optional[datetime] = None
    is_exhausted: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_attempt(self, error: Exception, delay: float) -> None:
        """Add a retry attempt record."""
        import traceback
        
        attempt = RetryAttempt(
            attempt_number=self.current_attempt,
            timestamp=datetime.now(),
            delay_seconds=delay,
            error_message=str(error),
            error_type=type(error).__name__,
            stack_trace=traceback.format_exc()
        )
        
        self.attempts.append(attempt)
        self.last_error = error
        self.next_retry_at = datetime.now() + timedelta(seconds=delay)
    
    def should_retry(self) -> bool:
        """Check if the job should be retried."""
        return (
            not self.is_exhausted and
            self.current_attempt < self.max_retries
        )
    
    def mark_exhausted(self) -> None:
        """Mark retry attempts as exhausted."""
        self.is_exhausted = True
        self.next_retry_at = None


class RetryableException(Exception):
    """Base class for exceptions that should trigger retries."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        max_retries: Optional[int] = None
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.max_retries = max_retries


class NonRetryableException(Exception):
    """Base class for exceptions that should NOT trigger retries."""
    pass


class RetryManager:
    """
    Advanced retry manager with configurable backoff strategies.
    """
    
    def __init__(self) -> None:
        self.retry_records: Dict[str, RetryInfo] = {}
        self.retry_callbacks: Dict[str, List[Callable[..., Any]]] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Default retry configurations for different exception types
        self.exception_configs: Dict[type, BackoffConfig] = {
            ConnectionError: BackoffConfig(
                strategy=RetryStrategy.EXPONENTIAL,
                base_delay=2.0,
                max_delay=60.0,
                max_retries=5
            ),
            TimeoutError: BackoffConfig(
                strategy=RetryStrategy.EXPONENTIAL_JITTER,
                base_delay=1.0,
                max_delay=30.0,
                max_retries=3
            ),
            RetryableException: BackoffConfig(
                strategy=RetryStrategy.EXPONENTIAL,
                base_delay=1.0,
                max_delay=300.0,
                max_retries=3
            )
        }
    
    def register_retry_config(
        self,
        exception_type: type,
        config: BackoffConfig
    ) -> None:
        """Register a retry configuration for a specific exception type."""
        self.exception_configs[exception_type] = config
    
    def get_retry_config(self, exception: Exception) -> BackoffConfig:
        """Get retry configuration for an exception."""
        # Check for custom retry configuration in exception
        if isinstance(exception, RetryableException):
            if exception.max_retries is not None:
                config = BackoffConfig(max_retries=exception.max_retries)
                if exception.retry_after is not None:
                    config.base_delay = exception.retry_after
                return config
        
        # Find matching configuration by exception type
        for exc_type, config in self.exception_configs.items():
            if isinstance(exception, exc_type):
                return config
        
        # Default configuration
        return BackoffConfig()
    
    def should_retry(self, job_id: str, exception: Exception) -> bool:
        """Determine if a job should be retried."""
        # Non-retryable exceptions are never retried
        if isinstance(exception, NonRetryableException):
            return False
        
        with self._lock:
            retry_info = self.retry_records.get(job_id)
            
            if retry_info is None:
                # First failure - create retry record
                config = self.get_retry_config(exception)
                retry_info = RetryInfo(
                    job_id=job_id,
                    max_retries=config.max_retries,
                    current_attempt=1,
                    backoff_config=config
                )
                self.retry_records[job_id] = retry_info
                return config.max_retries > 0
            
            return retry_info.should_retry()
    
    def schedule_retry(
        self,
        job_id: str,
        exception: Exception,
        retry_callback: Optional[Callable[..., Any]] = None
    ) -> Optional[float]:
        """
        Schedule a retry for a failed job.
        
        Returns:
            float: Delay in seconds until retry, or None if no retry scheduled
        """
        with self._lock:
            if not self.should_retry(job_id, exception):
                return None
            
            retry_info = self.retry_records[job_id]
            
            # Calculate delay for this attempt
            delay = retry_info.backoff_config.calculate_delay(retry_info.current_attempt)
            
            # Record the attempt
            retry_info.add_attempt(exception, delay)
            
            # Increment attempt counter
            retry_info.current_attempt += 1
            
            # Check if this was the last retry
            if retry_info.current_attempt > retry_info.max_retries:
                retry_info.mark_exhausted()
                self.logger.warning(
                    f"Job {job_id} exhausted all {retry_info.max_retries} retry attempts"
                )
                return None
            
            # Register retry callback if provided
            if retry_callback:
                if job_id not in self.retry_callbacks:
                    self.retry_callbacks[job_id] = []
                self.retry_callbacks[job_id].append(retry_callback)
            
            self.logger.info(
                f"Scheduled retry {retry_info.current_attempt}/{retry_info.max_retries} "
                f"for job {job_id} in {delay:.2f} seconds"
            )
            
            return delay
    
    def execute_with_retry(
        self,
        job_id: str,
        job_func: Callable[..., Any],
        *args: Any,
        config: Optional[BackoffConfig] = None,
        **kwargs: Any
    ) -> Any:
        """
        Execute a function with automatic retry logic.
        
        Args:
            job_id: Unique identifier for the job
            job_func: Function to execute
            *args: Arguments for the function
            config: Custom retry configuration
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: Result of the function execution
            
        Raises:
            Exception: The last exception if all retries are exhausted
        """
        if config:
            retry_info = RetryInfo(
                job_id=job_id,
                max_retries=config.max_retries,
                current_attempt=1,
                backoff_config=config
            )
            self.retry_records[job_id] = retry_info
        
        attempt = 1
        last_exception = None
        
        while True:
            try:
                result = job_func(*args, **kwargs)
                
                # Success - clean up retry record
                with self._lock:
                    if job_id in self.retry_records:
                        del self.retry_records[job_id]
                    if job_id in self.retry_callbacks:
                        del self.retry_callbacks[job_id]
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                delay = self.schedule_retry(job_id, e)
                
                if delay is None:
                    # No more retries
                    break
                
                # Wait before retry
                self.logger.info(f"Retrying job {job_id} in {delay:.2f} seconds")
                time.sleep(delay)
                attempt += 1
        
        # All retries exhausted
        self.logger.error(f"Job {job_id} failed after all retry attempts")
        if last_exception:
            raise last_exception
    
    async def execute_with_retry_async(
        self,
        job_id: str,
        job_func: Callable[..., Any],
        *args: Any,
        config: Optional[BackoffConfig] = None,
        **kwargs: Any
    ) -> Any:
        """
        Async version of execute_with_retry.
        """
        if config:
            retry_info = RetryInfo(
                job_id=job_id,
                max_retries=config.max_retries,
                current_attempt=1,
                backoff_config=config
            )
            self.retry_records[job_id] = retry_info
        
        attempt = 1
        last_exception = None
        
        while True:
            try:
                if asyncio.iscoroutinefunction(job_func):
                    result = await job_func(*args, **kwargs)
                else:
                    result = job_func(*args, **kwargs)
                
                # Success - clean up retry record
                with self._lock:
                    if job_id in self.retry_records:
                        del self.retry_records[job_id]
                    if job_id in self.retry_callbacks:
                        del self.retry_callbacks[job_id]
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                delay = self.schedule_retry(job_id, e)
                
                if delay is None:
                    # No more retries
                    break
                
                # Wait before retry
                self.logger.info(f"Retrying async job {job_id} in {delay:.2f} seconds")
                await asyncio.sleep(delay)
                attempt += 1
        
        # All retries exhausted
        self.logger.error(f"Async job {job_id} failed after all retry attempts")
        if last_exception:
            raise last_exception
    
    def get_retry_info(self, job_id: str) -> Optional[RetryInfo]:
        """Get retry information for a job."""
        with self._lock:
            return self.retry_records.get(job_id)
    
    def get_all_retry_info(self) -> Dict[str, RetryInfo]:
        """Get retry information for all jobs."""
        with self._lock:
            return dict(self.retry_records)
    
    def clear_retry_record(self, job_id: str) -> bool:
        """Clear retry record for a job."""
        with self._lock:
            if job_id in self.retry_records:
                del self.retry_records[job_id]
                if job_id in self.retry_callbacks:
                    del self.retry_callbacks[job_id]
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retry manager statistics."""
        with self._lock:
            total_jobs = len(self.retry_records)
            exhausted_jobs = sum(1 for info in self.retry_records.values() if info.is_exhausted)
            pending_retries = sum(1 for info in self.retry_records.values() if not info.is_exhausted)
            
            # Calculate average retry attempts
            total_attempts = sum(len(info.attempts) for info in self.retry_records.values())
            avg_attempts = total_attempts / total_jobs if total_jobs > 0 else 0
            
            return {
                "total_jobs": total_jobs,
                "exhausted_jobs": exhausted_jobs,
                "pending_retries": pending_retries,
                "average_attempts": round(avg_attempts, 2),
                "registered_configs": len(self.exception_configs)
            }


# Global retry manager instance
_retry_manager: Optional[RetryManager] = None


def get_retry_manager() -> RetryManager:
    """Get the global retry manager instance."""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = RetryManager()
    return _retry_manager


# Convenience decorators
def retry(
    max_retries: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 300.0,
    multiplier: float = 2.0,
    jitter: bool = True
) -> Callable[..., Any]:
    """
    Decorator for automatic retry with backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        strategy: Backoff strategy to use
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        multiplier: Backoff multiplier for exponential strategies
        jitter: Whether to add jitter to delays
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BackoffConfig(
                strategy=strategy,
                base_delay=base_delay,
                max_delay=max_delay,
                multiplier=multiplier,
                jitter=jitter,
                max_retries=max_retries
            )
            
            job_id = f"{func.__name__}_{id(func)}"
            retry_manager = get_retry_manager()
            
            return retry_manager.execute_with_retry(job_id, func, *args, config=config, **kwargs)
        
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BackoffConfig(
                strategy=strategy,
                base_delay=base_delay,
                max_delay=max_delay,
                multiplier=multiplier,
                jitter=jitter,
                max_retries=max_retries
            )
            
            job_id = f"{func.__name__}_{id(func)}"
            retry_manager = get_retry_manager()
            
            return await retry_manager.execute_with_retry_async(job_id, func, *args, config=config, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator