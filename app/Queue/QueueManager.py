from __future__ import annotations

from typing import Dict, Any, Optional, List, TYPE_CHECKING, cast, Union, Callable, Protocol, Literal, overload
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
import time
from datetime import datetime, timedelta
from functools import wraps
import uuid
from contextlib import asynccontextmanager

from app.Jobs.Job import ShouldQueue
from app.Jobs.Middleware import MiddlewareStack
from config.queue import get_connection_config
from app.Support.Types import T, validate_types, TypeConstants
from app.Support.ServiceContainer import container

if TYPE_CHECKING:
    from app.Queue.Worker import QueueWorker


# Laravel 12 Enhanced Queue Configuration
@dataclass
class QueueConfig:
    """Laravel 12 enhanced queue configuration."""
    name: str
    connection: str = "database"
    driver: str = "database"
    max_jobs: int = 0  # 0 = unlimited
    max_time: int = 0  # 0 = unlimited
    memory_limit: int = 128  # MB
    timeout: int = 60  # seconds
    sleep: int = 3  # seconds when idle
    retry_after: int = 3600  # seconds
    max_attempts: int = 3
    max_exceptions: int = 1  # Max exceptions before marking worker as failed
    
    # Priority settings
    priority_weights: Optional[Dict[str, int]] = None
    
    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_max: int = 100
    rate_limit_window: int = 60
    
    # Security settings
    encryption_enabled: bool = False
    signing_enabled: bool = False
    
    # Middleware
    middleware: Optional[List[str]] = None
    
    # Laravel 12 Enhanced Features
    unique_jobs: bool = False
    unique_for: int = 3600  # seconds
    throttle: Optional[Dict[str, int]] = None  # {"max_jobs": 10, "per_seconds": 60}
    batching: bool = False
    batch_size: int = 100
    chain_catch_callbacks: bool = True
    
    # Health monitoring
    health_check_enabled: bool = True
    health_check_interval: int = 300  # 5 minutes
    
    # Scaling
    auto_scaling: bool = False
    min_workers: int = 1
    max_workers: int = 10
    scale_up_threshold: int = 10  # jobs
    scale_down_threshold: int = 2   # jobs
    
    # Dead letter queue
    dlq_enabled: bool = False
    dlq_name: Optional[str] = None
    
    # Metrics
    metrics_enabled: bool = True
    metrics_store: str = "database"
    
    def __post_init__(self) -> None:
        if self.priority_weights is None:
            self.priority_weights = {
                "critical": 100,
                "high": 50, 
                "normal": 0,
                "low": -50
            }
        
        if self.middleware is None:
            self.middleware = []


