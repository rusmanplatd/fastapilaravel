from __future__ import annotations

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
from abc import ABC, abstractmethod

from app.Jobs.Job import ShouldQueue
from app.Jobs.Middleware import MiddlewareStack
from config.queue import get_connection_config

if TYPE_CHECKING:
    from app.Queue.Worker import QueueWorker


@dataclass
class QueueConfig:
    """Configuration for a specific queue."""
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
    priority_weights: Dict[str, int] = None
    
    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_max: int = 100
    rate_limit_window: int = 60
    
    # Security settings
    encryption_enabled: bool = False
    signing_enabled: bool = False
    
    # Middleware
    middleware: List[str] = None
    
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


class QueueDriver(ABC):
    """Abstract base class for queue drivers."""
    
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


class DatabaseQueueDriver(QueueDriver):
    """Database-based queue driver."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
    
    def push(self, job: ShouldQueue, queue: str = "default") -> str:
        """Push job to database queue."""
        from app.Services.QueueService import QueueService
        queue_service = QueueService()
        return queue_service.push(job, queue)
    
    def pop(self, queue: str = "default", timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Pop job from database queue."""
        # Implementation would use database operations
        # This is a simplified version
        return None
    
    def size(self, queue: str = "default") -> int:
        """Get database queue size."""
        from app.Services.QueueService import QueueService
        queue_service = QueueService()
        return queue_service.size(queue)
    
    def clear(self, queue: str = "default") -> int:
        """Clear database queue."""
        from app.Services.QueueService import QueueService
        queue_service = QueueService()
        return queue_service.clear_queue(queue)


class RedisQueueDriver(QueueDriver):
    """Redis-based queue driver."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.driver = None
    
    def _get_driver(self):
        """Get Redis driver instance."""
        if self.driver is None:
            from app.Queue.Drivers.RedisDriver import RedisQueueDriver
            self.driver = RedisQueueDriver(self.config)
        return self.driver
    
    def push(self, job: ShouldQueue, queue: str = "default") -> str:
        """Push job to Redis queue."""
        return self._get_driver().push(job, queue)
    
    def pop(self, queue: str = "default", timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Pop job from Redis queue."""
        return self._get_driver().pop(queue, timeout)
    
    def size(self, queue: str = "default") -> int:
        """Get Redis queue size."""
        return self._get_driver().get_queue_size(queue)
    
    def clear(self, queue: str = "default") -> int:
        """Clear Redis queue."""
        return self._get_driver().clear_queue(queue)


class QueueManager:
    """
    Advanced queue manager with per-queue configurations.
    """
    
    def __init__(self) -> None:
        self.queues: Dict[str, QueueConfig] = {}
        self.drivers: Dict[str, QueueDriver] = {}
        self.middleware_stacks: Dict[str, MiddlewareStack] = {}
        
        # Register default drivers
        self._register_default_drivers()
    
    def define_queue(
        self,
        name: str,
        connection: str = "database",
        **config_options
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
        """Push job to specific queue with its configuration."""
        config = self.get_queue_config(queue)
        driver = self.get_driver(config.connection)
        
        # Apply queue-specific job options
        self._apply_queue_config_to_job(job, config)
        
        # Apply middleware
        if queue in self.middleware_stacks:
            middleware_stack = self.middleware_stacks[queue]
            
            def push_job():
                return driver.push(job, queue)
            
            return middleware_stack.process(job, push_job)
        
        return driver.push(job, queue)
    
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
        self.config.middleware.extend(middleware_classes)
        return self
    
    def build(self) -> QueueConfig:
        """Build the configuration."""
        return self.config


# Global queue manager instance
global_queue_manager = QueueManager()

# Convenience function for defining queues
def define_queue(name: str, **options) -> QueueConfig:
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