# Laravel 12 Enhanced Queue Interfaces
class QueueDriver(ABC):
    """Laravel 12 enhanced queue driver interface."""
    
    @abstractmethod
    def push(self, job: ShouldQueue, queue: str = "default") -> str:
        """Push job to queue."""
        pass
    
    @abstractmethod
    def pop(self, queue: str = "default", timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Pop job from queue."""
        pass
    
    @abstractmethod
    def size(self, queue: str = "default") -> int:
        """Get queue size."""
        pass
    
    @abstractmethod
    def clear(self, queue: str = "default") -> int:
        """Clear queue."""
        pass
    
    # Laravel 12 Enhanced Methods
    @abstractmethod
    def delayed_push(self, job: ShouldQueue, delay: Union[int, datetime], queue: str = "default") -> str:
        """Push job with delay."""
        pass
    
    @abstractmethod
    def bulk_push(self, jobs: List[ShouldQueue], queue: str = "default") -> List[str]:
        """Push multiple jobs at once."""
        pass
    
    @abstractmethod
    def peek(self, queue: str = "default", count: int = 1) -> List[Dict[str, Any]]:
        """Peek at jobs without removing them."""
        pass
    
    @abstractmethod
    def release(self, job_id: str, delay: int = 0) -> bool:
        """Release job back to queue."""
        pass
    
    @abstractmethod
    def delete(self, job_id: str) -> bool:
        """Delete job from queue."""
        pass
    
    @abstractmethod
    def get_metrics(self, queue: str = "default") -> Dict[str, Any]:
        """Get queue metrics."""
        pass


class QueueConnection(Protocol):
    """Protocol for queue connections."""
    
    def push(self, job: ShouldQueue, queue: str = "default") -> str:
        ...
    
    def pop(self, queue: str = "default", timeout: int = 10) -> Optional[Dict[str, Any]]:
        ...
    
    def size(self, queue: str = "default") -> int:
        ...


class BatchableJob(Protocol):
    """Protocol for batchable jobs."""
    
    def get_batch_id(self) -> Optional[str]:
        ...
    
    def set_batch_id(self, batch_id: str) -> None:
        ...
    
    def batch_cancelled(self) -> bool:
        ...


class UniqueJob(Protocol):
    """Protocol for unique jobs."""
    
    def unique_id(self) -> str:
        ...
    
    def unique_for(self) -> int:
        ...


# Laravel 12 Queue Features
class JobBatch:
    """Laravel 12 job batch implementation."""
    
    def __init__(self, batch_id: str, name: Optional[str] = None) -> None:
        self.batch_id = batch_id
        self.name = name
        self.jobs: List[str] = []
        self.pending_jobs: int = 0
        self.processed_jobs: int = 0
        self.failed_jobs: int = 0
        self.created_at = datetime.now()
        self.finished_at: Optional[datetime] = None
        self.cancelled_at: Optional[datetime] = None
        self.allow_failures: bool = False
        self.then_callbacks: List[Callable[[], None]] = []
        self.catch_callbacks: List[Callable[[Exception], None]] = []
        self.finally_callbacks: List[Callable[[], None]] = []
    
    def add_job(self, job_id: str) -> None:
        """Add job to batch."""
        self.jobs.append(job_id)
        self.pending_jobs += 1
    
    def job_finished(self, job_id: str, failed: bool = False) -> None:
        """Mark job as finished."""
        if failed:
            self.failed_jobs += 1
        else:
            self.processed_jobs += 1
        
        self.pending_jobs -= 1
        
        if self.pending_jobs <= 0:
            self.finished_at = datetime.now()
    
    def progress(self) -> float:
        """Get batch progress percentage."""
        total = len(self.jobs)
        if total == 0:
            return 100.0
        return (self.processed_jobs / total) * 100.0
    
    def finished(self) -> bool:
        """Check if batch is finished."""
        return self.finished_at is not None
    
    def cancelled(self) -> bool:
        """Check if batch is cancelled."""
        return self.cancelled_at is not None
    
    def cancel(self) -> None:
        """Cancel the batch."""
        self.cancelled_at = datetime.now()
    
    def then(self, callback: Callable[[], None]) -> 'JobBatch':
        """Add success callback."""
        self.then_callbacks.append(callback)
        return self
    
    def catch(self, callback: Callable[[Exception], None]) -> 'JobBatch':
        """Add failure callback."""
        self.catch_callbacks.append(callback)
        return self
    
    def finally_(self, callback: Callable[[], None]) -> 'JobBatch':
        """Add final callback."""
        self.finally_callbacks.append(callback)
        return self


class JobChain:
    """Laravel 12 job chain implementation."""
    
    def __init__(self, chain_id: str) -> None:
        self.chain_id = chain_id
        self.jobs: List[ShouldQueue] = []
        self.current_job_index = 0
        self.failed = False
        self.catch_callbacks: List[Callable[[Exception], None]] = []
    
    def add_job(self, job: ShouldQueue) -> None:
        """Add job to chain."""
        self.jobs.append(job)
    
    def next_job(self) -> Optional[ShouldQueue]:
        """Get next job in chain."""
        if self.current_job_index < len(self.jobs):
            job = self.jobs[self.current_job_index]
            self.current_job_index += 1
            return job
        return None
    
    def job_failed(self, exception: Exception) -> None:
        """Handle job failure in chain."""
        self.failed = True
        for callback in self.catch_callbacks:
            callback(exception)
    
    def catch(self, callback: Callable[[Exception], None]) -> 'JobChain':
        """Add failure callback."""
        self.catch_callbacks.append(callback)
        return self


class QueueMonitor:
    """Laravel 12 queue monitoring."""
    
    def __init__(self) -> None:
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.health_checks: Dict[str, Dict[str, Any]] = {}
        self.last_check: Dict[str, datetime] = {}
    
    def record_job_processed(self, queue: str, success: bool, duration: float) -> None:
        """Record job processing metrics."""
        if queue not in self.metrics:
            self.metrics[queue] = {
                'total_jobs': 0,
                'successful_jobs': 0,
                'failed_jobs': 0,
                'avg_duration': 0.0,
                'last_activity': datetime.now()
            }
        
        metrics = self.metrics[queue]
        metrics['total_jobs'] += 1
        
        if success:
            metrics['successful_jobs'] += 1
        else:
            metrics['failed_jobs'] += 1
        
        # Update average duration
        prev_avg = metrics['avg_duration']
        total = metrics['total_jobs']
        metrics['avg_duration'] = ((prev_avg * (total - 1)) + duration) / total
        metrics['last_activity'] = datetime.now()
    
    def health_check(self, queue: str, driver: QueueDriver) -> Dict[str, Any]:
        """Perform health check on queue."""
        try:
            start_time = time.time()
            size = driver.size(queue)
            response_time = time.time() - start_time
            
            health = {
                'healthy': True,
                'size': size,
                'response_time': response_time,
                'last_check': datetime.now(),
                'errors': []
            }
            
            # Check for issues
            if response_time > 5.0:  # 5 second threshold
                health['errors'].append('Slow response time')
                health['healthy'] = False
            
            if size > 10000:  # Large queue threshold
                health['errors'].append('Large queue size')
                health['healthy'] = False
            
            self.health_checks[queue] = health
            self.last_check[queue] = datetime.now()
            
            return health
            
        except Exception as e:
            health = {
                'healthy': False,
                'error': str(e),
                'last_check': datetime.now()
            }
            self.health_checks[queue] = health
            return health
    
    def get_metrics(self, queue: str) -> Dict[str, Any]:
        """Get metrics for queue."""
        return self.metrics.get(queue, {})
    
    def get_health(self, queue: str) -> Dict[str, Any]:
        """Get health status for queue."""
        return self.health_checks.get(queue, {'healthy': False, 'error': 'No health check performed'})


class DatabaseQueueDriver(QueueDriver):
    """Database-based queue driver."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
    
    def push(self, job: ShouldQueue, queue: str = "default") -> str:
        """Push job to database queue."""
        from app.Services.QueueService import QueueService
        from config.database import get_database
        db = next(get_database())
        queue_service = QueueService(db)
        return queue_service.push(job, queue)
    
    def pop(self, queue: str = "default", timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Pop job from database queue."""
        # Implementation would use database operations
        # This is a simplified version
        return None
    
    def size(self, queue: str = "default") -> int:
        """Get database queue size."""
        from app.Services.QueueService import QueueService
        from config.database import get_database
        db = next(get_database())
        queue_service = QueueService(db)
        return queue_service.size(queue)
    
    def clear(self, queue: str = "default") -> int:
        """Clear database queue."""
        from app.Services.QueueService import QueueService
        from config.database import get_database
        db = next(get_database())
        queue_service = QueueService(db)
        return queue_service.clear_queue(queue)


class RedisQueueDriver(QueueDriver):
    """Redis-based queue driver."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.driver: Optional[QueueDriver] = None
    
    def _get_driver(self) -> QueueDriver:
        """Get Redis driver instance."""
        if self.driver is None:
            from app.Queue.Drivers.RedisDriver import RedisQueueDriver as RedisDriver
            self.driver = cast(QueueDriver, RedisDriver(self.config))
        
        # After assignment, driver is guaranteed to not be None
        assert self.driver is not None
        return self.driver
    
    def push(self, job: ShouldQueue, queue: str = "default") -> str:
        """Push job to Redis queue."""
        return self._get_driver().push(job, queue)
    
    def pop(self, queue: str = "default", timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Pop job from Redis queue."""
        return self._get_driver().pop(queue, timeout)
    
    def size(self, queue: str = "default") -> int:
        """Get Redis queue size."""
        return self._get_driver().size(queue)
    
    def clear(self, queue: str = "default") -> int:
        """Clear Redis queue."""
        return self._get_driver().clear(queue)


class QueueManager:
    """Laravel 12 enhanced queue manager with advanced features."""
    
    def __init__(self) -> None:
        self.queues: Dict[str, QueueConfig] = {}
        self.drivers: Dict[str, QueueDriver] = {}
        self.middleware_stacks: Dict[str, MiddlewareStack] = {}
        
        # Laravel 12 Enhanced Features
        self.batches: Dict[str, JobBatch] = {}
        self.chains: Dict[str, JobChain] = {}
        self.unique_jobs: Dict[str, Dict[str, Any]] = {}  # unique_id -> {job_id, expires_at}
        self.monitor = QueueMonitor()
        self.rate_limiters: Dict[str, Dict[str, Any]] = {}
        self.auto_scalers: Dict[str, 'QueueAutoScaler'] = {}
        
        # Register default drivers
        self._register_default_drivers()
    
    def define_queue(
        self,
        name: str,
        connection: str = "database",
        **config_options: Any
    ) -> QueueConfig:
        """Define a queue with specific configuration."""
        config = QueueConfig(
            name=name,
            connection=connection,
            **config_options
        )
        
        self.queues[name] = config
        
        # Set up middleware stack
        self._setup_middleware_stack(name, config)
        
        return config
    
    def get_queue_config(self, queue: str) -> QueueConfig:
        """Get configuration for a specific queue."""
        if queue in self.queues:
            return self.queues[queue]
        
        # Return default configuration
        return QueueConfig(name=queue)
    
    def get_driver(self, connection: str) -> QueueDriver:
        """Get queue driver for connection."""
        if connection not in self.drivers:
            config = get_connection_config(connection)
            driver_type = config.get("driver", "database")
            
            if driver_type == "database":
                self.drivers[connection] = DatabaseQueueDriver(config)
            elif driver_type == "redis":
                self.drivers[connection] = RedisQueueDriver(config)
            else:
                raise ValueError(f"Unsupported queue driver: {driver_type}")
        
        return self.drivers[connection]
    
    def push(self, job: ShouldQueue, queue: str = "default") -> str:
        """Push job to specific queue with Laravel 12 enhancements."""
        config = self.get_queue_config(queue)
        driver = self.get_driver(config.connection)
        
        # Check for unique jobs
        if config.unique_jobs and hasattr(job, 'unique_id'):
            unique_job = cast(UniqueJob, job)
            unique_id = unique_job.unique_id()
            
            if self._is_unique_job_duplicate(unique_id, config.unique_for):
                return self.unique_jobs[unique_id]['job_id']
            
            job_id = str(uuid.uuid4())
            self.unique_jobs[unique_id] = {
                'job_id': job_id,
                'expires_at': datetime.now() + timedelta(seconds=config.unique_for)
            }
        
        # Apply queue-specific job options
        self._apply_queue_config_to_job(job, config)
        
        # Check rate limiting
        if not self._check_rate_limit(queue, config):
            raise Exception(f"Rate limit exceeded for queue: {queue}")
        
        # Apply middleware
        if queue in self.middleware_stacks:
            middleware_stack = self.middleware_stacks[queue]
            
            def push_job() -> str:
                return driver.push(job, queue)
            
            result = middleware_stack.process(job, push_job)
            return str(result)
        
        return driver.push(job, queue)
    
    def push_on(self, queue: str, job: ShouldQueue) -> str:
        """Push job to specific queue."""
        return self.push(job, queue)
    
    def later(self, delay: Union[int, datetime], job: ShouldQueue, queue: str = "default") -> str:
        """Push job with delay."""
        config = self.get_queue_config(queue)
        driver = self.get_driver(config.connection)
        
        if hasattr(driver, 'delayed_push'):
            return driver.delayed_push(job, delay, queue)
        else:
            # Fallback for drivers that don't support delayed push
            return self.push(job, queue)
    
    def bulk(self, jobs: List[ShouldQueue], queue: str = "default") -> List[str]:
        """Push multiple jobs at once."""
        config = self.get_queue_config(queue)
        driver = self.get_driver(config.connection)
        
        if hasattr(driver, 'bulk_push'):
            return driver.bulk_push(jobs, queue)
        else:
            # Fallback: push jobs individually
            return [self.push(job, queue) for job in jobs]
    
    def _check_rate_limit(self, queue: str, config: QueueConfig) -> bool:
        """Check rate limiting for queue."""
        if not config.throttle:
            return True
        
        current_time = time.time()
        
        if queue not in self.rate_limiters:
            self.rate_limiters[queue] = {
                'requests': [],
                'max_jobs': config.throttle['max_jobs'],
                'per_seconds': config.throttle['per_seconds']
            }
        
        limiter = self.rate_limiters[queue]
        
        # Clean old requests
        cutoff_time = current_time - limiter['per_seconds']
        limiter['requests'] = [req_time for req_time in limiter['requests'] if req_time > cutoff_time]
        
        # Check if under limit
        if len(limiter['requests']) >= limiter['max_jobs']:
            return False
        
        # Add current request
        limiter['requests'].append(current_time)
        return True
    
    def _is_unique_job_duplicate(self, unique_id: str, unique_for: int) -> bool:
        """Check if unique job is duplicate."""
        if unique_id not in self.unique_jobs:
            return False
        
        expires_at = self.unique_jobs[unique_id]['expires_at']
        if datetime.now() > expires_at:
            del self.unique_jobs[unique_id]
            return False
        
        return True
    
    def create_worker_for_queue(self, queue: str) -> QueueWorker:
        """Create a worker configured for specific queue."""
        from app.Queue.Worker import QueueWorker, WorkerOptions
        
        config = self.get_queue_config(queue)
        
        worker_options = WorkerOptions(
            name=f"worker-{queue}",
            connection=config.connection,
            queue=queue,
            max_jobs=config.max_jobs,
            max_time=config.max_time,
            memory_limit=config.memory_limit,
            timeout=config.timeout,
            sleep=config.sleep
        )
        
        return QueueWorker(worker_options)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics for all managed queues."""
        stats = {}
        
        for queue_name, config in self.queues.items():
            driver = self.get_driver(config.connection)
            
            stats[queue_name] = {
                "size": driver.size(queue_name),
                "connection": config.connection,
                "driver": config.driver,
                "config": {
                    "max_attempts": config.max_attempts,
                    "timeout": config.timeout,
                    "memory_limit": config.memory_limit,
                    "rate_limit_enabled": config.rate_limit_enabled
                }
            }
        
        return stats
    
    async def get_queues(self, connection: str = "default") -> List[str]:
        """Get all queue names for a connection."""
        return list(self.queues.keys())
    
    async def failed_count(self, queue: str = "default", connection: str = "default") -> int:
        """Get count of failed jobs."""
        # Placeholder - would need to implement with database
        return 0
    
    async def recent_jobs(self, connection: str = "default", limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent jobs."""
        # Placeholder - would need to implement with database
        return []
    
    async def flush_failed(self) -> int:
        """Delete all failed jobs."""
        # Placeholder - would need to implement with database
        return 0
    
    async def get_failed_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific failed job."""
        # Placeholder - would need to implement with database
        return None
    
    async def get_failed_jobs(self) -> List[Dict[str, Any]]:
        """Get all failed jobs."""
        # Placeholder - would need to implement with database
        return []
    
    async def retry_failed(self, job_id: str) -> bool:
        """Retry a specific failed job."""
        # Placeholder - would need to implement with database
        return False
    
    async def retry_all_failed(self, queue: Optional[str] = None) -> int:
        """Retry all failed jobs."""
        # Placeholder - would need to implement with database
        return 0
    
    async def get_metrics(self, connection: str = "default") -> Dict[str, Any]:
        """Get queue metrics."""
        # Placeholder - would need to implement with database
        return {}
    
    async def clear(self, queue: str = "default", connection: str = "default") -> int:
        """Clear a queue."""
        driver = self.get_driver(connection)
        return driver.clear(queue)
    
    def _register_default_drivers(self) -> None:
        """Register default queue drivers."""
        # Drivers are created on-demand in get_driver()
        pass
    
    def _setup_middleware_stack(self, queue: str, config: QueueConfig) -> None:
        """Set up middleware stack for queue."""
        from app.Jobs.Middleware import (
            LoggingMiddleware,
            ThrottleMiddleware,
            RetryMiddleware,
            MemoryLimitMiddleware
        )
        
        stack = MiddlewareStack()
        
        # Add default middleware
        stack.add(LoggingMiddleware(detailed=True))
        
        if config.rate_limit_enabled:
            stack.add(ThrottleMiddleware(
                max_attempts=config.rate_limit_max,
                decay_seconds=config.rate_limit_window
            ))
        
        stack.add(RetryMiddleware(max_attempts=config.max_attempts))
        stack.add(MemoryLimitMiddleware(memory_limit_mb=config.memory_limit))
        
        # Add custom middleware from configuration
        if config.middleware:
            for middleware_class in config.middleware:
                # In a full implementation, you'd dynamically load middleware classes
                pass
        
        self.middleware_stacks[queue] = stack
    
    def _apply_queue_config_to_job(self, job: ShouldQueue, config: QueueConfig) -> None:
        """Apply queue configuration to job options."""
        if not job.options.max_attempts:
            job.options.max_attempts = config.max_attempts
        
        if not job.options.timeout:
            job.options.timeout = config.timeout


class QueueConfigBuilder:
    """Fluent builder for queue configurations."""
    
    def __init__(self, name: str) -> None:
        self.config = QueueConfig(name=name)
    
    def connection(self, connection: str) -> QueueConfigBuilder:
        """Set connection."""
        self.config.connection = connection
        return self
    
    def driver(self, driver: str) -> QueueConfigBuilder:
        """Set driver."""
        self.config.driver = driver
        return self
    
    def max_jobs(self, max_jobs: int) -> QueueConfigBuilder:
        """Set max jobs."""
        self.config.max_jobs = max_jobs
        return self
    
    def memory_limit(self, memory_mb: int) -> QueueConfigBuilder:
        """Set memory limit."""
        self.config.memory_limit = memory_mb
        return self
    
    def timeout(self, timeout_seconds: int) -> QueueConfigBuilder:
        """Set job timeout."""
        self.config.timeout = timeout_seconds
        return self
    
    def max_attempts(self, attempts: int) -> QueueConfigBuilder:
        """Set max retry attempts."""
        self.config.max_attempts = attempts
        return self
    
    def rate_limit(self, max_attempts: int, window_seconds: int) -> QueueConfigBuilder:
        """Enable rate limiting."""
        self.config.rate_limit_enabled = True
        self.config.rate_limit_max = max_attempts
        self.config.rate_limit_window = window_seconds
        return self
    
    def encryption(self, enabled: bool = True) -> QueueConfigBuilder:
        """Enable encryption."""
        self.config.encryption_enabled = enabled
        return self
    
    def signing(self, enabled: bool = True) -> QueueConfigBuilder:
        """Enable signing."""
        self.config.signing_enabled = enabled
        return self
    
    def middleware(self, *middleware_classes: str) -> QueueConfigBuilder:
        """Add middleware."""
        if self.config.middleware is None:
            self.config.middleware = []
        self.config.middleware.extend(middleware_classes)
        return self
    
    def build(self) -> QueueConfig:
        """Build the configuration."""
        return self.config


class QueueAutoScaler:
    """Laravel 12 auto-scaling for queues."""
    
    def __init__(self, config: QueueConfig) -> None:
        self.config = config
        self.current_workers = config.min_workers
        self.last_scale_action = datetime.now()
        self.scale_cooldown = 60  # seconds
    
    def should_scale_up(self, queue_size: int) -> bool:
        """Check if should scale up workers."""
        if not self.config.auto_scaling:
            return False
        
        if self.current_workers >= self.config.max_workers:
            return False
        
        if queue_size >= self.config.scale_up_threshold:
            cooldown_elapsed = (datetime.now() - self.last_scale_action).total_seconds() >= self.scale_cooldown
            return cooldown_elapsed
        
        return False
    
    def should_scale_down(self, queue_size: int) -> bool:
        """Check if should scale down workers."""
        if not self.config.auto_scaling:
            return False
        
        if self.current_workers <= self.config.min_workers:
            return False
        
        if queue_size <= self.config.scale_down_threshold:
            cooldown_elapsed = (datetime.now() - self.last_scale_action).total_seconds() >= self.scale_cooldown
            return cooldown_elapsed
        
        return False
    
    def scale_up(self) -> None:
        """Scale up workers."""
        if self.current_workers < self.config.max_workers:
            self.current_workers += 1
            self.last_scale_action = datetime.now()
    
    def scale_down(self) -> None:
        """Scale down workers."""
        if self.current_workers > self.config.min_workers:
            self.current_workers -= 1
            self.last_scale_action = datetime.now()


# Laravel 12 Batch Operations
class BatchRepository:
    """Repository for managing job batches."""
    
    def __init__(self) -> None:
        self.batches: Dict[str, JobBatch] = {}
    
    def create_batch(self, name: Optional[str] = None) -> JobBatch:
        """Create new job batch."""
        batch_id = str(uuid.uuid4())
        batch = JobBatch(batch_id, name)
        self.batches[batch_id] = batch
        return batch
    
    def find_batch(self, batch_id: str) -> Optional[JobBatch]:
        """Find batch by ID."""
        return self.batches.get(batch_id)
    
    def store_batch(self, batch: JobBatch) -> None:
        """Store batch."""
        self.batches[batch.batch_id] = batch
    
    def delete_batch(self, batch_id: str) -> bool:
        """Delete batch."""
        if batch_id in self.batches:
            del self.batches[batch_id]
            return True
        return False


# Laravel 12 Chain Operations
class ChainRepository:
    """Repository for managing job chains."""
    
    def __init__(self) -> None:
        self.chains: Dict[str, JobChain] = {}
    
    def create_chain(self, jobs: List[ShouldQueue]) -> JobChain:
        """Create new job chain."""
        chain_id = str(uuid.uuid4())
        chain = JobChain(chain_id)
        
        for job in jobs:
            chain.add_job(job)
        
        self.chains[chain_id] = chain
        return chain
    
    def find_chain(self, chain_id: str) -> Optional[JobChain]:
        """Find chain by ID."""
        return self.chains.get(chain_id)
    
    def store_chain(self, chain: JobChain) -> None:
        """Store chain."""
        self.chains[chain.chain_id] = chain
    
    def delete_chain(self, chain_id: str) -> bool:
        """Delete chain."""
        if chain_id in self.chains:
            del self.chains[chain_id]
            return True
        return False


# Global instances
global_queue_manager = QueueManager()
batch_repository = BatchRepository()
chain_repository = ChainRepository()

# Convenience function for defining queues
def define_queue(name: str, **options: Any) -> QueueConfig:
    """Define a queue with specific configuration."""
    return global_queue_manager.define_queue(name, **options)

# Queue configuration presets
def high_throughput_queue(name: str) -> QueueConfig:
    """Create a high-throughput queue configuration."""
    return (QueueConfigBuilder(name)
            .connection("redis")
            .max_jobs(1000)
            .memory_limit(256)
            .timeout(30)
            .rate_limit(1000, 60)
            .build())

def secure_queue(name: str) -> QueueConfig:
    """Create a secure queue configuration."""
    return (QueueConfigBuilder(name)
            .encryption(True)
            .signing(True)
            .max_attempts(1)  # No retries for security
            .timeout(120)
            .build())

def batch_processing_queue(name: str) -> QueueConfig:
    """Create a batch processing queue configuration."""
    return (QueueConfigBuilder(name)
            .memory_limit(512)
            .timeout(1800)  # 30 minutes
            .max_attempts(1)
            .rate_limit(10, 60)  # Slower rate for heavy jobs
            .build())


# Laravel 12 Queue Helper Functions
@validate_types
def dispatch(job: ShouldQueue, queue: str = "default") -> str:
    """Dispatch job to queue."""
    return global_queue_manager.push(job, queue)


@validate_types
def dispatch_sync(job: ShouldQueue) -> Any:
    """Dispatch job synchronously."""
    return job.handle()


@validate_types
def dispatch_now(job: ShouldQueue) -> Any:
    """Dispatch job immediately."""
    return job.handle()


@validate_types
def dispatch_after(delay: Union[int, datetime], job: ShouldQueue, queue: str = "default") -> str:
    """Dispatch job after delay."""
    return global_queue_manager.later(delay, job, queue)


@validate_types
def dispatch_unless(condition: bool, job: ShouldQueue, queue: str = "default") -> Optional[str]:
    """Dispatch job unless condition is true."""
    if not condition:
        return global_queue_manager.push(job, queue)
    return None


@validate_types
def dispatch_if(condition: bool, job: ShouldQueue, queue: str = "default") -> Optional[str]:
    """Dispatch job if condition is true."""
    if condition:
        return global_queue_manager.push(job, queue)
    return None


def batch(jobs: List[ShouldQueue]) -> 'BatchBuilder':
    """Create job batch."""
    return BatchBuilder(jobs)


def chain(jobs: List[ShouldQueue]) -> 'ChainBuilder':
    """Create job chain."""
    return ChainBuilder(jobs)


class BatchBuilder:
    """Fluent builder for job batches."""
    
    def __init__(self, jobs: List[ShouldQueue]) -> None:
        self.jobs = jobs
        self.batch_name: Optional[str] = None
        self.allow_failures = False
        self.then_callbacks: List[Callable[[], None]] = []
        self.catch_callbacks: List[Callable[[Exception], None]] = []
        self.finally_callbacks: List[Callable[[], None]] = []
    
    def name(self, name: str) -> 'BatchBuilder':
        """Set batch name."""
        self.batch_name = name
        return self
    
    def allow_failures(self, allow: bool = True) -> 'BatchBuilder':
        """Allow failures in batch."""
        self.allow_failures = allow
        return self
    
    def then(self, callback: Callable[[], None]) -> 'BatchBuilder':
        """Add success callback."""
        self.then_callbacks.append(callback)
        return self
    
    def catch(self, callback: Callable[[Exception], None]) -> 'BatchBuilder':
        """Add failure callback."""
        self.catch_callbacks.append(callback)
        return self
    
    def finally_(self, callback: Callable[[], None]) -> 'BatchBuilder':
        """Add final callback."""
        self.finally_callbacks.append(callback)
        return self
    
    def dispatch(self) -> str:
        """Dispatch the batch."""
        batch = batch_repository.create_batch(self.batch_name)
        batch.allow_failures = self.allow_failures
        batch.then_callbacks = self.then_callbacks
        batch.catch_callbacks = self.catch_callbacks
        batch.finally_callbacks = self.finally_callbacks
        
        # Dispatch all jobs
        for job in self.jobs:
            if hasattr(job, 'set_batch_id'):
                batchable_job = cast(BatchableJob, job)
                batchable_job.set_batch_id(batch.batch_id)
            
            job_id = global_queue_manager.push(job)
            batch.add_job(job_id)
        
        batch_repository.store_batch(batch)
        return batch.batch_id


class ChainBuilder:
    """Fluent builder for job chains."""
    
    def __init__(self, jobs: List[ShouldQueue]) -> None:
        self.jobs = jobs
        self.catch_callbacks: List[Callable[[Exception], None]] = []
    
    def catch(self, callback: Callable[[Exception], None]) -> 'ChainBuilder':
        """Add failure callback."""
        self.catch_callbacks.append(callback)
        return self
    
    def dispatch(self) -> str:
        """Dispatch the chain."""
        chain = chain_repository.create_chain(self.jobs)
        chain.catch_callbacks = self.catch_callbacks
        
        # Dispatch first job
        if self.jobs:
            first_job = chain.next_job()
            if first_job:
                global_queue_manager.push(first_job)
        
        chain_repository.store_chain(chain)
        return chain.chain_id


# Laravel 12 Queue Decorators
def queue_job(queue: str = "default", connection: Optional[str] = None, delay: Optional[int] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to queue a function as a job."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> str:
            from app.Jobs.CallableJob import CallableJob
            
            job = CallableJob(func, args, kwargs)
            
            if delay:
                return global_queue_manager.later(delay, job, queue)
            else:
                return global_queue_manager.push(job, queue)
        
        return wrapper
    return decorator


def queue_unique(unique_id: str, unique_for: int = 3600) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for unique job queuing."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[str]:
            # Check if unique job already exists
            if unique_id in global_queue_manager.unique_jobs:
                unique_job = global_queue_manager.unique_jobs[unique_id]
                if datetime.now() < unique_job['expires_at']:
                    return unique_job['job_id']
            
            # Queue new unique job
            from app.Jobs.CallableJob import CallableJob
            job = CallableJob(func, args, kwargs)
            job_id = global_queue_manager.push(job)
            
            # Store unique job reference
            global_queue_manager.unique_jobs[unique_id] = {
                'job_id': job_id,
                'expires_at': datetime.now() + timedelta(seconds=unique_for)
            }
            
            return job_id
        
        return wrapper
    return decorator


# Export Laravel 12 queue functionality
__all__ = [
    'QueueConfig',
    'QueueDriver',
    'QueueConnection',
    'BatchableJob',
    'UniqueJob',
    'JobBatch',
    'JobChain',
    'QueueMonitor',
    'QueueManager',
    'QueueAutoScaler',
    'BatchRepository',
    'ChainRepository',
    'QueueConfigBuilder',
    'BatchBuilder',
    'ChainBuilder',
    'global_queue_manager',
    'batch_repository',
    'chain_repository',
    'dispatch',
    'dispatch_sync',
    'dispatch_now',
    'dispatch_after',
    'dispatch_unless',
    'dispatch_if',
    'batch',
    'chain',
    'queue_job',
    'queue_unique',
    'define_queue',
    'high_throughput_queue',
    'secure_queue',
    'batch_processing_queue',
]